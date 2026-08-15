"""Tests for the Transport for London (TfL Road Disruption) adapter.

Credential-free, live-verified 2026-08-15 - see the module docstring in
``streetworks.tfl.client``. ``tfl_disruptions_live_pull.json`` holds 3
REAL records trimmed from a real, unauthenticated pull (118 total): one
"TfL works" and one "Utility works" real Works record, and one real
non-Works record ("Hazards"/Fire, to prove the roadworks filter excludes
it). Not synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_tfl
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.tfl import BASE_URL, TflClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tfl_disruptions_live_pull.json"
RECORDS = json.loads(FIXTURE_PATH.read_text())
WORKS = [r for r in RECORDS if r["category"] == "Works"]


def _mock_feed() -> respx.Route:
    return respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=RECORDS))


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_disruptions_needs_no_credentials_and_is_unfiltered():
    _mock_feed()
    with TflClient() as tfl:
        records = list(tfl.iter_disruptions())
    assert len(records) == len(RECORDS)


@respx.mock
def test_iter_roadworks_excludes_non_works_category():
    _mock_feed()
    with TflClient() as tfl:
        records = list(tfl.iter_roadworks())
    assert len(records) == len(WORKS)
    assert all(r["category"] == "Works" for r in records)


@respx.mock
def test_iter_disruptions_omits_app_key_when_not_supplied():
    route = _mock_feed()
    with TflClient() as tfl:
        list(tfl.iter_disruptions())
    assert "app_key" not in route.calls[0].request.url.params


@respx.mock
def test_iter_disruptions_sends_app_key_when_supplied():
    route = _mock_feed()
    with TflClient(app_key="my-key") as tfl:
        list(tfl.iter_disruptions())
    assert route.calls[0].request.url.params["app_key"] == "my-key"


def test_client_requires_no_credentials():
    TflClient()


# --------------------------------------------------------------------------- #
# Converter
# --------------------------------------------------------------------------- #


def test_from_tfl_produces_one_works_per_record_no_grouping():
    works_list = from_tfl(WORKS)
    assert len(works_list) == len(WORKS)
    assert all(len(w.sites) == 1 for w in works_list)


def test_from_tfl_reference_is_id():
    works_list = from_tfl(WORKS)
    refs = {w.reference for w in works_list}
    assert "TIMS-231236" in refs


def test_from_tfl_coordinate_is_flipped_to_lat_lon():
    """Genuine WGS84 with an explicit stated CRS - GeoJSON's (lon, lat)
    must be flipped to this SDK's (lat, lon)."""
    works_list = from_tfl(WORKS)
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.crs == "EPSG:4326"
    # real London latitude is ~51.x, longitude is small/negative.
    assert 51 < coord.value[0] < 52
    assert -1 < coord.value[1] < 1


def test_from_tfl_works_type_is_subcategory():
    works_list = from_tfl(WORKS)
    types = {w.sites[0].works_type for w in works_list}
    assert types == {"TfL works", "Utility works"}


def test_from_tfl_promoter_is_never_populated():
    """No per-record organisation-name field exists in this schema."""
    works_list = from_tfl(WORKS)
    assert all(w.promoter is None for w in works_list)


def test_from_tfl_territory_and_administrative_area():
    works_list = from_tfl(WORKS)
    assert all(w.territory == "England" for w in works_list)
    assert all(w.administrative_area == "Transport for London" for w in works_list)
    assert all(w.source_grade == SourceGrade.OPERATOR for w in works_list)


def test_from_tfl_active_status_is_verified_with_actual_dates():
    works_list = from_tfl(WORKS)
    site = works_list[0].sites[0]
    assert site.status == "Active"
    assert site.actual_start is not None
    assert site.proposed_start is None
    assert site.date_confidence is DateConfidence.VERIFIED


def test_from_tfl_traffic_management_is_comments():
    works_list = from_tfl(WORKS)
    assert all(w.sites[0].traffic_management for w in works_list)


def test_from_tfl_location_description_is_location():
    works_list = from_tfl(WORKS)
    assert all(w.sites[0].location_description for w in works_list)
