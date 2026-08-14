"""Tests for the Kanton Zürich (Baustellen Kantonsstrassen) adapter.

Credential-free, live-verified 2026-08-14 - see the module docstring in
``streetworks.canton_zurich.client``. ``canton_zurich_baustellen_live_pull.json``
holds 4 REAL features trimmed from a real, unauthenticated pull (66
total): one ``status_baustelle: "aktiv (Bauzeit)"`` (active) row, and
three ``"zukünftig (Bauzeit in Zukunft)"`` (upcoming) rows - two of
which share an identical ``strassenname``/``datum_baubeginn`` (the one
real composite-key collision found live: two genuinely distinct closures,
opposite directions of the same road, different times/descriptions).
Not synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.canton_zurich import BASE_URL, CantonZurichClient
from streetworks.common import from_canton_zurich
from streetworks.common.models import DateConfidence, SourceGrade

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "canton_zurich_baustellen_live_pull.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())
FEATURES = FIXTURE_JSON["features"]


def _mock_feed() -> respx.Route:
    return respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_returns_every_feature():
    _mock_feed()
    with CantonZurichClient() as canton_zurich:
        features = canton_zurich.iter_roadworks()
    assert len(features) == len(FEATURES)


@respx.mock
def test_iter_roadworks_requests_native_crs_and_working_format():
    route = _mock_feed()
    with CantonZurichClient() as canton_zurich:
        canton_zurich.iter_roadworks()
    params = route.calls[0].request.url.params
    assert params["SRSNAME"] == "EPSG:2056"
    assert params["OUTPUTFORMAT"] == "application/json"
    assert params["TYPENAMES"] == "ms:baustellen-detailansicht"


def test_client_requires_no_credentials():
    CantonZurichClient()


# --------------------------------------------------------------------------- #
# Converter
# --------------------------------------------------------------------------- #


def test_from_canton_zurich_produces_one_works_per_feature_no_grouping():
    works_list = from_canton_zurich(FEATURES)
    assert len(works_list) == len(FEATURES)
    assert all(len(w.sites) == 1 for w in works_list)


def test_from_canton_zurich_reference_is_always_none():
    """No unique identifier field exists in this schema - a genuine
    gap, not an extraction miss."""
    works_list = from_canton_zurich(FEATURES)
    assert all(w.reference is None for w in works_list)


def test_from_canton_zurich_coordinate_stays_unswapped_easting_northing():
    """EPSG:2056 (Swiss LV95) is projected - Coordinate.value must be
    (easting, northing) as given, never swapped to (lat, lon)."""
    works_list = from_canton_zurich(FEATURES)
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.crs == "EPSG:2056"
    # real LV95 easting is ~2,700,000, northing is ~1,260,000 for Zürich.
    assert 2_400_000 < coord.value[0] < 2_900_000
    assert 1_000_000 < coord.value[1] < 1_400_000


def test_from_canton_zurich_polygon_uses_first_ring_vertex_as_value_only():
    works_list = from_canton_zurich(FEATURES)
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.points is None
    assert coord.parts is None


def test_from_canton_zurich_territory_and_administrative_area():
    works_list = from_canton_zurich(FEATURES)
    assert all(w.territory == "Switzerland" for w in works_list)
    assert all(w.administrative_area == "Kanton Zürich" for w in works_list)
    assert all(w.source_grade == SourceGrade.OPERATOR for w in works_list)


def test_from_canton_zurich_promoter_is_never_populated():
    """ansprechperson/telefonnummer name an individual, not an
    organisation - promoter must stay None."""
    works_list = from_canton_zurich(FEATURES)
    assert all(w.promoter is None for w in works_list)


def test_from_canton_zurich_active_status_is_verified_with_actual_dates():
    works_list = from_canton_zurich(FEATURES)
    active = [w for w in works_list if w.sites[0].status == "aktiv (Bauzeit)"]
    assert len(active) == 1
    site = active[0].sites[0]
    assert site.actual_start is not None
    assert site.proposed_start is None
    assert site.date_confidence is DateConfidence.VERIFIED


def test_from_canton_zurich_upcoming_status_is_estimated_with_proposed_dates():
    works_list = from_canton_zurich(FEATURES)
    upcoming = [w for w in works_list if w.sites[0].status == "zukünftig (Bauzeit in Zukunft)"]
    assert len(upcoming) == 3
    for works in upcoming:
        site = works.sites[0]
        assert site.actual_start is None
        assert site.proposed_start is not None
        assert site.date_confidence is DateConfidence.ESTIMATED


def test_from_canton_zurich_same_composite_key_pair_stays_two_distinct_works():
    """Two real, genuinely distinct closures (opposite directions of
    the same road, different times/descriptions) share an identical
    strassenname/datum_baubeginn - must NOT be collapsed into one."""
    works_list = from_canton_zurich(FEATURES)
    forchautostrasse = [
        w for w in works_list if "Forchautostrasse" in (w.sites[0].location_description or "")
    ]
    same_date = [
        w
        for w in forchautostrasse
        if w.sites[0].proposed_start is not None and w.sites[0].proposed_start.day == 17
    ]
    assert len(same_date) == 2
    descriptions = {w.raw["properties"]["beschreibung"] for w in same_date}
    assert len(descriptions) == 2  # genuinely different real records


def test_from_canton_zurich_traffic_management_carries_verkehrsfuehrung():
    works_list = from_canton_zurich(FEATURES)
    assert any(w.sites[0].traffic_management for w in works_list)


def test_from_canton_zurich_street_ref_is_never_populated():
    works_list = from_canton_zurich(FEATURES)
    assert all(s.street_ref is None for w in works_list for s in w.sites)
