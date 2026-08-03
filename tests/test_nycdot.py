"""Tests for the NYC DOT Street Construction Permits adapter.

Credential-free, live-verified from day one - see the module docstring
in ``streetworks.nycdot.client``. ``nycdot_permits_live_pull.json`` holds
6 REAL permits from a real, unauthenticated pull (2026-08-02): a real
applicationtrackingid group of 3 (POINT/POINT/LINESTRING geometry, all
DOT IN-HOUSE PAVING AND MILLING - a real multi-segment paving job), a
real MULTIPOINT STREET OPENING PERMIT, a real permit with no geometry at
all (cross-street text only), and a real BUILDING OPERATION PERMIT (the
series deliberately excluded from the default roadworks filter) - not
synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_nycdot
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.nycdot import PERMITS_URL, NycDotClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "nycdot_permits_live_pull.json"
PERMITS = json.loads(FIXTURE_PATH.read_text())


def _by_number(number: str):
    return next(p for p in PERMITS if p["permitnumber"] == number)


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_permits_needs_no_credentials_and_defaults_unfiltered():
    route = respx.get(PERMITS_URL).mock(return_value=httpx.Response(200, json=PERMITS))
    with NycDotClient() as nycdot:
        permits = list(nycdot.iter_permits())
    assert len(permits) == 6
    assert route.calls[0].request.url.params.get("$where") == "1=1"


@respx.mock
def test_iter_roadworks_filters_to_the_two_confirmed_series():
    route = respx.get(PERMITS_URL).mock(
        return_value=httpx.Response(200, json=[])
    )
    with NycDotClient() as nycdot:
        list(nycdot.iter_roadworks())
    where = route.calls[0].request.url.params.get("$where")
    assert "STREET OPENING PERMIT" in where
    assert "DOT IN-HOUSE PAVING AND MILLING" in where
    assert "BUILDING OPERATION PERMIT" not in where


@respx.mock
def test_iter_permits_requests_the_soda_pagination_params():
    """Pagination completeness itself is covered by test_socrata.py's own
    SodaClient suite - this just confirms NycDotClient wires the shared
    client through unchanged."""
    route = respx.get(PERMITS_URL).mock(return_value=httpx.Response(200, json=PERMITS))
    with NycDotClient() as nycdot:
        list(nycdot.iter_permits())
    assert route.calls[0].request.url.params.get("$limit") == "1000"
    assert route.calls[0].request.url.params.get("$offset") == "0"


def test_client_requires_no_credentials():
    NycDotClient()


# --------------------------------------------------------------------------- #
# Converter - the real applicationtrackingid grouping
# --------------------------------------------------------------------------- #


def test_from_nycdot_groups_a_real_multi_permit_application():
    """A real application (2023061300973320) with 3 real permits - the
    Street Manager-style Works/WorksSite umbrella grouping."""
    works_list = from_nycdot(PERMITS)
    paving = next(w for w in works_list if w.reference == "2023061300973320")
    assert len(paving.sites) == 3
    assert {s.reference for s in paving.sites} == {
        "Q152023164A00",
        "Q152023164A01",
        "Q152023164A02",
    }
    assert paving.promoter is not None
    assert paving.territory == "USA"
    assert paving.administrative_area == "New York City Department of Transportation (DOT)"
    assert paving.source_grade == SourceGrade.REGISTER


def test_from_nycdot_site_geometry_covers_point_and_linestring():
    works_list = from_nycdot(PERMITS)
    paving = next(w for w in works_list if w.reference == "2023061300973320")
    point_site = next(s for s in paving.sites if s.reference == "Q152023164A00")
    line_site = next(s for s in paving.sites if s.reference == "Q152023164A02")
    assert point_site.coordinate.crs == "EPSG:2263"
    assert point_site.coordinate.points is None
    assert line_site.coordinate.points is not None
    assert len(line_site.coordinate.points) == 2


def test_from_nycdot_multipoint_geometry():
    works_list = from_nycdot(PERMITS)
    solo = next(w for w in works_list if w.sites[0].reference == "X012020237A19")
    site = solo.sites[0]
    assert site.coordinate.crs == "EPSG:2263"
    assert site.coordinate.points is not None
    assert len(site.coordinate.points) == 2


def test_from_nycdot_handles_a_real_permit_with_no_geometry():
    works_list = from_nycdot(PERMITS)
    solo = next(w for w in works_list if w.sites[0].reference == "M012025198A73")
    site = solo.sites[0]
    assert site.coordinate is None
    assert site.location_description == "OLD SLIP between FRONT STREET and WATER STREET (Manhattan)"


def test_from_nycdot_location_description_with_only_a_from_street():
    works_list = from_nycdot(PERMITS)
    solo = next(w for w in works_list if w.sites[0].reference == "X012020237A19")
    site = solo.sites[0]
    assert site.location_description == "SEDGWICK AVENUE at STEVENSON PLACE (Bronx)"


def test_from_nycdot_street_ref_is_never_populated():
    """No LION segmentid or any other street identifier is stated
    anywhere in the real 39-column schema - see the module docstring for
    the full finding."""
    works_list = from_nycdot(PERMITS)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_nycdot_date_confidence_is_always_estimated():
    """No real 'confirmed to have happened' signal exists on this
    dataset - issued does not mean active. See module docstring."""
    works_list = from_nycdot(PERMITS)
    for w in works_list:
        for site in w.sites:
            assert site.date_confidence is DateConfidence.ESTIMATED
            assert site.actual_start is None
            assert site.actual_end is None


def test_from_nycdot_dates_are_parsed_but_timezone_naive():
    works_list = from_nycdot(PERMITS)
    solo = next(w for w in works_list if w.sites[0].reference == "M012025198A73")
    site = solo.sites[0]
    assert site.proposed_start is not None
    assert site.proposed_start.tzinfo is None


def test_from_nycdot_promoter_is_the_permittee():
    works_list = from_nycdot(PERMITS)
    solo = next(w for w in works_list if w.sites[0].reference == "M012025198A73")
    assert solo.promoter == "CONSOLIDATED EDISON"


def test_from_nycdot_building_operation_permit_still_converts_when_passed_directly():
    """from_nycdot() itself never filters by series - only
    NycDotClient.iter_roadworks()'s $where does. A caller who fetches
    BUILDING OPERATION PERMIT rows explicitly still gets a real Works
    back, not a silent drop."""
    building = _by_number("B022025191A38")
    works_list = from_nycdot([building])
    assert len(works_list) == 1
    assert works_list[0].sites[0].works_type == "OCCUPANCY OF ROADWAY AS STIPULATED"


def test_from_nycdot_thin_group_falls_back_when_tracking_id_missing():
    permit = dict(_by_number("M012025198A73"))
    del permit["applicationtrackingid"]
    works_list = from_nycdot([permit])
    assert len(works_list) == 1
    assert works_list[0].reference == permit["permitnumber"]
