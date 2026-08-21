"""Tests for streetworks.common.from_vancouver.

Fixtures are real trimmed Vancouver "Road Ahead" records
(tests/fixtures/vancouver_*.json), captured live 2026-08-21 - Vancouver's
open data is licensed under the Open Government Licence - Vancouver, so
real records are committed here, the same way Jersey's/Quebec's are.
Covers a real null-location record, real LineString/MultiLineString
geometry, a real GeometryCollection (LineStrings + Polygons mixed - not
decomposed, falls back to the point only) and a real Point-geometry
upcoming record.
"""

import json
from datetime import timedelta
from pathlib import Path

from streetworks.common import DateConfidence, from_vancouver

FIXTURES = {
    name: json.loads(
        (Path(__file__).parent / "fixtures" / f"vancouver_{name}.json").read_text(encoding="utf-8")
    )["results"]
    for name in ("current_closures", "under_construction", "upcoming")
}


def test_current_closures_are_verified_with_actual_end():
    works_list = from_vancouver(
        FIXTURES["current_closures"],
        status="Current closure",
        date_confidence=DateConfidence.VERIFIED,
    )
    site = works_list[0].sites[0]
    assert site.status == "Current closure"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert site.actual_end is not None
    assert site.actual_end.tzinfo is not None
    assert site.proposed_end is None


def test_upcoming_is_estimated_with_proposed_end():
    works_list = from_vancouver(
        FIXTURES["upcoming"], status="Upcoming", date_confidence=DateConfidence.ESTIMATED
    )
    site = works_list[0].sites[0]
    assert site.status == "Upcoming"
    assert site.date_confidence is DateConfidence.ESTIMATED
    assert site.proposed_end is not None
    assert site.actual_end is None


def test_null_location_stays_none_not_fabricated():
    # A real current-closure record has no location/project stated at all.
    works_list = from_vancouver(
        FIXTURES["current_closures"],
        status="Current closure",
        date_confidence=DateConfidence.VERIFIED,
    )
    null_location = [w for w in works_list if w.sites[0].location_description is None]
    assert null_location  # a real record exists in this fixture


def test_linestring_and_multilinestring_geometry_populate_points():
    works_list = from_vancouver(
        FIXTURES["current_closures"],
        status="Current closure",
        date_confidence=DateConfidence.VERIFIED,
    )
    with_points = [w for w in works_list if w.sites[0].coordinate.points]
    assert with_points  # real LineString/MultiLineString records exist


def test_geometry_collection_falls_back_to_point_only():
    # A real record has GeometryCollection geometry (LineStrings mixed
    # with real Polygons) - too structurally varied to decompose, so it
    # still gets a real representative point, just no .points.
    works_list = from_vancouver(
        FIXTURES["under_construction"],
        status="Under construction",
        date_confidence=DateConfidence.VERIFIED,
    )
    gc_site = next(
        w.sites[0]
        for w in works_list
        if (w.raw.get("geom") or {}).get("geometry", {}).get("type") == "GeometryCollection"
    )
    assert gc_site.coordinate is not None
    assert gc_site.coordinate.points is None


def test_point_geometry_upcoming_record_still_gets_a_coordinate():
    works_list = from_vancouver(
        FIXTURES["upcoming"], status="Upcoming", date_confidence=DateConfidence.ESTIMATED
    )
    point_site = next(
        w.sites[0]
        for w in works_list
        if (w.raw.get("geom") or {}).get("geometry", {}).get("type") == "Point"
    )
    assert point_site.coordinate is not None
    assert point_site.coordinate.points is None


def test_coordinate_uses_geo_point_2d_lat_lon_order():
    works_list = from_vancouver(
        FIXTURES["current_closures"],
        status="Current closure",
        date_confidence=DateConfidence.VERIFIED,
    )
    coordinate = works_list[0].coordinate
    assert coordinate.crs == "EPSG:4326"
    lat, lon = coordinate.value
    assert 49 < lat < 50  # real Vancouver latitude band
    assert -124 < lon < -122  # real Vancouver longitude band


def test_dates_are_localised_to_america_vancouver():
    works_list = from_vancouver(
        FIXTURES["upcoming"], status="Upcoming", date_confidence=DateConfidence.ESTIMATED
    )
    end = works_list[0].sites[0].proposed_end
    assert end.utcoffset() != timedelta(0)  # real Pacific Time offset, not UTC


def test_territory_and_administrative_area():
    works_list = from_vancouver(
        FIXTURES["current_closures"],
        status="Current closure",
        date_confidence=DateConfidence.VERIFIED,
    )
    assert all(w.territory == "Canada" for w in works_list)
    assert all(w.administrative_area == "City of Vancouver" for w in works_list)
