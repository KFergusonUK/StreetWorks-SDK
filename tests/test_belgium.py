"""Tests for the Belgium (Flanders/Verkeerscentrum) DATEX II v3 adapter.

The fixture is **synthetic**, not trimmed from a live pull - unlike every
other DATEX II fixture in this suite. transportdata.be's real terms of
use prohibit distributing the data to third parties for commercial
purposes; since this SDK is itself redistributed openly, real data was
judged too close to that restriction to include (same call already made
for Autobahn GmbH's unconfirmed licence). The fixture is built to the real,
live-confirmed shape instead: real namespace URIs, real element structure,
real EPSG:31370 (Belgian Lambert 72) coordinate values (in-range, not the
genuine road segments), and the real discriminator split this feed
surfaced - a dedicated ``MaintenanceWorks`` record, a generic
``RoadOrCarriagewayOrLaneManagement`` record with
``roadOrCarriagewayOrLaneManagementType=newRoadworksLayout`` (a second,
different-shaped discriminator gap from Spain/DGT's), a sibling
``RoadOrCarriagewayOrLaneManagement`` record with a *non*-roadworks type
value (``narrowLanes`` - proves the discriminator doesn't over-match the
whole xsi:type), and a mixed situation (a roadworks record sharing a
situation with a non-roadworks ``GeneralNetworkManagement`` one).
"""

from pathlib import Path

import httpx
import respx

from streetworks.common import from_datex2
from streetworks.datex2 import iter_roadworks_full, iter_situations_full
from streetworks.datex2.belgium import CRS, DATEX_PATH, BelgiumClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "belgium_datex2v3full.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def test_parses_situations():
    situations = list(iter_situations_full(FIXTURE_PATH))
    assert [s.id for s in situations] == [
        "EVT90000001",
        "EVT90000002",
        "EVT90000003",
        "EVT90000004",
    ]


def test_iter_roadworks_excludes_non_roadworks_type_value():
    # EVT90000003 is RoadOrCarriagewayOrLaneManagement too, same xsi:type as
    # EVT90000002's real roadworks record, but its own type value
    # (narrowLanes) isn't one of the two roadworks signals - proves the
    # discriminator checks the specific value, not just the xsi:type.
    roadworks = list(iter_roadworks_full(FIXTURE_PATH))
    assert [s.id for s in roadworks] == ["EVT90000001", "EVT90000002", "EVT90000004"]


def test_maintenance_works_uses_lambert72_coordinates():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "EVT90000001")
    works = situation.roadworks[0]
    assert works.record_type == "MaintenanceWorks"
    assert works.road_maintenance_type == "roadworks"
    assert works.location.kind == "SingleRoadLinearLocation"
    # Lambert 72 eastings/northings, not WGS84 degrees - the values alone
    # (hundred-thousands) are the tell; see belgium.py's own docstring.
    assert works.location.points == ((150000.0, 200000.0), (150200.0, 200150.0))
    # Alert-C is present alongside the coordinates, not instead of them -
    # falls back to the raw numeric code since this fixture has no
    # alertCLocationName element (unlike France's real fixture).
    assert works.location.alert_c_location == "10001"


def test_road_or_carriageway_or_lane_management_new_roadworks_layout():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "EVT90000002")
    works = situation.roadworks[0]
    assert works.record_type == "RoadOrCarriagewayOrLaneManagement"
    assert works.road_or_carriageway_or_lane_management_type == "newRoadworksLayout"
    assert works.is_roadworks is True
    assert works.location.points == ((160000.0, 210000.0), (160100.0, 210080.0))


def test_narrow_lanes_is_not_roadworks():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "EVT90000003")
    record = situation.records[0]
    assert record.record_type == "RoadOrCarriagewayOrLaneManagement"
    assert record.road_or_carriageway_or_lane_management_type == "narrowLanes"
    assert record.is_roadworks is False
    assert situation.roadworks == []
    assert situation.measures == [record]


def test_mixed_situation_splits_roadworks_and_measures():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "EVT90000004")
    assert len(situation.roadworks) == 1
    assert len(situation.measures) == 1
    assert situation.roadworks[0].record_type == "MaintenanceWorks"
    assert situation.measures[0].record_type == "GeneralNetworkManagement"


def test_from_datex2_carries_lambert72_crs_through():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "EVT90000001")
    works = from_datex2(
        situation, territory="Belgium", administrative_area="Flanders", crs=CRS
    )
    assert works.coordinate is not None
    assert works.coordinate.crs == "EPSG:31370"
    assert works.coordinate.value == (150000.0, 200000.0)
    assert works.sites[0].coordinate.crs == "EPSG:31370"


def test_from_datex2_works_type_falls_back_to_lane_management_type():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "EVT90000002")
    works = from_datex2(situation, territory="Belgium", crs=CRS)
    # No road_maintenance_type/construction_work_type on this record - the
    # new fallback should surface "newRoadworksLayout", not the bare
    # xsi:type "RoadOrCarriagewayOrLaneManagement".
    assert works.sites[0].works_type == "newRoadworksLayout"


@respx.mock
def test_client_fetches_and_parses():
    respx.get(f"https://www.verkeerscentrum.be/{DATEX_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with BelgiumClient() as be:
        situations = list(be.iter_situations())
    assert len(situations) == 4


@respx.mock
def test_client_iter_roadworks_filters():
    respx.get(f"https://www.verkeerscentrum.be/{DATEX_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with BelgiumClient() as be:
        roadworks = list(be.iter_roadworks())
    assert len(roadworks) == 3
