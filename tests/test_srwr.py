"""Tests for the SRWR Open Data provider.

Fixture lines are taken from real published (redacted) extract data, lightly
trimmed. The fixture reproduces the real files' structure: a 000 licensing
header per daily section, records sorted by Record Type within a section.
"""

import io
from datetime import datetime

import httpx
import pytest
import respx

from streetworks.srwr import (
    SRWRClient,
    describe,
    iter_activities,
    iter_records,
    latest_activities,
)

HEADER = (
    '02,000,"#SRWR data for 2026-07-04, Produced 2026-07-05 02:00, '
    'For licensing visit https://roadworks.scot/opendata"'
)
ACTIVITY_A = (
    '02,001,03268777,2022-12-09 09:13:35.08,2026-07-04 04:20:09.72,'
    '010360002,"TL002-S1711",009066001,02,"False",,2,84202034,"False"'
)
ACTIVITY_B = (
    '02,001,03889647,2025-09-03 10:03:03.88,2026-07-04 04:12:28.06,'
    '010250001,"EG001-FULMAR2",009066001,02,"False",,1,84202352,"False"'
)
STREET_A = '02,004,03268777,"False","84202034","B9157 Main Road"'
PHASE_A = (
    '02,007,03268777,2022-12-09 09:13:35.08,2026-07-04 04:20:09.72,,'
    '"Outside Crossgates Cottages",2,,05,07,"False",'
    '"LINESTRING (333226.5 709261.7, 333285.0 709270.1)",03,07,"False","False",'
    '"False","False","False","False","False","False",'
    '"True","False","False","False","False","False"'
)
NOTICE_A = (
    '02,006,03268777,010360002,2,38,2022-12-09 09:13:35.08,'
    '"Revised duration",,1,"False",3,,,2022-12-12 08:00:00.00,2022-12-16 17:00:00.00'
)

SECTION_1 = "\r\n".join([HEADER, ACTIVITY_A, ACTIVITY_B, STREET_A, NOTICE_A, PHASE_A])
# A later daily section updating only Activity A (new phase status: Closed -> Cleared)
PHASE_A2 = PHASE_A.replace(",05,07,", ",05,06,")
SECTION_2 = "\r\n".join([HEADER, ACTIVITY_A, PHASE_A2])
MONTHLY = SECTION_1 + "\r\n" + SECTION_2 + "\r\n"


def test_parses_real_activity_record():
    records = list(iter_records(io.StringIO(SECTION_1)))
    assert [r.record_type for r in records] == ["000", "001", "001", "004", "006", "007"]
    act = records[1]
    assert act.activity_id == 3268777
    assert act.activity_reference == "TL002-S1711"
    assert act.usrn == 84202034
    assert act.created == datetime(2022, 12, 9, 9, 13, 35, 80000)
    assert act.is_archive_ready is False
    assert act.archive_relevant_date is None  # empty field -> None


def test_quoted_fields_with_commas_survive():
    phase = next(iter_records(io.StringIO(SECTION_1), record_types=["007"]))
    assert "333226.5 709261.7, 333285.0" in phase.geometry
    assert phase.works_type == "05"
    assert phase.street_traffic_sensitive is True


def test_record_type_filter():
    only = list(iter_records(io.StringIO(SECTION_1), record_types=["001"]))
    assert len(only) == 2
    assert all(r.record_type == "001" for r in only)


def test_unknown_field_raises_helpfully():
    record = next(iter_records(io.StringIO(SECTION_1), record_types=["001"]))
    with pytest.raises(AttributeError, match="Activity"):
        _ = record.nonexistent_field


def test_groups_type_sorted_sections_into_activities():
    activities = {a.activity_id: a for a in iter_activities(io.StringIO(SECTION_1))}
    assert set(activities) == {3268777, 3889647}
    a = activities[3268777]
    # Records of different types, non-contiguous in the file, same bundle:
    assert a.activity is not None
    assert len(a.streets) == 1 and len(a.notices) == 1 and len(a.phases) == 1
    assert activities[3889647].phases == []


def test_latest_wins_across_daily_sections():
    latest = {a.activity_id: a for a in latest_activities(io.StringIO(MONTHLY))}
    assert set(latest) == {3268777, 3889647}
    # Activity A's newer section (status 06 Cleared) supersedes the older (07 Closed)
    assert latest[3268777].phases[-1].activity_status == "06"
    # Activity B only appeared in section 1 and is retained
    assert latest[3889647].activity.activity_reference == "EG001-FULMAR2"


def test_describe_tolerates_unpadded_codes():
    assert describe("notice_type", "05") == "Cancellation"
    assert describe("notice_type", "5") == "Cancellation"  # real data is unpadded
    assert describe("works_type", "04") == "Major"
    assert describe("activity_status", 6) == "Cleared"
    assert describe("works_type", None) is None
    assert describe("works_type", "999") == "999"  # unknown codes pass through


@respx.mock
def test_client_downloads_daily(tmp_path):
    respx.get("https://downloads.srwr.scot/export/daily").mock(
        return_value=httpx.Response(200, content=b"PK\x03\x04fakezip")
    )
    with SRWRClient() as srwr:
        path = srwr.download_daily(tmp_path / "daily.zip")
    assert path.read_bytes().startswith(b"PK")


@respx.mock
def test_client_retries_transient_lockout(tmp_path):
    """The spec warns archives are transiently unavailable during roll-up."""
    route = respx.get("https://downloads.srwr.scot/export/04.zip").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, content=b"PK\x03\x04ok"),
        ]
    )
    with SRWRClient() as srwr:
        path = srwr.download_archive("04.zip", tmp_path / "04.zip")
    assert route.call_count == 2
    assert path.read_bytes().endswith(b"ok")


@respx.mock
def test_client_follows_redirect(tmp_path):
    """The export host 301s (e.g. /daily -> /daily/); the client must follow."""
    respx.get("https://downloads.srwr.scot/export/daily").mock(
        return_value=httpx.Response(
            301, headers={"location": "https://downloads.srwr.scot/export/daily/"}
        )
    )
    respx.get("https://downloads.srwr.scot/export/daily/").mock(
        return_value=httpx.Response(200, content=b"PK\x03\x04real")
    )
    with SRWRClient() as srwr:
        path = srwr.download_daily(tmp_path / "d.zip")
    assert path.read_bytes().endswith(b"real")


@respx.mock
def test_client_rejects_html_file_listing(tmp_path):
    respx.get("https://downloads.srwr.scot/export/daily").mock(
        return_value=httpx.Response(200, content=b"<!DOCTYPE html><html>File List")
    )
    with SRWRClient() as srwr:
        with pytest.raises(ValueError, match="HTML page, not an archive"):
            srwr.download_daily(tmp_path / "d.zip")
