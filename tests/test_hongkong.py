"""Tests for the Hong Kong (Transport Department / Highways Department
Roadworks Location) adapter.

Credential-free, live-verified 2026-08-24 - see the module docstring in
``streetworks.hongkong.client``. ``hongkong_roadworks_live_pull.json``
holds 3 REAL records trimmed from a real, unauthenticated pull (8 total),
spanning three real ``workstype`` values (Routine road maintenance
works, Structure maintenance works, Traffic diversion). Not synthetic.
All 8 real records in the live pull were ``worksstatus="In Progress"`` -
"Under Preparation" is a real, documented spec value but wasn't observed
live.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_hongkong
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.hongkong import BASE_URL, HongKongClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "hongkong_roadworks_live_pull.json"
RECORDS = json.loads(FIXTURE_PATH.read_text())


def _mock_feed() -> respx.Route:
    return respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=RECORDS))


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


def test_client_requires_no_credentials():
    HongKongClient()


@respx.mock
def test_iter_roadworks_needs_no_credentials_and_returns_every_record():
    _mock_feed()
    with HongKongClient() as client:
        records = list(client.iter_roadworks())
    assert len(records) == len(RECORDS)


@respx.mock
def test_iter_roadworks_sends_no_auth_params_or_headers():
    route = _mock_feed()
    with HongKongClient() as client:
        list(client.iter_roadworks())
    request = route.calls[0].request
    assert dict(request.url.params) == {}
    assert "Authorization" not in request.headers


# --------------------------------------------------------------------------- #
# Converter
# --------------------------------------------------------------------------- #


def test_from_hongkong_produces_one_works_per_record_no_grouping():
    works_list = from_hongkong(RECORDS)
    assert len(works_list) == len(RECORDS)
    assert all(len(w.sites) == 1 for w in works_list)


def test_from_hongkong_reference_is_roadworks_id():
    works_list = from_hongkong(RECORDS)
    refs = {w.reference for w in works_list}
    assert refs == {"33961", "33778", "33951"}


def test_from_hongkong_coordinate_is_real_wgs84_no_flip_needed():
    """latitude/longitude are already top-level fields, not GeoJSON
    (lon, lat) - no flip needed, unlike from_tfl/from_brussels."""
    works_list = from_hongkong(RECORDS)
    coord = works_list[0].sites[0].coordinate
    assert coord is not None
    assert coord.crs == "EPSG:4326"
    # real Hong Kong latitude is ~22.x, longitude ~114.x.
    assert 22 < coord.value[0] < 23
    assert 113 < coord.value[1] < 115


def test_from_hongkong_works_type_is_english_workstype():
    works_list = from_hongkong(RECORDS)
    types = {w.sites[0].works_type for w in works_list}
    assert types == {
        "Routine road maintenance works",
        "Structure maintenance works",
        "Traffic diversion",
    }


def test_from_hongkong_promoter_is_datasource():
    works_list = from_hongkong(RECORDS)
    assert all(w.promoter == "Highways Department" for w in works_list)


def test_from_hongkong_territory_and_administrative_area():
    works_list = from_hongkong(RECORDS)
    assert all(w.territory == "Hong Kong" for w in works_list)
    assert all(w.administrative_area == "Highways Department" for w in works_list)
    assert all(w.source_grade == SourceGrade.OPERATOR for w in works_list)


def test_from_hongkong_in_progress_status_is_verified_with_actual_dates():
    works_list = from_hongkong(RECORDS)
    site = works_list[0].sites[0]
    assert site.status == "In Progress"
    assert site.actual_start is not None
    assert site.proposed_start is None
    assert site.date_confidence is DateConfidence.VERIFIED


def test_from_hongkong_under_preparation_status_yields_proposed_dates():
    record = dict(RECORDS[0])
    record["worksstatus"] = "Under Preparation"
    works_list = from_hongkong([record])
    site = works_list[0].sites[0]
    assert site.actual_start is None
    assert site.proposed_start is not None
    assert site.date_confidence is DateConfidence.ESTIMATED


def test_from_hongkong_location_description_is_locdesc():
    works_list = from_hongkong(RECORDS)
    assert all(w.sites[0].location_description for w in works_list)
    assert "Nam Cheong Station" in works_list[0].sites[0].location_description


def test_from_hongkong_traffic_management_is_empty_remark_treated_as_none():
    """Every real record checked had an empty remark - a real, honest
    gap, not an error."""
    works_list = from_hongkong(RECORDS)
    assert all(w.sites[0].traffic_management is None for w in works_list)


def test_from_hongkong_chinese_fields_stay_on_raw_only():
    works_list = from_hongkong(RECORDS)
    site = works_list[0].sites[0]
    assert site.raw["workstype_tc"] == "例行道路保養工程"
    assert site.works_type == "Routine road maintenance works"
