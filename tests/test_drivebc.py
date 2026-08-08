"""Tests for the DriveBC (British Columbia) Open511 adapter.

Credential-free, live-verified - see the module docstring in
``streetworks.drivebc.client``. ``drivebc_events_live_pull.json`` holds
6 REAL events from a real, unauthenticated pull (2026-08-08): a real
``INCIDENT`` (excluded), a real ``CONSTRUCTION`` with a ``LineString`` +
open-ended ``intervals`` window, a real ``CONSTRUCTION`` with a
``LineString`` + ``recurring_schedules`` (the genuinely different
day-of-week/daily-time shape), a real ``CONSTRUCTION`` with a ``Point`` +
closed ``intervals`` window, a real ``ROAD_CONDITION`` (excluded), and a
real ``WEATHER_CONDITION`` (excluded). LineString vertex lists are
trimmed for fixture size, coordinates are real.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_drivebc
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.drivebc import EVENTS_URL, DriveBCClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "drivebc_events_live_pull.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text())
RECORDS = FIXTURE["events"]


def _by_id(records: list[dict], event_id: str) -> dict:
    return next(r for r in records if r["id"] == event_id)


def _mock_page(events: list[dict]) -> None:
    respx.get(EVENTS_URL).mock(
        return_value=httpx.Response(
            200, json={"events": events, "pagination": {"offset": "0"}}
        )
    )


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_events_needs_no_credentials_and_is_unfiltered():
    _mock_page(RECORDS)
    with DriveBCClient() as drivebc:
        records = list(drivebc.iter_events())
    assert len(records) == len(RECORDS)  # includes INCIDENT/ROAD_CONDITION/WEATHER_CONDITION


@respx.mock
def test_iter_roadworks_filters_to_construction():
    _mock_page(RECORDS)
    with DriveBCClient() as drivebc:
        records = list(drivebc.iter_roadworks())
    assert len(records) == 3
    assert all(r["event_type"] == "CONSTRUCTION" for r in records)


@respx.mock
def test_iter_events_pages_via_offset_until_a_short_page():
    """A full-length (500) first page means "there might be more" - the
    client must request a second page and stop once it comes back short."""
    full_page = RECORDS * 84  # 6*84=504 > 500, exercises the >=_MAX_LIMIT branch once
    first_500 = full_page[:500]
    remainder = full_page[500:]
    route = respx.get(EVENTS_URL)
    route.side_effect = [
        httpx.Response(200, json={"events": first_500, "pagination": {"offset": "0"}}),
        httpx.Response(200, json={"events": remainder, "pagination": {"offset": "500"}}),
    ]
    with DriveBCClient() as drivebc:
        records = list(drivebc.iter_events())
    assert len(records) == len(full_page)
    assert route.call_count == 2


def test_client_requires_no_credentials():
    DriveBCClient()


# --------------------------------------------------------------------------- #
# Converter - no grouping, 1:1
# --------------------------------------------------------------------------- #


def test_from_drivebc_produces_one_works_per_record_no_grouping():
    works_list = from_drivebc(RECORDS)
    assert len(works_list) == len(RECORDS)
    assert all(len(w.sites) == 1 for w in works_list)
    assert all(w.territory == "Canada" for w in works_list)
    assert all(w.source_grade == SourceGrade.OPERATOR for w in works_list)


def test_from_drivebc_point_geometry():
    works_list = from_drivebc([_by_id(RECORDS, "drivebc.ca/DBC-92059")])
    coord = works_list[0].sites[0].coordinate
    assert coord.crs == "EPSG:4326"
    assert coord.points is None


def test_from_drivebc_linestring_geometry_captures_all_points():
    works_list = from_drivebc([_by_id(RECORDS, "drivebc.ca/RIDE-100556")])
    coord = works_list[0].sites[0].coordinate
    assert coord.points is not None
    assert len(coord.points) > 1
    assert coord.value == coord.points[0]


def test_from_drivebc_street_ref_is_never_populated():
    works_list = from_drivebc(RECORDS)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_drivebc_date_confidence_is_always_estimated():
    works_list = from_drivebc(RECORDS)
    for w in works_list:
        for site in w.sites:
            assert site.date_confidence is DateConfidence.ESTIMATED
            assert site.actual_start is None
            assert site.actual_end is None


def test_from_drivebc_parses_open_ended_intervals():
    """RIDE-100556's real interval is "2026-07-15T03:00/" - no end."""
    works_list = from_drivebc([_by_id(RECORDS, "drivebc.ca/RIDE-100556")])
    site = works_list[0].sites[0]
    assert site.proposed_start is not None
    assert site.proposed_start.year == 2026
    assert site.proposed_start.month == 7
    assert site.proposed_end is None


def test_from_drivebc_parses_closed_intervals():
    works_list = from_drivebc([_by_id(RECORDS, "drivebc.ca/DBC-92059")])
    site = works_list[0].sites[0]
    assert site.proposed_start is not None
    assert site.proposed_end is not None
    assert site.proposed_start < site.proposed_end


def test_from_drivebc_parses_recurring_schedules():
    """DBC-82106's real schedule is recurring_schedules, not intervals -
    a genuinely different shape (day-of-week + daily time window)."""
    record = _by_id(RECORDS, "drivebc.ca/DBC-82106")
    assert "recurring_schedules" in record["schedule"]
    works_list = from_drivebc([record])
    site = works_list[0].sites[0]
    assert site.proposed_start is not None
    assert site.proposed_end is not None
    assert site.proposed_start < site.proposed_end


def test_from_drivebc_excluded_records_still_convert_when_passed_directly():
    """from_drivebc() itself never filters by event_type - only
    DriveBCClient.iter_roadworks() does."""
    works_list = from_drivebc([_by_id(RECORDS, "drivebc.ca/DBC-47311")])
    assert len(works_list) == 1
    assert works_list[0].sites[0].works_type == "HAZARD"


def test_from_drivebc_location_description_uses_road_name_and_span():
    works_list = from_drivebc([_by_id(RECORDS, "drivebc.ca/DBC-92059")])
    assert works_list[0].sites[0].location_description is not None
