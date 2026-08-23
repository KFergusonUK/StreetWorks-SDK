"""Tests for streetworks.common.from_singapore. **Pending live
verification** - see streetworks.singapore.client's own module docstring.
Fixtures are synthetic, built from LTA DataMall's own documented sample
values, not real pulled data - see test_singapore.py's own docstring.
"""

import json
from datetime import datetime
from pathlib import Path

from streetworks.common import DateConfidence, from_singapore

ROAD_WORKS = [
    {**r, "kind": "road_works"}
    for r in json.loads(
        (Path(__file__).parent / "fixtures" / "singapore_road_works.json").read_text()
    )["value"]
]
ROAD_OPENINGS = [
    {**r, "kind": "road_openings"}
    for r in json.loads(
        (Path(__file__).parent / "fixtures" / "singapore_road_openings.json").read_text()
    )["value"]
]
INCIDENTS = [
    {**r, "kind": "incident"}
    for r in json.loads(
        (Path(__file__).parent / "fixtures" / "singapore_traffic_incidents.json").read_text()
    )["value"]
]
ROADWORK_INCIDENT = [r for r in INCIDENTS if r["Type"] == "Roadwork"]


def test_road_works_reference_type_promoter_and_location():
    works = from_singapore(ROAD_WORKS)[0]
    assert works.reference == "RMAPP-201512-0217"
    assert works.promoter == "SP POWERGRID LTD - REGIONAL NETWORK CENTRAL"
    assert works.sites[0].works_type == "Approved Road Works"
    assert works.sites[0].location_description == "ADAM DRIVE"


def test_road_works_coordinate_is_none_no_field_exists():
    works = from_singapore(ROAD_WORKS)[0]
    assert works.coordinate is None


def test_road_works_dates_parsed_and_estimated():
    site = from_singapore(ROAD_WORKS)[0].sites[0]
    assert site.proposed_start == datetime(2015, 12, 14)
    assert site.proposed_end == datetime(2016, 7, 31)
    assert site.date_confidence is DateConfidence.ESTIMATED


def test_road_openings_uses_the_distinct_works_type():
    works = from_singapore(ROAD_OPENINGS)[0]
    assert works.sites[0].works_type == "Planned Road Openings"
    assert works.reference == "RMAPP-201603-0900"


def test_incident_kind_has_coordinate_but_no_reference_or_dates():
    works = from_singapore(ROADWORK_INCIDENT)[0]
    assert works.reference is None
    assert works.coordinate.value == (1.32993, 103.78521)
    assert works.coordinate.crs == "EPSG:4326"
    site = works.sites[0]
    assert site.proposed_start is None
    assert site.proposed_end is None
    assert site.date_confidence is DateConfidence.UNKNOWN
    assert site.works_type == "Roadwork"
    assert "PIE" in site.traffic_management


def test_incident_kind_has_no_promoter_no_comparable_field():
    works = from_singapore(ROADWORK_INCIDENT)[0]
    assert works.promoter is None


def test_territory_and_administrative_area():
    works_list = from_singapore(ROAD_WORKS + ROAD_OPENINGS + ROADWORK_INCIDENT)
    assert all(w.territory == "Singapore" for w in works_list)
    assert all(w.administrative_area == "Land Transport Authority (LTA)" for w in works_list)
