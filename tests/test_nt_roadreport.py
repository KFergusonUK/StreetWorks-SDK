"""Tests for the Northern Territory (Road Report NT) adapter.

Credential-free, live-verified 2026-08-19 against
``GET /api/Obstruction/GetAll`` - see the module docstring in
``streetworks.au.nt``. ``nt_roadreport_live_pull.json`` holds five REAL
records trimmed from that pull (140 CURRENT total, 26 Roadworks): three
real ``Roadworks`` covering a typical start/end line, a Road Closed
works record, and the one real identical-start/end point, plus one
weight-restriction and one flooding record so the works filter can be
shown excluding conditions. Not synthetic.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.au.nt import (
    BASE_URL,
    GETALL_PATH,
    ROADWORKS_TYPE,
    RoadReportNtClient,
    is_roadworks,
)
from streetworks.common import DateConfidence, from_au_nt_roadreport
from streetworks.exceptions import StreetworksError
from streetworks.registry import get_provider

LIVE_PULL_PATH = Path(__file__).parent / "fixtures" / "nt_roadreport_live_pull.json"
LIVE_PULL_JSON = json.loads(LIVE_PULL_PATH.read_text())
LIVE_RECORDS = LIVE_PULL_JSON["response"]
GETALL_URL = f"{BASE_URL}{GETALL_PATH}"


def _record(obstruction_id: int) -> dict:
    return next(r for r in LIVE_RECORDS if r["obstructionId"] == obstruction_id)


# --------------------------------------------------------------------------- #
# Client wiring
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_filters_client_side_to_official_works():
    """GetAll mixes conditions with works - iter_roadworks() must keep
    only obstructionType == Roadworks (code 28)."""
    respx.get(GETALL_URL).mock(return_value=httpx.Response(200, json=LIVE_PULL_JSON))
    with RoadReportNtClient() as nt:
        roadworks = nt.iter_roadworks()
    assert len(roadworks) == 3
    assert all(r["obstructionType"] == ROADWORKS_TYPE for r in roadworks)
    assert {r["obstructionId"] for r in roadworks} == {13514, 13521, 14756}


@respx.mock
def test_iter_obstructions_returns_every_type():
    respx.get(GETALL_URL).mock(return_value=httpx.Response(200, json=LIVE_PULL_JSON))
    with RoadReportNtClient() as nt:
        items = nt.iter_obstructions()
    assert len(items) == 5
    types = {r["obstructionType"] for r in items}
    assert ROADWORKS_TYPE in types
    assert "Flooding" in types
    assert "Maximum 7 Axles" in types


@respx.mock
def test_get_obstructions_returns_the_live_envelope():
    respx.get(GETALL_URL).mock(return_value=httpx.Response(200, json=LIVE_PULL_JSON))
    with RoadReportNtClient() as nt:
        payload = nt.get_obstructions()
    assert payload["success"] is True
    assert len(payload["response"]) == 5


@respx.mock
def test_success_false_raises_streetworks_error():
    respx.get(GETALL_URL).mock(
        return_value=httpx.Response(
            200, json={"success": False, "message": "nope", "response": []}
        )
    )
    with RoadReportNtClient() as nt, pytest.raises(StreetworksError, match="success=false"):
        nt.get_obstructions()


def test_client_requires_no_credentials():
    RoadReportNtClient()


def test_is_roadworks_accepts_type_or_code():
    assert is_roadworks({"obstructionType": "Roadworks", "obstructionTypeCode": "28"})
    assert is_roadworks({"obstructionType": "Roadworks"})
    assert is_roadworks({"obstructionTypeCode": "28"})
    assert is_roadworks({"obstructionTypeCode": 28})
    assert not is_roadworks({"obstructionType": "Flooding", "obstructionTypeCode": "34"})


# --------------------------------------------------------------------------- #
# Converter - start/end [lat, lon], works-only
# --------------------------------------------------------------------------- #


def test_from_au_nt_roadreport_maps_a_real_line_work():
    works = from_au_nt_roadreport(LIVE_RECORDS)
    assert len(works) == 3

    arnhem = next(w for w in works if w.reference == "13514")
    assert arnhem.territory == "Australia"
    assert arnhem.administrative_area == (
        "Department of Infrastructure, Planning and Logistics"
    )
    assert arnhem.coordinate.crs == "EPSG:4326"
    # Source is already [lat, lon] - this SDK's stated Coordinate convention.
    assert arnhem.coordinate.value == (-12.6576980147, 131.3174101844)
    assert arnhem.coordinate.points == (
        (-12.6576980147, 131.3174101844),
        (-12.6758609326, 131.3765599685),
    )

    site = arnhem.sites[0]
    assert site.works_type == "Roadworks"
    assert site.status == "CURRENT"
    assert site.location_description == "Arnhem Highway, At Adelaide River Floodplain"
    assert site.proposed_start == datetime(2025, 2, 5, 11, 0, 37)
    assert site.proposed_start.tzinfo is None
    assert site.proposed_end is None
    assert site.date_confidence is DateConfidence.ESTIMATED
    assert site.traffic_management.startswith("With Caution")
    assert "Speed reduction" in site.traffic_management


def test_identical_start_and_end_is_a_point_not_a_line():
    """Shady Camp Access is the one real Roadworks record whose
    startPoint equals endPoint - a genuine point, not a synthetic line."""
    works = from_au_nt_roadreport([_record(14756)])[0]
    assert works.coordinate.points is None
    assert works.coordinate.value == (-12.5213569999, 131.8057219999)


def test_converter_skips_condition_records():
    """A mixed GetAll list must not pretend flooding/weight limits are
    street works."""
    works = from_au_nt_roadreport(LIVE_RECORDS)
    references = {w.reference for w in works}
    assert references == {"13514", "13521", "14756"}
    assert "8785" not in references
    assert "14100" not in references


def test_closed_roadworks_keeps_restriction_in_traffic_management():
    works = from_au_nt_roadreport([_record(13521)])[0]
    assert works.sites[0].traffic_management.startswith("Road Closed")


def test_coordinate_handles_missing_points():
    assert from_au_nt_roadreport(
        [{"obstructionType": "Roadworks", "startPoint": None, "endPoint": None}]
    )[0].coordinate is None


def test_date_to_is_mapped_when_present():
    record = {
        **_record(13514),
        "dateTo": "2026-09-01 17:00:00",
    }
    site = from_au_nt_roadreport([record])[0].sites[0]
    assert site.proposed_end == datetime(2026, 9, 1, 17, 0, 0)


# --------------------------------------------------------------------------- #
# Registry - nt is a real, verified adapter now
# --------------------------------------------------------------------------- #


def test_get_provider_resolves_nt_to_a_usable_client():
    NtClient = get_provider("nt")
    assert NtClient is RoadReportNtClient
    client = NtClient()
    assert hasattr(client, "iter_roadworks")
