"""Tests for streetworks.opendata.archive.

Fixtures are real, cut 2026-10-28 from the live archive: two pages of the
public bucket listing (``prefix=section_58/``, the first page capped at two
keys), and small zips of real events - two per event type from the
2026/09 ``activity`` and ``section_58`` files, one per event type from the
2026/09 ``permit`` file (read over HTTP ranges, not downloaded whole). Member
names and bytes are DfT's; only the zip around them is rebuilt.
"""

import hashlib
import shutil
import zipfile
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.exceptions import NotFoundError, TransportError
from streetworks.opendata import EventNotification
from streetworks.opendata.archive import (
    BASE_URL,
    ArchiveClient,
    ReadStats,
    Topic,
    iter_events,
)

FIXTURES = Path(__file__).parent / "fixtures"
PERMIT = FIXTURES / "streetmanager_archive_permit_2026-09_sample.zip"
ACTIVITY = FIXTURES / "streetmanager_archive_activity_2026-09_sample.zip"
SECTION_58 = FIXTURES / "streetmanager_archive_section_58_2026-09_sample.zip"
S58_URL = f"{BASE_URL}/section_58/2026/09.zip"


def _etag(content: bytes) -> str:
    return f'"{hashlib.md5(content).hexdigest()}"'


def _head(content: bytes, etag: str | None = None) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-length": str(len(content)), "etag": etag or _etag(content)},
    )


# --- ArchiveClient ----------------------------------------------------------


def test_url_is_built_without_io():
    with ArchiveClient() as arc:
        assert arc.url(Topic.PERMIT, 2026, 9) == f"{BASE_URL}/permit/2026/09.zip"
        assert arc.url("section_58", 2022, 3) == f"{BASE_URL}/section_58/2022/03.zip"
        with pytest.raises(ValueError):
            arc.url(Topic.PERMIT, 2026, 13)


@respx.mock
def test_available_is_false_for_an_unpublished_month():
    respx.head(f"{BASE_URL}/permit/2026/09.zip").mock(return_value=httpx.Response(200))
    respx.head(f"{BASE_URL}/permit/2026/12.zip").mock(return_value=httpx.Response(404))
    with ArchiveClient() as arc:
        assert arc.available(Topic.PERMIT, 2026, 9) is True
        assert arc.available(Topic.PERMIT, 2026, 12) is False


@respx.mock
def test_files_follows_the_listing_continuation_token():
    page1 = (FIXTURES / "streetmanager_archive_listing_page1.xml").read_bytes()
    page2 = (FIXTURES / "streetmanager_archive_listing_page2.xml").read_bytes()
    route = respx.get(f"{BASE_URL}/").mock(
        side_effect=[httpx.Response(200, content=page1), httpx.Response(200, content=page2)]
    )
    with ArchiveClient() as arc:
        files = arc.files(Topic.SECTION_58)

    assert route.calls[0].request.url.params["prefix"] == "section_58/"
    assert "continuation-token" not in route.calls[0].request.url.params
    assert route.calls[1].request.url.params["continuation-token"].startswith("1i9EeqEmy3")
    assert len(files) == 55
    first, last = files[0], files[-1]
    assert (first.topic, first.year, first.month) == (Topic.SECTION_58, 2022, 3)
    assert (last.year, last.month, last.size) == (2026, 9, 3089473)
    assert last.etag == '"5427bb520282cd020dbd5891d984e07b"'
    assert last.url == S58_URL


@respx.mock
def test_download_streams_to_dest_and_verifies_the_etag(tmp_path):
    content = SECTION_58.read_bytes()
    respx.head(S58_URL).mock(return_value=_head(content))
    respx.get(S58_URL).mock(return_value=httpx.Response(200, content=content))
    with ArchiveClient() as arc:
        path = arc.download(Topic.SECTION_58, 2026, 9, tmp_path / "sm" / "s58.zip")
    assert path.read_bytes() == content
    assert not list(tmp_path.rglob("*.part"))


@respx.mock
def test_download_resumes_a_part_file_with_a_range_request(tmp_path):
    content = SECTION_58.read_bytes()
    dest = tmp_path / "s58.zip"
    (tmp_path / "s58.zip.part").write_bytes(content[:1000])
    respx.head(S58_URL).mock(return_value=_head(content))
    route = respx.get(S58_URL).mock(return_value=httpx.Response(206, content=content[1000:]))
    with ArchiveClient() as arc:
        arc.download(Topic.SECTION_58, 2026, 9, dest)
    assert route.calls[0].request.headers["range"] == "bytes=1000-"
    assert route.calls[0].request.headers["if-range"] == _etag(content)
    assert dest.read_bytes() == content


@respx.mock
def test_download_starts_over_when_the_server_sends_the_whole_file(tmp_path):
    content = SECTION_58.read_bytes()
    dest = tmp_path / "s58.zip"
    (tmp_path / "s58.zip.part").write_bytes(b"x" * 1000)
    respx.head(S58_URL).mock(return_value=_head(content))
    respx.get(S58_URL).mock(return_value=httpx.Response(200, content=content))
    with ArchiveClient() as arc:
        arc.download(Topic.SECTION_58, 2026, 9, dest)
    assert dest.read_bytes() == content


