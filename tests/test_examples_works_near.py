"""Tests for examples/works_near/ - the UK-first works-near-here join
layer, kept as example code (not a package export) - see
examples/works_near/query.py's own module docstring for why.

HTTP is mocked with respx and existing fixtures (Traffic Wales RSS,
National Highways DATEX JSON, Street Manager sandbox permits, SRWR
extract lines). No live network, no credentials.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import httpx
import pytest
import respx

from examples.works_near.query import (
    V1_DISTANCE_PROVIDERS,
    V1_USRN_PROVIDERS,
    _live_enough,
    _unverified_registry_keys,
    _usrn_matches,
    haversine_m,
    nearest_wgs84_distance_m,
    v1_providers,
    works_near,
    works_near_usrn,
)
from streetworks.common import Coordinate, Works, WorksSite
from streetworks.registry import _REGISTRY
from streetworks.streetmanager import StreetManagerClient

FIXTURES = Path(__file__).parent / "fixtures"
WALES_RSS = (FIXTURES / "trafficwales_roadworks.xml").read_text(encoding="utf-8")
NH_JSON = json.loads((FIXTURES / "nationalhighways_closures_planned.json").read_text())
SM_PERMITS = json.loads((FIXTURES / "streetmanager_permits_sandbox.json").read_text())

# Real Traffic Wales fixture points (see tests/fixtures/trafficwales_roadworks.xml).
RAGLAN = (51.78344, -2.939548)
NANTGAREDIG = (51.871273, -4.227312)
KILGETTY = (51.728565, -4.724212)

# Real National Highways fixture point (A27 Falmer slip).
A27_FALMER = (50.863689, -0.07643)

SANDBOX = "https://api.sandbox.manage-roadworks.service.gov.uk"

SRWR_HEADER = (
    '02,000,"#SRWR data for 2026-07-04, Produced 2026-07-05 02:00, '
    'For licensing visit https://roadworks.scot/opendata"'
)
SRWR_ACTIVITY_A = (
    "02,001,03268777,2022-12-09 09:13:35.08,2026-07-04 04:20:09.72,"
    '010360002,"TL002-S1711",009066001,02,"False",,2,84202034,"False"'
)
SRWR_ACTIVITY_B = (
    "02,001,03889647,2025-09-03 10:03:03.88,2026-07-04 04:12:28.06,"
    '010250001,"EG001-FULMAR2",009066001,02,"False",,1,84202352,"False"'
)
SRWR_PHASE_A = (
    "02,007,03268777,2022-12-09 09:13:35.08,2026-07-04 04:20:09.72,,"
    '"Outside Crossgates Cottages",2,,05,07,"False",'
    '"LINESTRING (333226.5 709261.7, 333285.0 709270.1)",03,07,"False","False",'
    '"False","False","False","False","False","False",'
    '"True","False","False","False","False","False"'
)
SRWR_PHASE_B = (
    "02,007,03889647,2025-09-03 10:03:03.88,2026-07-04 04:12:28.06,,"
    '"Somewhere else",1,,05,07,"False",'
    '"LINESTRING (1 1, 2 2)",03,07,"False","False",'
    '"False","False","False","False","False","False",'
    '"False","False","False","False","False","False"'
)
SRWR_EXTRACT = "\r\n".join(
    [SRWR_HEADER, SRWR_ACTIVITY_A, SRWR_ACTIVITY_B, SRWR_PHASE_A, SRWR_PHASE_B]
)


def _auth_response() -> dict:
    import base64
    import time

    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = (
        base64.urlsafe_b64encode(json.dumps({"exp": time.time() + 3600}).encode())
        .rstrip(b"=")
        .decode()
    )
    return {
        "idToken": f"{header}.{payload}.sig",
        "accessToken": "access",
        "refreshToken": "refresh",
        "organisationReference": "1234",
    }


def _wales_route() -> None:
    respx.get("https://traffic.wales/feeds/roadworks/rss.xml").mock(
        return_value=httpx.Response(200, content=WALES_RSS.encode())
    )


def _nh_route() -> None:
    respx.get("https://api.data.nationalhighways.co.uk/roads/v2.0/closures").mock(
        return_value=httpx.Response(200, json=NH_JSON, headers={"x-next": ""})
    )


# --------------------------------------------------------------------------- #
# Distance helper
# --------------------------------------------------------------------------- #


def test_haversine_zero_for_the_same_point():
    assert haversine_m(*RAGLAN, *RAGLAN) == 0.0


def test_haversine_known_distance_is_plausible():
    # Raglan -> Kilgetty is ~120 km on the ground; a 10% band is enough to
    # catch a degrees/radians or km/m mix-up without claiming survey accuracy.
    distance_m = haversine_m(*RAGLAN, *KILGETTY)
    assert 100_000 < distance_m < 140_000


def test_distance_filter_uses_wgs84_only_and_skips_other_crs():
    wgs = Works(
        reference="wgs",
        coordinate=Coordinate(value=RAGLAN, crs="EPSG:4326"),
        sites=(WorksSite(coordinate=Coordinate(value=RAGLAN, crs="EPSG:4326")),),
    )
    bng = Works(
        reference="bng",
        coordinate=Coordinate(value=(425334.09, 533885.19), crs="EPSG:27700"),
        sites=(WorksSite(coordinate=Coordinate(value=(425334.09, 533885.19), crs="EPSG:27700")),),
    )
    assert nearest_wgs84_distance_m(wgs, *RAGLAN) == 0.0
    assert nearest_wgs84_distance_m(bng, *RAGLAN) is None


def test_usrn_match_reads_works_and_site_and_street_ref():
    from streetworks.common import Identifier

    on_works = Works(location_usrn="84202034")
    on_site = Works(sites=(WorksSite(location_usrn="84202034"),))
    on_ref = Works(sites=(WorksSite(street_ref=Identifier(scheme="usrn", value="84202034")),))
    other = Works(location_usrn="999")
    assert _usrn_matches(on_works, "84202034")
    assert _usrn_matches(on_site, "84202034")
    assert _usrn_matches(on_ref, "84202034")
    assert not _usrn_matches(other, "84202034")


# --------------------------------------------------------------------------- #
# Provider selection - skip unverified / credential-gated / no-geometry
# --------------------------------------------------------------------------- #


def test_v1_allowlist_excludes_unverified_and_unavailable_and_no_geometry():
    unverified = _unverified_registry_keys()
    assert unverified  # the skip rule is meaningless if the set is empty
    assert unverified.isdisjoint(V1_DISTANCE_PROVIDERS | V1_USRN_PROVIDERS)
    assert "maproad" in unverified
    assert "vejdirektoratet" in unverified
    assert "trafikverket" in unverified
    # TrafficWatchNI is verified and keyless but has no geometry.
    assert "trafficwatchni" not in V1_DISTANCE_PROVIDERS
    assert "trafficwatchni" not in V1_USRN_PROVIDERS
    # Open USRN is a gazetteer, not a works feed.
    assert "openusrn" not in V1_DISTANCE_PROVIDERS
    assert "openusrn" not in V1_USRN_PROVIDERS


def test_live_enough_rejects_unverified_even_with_credentials_in_hand():
    trafikverket = next(e for e in _REGISTRY if e.key == "trafikverket")
    assert not trafikverket.verified
    assert _live_enough(trafikverket, credentials_supplied=True) is False


def test_live_enough_rejects_credential_gated_without_credentials():
    nh = next(e for e in _REGISTRY if e.key == "nationalhighways")
    assert nh.verified and nh.credentials
    assert _live_enough(nh, credentials_supplied=False) is False
    assert _live_enough(nh, credentials_supplied=True) is True


def test_v1_providers_skips_national_highways_without_a_key():
    planned = v1_providers(lat=RAGLAN[0], lon=RAGLAN[1])
    assert planned == ("trafficwales",)


def test_v1_providers_includes_national_highways_when_key_supplied():
    planned = v1_providers(lat=RAGLAN[0], lon=RAGLAN[1], national_highways_key="k")
    assert planned == ("trafficwales", "nationalhighways")


def test_v1_providers_usrn_without_sources_is_empty():
    assert v1_providers(usrn=84202034) == ()


# --------------------------------------------------------------------------- #
# works_near - validation
# --------------------------------------------------------------------------- #


def test_works_near_requires_a_point_or_a_usrn():
    with pytest.raises(ValueError, match="lat/lon and/or usrn"):
        works_near()


def test_works_near_requires_lat_and_lon_together():
    with pytest.raises(ValueError, match="together"):
        works_near(lat=51.0)


def test_works_near_rejects_negative_radius():
    with pytest.raises(ValueError, match="radius_m"):
        works_near(*RAGLAN, radius_m=-1)


# --------------------------------------------------------------------------- #
# works_near - distance path (Traffic Wales + National Highways)
# --------------------------------------------------------------------------- #


@respx.mock
def test_distance_filter_keeps_nearby_wales_items_and_drops_far_ones():
    _wales_route()
    # 1 km around the Raglan point: two fixture items share that exact
    # georss:point; Nantgaredig and Kilgetty are tens of km away.
    hits = works_near(*RAGLAN, radius_m=1_000)
    assert {hit.provider for hit in hits} == {"trafficwales"}
    assert all(hit.match == "distance" for hit in hits)
    assert all(hit.distance_m is not None and hit.distance_m <= 1_000 for hit in hits)
    assert len(hits) == 2
    descriptions = {hit.works.sites[0].location_description for hit in hits}
    assert any(d and "Raglan" in d for d in descriptions)
    assert not any(d and "Kilgetty" in d for d in descriptions)


@respx.mock
def test_distance_path_does_not_call_national_highways_without_credentials():
    wales = respx.get("https://traffic.wales/feeds/roadworks/rss.xml").mock(
        return_value=httpx.Response(200, content=WALES_RSS.encode())
    )
    nh = respx.get("https://api.data.nationalhighways.co.uk/roads/v2.0/closures").mock(
        return_value=httpx.Response(200, json=NH_JSON)
    )
    works_near(*RAGLAN, radius_m=1_000)
    assert wales.call_count == 1
    assert nh.call_count == 0


@respx.mock
def test_no_cross_provider_dedupe_keeps_every_record():
    _wales_route()
    _nh_route()
    # Wide enough that every WGS84 fixture record is in range - the point
    # is that Traffic Wales and National Highways results are concatenated,
    # never merged, even if a caller later imagines they "look the same".
    hits = works_near(*RAGLAN, radius_m=500_000, national_highways_key="test-key")
    providers = [hit.provider for hit in hits]
    assert providers.count("trafficwales") == 4  # all four Wales fixture items
    assert providers.count("nationalhighways") == 3  # three roadworks situations
    # Four Wales items share reference=None; they are still four rows.
    assert len(hits) == 7
    wales = [hit for hit in hits if hit.provider == "trafficwales"]
    nh = [hit for hit in hits if hit.provider == "nationalhighways"]
    assert {hit.works.territory for hit in wales} == {"Wales"}
    assert {hit.works.territory for hit in nh} == {"England"}
    assert {hit.works.administrative_area for hit in nh} == {"National Highways"}


@respx.mock
def test_national_highways_distance_filter_around_its_own_point():
    _wales_route()
    _nh_route()
    hits = works_near(*A27_FALMER, radius_m=5_000, national_highways_key="test-key")
    nh_hits = [hit for hit in hits if hit.provider == "nationalhighways"]
    assert nh_hits
    assert any(hit.works.reference == "467118" for hit in nh_hits)
    # Welsh fixture points are hundreds of km from Falmer.
    assert not any(hit.provider == "trafficwales" for hit in hits)


# --------------------------------------------------------------------------- #
# works_near - USRN path (SRWR + Street Manager)
# --------------------------------------------------------------------------- #


def test_usrn_path_matches_srwr_extract_and_skips_other_activities():
    hits = works_near_usrn(84202034, srwr_source=io.StringIO(SRWR_EXTRACT))
    assert len(hits) == 1
    assert hits[0].provider == "srwr"
    assert hits[0].match == "usrn"
    assert hits[0].distance_m is None
    assert hits[0].works.location_usrn == "84202034"
    assert hits[0].works.reference == "TL002-S1711"
    assert hits[0].works.territory == "Scotland"


def test_usrn_path_without_sources_returns_empty_and_does_not_need_a_point():
    assert works_near_usrn(84202034) == []


@respx.mock
def test_usrn_path_filters_street_manager_permits_client_side():
    respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        return_value=httpx.Response(200, json=_auth_response())
    )
    route = respx.get(f"{SANDBOX}/v6/reporting/permits").mock(
        return_value=httpx.Response(
            200, json={"pagination": {"has_next_page": False}, "rows": SM_PERMITS["rows"]}
        )
    )
    with StreetManagerClient("user@example.com", "pw") as sm:
        hits = works_near_usrn(33909869, street_manager=sm)

    assert route.calls[0].request.url.params["usrn"] == "33909869"
    assert len(hits) == 1
    assert hits[0].provider == "streetmanager"
    assert hits[0].match == "usrn"
    assert hits[0].works.reference == "UG00065061596"
    assert hits[0].works.location_usrn == "33909869"
    # The other fixture work (UG27724003165) is on USRN 33910212.
    assert all(hit.works.reference != "UG27724003165" for hit in hits)


@respx.mock
def test_point_plus_usrn_concatenates_distance_and_usrn_hits():
    _wales_route()
    hits = works_near(
        *RAGLAN,
        usrn=84202034,
        radius_m=1_000,
        srwr_source=io.StringIO(SRWR_EXTRACT),
    )
    assert {hit.provider for hit in hits} == {"trafficwales", "srwr"}
    assert any(hit.match == "distance" for hit in hits)
    assert any(hit.match == "usrn" and hit.provider == "srwr" for hit in hits)
    # USRN-only hits sort after distance hits.
    assert hits[-1].provider == "srwr"
