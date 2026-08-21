"""Tests for streetworks.common.from_toronto.

Fixture is real trimmed Toronto Road Restrictions/Closures data - see
tests/test_toronto.py's own docstring for exactly what it covers.
"""

import json
from datetime import timezone
from pathlib import Path

from streetworks.common import DateConfidence, from_toronto

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "toronto_road_restrictions.json").read_text(
        encoding="utf-8"
    )
)["Closure"]


def _by_id(works_list):
    return {w.reference: w for w in works_list}


def test_construction_and_road_closed_types_both_map_to_status():
    works_list = from_toronto(FIXTURE)
    statuses = {w.sites[0].status for w in works_list}
    assert statuses == {"CONSTRUCTION", "ROAD_CLOSED"}


def test_a_record_with_a_literal_backslash_in_description_converts_cleanly():
    works_list = from_toronto(FIXTURE)
    works = _by_id(works_list)["Tor-RD52026-4929"]
    assert "WATER \\ SEWER" in works.sites[0].traffic_management


def test_garbled_work_event_type_is_carried_through_not_filtered():
    # A real, confirmed export defect - see streetworks.toronto.client's
    # own module docstring. Not silently dropped or cleaned up.
    works_list = from_toronto(FIXTURE)
    garbled = [
        w
        for w in works_list
        if w.sites[0].works_type and w.sites[0].works_type.startswith('{"tabledata"')
    ]
    assert garbled  # a real record exists in this fixture


def test_clean_work_event_type_is_used_directly():
    works_list = from_toronto(FIXTURE)
    works = _by_id(works_list)["Tor-RD1H2026-1713"]
    assert works.sites[0].works_type == "Toronto Hydro Street Lighting"


def test_contractor_maps_to_promoter_and_can_be_absent():
    works_list = from_toronto(FIXTURE)
    populated = _by_id(works_list)["Tor-RD52026-1265"]
    assert populated.promoter == "EnVision Consultants Ltd."
    absent = next(w for w in works_list if w.promoter is None)
    assert absent.sites[0].coordinate is not None  # still converts cleanly


def test_date_confidence_is_uniformly_estimated():
    works_list = from_toronto(FIXTURE)
    for works in works_list:
        assert works.sites[0].date_confidence is DateConfidence.ESTIMATED
        assert works.sites[0].actual_start is None


def test_epoch_millis_dates_parse_to_utc():
    works_list = from_toronto(FIXTURE)
    start = works_list[0].sites[0].proposed_start
    assert start is not None
    assert start.tzinfo is timezone.utc
    assert 2020 < start.year < 2030


def test_geo_polyline_populates_points_when_present():
    works_list = from_toronto(FIXTURE)
    with_points = [w for w in works_list if w.coordinate and w.coordinate.points]
    assert with_points  # every real record in this fixture has one


def test_coordinate_falls_back_to_plain_lat_lon_bounds():
    works_list = from_toronto(FIXTURE)
    coordinate = works_list[0].coordinate
    assert coordinate.crs == "EPSG:4326"
    lat, lon = coordinate.value
    assert 43 < lat < 44  # real Toronto latitude band
    assert -80 < lon < -79  # real Toronto longitude band


def test_territory_and_administrative_area():
    works_list = from_toronto(FIXTURE)
    assert all(w.territory == "Canada" for w in works_list)
    assert all(w.administrative_area == "City of Toronto" for w in works_list)
