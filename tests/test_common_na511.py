"""Tests for streetworks.common.from_na511.

Fixture is real Ontario 511 event data
(tests/fixtures/na511_ontario_events.json) - see test_na511.py's own
docstring. Covers a real record with a populated EncodedPolyline, a real
record without one, and a real non-roadwork event (excluded upstream by
NA511Client.iter_roadworks(), not by this converter - from_na511 assumes
its caller already filtered).
"""

import json
from datetime import timezone
from pathlib import Path

from streetworks.common import DateConfidence, from_na511

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "na511_ontario_events.json").read_text(
        encoding="utf-8"
    )
)
ROADWORK = [e for e in FIXTURE if e["EventType"] == "roadwork"]


def _by_id(works_list):
    return {w.reference: w for w in works_list}


def test_polyline_is_decoded_and_matches_the_stated_point():
    works_list = from_na511(ROADWORK, territory="Canada", administrative_area="Ontario MTO")
    works = _by_id(works_list)["225175"]
    coordinate = works.coordinate
    assert coordinate.crs == "EPSG:4326"
    assert coordinate.points is not None
    assert len(coordinate.points) > 1
    # The polyline's own first decoded point matches the record's stated
    # Latitude/Longitude within real encoding-precision rounding (the
    # polyline stores 5 decimal digits, Latitude/Longitude 6) - see
    # module docstring.
    lat, lon = coordinate.points[0]
    assert abs(lat - 43.9777) < 0.001
    assert abs(lon - (-79.392876)) < 0.001


def test_falls_back_to_plain_lat_lon_when_no_polyline():
    works_list = from_na511(ROADWORK, territory="Canada", administrative_area="Ontario MTO")
    works = _by_id(works_list)["216791"]
    assert works.coordinate is not None
    assert works.coordinate.points is None
    lat, lon = works.coordinate.value
    assert 41 < lat < 57  # real Ontario latitude band
    assert -95 < lon < -74  # real Ontario longitude band


def test_date_confidence_is_uniformly_estimated():
    works_list = from_na511(ROADWORK, territory="Canada", administrative_area="Ontario MTO")
    for works in works_list:
        assert works.sites[0].date_confidence is DateConfidence.ESTIMATED


def test_epoch_seconds_not_milliseconds():
    works_list = from_na511(ROADWORK, territory="Canada", administrative_area="Ontario MTO")
    works = _by_id(works_list)["225175"]
    start = works.sites[0].proposed_start
    assert start.tzinfo is timezone.utc
    assert 2020 < start.year < 2030  # sane real year, not 1970-ish (ms bug)


def test_lanes_affected_lands_on_traffic_management():
    works_list = from_na511(ROADWORK, territory="Canada", administrative_area="Ontario MTO")
    works = _by_id(works_list)["225175"]
    assert works.sites[0].traffic_management == "1 Right Lane(s)"


def test_territory_and_administrative_area_pass_through():
    works_list = from_na511(ROADWORK, territory="Canada", administrative_area="Ontario MTO")
    assert all(w.territory == "Canada" for w in works_list)
    assert all(w.administrative_area == "Ontario MTO" for w in works_list)
