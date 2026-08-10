"""Tests for the Oslo (SøkSys activities) adapter.

Credential-free, live-verified 2026-08-10 - see the module docstring in
``streetworks.oslo.client``. ``oslo_soksys_activities_live_pull.json``
holds 13 REAL features trimmed from a real, unauthenticated pull (1354
total): a real 8-row multi-geometry permit (activity_id 3cc7a5e7...,
4 distinct real ids each duplicated once - a real tiling artifact, and
the 4 distinct ids are 4 genuinely separate real sub-areas of one
permit), a real exact-duplicate-id pair (activity_id 86a29225...), a
plain single-row Gravearbeid permit, a plain single-row Arbeidstillatelse
permit, and a Containerutsett permit (to prove client-side exclusion).
Not synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_oslo
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.oslo import ACTIVITIES_URL, OsloClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "oslo_soksys_activities_live_pull.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())
FEATURES = FIXTURE_JSON["features"]


def _by_activity(features: list[dict], activity_id: str) -> list[dict]:
    return [f for f in features if f["properties"]["activity_id"] == activity_id]


def _mock_feed() -> respx.Route:
    # The real API double-encodes its response body (a JSON string
    # literal containing escaped GeoJSON) - json= here is dumped once by
    # httpx.Response, so passing an already-dumped string reproduces the
    # real double-encoding. See module docstring / client.py's own.
    return respx.get(ACTIVITIES_URL).mock(
        return_value=httpx.Response(200, json=json.dumps(FIXTURE_JSON))
    )


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_activities_needs_no_credentials_and_is_unfiltered():
    _mock_feed()
    with OsloClient() as oslo:
        features = list(oslo.iter_activities())
    assert len(features) == len(FEATURES)  # includes Containerutsett + duplicates


@respx.mock
def test_iter_roadworks_excludes_containerutsett():
    _mock_feed()
    with OsloClient() as oslo:
        features = list(oslo.iter_roadworks())
    assert len(features) == len(FEATURES) - 1  # only the one Containerutsett row
    assert all(f["properties"]["activity_type"] != "Containerutsett" for f in features)


@respx.mock
def test_iter_activities_sends_the_real_extent_and_filter_params():
    route = _mock_feed()
    with OsloClient() as oslo:
        list(oslo.iter_activities())
    params = route.calls[0].request.url.params
    assert params["filter"] == "atimequick=4"
    assert "," in params["extent"]


def test_client_requires_no_credentials():
    OsloClient()


# --------------------------------------------------------------------------- #
# Converter - id-dedupe, then activity_id grouping
# --------------------------------------------------------------------------- #


def test_from_oslo_dedupes_exact_id_duplicates():
    """The 2-row exact-duplicate-id permit (86a29225...) must collapse
    to a single WorksSite, not two."""
    works_list = from_oslo(_by_activity(FEATURES, "86a29225-958b-460f-aad0-b245005bbe2b"))
    assert len(works_list) == 1
    assert len(works_list[0].sites) == 1


def test_from_oslo_keeps_genuine_multi_site_permit_as_several_worksites():
    """activity_id 3cc7a5e7... has 8 raw rows but only 4 distinct real
    ids (each duplicated once) - must dedupe to 4 WorksSites under one
    Works, not 8 and not 1."""
    works_list = from_oslo(_by_activity(FEATURES, "3cc7a5e7-4698-45c5-815d-123f982e72dc"))
    assert len(works_list) == 1
    works = works_list[0]
    assert len(works.sites) == 4
    assert works.reference == "2024/89422"
    site_refs = {s.reference for s in works.sites}
    assert site_refs == {
        "3ac981ed-988a-479a-9b8d-c9c0f2eb7043",
        "4c9bab11-ef1d-47f1-8b9c-810cc44a26e8",
        "68265163-77d6-44c5-b3c2-58e93d7dee4c",
        "b8d6c8f7-8def-4643-b15a-d526a6da526b",
    }


def test_from_oslo_coordinate_stays_unswapped_easting_northing():
    """EPSG:25832 is projected - Coordinate.value must be (easting,
    northing) as given, never swapped to (lat, lon)."""
    works_list = from_oslo(_by_activity(FEATURES, "00af5f6c-297e-4e67-9abb-3fa69b5a854e"))
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.crs == "EPSG:25832"
    # real easting is ~597000, real northing is ~6644000 - easting must
    # stay first, not be swapped with the much larger northing value.
    assert 500000 < coord.value[0] < 700000
    assert coord.value[1] > 6000000


def test_from_oslo_polygon_uses_first_ring_vertex_as_value_only():
    works_list = from_oslo(_by_activity(FEATURES, "00af5f6c-297e-4e67-9abb-3fa69b5a854e"))
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.points is None
    assert coord.parts is None


def test_from_oslo_territory_and_administrative_area():
    works_list = from_oslo(FEATURES)
    assert all(w.territory == "Norway" for w in works_list)
    assert all(w.administrative_area == "Oslo kommune" for w in works_list)
    assert all(w.source_grade == SourceGrade.REGISTER for w in works_list)


def test_from_oslo_promoter_is_sender():
    works_list = from_oslo(_by_activity(FEATURES, "00a51865-95e4-4dbc-a689-c1035cbf179d"))
    assert works_list[0].promoter == "VEISKILTING AS"


def test_from_oslo_works_type_is_activity_type():
    works_list = from_oslo(_by_activity(FEATURES, "00af5f6c-297e-4e67-9abb-3fa69b5a854e"))
    assert works_list[0].sites[0].works_type == "Gravearbeid"


def test_from_oslo_reference_is_file_number():
    works_list = from_oslo(_by_activity(FEATURES, "00a51865-95e4-4dbc-a689-c1035cbf179d"))
    assert works_list[0].reference == "2026/52252"


def test_from_oslo_date_confidence_is_estimated_not_verified():
    """status is real ('Innvilget' = Approved) but a granted permit is
    not a confirmed-happening signal - date_confidence must stay
    ESTIMATED, matching Copenhagen/NYC DOT/Chicago/Paris."""
    works_list = from_oslo(_by_activity(FEATURES, "00af5f6c-297e-4e67-9abb-3fa69b5a854e"))
    site = works_list[0].sites[0]
    assert site.status == "Innvilget"
    assert site.date_confidence is DateConfidence.ESTIMATED
    assert site.proposed_start is not None
    assert site.actual_start is None
    assert site.actual_end is None


def test_from_oslo_street_ref_is_never_populated():
    works_list = from_oslo(FEATURES)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_oslo_containerutsett_still_converts_when_passed_directly():
    """from_oslo() itself never filters by activity_type - only
    OsloClient.iter_roadworks() does, matching the Roma/Copenhagen
    precedent that the converter never filters, only the client does."""
    works_list = from_oslo(_by_activity(FEATURES, "32162db1-dd5a-46a9-9deb-bd4e71b422f7"))
    assert len(works_list) == 1
    assert works_list[0].sites[0].works_type == "Containerutsett"
