"""Tests for the Helsinki (Kaivuilmoitus excavation notifications) adapter.

Credential-free, live-verified 2026-08-13 - see the module docstring in
``streetworks.helsinki.client``. ``helsinki_kaivuilmoitus_live_pull.json``
holds 6 REAL features trimmed from a real, unauthenticated pull (3,431
total): a real 4-row multi-geometry application (``KP2100964-112``, one
excavation notification genuinely spanning 4 distinct real sub-areas), a
plain single-row application (``KP1900206-23``), and a real
``status: "Tuleva"`` (upcoming, not yet active) application
(``KP2600373-3``, to exercise the VERIFIED/ESTIMATED branch). Not
synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_helsinki
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.helsinki import BASE_URL, HelsinkiClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "helsinki_kaivuilmoitus_live_pull.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())
FEATURES = FIXTURE_JSON["features"]


def _by_reference(features: list[dict], reference: str) -> list[dict]:
    return [f for f in features if f["properties"]["hakemustunnus"] == reference]


def _mock_feed() -> respx.Route:
    return respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=FIXTURE_JSON))


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_returns_every_feature():
    _mock_feed()
    with HelsinkiClient() as helsinki:
        features = list(helsinki.iter_roadworks())
    assert len(features) == len(FEATURES)


@respx.mock
def test_iter_roadworks_requests_native_crs_not_reprojected():
    route = _mock_feed()
    with HelsinkiClient() as helsinki:
        list(helsinki.iter_roadworks())
    params = route.calls[0].request.url.params
    assert params["SRSNAME"] == "EPSG:3879"
    assert params["TYPENAMES"] == "avoindata:Kaivuilmoitus_alue"


def test_client_requires_no_credentials():
    HelsinkiClient()


# --------------------------------------------------------------------------- #
# Converter - hakemustunnus grouping
# --------------------------------------------------------------------------- #


def test_from_helsinki_groups_multi_row_application_into_one_works():
    """KP2100964-112 has 4 real rows - must become one Works with 4
    WorksSites, not 4 separate Works."""
    works_list = from_helsinki(_by_reference(FEATURES, "KP2100964-112"))
    assert len(works_list) == 1
    works = works_list[0]
    assert works.reference == "KP2100964-112"
    assert len(works.sites) == 4
    site_refs = {s.reference for s in works.sites}
    assert site_refs == {"3", "4", "5", "6"}


def test_from_helsinki_single_row_application():
    works_list = from_helsinki(_by_reference(FEATURES, "KP1900206-23"))
    assert len(works_list) == 1
    assert len(works_list[0].sites) == 1
    assert works_list[0].sites[0].reference == "1"


def test_from_helsinki_coordinate_stays_unswapped_easting_northing():
    """EPSG:3879 is projected - Coordinate.value must be (easting,
    northing) as given, never swapped to (lat, lon)."""
    works_list = from_helsinki(_by_reference(FEATURES, "KP1900206-23"))
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.crs == "EPSG:3879"
    # real easting is ~25,495,000 (ETRS-GK25FIN false-easting encodes the
    # zone), real northing is ~6,671,000 - easting must stay first.
    assert 25_000_000 < coord.value[0] < 26_000_000
    assert 6_000_000 < coord.value[1] < 7_000_000


def test_from_helsinki_polygon_uses_first_ring_vertex_as_value_only():
    works_list = from_helsinki(_by_reference(FEATURES, "KP1900206-23"))
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.points is None
    assert coord.parts is None


def test_from_helsinki_territory_and_administrative_area():
    works_list = from_helsinki(FEATURES)
    assert all(w.territory == "Finland" for w in works_list)
    assert all(w.administrative_area == "Helsingin kaupunki" for w in works_list)
    assert all(w.source_grade == SourceGrade.REGISTER for w in works_list)


def test_from_helsinki_promoter_is_never_populated():
    """hakija/tyon_suorittaja are confirmed empty across the real
    dataset - promoter must stay None, not fabricated."""
    works_list = from_helsinki(FEATURES)
    assert all(w.promoter is None for w in works_list)


def test_from_helsinki_works_type_is_hakemus():
    works_list = from_helsinki(_by_reference(FEATURES, "KP1900206-23"))
    assert works_list[0].sites[0].works_type == "Kaivuilmoitus"


def test_from_helsinki_active_status_is_verified_with_actual_dates():
    """status "Käynnissä" genuinely means the excavation is active now -
    must populate actual_start/actual_end and grade VERIFIED."""
    works_list = from_helsinki(_by_reference(FEATURES, "KP1900206-23"))
    site = works_list[0].sites[0]
    assert site.status == "Käynnissä"
    assert site.actual_start is not None
    assert site.actual_end is not None
    assert site.proposed_start is None
    assert site.date_confidence is DateConfidence.VERIFIED


def test_from_helsinki_upcoming_status_is_estimated_with_proposed_dates():
    """status "Tuleva" means not yet active - must populate only
    proposed_start/proposed_end and grade ESTIMATED, not VERIFIED."""
    works_list = from_helsinki(_by_reference(FEATURES, "KP2600373-3"))
    site = works_list[0].sites[0]
    assert site.status == "Tuleva"
    assert site.actual_start is None
    assert site.actual_end is None
    assert site.proposed_start is not None
    assert site.date_confidence is DateConfidence.ESTIMATED


def test_from_helsinki_location_description_is_address():
    works_list = from_helsinki(_by_reference(FEATURES, "KP1900206-23"))
    assert works_list[0].sites[0].location_description is not None


def test_from_helsinki_street_ref_is_never_populated():
    works_list = from_helsinki(FEATURES)
    assert all(s.street_ref is None for w in works_list for s in w.sites)
