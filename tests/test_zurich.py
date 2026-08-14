"""Tests for the Stadt Zürich (Aktuelle Tiefbauprojekte im öffentlichen
Grund) adapter.

Credential-free, live-verified 2026-08-14 - see the module docstring in
``streetworks.zurich.client``. ``zurich_tiefbauprojekte_live_pull.json``
holds 3 REAL features trimmed from a real, unauthenticated pull (140
total), each with a distinct real ``baunr``. Not synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_zurich
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.zurich import BASE_URL, ZurichClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "zurich_tiefbauprojekte_live_pull.json"
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
    with ZurichClient() as zurich:
        features = zurich.iter_roadworks()
    assert len(features) == len(FEATURES)


@respx.mock
def test_iter_roadworks_requests_working_format_and_both_typename_params():
    """This server 500s on WFS 2.0.0's plural TYPENAMES alone - the
    client must also send the singular TYPENAME it actually needs."""
    route = _mock_feed()
    with ZurichClient() as zurich:
        zurich.iter_roadworks()
    params = route.calls[0].request.url.params
    assert params["OUTPUTFORMAT"] == "application/vnd.geo+json"
    assert params["VERSION"] == "1.1.0"
    assert params["TYPENAME"] == "aer_baustellen_a"


def test_client_requires_no_credentials():
    ZurichClient()


# --------------------------------------------------------------------------- #
# Converter
# --------------------------------------------------------------------------- #


def test_from_zurich_produces_one_works_per_feature_no_grouping():
    works_list = from_zurich(FEATURES)
    assert len(works_list) == len(FEATURES)
    assert all(len(w.sites) == 1 for w in works_list)


def test_from_zurich_reference_is_baunr():
    works_list = from_zurich(FEATURES)
    refs = {w.reference for w in works_list}
    assert "18071" in refs


def test_from_zurich_coordinate_is_flipped_to_lat_lon():
    """Genuine WGS84 (confirmed empirically despite an empty capabilities
    DefaultSRS tag) - GeoJSON's (lon, lat) must be flipped to (lat, lon)."""
    works_list = from_zurich(FEATURES)
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.crs == "EPSG:4326"
    # real Zürich latitude is ~47.4, longitude ~8.5 - lat must come first.
    assert 46 < coord.value[0] < 48
    assert 7 < coord.value[1] < 10


def test_from_zurich_multipolygon_uses_first_ring_vertex_as_value_only():
    works_list = from_zurich(FEATURES)
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.points is None
    assert coord.parts is None


def test_from_zurich_works_type_is_kategorie():
    works_list = from_zurich(FEATURES)
    assert all(w.sites[0].works_type == "Grössere Baustelle" for w in works_list)


def test_from_zurich_promoter_is_never_populated():
    """projektleiter names an individual, not an organisation -
    promoter must stay None."""
    works_list = from_zurich(FEATURES)
    assert all(w.promoter is None for w in works_list)


def test_from_zurich_territory_and_administrative_area():
    works_list = from_zurich(FEATURES)
    assert all(w.territory == "Switzerland" for w in works_list)
    assert all(w.administrative_area == "Stadt Zürich" for w in works_list)
    assert all(w.source_grade == SourceGrade.OPERATOR for w in works_list)


def test_from_zurich_date_confidence_is_always_estimated():
    """No status field exists - only planned dates."""
    works_list = from_zurich(FEATURES)
    assert all(
        s.date_confidence is DateConfidence.ESTIMATED for w in works_list for s in w.sites
    )


def test_from_zurich_street_ref_is_never_populated():
    works_list = from_zurich(FEATURES)
    assert all(s.street_ref is None for w in works_list for s in w.sites)
