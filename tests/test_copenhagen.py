"""Tests for the Copenhagen (Gravetilladelser) adapter.

Credential-free, live-verified 2026-08-10 - see the module docstring in
``streetworks.copenhagen.client``. ``copenhagen_gravetilladelser_live_pull.json``
holds 6 REAL features trimmed from a real, unauthenticated pull (2240
total) - a real multi-geometry permit (sagsnr 792947, one Point + one
Polygon row, same permit), a real LineString-only permit (672255), a real
Point-only permit (745466), and a real permit with both a LineString and
a Point row (645629, to prove the LineString-over-Point priority). Not
synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_copenhagen
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.copenhagen import CopenhagenClient
from streetworks.copenhagen.client import _WFS_PARAMS, WFS_BASE_URL

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "copenhagen_gravetilladelser_live_pull.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())
FEATURES = FIXTURE_JSON["features"]


def _by_sagsnr(features: list[dict], sagsnr: int) -> list[dict]:
    return [f for f in features if f["properties"]["sagsnr"] == sagsnr]


def _mock_feed() -> respx.Route:
    return respx.get(WFS_BASE_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_needs_no_credentials_and_is_unfiltered():
    _mock_feed()
    with CopenhagenClient() as copenhagen:
        features = list(copenhagen.iter_roadworks())
    assert len(features) == len(FEATURES)  # raw, undeduped - see module docstring


@respx.mock
def test_iter_roadworks_requests_the_real_wfs_getfeature_params():
    route = _mock_feed()
    with CopenhagenClient() as copenhagen:
        list(copenhagen.iter_roadworks())
    params = route.calls[0].request.url.params
    assert params["service"] == "WFS"
    assert params["typeName"] == _WFS_PARAMS["typeName"]
    assert params["outputFormat"] == "json"
    assert params["SRSNAME"] == "EPSG:4326"


def test_client_requires_no_credentials():
    CopenhagenClient()


# --------------------------------------------------------------------------- #
# Converter - dedupe by sagsnr, geometry priority
# --------------------------------------------------------------------------- #


def test_from_copenhagen_dedupes_multi_geometry_permit_into_one_works():
    """sagsnr 792947 has two real rows (Point + Polygon) for the same
    permit - must collapse to exactly one Works, one WorksSite."""
    works_list = from_copenhagen(_by_sagsnr(FEATURES, 792947))
    assert len(works_list) == 1
    assert len(works_list[0].sites) == 1
    assert works_list[0].reference == "792947"


def test_from_copenhagen_prefers_point_over_polygon():
    """Point beats Polygon (Polygon is never used at all) - the
    dedupe-and-select coordinate for 792947 must come from its real
    Point row, not a fabricated centroid of its Polygon row."""
    works = from_copenhagen(_by_sagsnr(FEATURES, 792947))[0]
    assert works.coordinate is not None
    assert works.coordinate.crs == "EPSG:4326"
    assert works.coordinate.value == (55.63970883, 12.57793567)  # (lat, lon)
    assert works.coordinate.points is None  # a Point, not a line


def test_from_copenhagen_prefers_linestring_over_point():
    """sagsnr 645629 has both a real LineString row and a real Point row
    for the same permit - LineString must win, per module docstring."""
    works = from_copenhagen(_by_sagsnr(FEATURES, 645629))[0]
    assert len(works.sites) == 1
    coord = works.coordinate
    assert coord is not None
    assert coord.points is not None
    assert len(coord.points) == 2
    assert coord.value == coord.points[0]
    # real LineString coordinates for this permit, swapped to (lat, lon)
    assert coord.value == (55.71522842, 12.53686488)


def test_from_copenhagen_linestring_only_permit_keeps_full_line():
    works = from_copenhagen(_by_sagsnr(FEATURES, 672255))[0]
    coord = works.coordinate
    assert coord is not None
    assert coord.points is not None
    assert len(coord.points) == 2
    assert coord.value == (55.68894485, 12.57536938)


def test_from_copenhagen_point_only_permit():
    works = from_copenhagen(_by_sagsnr(FEATURES, 745466))[0]
    coord = works.coordinate
    assert coord is not None
    assert coord.points is None
    assert coord.value == (55.65444431, 12.6104)


def test_from_copenhagen_territory_and_administrative_area():
    works_list = from_copenhagen(FEATURES)
    assert all(w.territory == "Denmark" for w in works_list)
    assert all(w.administrative_area == "Københavns Kommune" for w in works_list)
    assert all(w.source_grade == SourceGrade.REGISTER for w in works_list)


def test_from_copenhagen_promoter_is_bygherre():
    works = from_copenhagen(_by_sagsnr(FEATURES, 745466))[0]
    assert works.promoter == "Cosmo 19 ApS"


def test_from_copenhagen_works_type_is_kategori():
    works = from_copenhagen(_by_sagsnr(FEATURES, 745466))[0]
    assert works.sites[0].works_type == "Asfaltarbejder"


def test_from_copenhagen_location_description_includes_gravetype():
    works = from_copenhagen(_by_sagsnr(FEATURES, 745466))[0]
    desc = works.sites[0].location_description
    assert desc is not None
    assert "Amagerbrogade 160" in desc
    assert "Fortov" in desc


def test_from_copenhagen_operating_window_from_tidspunkt_fields():
    works = from_copenhagen(_by_sagsnr(FEATURES, 745466))[0]
    assert works.sites[0].operating_window == "07:00–23:30"


def test_from_copenhagen_contractor_folded_into_traffic_management():
    """entreprenoer has no dedicated model field - folded into
    traffic_management rather than dropped, see module docstring."""
    works = from_copenhagen(_by_sagsnr(FEATURES, 745466))[0]
    assert works.sites[0].traffic_management == "Contractor: ALEKTO A/S"


def test_from_copenhagen_dates_parse_the_real_ddmmyy_format():
    works = from_copenhagen(_by_sagsnr(FEATURES, 745466))[0]
    site = works.sites[0]
    assert site.proposed_start is not None
    assert site.proposed_start.year == 2025
    assert site.proposed_start.month == 12
    assert site.proposed_start.day == 9
    assert site.proposed_end is not None
    assert site.proposed_end.year == 2026
    assert site.date_confidence is DateConfidence.ESTIMATED
    assert site.actual_start is None
    assert site.actual_end is None


def test_from_copenhagen_street_ref_is_never_populated():
    works_list = from_copenhagen(FEATURES)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_copenhagen_dedupes_across_the_whole_fixture():
    """6 raw rows across 4 real permits (792947 x2, 672255 x1, 745466 x1,
    645629 x2) - must collapse to 4 real Works, never 6."""
    works_list = from_copenhagen(FEATURES)
    assert len(works_list) == 4
    references = {w.reference for w in works_list}
    assert references == {"792947", "672255", "745466", "645629"}
