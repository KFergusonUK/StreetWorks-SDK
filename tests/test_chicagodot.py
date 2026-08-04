"""Tests for the Chicago CDOT Street Closures adapter.

Credential-free, live-verified from day one - see the module docstring
in ``streetworks.chicagodot.client``. ``chicagodot_permits_live_pull.json``
holds 6 REAL rows from a real, unauthenticated pull (2026-08-03): a real
applicationnumber group of 3 (``DOT604194``, a real restoration job
spanning 3 genuinely different real street locations), a real
``GenOpening`` permit with geometry, a real ``BlockParty`` permit (a
worktype deliberately excluded from the default roadworks filter), and
a real ``GenOpening`` permit with no geometry at all - not synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.chicagodot import STREET_CLOSURES_URL, ChicagoDotClient
from streetworks.common import from_chicagodot
from streetworks.common.models import DateConfidence, SourceGrade

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "chicagodot_permits_live_pull.json"
PERMITS = json.loads(FIXTURE_PATH.read_text())


def _by_key(unique_key: str):
    return next(p for p in PERMITS if p["uniquekey"] == unique_key)


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_permits_needs_no_credentials_and_defaults_unfiltered():
    route = respx.get(STREET_CLOSURES_URL).mock(return_value=httpx.Response(200, json=PERMITS))
    with ChicagoDotClient() as chicago:
        permits = list(chicago.iter_permits())
    assert len(permits) == 6
    assert route.calls[0].request.url.params.get("$where") == "1=1"


@respx.mock
def test_iter_roadworks_filters_to_the_confirmed_worktypes():
    route = respx.get(STREET_CLOSURES_URL).mock(return_value=httpx.Response(200, json=[]))
    with ChicagoDotClient() as chicago:
        list(chicago.iter_roadworks())
    where = route.calls[0].request.url.params.get("$where")
    roadworks_worktypes = (
        "GenOpening",
        "Restorat",
        "GenOccupy",
        "WorkInAdv",
        "SoilNWell",
        "StClosure",
        "Driveway",
    )
    for worktype in roadworks_worktypes:
        assert worktype in where
    assert "BlockParty" not in where
    assert "Festival" not in where


@respx.mock
def test_iter_permits_requests_the_soda_pagination_params():
    """Pagination completeness itself is covered by test_socrata.py's own
    SodaClient suite - this just confirms ChicagoDotClient wires the
    shared client through unchanged."""
    route = respx.get(STREET_CLOSURES_URL).mock(return_value=httpx.Response(200, json=PERMITS))
    with ChicagoDotClient() as chicago:
        list(chicago.iter_permits())
    assert route.calls[0].request.url.params.get("$limit") == "1000"
    assert route.calls[0].request.url.params.get("$offset") == "0"


def test_client_requires_no_credentials():
    ChicagoDotClient()


# --------------------------------------------------------------------------- #
# Converter - the real applicationnumber grouping
# --------------------------------------------------------------------------- #


def test_from_chicagodot_groups_a_real_multi_row_application():
    """A real application (DOT604194) with 3 real rows across 3 real,
    genuinely different street locations - a citywide restoration job."""
    works_list = from_chicagodot(PERMITS)
    restoration = next(w for w in works_list if w.reference == "DOT604194")
    assert len(restoration.sites) == 3
    assert {s.reference for s in restoration.sites} == {
        "6484156747",
        "6484156751",
        "6484156752",
    }
    assert restoration.promoter == "BIGANE PAVING CO (CONSTRUCTION)*"
    assert restoration.territory == "USA"
    assert restoration.administrative_area == "City of Chicago Department of Transportation (CDOT)"
    assert restoration.source_grade == SourceGrade.REGISTER


def test_from_chicagodot_site_geometry_is_native_wgs84_point():
    works_list = from_chicagodot(PERMITS)
    restoration = next(w for w in works_list if w.reference == "DOT604194")
    site = restoration.sites[0]
    assert site.coordinate.crs == "EPSG:4326"
    assert site.coordinate.value == (41.752943189885734, -87.5845878594989)


def test_from_chicagodot_handles_a_real_permit_with_no_geometry():
    works_list = from_chicagodot(PERMITS)
    solo = next(w for w in works_list if w.sites[0].reference == "13173611488130")
    site = solo.sites[0]
    assert site.coordinate is None
    assert site.location_description == "3800-3999 W STRONG ST"


def test_from_chicagodot_location_description_with_equal_from_to():
    works_list = from_chicagodot(PERMITS)
    solo = next(w for w in works_list if w.sites[0].reference == "19742762488264")
    site = solo.sites[0]
    assert site.location_description == "5107 N MARMORA AVE"


def test_from_chicagodot_traffic_management_carries_streetclosure():
    works_list = from_chicagodot(PERMITS)
    solo = next(w for w in works_list if w.sites[0].reference == "19742762488264")
    assert solo.sites[0].traffic_management == "Curblane"


def test_from_chicagodot_street_ref_is_never_populated():
    """No segment/street identifier is stated anywhere in the real
    46-column schema - see the module docstring for the full finding."""
    works_list = from_chicagodot(PERMITS)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_chicagodot_date_confidence_is_always_estimated():
    """No real 'confirmed to have happened' signal exists on this
    dataset - applicationstatus describes the application's lifecycle,
    not the work's. See module docstring."""
    works_list = from_chicagodot(PERMITS)
    for w in works_list:
        for site in w.sites:
            assert site.date_confidence is DateConfidence.ESTIMATED
            assert site.actual_start is None
            assert site.actual_end is None


def test_from_chicagodot_dates_are_parsed():
    works_list = from_chicagodot(PERMITS)
    solo = next(w for w in works_list if w.sites[0].reference == "19742762488264")
    site = solo.sites[0]
    assert site.proposed_start is not None
    assert site.proposed_end is not None


def test_from_chicagodot_blockparty_still_converts_when_passed_directly():
    """from_chicagodot() itself never filters by worktype - only
    ChicagoDotClient.iter_roadworks()'s $where does. A caller who
    fetches a BlockParty row explicitly still gets a real Works back,
    not a silent drop."""
    block_party = _by_key("2667442842021")
    works_list = from_chicagodot([block_party])
    assert len(works_list) == 1
    assert works_list[0].sites[0].works_type == "Block Party"


def test_from_chicagodot_thin_group_falls_back_when_application_number_missing():
    permit = dict(_by_key("19742762488264"))
    del permit["applicationnumber"]
    works_list = from_chicagodot([permit])
    assert len(works_list) == 1
    assert works_list[0].reference == permit["uniquekey"]
