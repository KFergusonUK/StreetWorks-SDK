"""Tests for the National Highways DATEX II v3.4 JSON adapter.

The fixture is four real situations (lightly trimmed - one record kept per
situation) taken from a live call to
``GET /roads/v2.0/closures?closureType=planned``, covering the cases that
matter: a single-location roadMaintenance record, a multi-location
roadMaintenance record, a multi-location constructionWork record, and a
multi-location authorityOperation record (not roadworks - exercises the
cause.causeType filtering).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import respx

from streetworks.datex2 import ClosureType, NationalHighwaysClient
from streetworks.datex2.nationalhighways import parse_situations

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "nationalhighways_closures_planned.json").read_text(
        encoding="utf-8"
    )
)


def _situation(situations, situation_id):
    return next(s for s in situations if s.id == situation_id)


def test_parses_single_location_roadmaintenance_record():
    situations = parse_situations(FIXTURE)
    s = _situation(situations, "467118")
    assert len(s.roadworks) == 1 and len(s.measures) == 0

    works = s.roadworks[0]
    assert works.record_type == "MaintenanceWorks"
    assert works.cause_type == "roadMaintenance"
    assert works.road_maintenance_type == "maintenanceWork"
    assert works.comments == ("A27 westbound Falmer exit slip road closure",)
    assert works.source_name == "roadworks"
    assert works.validity.status == "planned"
    assert works.validity.overall_start == datetime(2026, 6, 17, 5, tzinfo=timezone.utc)
    assert works.validity.overall_end == datetime(2026, 7, 26, 19, tzinfo=timezone.utc)

    assert works.location.kind == "LinearLocation"
    assert len(works.location.points) == 16
    assert works.location.point == (50.863689, -0.07643)
    assert works.location.carriageway == "slipRoads"
    assert works.location.road_number == "A27"


def test_parses_multi_location_roadmaintenance_record():
    situations = parse_situations(FIXTURE)
    works = _situation(situations, "473996").roadworks[0]
    assert works.record_type == "MaintenanceWorks"
    assert works.validity.status == "suspended"
    assert works.location.kind == "LocationGroupByList"
    # concatenation of all 11 locationContainedInGroup segments
    assert len(works.location.points) == 147
    assert works.location.point == (52.572002, -0.320257)


def test_parses_construction_work_record():
    situations = parse_situations(FIXTURE)
    works = _situation(situations, "458159").roadworks[0]
    assert works.record_type == "ConstructionWorks"
    assert works.cause_type == "constructionWork"
    assert works.construction_work_type == "roadImprovementOrUpgrading"
    assert works.road_maintenance_type is None
    assert len(works.location.points) == 87


def test_authority_operation_is_not_roadworks():
    """cause.causeType outside {roadMaintenance, constructionWork} must land in
    .measures, not .roadworks - this is the whole point of keying off cause
    instead of a (nonexistent, in JSON) record type."""
    situations = parse_situations(FIXTURE)
    s = _situation(situations, "409447")
    assert len(s.roadworks) == 0
    assert len(s.measures) == 1
    measure = s.measures[0]
    assert measure.record_type == "RoadOrCarriagewayOrLaneManagement"
    assert measure.cause_type == "authorityOperation"


def test_parse_situations_unwraps_d2payload_or_accepts_body_directly():
    wrapped = parse_situations(FIXTURE)
    unwrapped = parse_situations(FIXTURE["D2Payload"])
    assert [s.id for s in wrapped] == [s.id for s in unwrapped]


@respx.mock
def test_client_get_closures_sends_key_and_forces_json():
    route = respx.get("https://api.data.nationalhighways.co.uk/roads/v2.0/closures").mock(
        return_value=httpx.Response(200, json=FIXTURE, headers={"x-next": ""})
    )
    with NationalHighwaysClient("test-key") as nh:
        payload, next_url = nh.get_closures(ClosureType.PLANNED)

    assert route.calls.last.request.headers["Ocp-Apim-Subscription-Key"] == "test-key"
    assert route.calls.last.request.headers["X-Response-MediaType"] == "application/json"
    assert route.calls.last.request.url.params["closureType"] == "planned"
    assert payload == FIXTURE
    assert next_url == ""


@respx.mock
def test_client_iter_pages_follows_x_next_cursor():
    all_situations = FIXTURE["D2Payload"]["situation"]
    first_page = {"D2Payload": {**FIXTURE["D2Payload"], "situation": all_situations[:2]}}
    second_page = {"D2Payload": {**FIXTURE["D2Payload"], "situation": all_situations[2:]}}
    next_url = (
        "https://api.data.nationalhighways.co.uk/roads/v2.0/closures"
        "?closureType=planned&PageCursor=123"
    )

    # One route for both calls (the cursor request lands on the same path,
    # still carrying closureType - a params= subset matcher would match it
    # too and loop forever); side_effect assigns responses by call order.
    route = respx.get("https://api.data.nationalhighways.co.uk/roads/v2.0/closures").mock(
        side_effect=[
            httpx.Response(200, json=first_page, headers={"x-next": next_url}),
            httpx.Response(200, json=second_page),
        ]
    )

    with NationalHighwaysClient("test-key") as nh:
        pages = list(nh.iter_pages(ClosureType.PLANNED))

    assert route.call_count == 2
    assert len(pages) == 2
    assert [s["idG"] for s in pages[0]["D2Payload"]["situation"]] == ["467118", "473996"]
    assert [s["idG"] for s in pages[1]["D2Payload"]["situation"]] == ["458159", "409447"]


@respx.mock
def test_client_iter_roadworks_pages_and_filters():
    respx.get(
        "https://api.data.nationalhighways.co.uk/roads/v2.0/closures",
        params={"closureType": "planned"},
    ).mock(return_value=httpx.Response(200, json=FIXTURE, headers={"x-next": ""}))

    with NationalHighwaysClient("test-key") as nh:
        roadworks = list(nh.iter_roadworks(ClosureType.PLANNED))

    # 3 of the 4 fixture situations are roadworks; the authorityOperation one is not
    assert {s.id for s in roadworks} == {"467118", "473996", "458159"}
