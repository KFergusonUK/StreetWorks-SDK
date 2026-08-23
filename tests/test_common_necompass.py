"""Tests for streetworks.common.from_necompass.

Fixture is real New England Compass C2C data, parsed through the real
client (tests/fixtures/necompass_*.xml) - see test_necompass.py's own
docstring. Covers a real laneClosure record with full start/end dates
and real LineString geometry (midpoints), a real laneClosure record with
no end_location (point-only fallback), and a real incident-kind record
(confirmed_date fallback, no proposed_end at all).
"""

from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from streetworks.common import DateConfidence, from_necompass
from streetworks.necompass.client import _parse_record

_NS = "{http://its.gov/c2c_icd}"


def _records_from_fixture(filename: str, tag: str, kind: str) -> list[dict]:
    data = (Path(__file__).parent / "fixtures" / filename).read_bytes()
    root = ElementTree.fromstring(data)
    return [_parse_record(e, kind=kind) for e in root.iter(f"{_NS}{tag}")]


LANE_CLOSURES = _records_from_fixture(
    "necompass_maine_lane_closures.xml", "laneClosure", "laneClosure"
)
INCIDENTS = _records_from_fixture(
    "necompass_newhampshire_incidents.xml", "incident", "incident"
)


def _by_id(works_list):
    return {w.reference: w for w in works_list}


def test_real_line_geometry_with_start_midpoints_and_end():
    works = _by_id(from_necompass(LANE_CLOSURES))["ME26-002917"]
    coordinate = works.coordinate
    assert coordinate.crs == "EPSG:4326"
    assert coordinate.points is not None
    assert len(coordinate.points) == 27  # start + 25 midpoints + end
    lat, lon = coordinate.value
    assert abs(lat - 44.345313) < 0.0001
    assert abs(lon - (-70.14512)) < 0.0001


def test_real_start_and_end_dates_parsed():
    works = _by_id(from_necompass(LANE_CLOSURES))["ME26-002917"]
    site = works.sites[0]
    assert site.proposed_start == datetime(2026, 8, 19, 7, 0, 0)
    assert site.proposed_end == datetime(2026, 10, 3, 16, 0, 0)


def test_point_only_record_has_no_line_geometry():
    works = _by_id(from_necompass(LANE_CLOSURES))["ME26-002801"]
    assert works.coordinate is not None
    assert works.coordinate.points is None


def test_special_event_record_still_converts_since_filtering_is_the_callers_job():
    works = _by_id(from_necompass(LANE_CLOSURES))["ME26-002895"]
    assert works.sites[0].works_type == "SpecialEvent"


def test_works_type_and_status_and_traffic_management():
    works = _by_id(from_necompass(LANE_CLOSURES))["ME26-002917"]
    site = works.sites[0]
    assert site.works_type == "RoadMaintenance"
    assert site.status == "Opened"
    assert site.traffic_management == "Unknown lanes closed"


def test_location_description_combines_roadway_direction_and_place():
    works = _by_id(from_necompass(LANE_CLOSURES))["ME26-002917"]
    assert works.sites[0].location_description == "ROUTE 106 North — Leeds, Androscoggin"


def test_territory_and_administrative_area_derived_from_net_id():
    works_list = from_necompass(LANE_CLOSURES)
    assert all(w.territory == "USA" for w in works_list)
    assert all(
        w.administrative_area == "Maine Department of Transportation (MaineDOT)"
        for w in works_list
    )


def test_date_confidence_is_uniformly_estimated():
    for works in from_necompass(LANE_CLOSURES):
        assert works.sites[0].date_confidence is DateConfidence.ESTIMATED


def test_incident_kind_record_falls_back_to_confirmed_date_with_no_end():
    """incident-kind records have no startDate/endDate at all - only
    confirmedDate/confirmedTime, and no end date whatsoever - a real,
    confirmed gap, not an oversight."""
    works = _by_id(from_necompass(INCIDENTS))["NH24-003127"]
    site = works.sites[0]
    assert site.proposed_start == datetime(2024, 7, 11, 3, 51, 2)
    assert site.proposed_end is None
    assert works.administrative_area == "New Hampshire Department of Transportation (NHDOT)"
