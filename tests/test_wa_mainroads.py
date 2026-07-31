"""Tests for the Western Australia (Main Roads WA WebEOC Roadworks) adapter.

Credential-free, live-verified from day one - see the module docstring in
``streetworks.au.wa``. ``wa_mainroads_live_pull.json`` holds five REAL
features trimmed from a real, unauthenticated pull (2026-07-31) against
layer 2: a local road (``Road=="LOCAL ROAD"`` sentinel), a state road with
a ``SeeMoreUrl`` reference link, a "PTA Works" record (a real, undocumented
work type), a record with an empty ``Suburb``, and a Pilbara-region record
whose ``SeeMoreUrl`` has no ``https://`` scheme - not synthetic.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.au.wa import BASE_URL, ROADWORKS_LAYER, WaMainRoadsClient
from streetworks.common import DateConfidence, from_au_wa_mainroads
from streetworks.common.from_au_wa_mainroads import _coordinate, _web_mercator_to_wgs84

LIVE_PULL_PATH = Path(__file__).parent / "fixtures" / "wa_mainroads_live_pull.json"
LIVE_PULL_JSON = json.loads(LIVE_PULL_PATH.read_text())
LIVE_FEATURES = LIVE_PULL_JSON["features"]


# --------------------------------------------------------------------------- #
# Client wiring - the pagination strategy itself is tested generically in
# test_arcgis_client.py; this only confirms WaMainRoadsClient reaches the
# real layer/query endpoint correctly, the same minimal shape
# test_arcgis_jersey.py uses.
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_queries_the_real_roadworks_layer():
    respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectIdField": "FID",
                "maxRecordCount": 2000,
                "advancedQueryCapabilities": {"supportsPagination": True},
                "fields": [{"name": "FID"}],
            },
        )
    )
    respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}/query").mock(
        return_value=httpx.Response(200, json=LIVE_PULL_JSON)
    )
    with WaMainRoadsClient() as wa:
        features = list(wa.iter_roadworks())
    assert len(features) == 5
    assert features[0]["properties"]["GlobalID"] == "ad4ef33e-90a6-4c11-bd8d-003cf1aec4b8"


@respx.mock
def test_iter_roadworks_requests_outsr_4326():
    route = respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectIdField": "FID",
                "maxRecordCount": 2000,
                "advancedQueryCapabilities": {"supportsPagination": True},
                "fields": [{"name": "FID"}],
            },
        )
    )
    query_route = respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with WaMainRoadsClient() as wa:
        list(wa.iter_roadworks())
    assert route.called
    assert query_route.calls[0].request.url.params.get("outSR") == "4326"


# --------------------------------------------------------------------------- #
# Gating check 1 - the runtime coordinate guard
# --------------------------------------------------------------------------- #


def test_web_mercator_to_wgs84_round_trips_a_known_point():
    # Perth CBD (115.8605, -31.9505) forward-projected to EPSG:3857 via the
    # standard spherical Mercator formula.
    lon, lat = _web_mercator_to_wgs84(12897531.863054074, -3756814.7353761178)
    assert lon == pytest.approx(115.8605, abs=1e-6)
    assert lat == pytest.approx(-31.9505, abs=1e-6)


def test_coordinate_guard_reprojects_web_mercator_metres():
    """Projected metres slipping through (outSR ignored) must be caught by
    value range and reprojected explicitly, never passed through as if
    they were degrees."""
    feature = {
        "geometry": {"type": "Point", "coordinates": [12897531.863054074, -3756814.7353761178]}
    }
    coordinate = _coordinate(feature)
    assert coordinate is not None
    assert coordinate.crs == "EPSG:4326"
    lon, lat = coordinate.value
    assert 115 < lon < 117  # plausible WA longitude, not a raw Web Mercator metre value
    assert -33 < lat < -31


def test_coordinate_guard_passes_through_genuine_wgs84():
    """A point already in plausible WGS84 degree range (outSR genuinely
    honoured, the confirmed-live case) must not be altered."""
    feature = {"geometry": {"type": "Point", "coordinates": [115.8605, -31.9505]}}
    coordinate = _coordinate(feature)
    assert coordinate is not None
    assert coordinate.crs == "EPSG:4326"
    assert coordinate.value == (115.8605, -31.9505)


def test_coordinate_guard_handles_missing_or_non_point_geometry():
    assert _coordinate({"geometry": None}) is None
    assert _coordinate({"geometry": {"type": "Polygon", "coordinates": []}}) is None
    assert _coordinate({}) is None


# --------------------------------------------------------------------------- #
# Gating check 2 - the locked DD/MM/YYYY date format
# --------------------------------------------------------------------------- #


def test_real_pull_confirms_dd_mm_yyyy_date_order():
    """Real finding: 397/681 real date-field values across a full live
    pull have a first component > 12 (can only be a day), zero have a
    second component > 12 - locking DD/MM, not the US MM/DD order."""
    works = from_au_wa_mainroads(LIVE_FEATURES)
    # EntryDate "15/10/2024 10:46:08" (day=15) proves day-first order -
    # this record's own DateStarte would parse identically either way, so
    # the disambiguating evidence is EntryDate, kept on .raw.
    site = next(w for w in works if w.reference == "e32798b8-9f42-4f51-86fd-d7347c53efb6").sites[0]
    entry_date = site.raw.get("properties", {}).get("EntryDate")
    assert entry_date == "15/10/2024 10:46:08"
    assert site.proposed_start == datetime(2024, 6, 4, 10, 44, 0)


def test_date_parsing_is_timezone_naive():
    works = from_au_wa_mainroads(LIVE_FEATURES)
    site = works[0].sites[0]
    assert site.proposed_start.tzinfo is None
    assert site.proposed_end.tzinfo is None


# --------------------------------------------------------------------------- #
# Real field-mapping findings
# --------------------------------------------------------------------------- #


def test_local_road_sentinel_is_resolved_to_the_real_local_road_name():
    """Real finding: Road=='LOCAL ROAD' is a literal sentinel, not a real
    road name - LocalRoadName carries the real name in exactly those
    records, confirmed live to be perfectly mutually exclusive."""
    works = from_au_wa_mainroads(LIVE_FEATURES)
    boddington = next(w for w in works if w.reference == "ad4ef33e-90a6-4c11-bd8d-003cf1aec4b8")
    # The sentinel string itself must never leak into location_description.
    assert "LOCAL ROAD" not in boddington.sites[0].location_description
    assert "Ashcroft Rd" in boddington.sites[0].location_description


def test_reference_is_keyed_on_global_id_not_fid():
    works = from_au_wa_mainroads(LIVE_FEATURES)
    references = {w.reference for w in works}
    assert references == {f["properties"]["GlobalID"] for f in LIVE_FEATURES}
    # FID values are real, distinct integers - reference must not be one of them.
    fids = {str(f["properties"]["FID"]) for f in LIVE_FEATURES}
    assert not (references & fids)


def test_work_status_always_empty_never_promotes_past_estimated():
    """Real finding: WorkStatus is a real field, confirmed always empty
    (0/227 in one full live pull) - status maps to None, not '', and
    date_confidence never reaches VERIFIED since there's no live signal
    to justify it."""
    works = from_au_wa_mainroads(LIVE_FEATURES)
    for w in works:
        assert w.sites[0].status is None
        assert w.sites[0].date_confidence is DateConfidence.ESTIMATED
        assert w.sites[0].actual_start is None
        assert w.sites[0].actual_end is None


def test_real_undocumented_pta_works_type_is_carried_through():
    """Real finding: the ArcGIS item's own catalogue documents four work
    types (Maintenance/Resurfacing/Upgrades/Utility works) - a live pull
    found a real fifth value, 'PTA Works', not filtered out here."""
    works = from_au_wa_mainroads(LIVE_FEATURES)
    pta = next(w for w in works if w.sites[0].works_type == "PTA Works")
    assert "Midland" in pta.sites[0].location_description


def test_see_more_url_becomes_a_notice_with_no_fabricated_text():
    """SeeMoreName is confirmed always null in real data - Notice.text must
    stay honestly None, not a fabricated label like 'Find out more'."""
    works = from_au_wa_mainroads(LIVE_FEATURES)
    with_link = next(w for w in works if w.sites[0].notices)
    notice = with_link.sites[0].notices[0]
    assert notice.text is None
    assert notice.raw == (
        "https://www.mainroads.wa.gov.au/4a8ff1/globalassets/projects-initiatives/"
        "projects/metro/swan-river-crossings/src-qv-from-tydeman-to-fremantle-traffic-bridge-psp-detour.jpg"
    )


def test_see_more_url_without_a_scheme_is_carried_through_unmodified():
    """Real finding: at least one real SeeMoreUrl value has no https://
    scheme at all - never silently corrected."""
    works = from_au_wa_mainroads(LIVE_FEATURES)
    pilbara = next(w for w in works if w.reference == "ff0549df-87e0-45a5-9de0-23c8b0c73612")
    notice = pilbara.sites[0].notices[0]
    assert notice.raw == (
        "www.mainroads.wa.gov.au/projects-initiatives/all-projects/regional/karratha-tom-price/"
    )


def test_no_see_more_url_means_no_notices():
    works = from_au_wa_mainroads(LIVE_FEATURES)
    boddington = next(w for w in works if w.reference == "ad4ef33e-90a6-4c11-bd8d-003cf1aec4b8")
    assert boddington.sites[0].notices == ()


def test_from_au_wa_mainroads_maps_the_real_boddington_feature():
    works = from_au_wa_mainroads(LIVE_FEATURES)
    work = next(w for w in works if w.reference == "ad4ef33e-90a6-4c11-bd8d-003cf1aec4b8")
    assert work.territory == "Australia"
    assert work.administrative_area == "Main Roads Western Australia"
    assert work.coordinate.value == (116.410315549036, -32.8307254877164)
    assert work.coordinate.crs == "EPSG:4326"
    assert work.coordinate.points is None

    site = work.sites[0]
    assert site.works_type == "Maintenance"
    assert site.traffic_management == "Long term Road Closure - April 2023 to April 2038"
    assert site.proposed_start == datetime(2023, 4, 1, 0, 0, 0)
    assert site.proposed_end == datetime(2038, 4, 30, 0, 0, 0)
