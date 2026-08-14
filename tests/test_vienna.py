"""Tests for the Vienna (verkehrswirksame Baustellen) adapter.

Credential-free, live-verified 2026-08-14 - see the module docstring in
``streetworks.vienna.client``. ``vienna_baustellen_live_pull.json``
holds 4 REAL features trimmed from a real, unauthenticated pull (111
total, 39 point + 72 line): two real Point features (one with a real
``ANTRAGSTELLER``, one with ``null`` - the genuine partial gap found
live) and two real LineString features. Not synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_vienna
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.vienna import BASE_URL, LINE_TYPE_NAME, POINT_TYPE_NAME, ViennaClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vienna_baustellen_live_pull.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())
FEATURES = FIXTURE_JSON["features"]

POINTS = [f for f in FEATURES if f["geometry"]["type"] == "Point"]
LINES = [f for f in FEATURES if f["geometry"]["type"] == "LineString"]


def _mock_feed() -> None:
    respx.get(BASE_URL).mock(
        side_effect=lambda request: httpx.Response(
            200,
            json={"type": "FeatureCollection", "features": POINTS}
            if POINT_TYPE_NAME in request.url.params.get("TYPENAMES", "")
            else {"type": "FeatureCollection", "features": LINES},
        )
    )


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_combines_both_layers():
    _mock_feed()
    with ViennaClient() as vienna:
        features = vienna.iter_roadworks()
    assert len(features) == len(POINTS) + len(LINES)


@respx.mock
def test_iter_roadworks_requests_native_crs_and_working_format():
    _mock_feed()
    with ViennaClient() as vienna:
        vienna.iter_roadworks()
    calls = respx.calls
    assert len(calls) == 2
    for call in calls:
        params = call.request.url.params
        assert params["SRSNAME"] == "EPSG:31256"
        assert params["OUTPUTFORMAT"] == "application/json"
        assert params["VERSION"] == "1.1.0"
    type_names_requested = {call.request.url.params["TYPENAME"] for call in calls}
    assert type_names_requested == {POINT_TYPE_NAME, LINE_TYPE_NAME}


def test_client_requires_no_credentials():
    ViennaClient()


# --------------------------------------------------------------------------- #
# Converter
# --------------------------------------------------------------------------- #


def test_from_vienna_produces_one_works_per_feature_no_grouping():
    works_list = from_vienna(FEATURES)
    assert len(works_list) == len(FEATURES)
    assert all(len(w.sites) == 1 for w in works_list)


def test_from_vienna_reference_is_objectid():
    works_list = from_vienna(POINTS)
    refs = {w.reference for w in works_list}
    assert "1656294455" in refs


def test_from_vienna_point_coordinate_stays_unswapped():
    """EPSG:31256 (MGI / Austria GK East) is projected - Coordinate.value
    must be (x, y) as given, never swapped to (lat, lon)."""
    works_list = from_vienna([POINTS[0]])
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.crs == "EPSG:31256"
    assert coord.points is None
    # real GK East easting/northing for Vienna are both in this range.
    assert 0 < coord.value[0] < 50_000
    assert 300_000 < coord.value[1] < 400_000


def test_from_vienna_linestring_populates_points():
    works_list = from_vienna([LINES[0]])
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.points is not None
    assert len(coord.points) > 1
    assert coord.value == coord.points[0]


def test_from_vienna_promoter_is_antragsteller_when_present():
    works_list = from_vienna(POINTS)
    with_promoter = [w for w in works_list if w.reference == "1656294455"]
    assert with_promoter[0].promoter == "MA28"


def test_from_vienna_promoter_stays_none_when_source_states_none():
    """A real partial gap - ANTRAGSTELLER is null on some real rows,
    left None rather than fabricated."""
    works_list = from_vienna(POINTS)
    without_promoter = [w for w in works_list if w.reference == "1655785353"]
    assert without_promoter[0].promoter is None


def test_from_vienna_territory_and_administrative_area():
    works_list = from_vienna(FEATURES)
    assert all(w.territory == "Austria" for w in works_list)
    assert all(w.administrative_area == "Stadt Wien" for w in works_list)
    assert all(w.source_grade == SourceGrade.REGISTER for w in works_list)


def test_from_vienna_date_confidence_is_always_estimated():
    """No explicit status field exists - only planned dates."""
    works_list = from_vienna(FEATURES)
    assert all(
        s.date_confidence is DateConfidence.ESTIMATED for w in works_list for s in w.sites
    )


def test_from_vienna_dates_parse_as_naive_datetimes():
    """A real confirmed CPython quirk: fromisoformat silently drops the
    UTC offset for a bare-date-plus-Z string - not a bug in this SDK."""
    works_list = from_vienna([POINTS[0]])
    start = works_list[0].sites[0].proposed_start
    assert start is not None
    assert start.tzinfo is None


def test_from_vienna_works_type_is_behinderungsart():
    works_list = from_vienna([LINES[0]])
    assert works_list[0].sites[0].works_type == "Rohrlegung"


def test_from_vienna_street_ref_is_never_populated():
    works_list = from_vienna(FEATURES)
    assert all(s.street_ref is None for w in works_list for s in w.sites)