@respx.mock
def test_download_restarts_once_when_a_resumed_part_was_from_another_copy(tmp_path):
    content = SECTION_58.read_bytes()
    dest = tmp_path / "s58.zip"
    (tmp_path / "s58.zip.part").write_bytes(b"x" * 1000)  # same server, older file
    respx.head(S58_URL).mock(return_value=_head(content))
    route = respx.get(S58_URL).mock(
        side_effect=[
            httpx.Response(206, content=content[1000:]),
            httpx.Response(200, content=content),
        ]
    )
    with ArchiveClient() as arc:
        arc.download(Topic.SECTION_58, 2026, 9, dest)
    assert "range" not in route.calls[1].request.headers
    assert dest.read_bytes() == content


@respx.mock
def test_download_raises_and_keeps_nothing_when_a_fresh_file_fails_its_etag(tmp_path):
    content = SECTION_58.read_bytes()
    respx.head(S58_URL).mock(return_value=_head(content, etag='"' + "0" * 32 + '"'))
    respx.get(S58_URL).mock(return_value=httpx.Response(200, content=content))
    with ArchiveClient() as arc, pytest.raises(TransportError):
        arc.download(Topic.SECTION_58, 2026, 9, tmp_path / "s58.zip")
    assert list(tmp_path.iterdir()) == []


@respx.mock
def test_download_of_an_unpublished_month_raises_not_found(tmp_path):
    respx.head(f"{BASE_URL}/permit/2026/12.zip").mock(return_value=httpx.Response(404))
    with ArchiveClient() as arc, pytest.raises(NotFoundError):
        arc.download(Topic.PERMIT, 2026, 12, tmp_path / "p.zip")


# --- iter_events -------------------------------------------------------------


def test_iter_events_yields_every_real_event_in_a_zip():
    stats = ReadStats()
    events = list(iter_events(PERMIT, stats=stats))
    assert all(isinstance(e, EventNotification) for e in events)
    assert {e.event_type for e in events} == {
        "PERMIT_SUBMITTED",
        "PERMIT_GRANTED",
        "PERMIT_REFUSED",
        "PERMIT_CANCELLED",
        "PERMIT_REVOKED",
        "PERMIT_ALTERATION_GRANTED",
        "WORK_START",
        "WORK_STOP",
        "WORK_START_REVERTED",
        "WORK_STOP_REVERTED",
        "CURRENT_TRAFFIC_MANAGEMENT_UPDATED",
    }
    assert stats == ReadStats(zips=1, members=11, events=11)
    assert all(e.object_type == "PERMIT" and e.object_data["usrn"] for e in events)


def test_iter_events_reads_every_zip_under_a_folder(tmp_path):
    for path in (PERMIT, ACTIVITY, SECTION_58):
        (tmp_path / path.stem).mkdir()
        shutil.copy(path, tmp_path / path.stem / path.name)
    stats = ReadStats()
    events = list(iter_events(tmp_path, stats=stats))
    assert stats.zips == 3
    assert len(events) == 11 + 6 + 8
    assert {e.object_type for e in events} == {"PERMIT", "ACTIVITY", "SECTION_58"}


def test_iter_events_filters_by_event_type_and_object_data():
    events = list(iter_events(SECTION_58))
    target = events[0]
    ha = target.object_data["highway_authority_swa_code"]

    assert {e.event_type for e in iter_events(SECTION_58, event_types="SECTION_58_CLOSED")} == {
        "SECTION_58_CLOSED"
    }
    by_usrn = list(iter_events(SECTION_58, usrn=int(target.object_data["usrn"])))
    assert target.event_reference in {e.event_reference for e in by_usrn}
    assert all(e.object_data["usrn"] == target.object_data["usrn"] for e in by_usrn)
    assert all(
        e.object_data["highway_authority_swa_code"] == ha
        for e in iter_events(SECTION_58, ha_org=[ha, "no-such-code"])
    )
    # Section 58 events carry no promoter, so a promoter filter matches none.
    assert list(iter_events(SECTION_58, promoter_org="anything")) == []


def test_iter_events_skips_and_counts_bad_zips_and_members(tmp_path):
    (tmp_path / "not-a-zip.zip").write_bytes(b"this is not a zip")
    with zipfile.ZipFile(tmp_path / "mixed.zip", "w") as z:
        with zipfile.ZipFile(ACTIVITY) as real:
            first = real.namelist()[0]
            z.writestr(first, real.read(first))
        z.writestr("truncated.json", '{"event_type": ')
        z.writestr("list.json", "[]")
    stats = ReadStats()
    events = list(iter_events(tmp_path, stats=stats))
    assert len(events) == 1
    assert stats == ReadStats(zips=1, bad_zips=1, members=3, bad_members=2, events=1)
