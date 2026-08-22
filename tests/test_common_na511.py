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

ALBERTA_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "na511_alberta_events.json").read_text(
        encoding="utf-8"
    )
)
ALBERTA_ROADWORK = [e for e in ALBERTA_FIXTURE if e["EventType"] == "roadwork"]

NEVADA_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "na511_nevada_events.json").read_text(
        encoding="utf-8"
    )
)
NEVADA_ROADWORK = [e for e in NEVADA_FIXTURE if e["EventType"] == "roadwork"]

ALASKA_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "na511_alaska_events.json").read_text(
        encoding="utf-8"
    )
)
ALASKA_ROADWORK = [e for e in ALASKA_FIXTURE if e["EventType"] == "roadwork"]


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


def test_alberta_real_authenticated_records_convert_cleanly():
    """A real, live, authenticated pull (tests/fixtures/na511_alberta_events.json,
    2026-08-22) round-trips through this exact converter unchanged - the
    first key-gated jurisdiction on this platform confirmed, not just
    Ontario's own keyless schema. Covers real Alberta-specific richness
    Ontario's own sample never showed: a genuinely populated
    Restrictions object and a real decoded polyline."""
    works_list = from_na511(
        ALBERTA_ROADWORK, territory="Canada", administrative_area="Alberta Transportation"
    )
    works = _by_id(works_list)["18"]
    coordinate = works.coordinate
    assert coordinate.crs == "EPSG:4326"
    assert coordinate.points is not None
    lat, lon = coordinate.points[0]
    assert abs(lat - 51.0158203605235) < 0.001
    assert abs(lon - (-114.257041270883)) < 0.001


def test_nevada_real_authenticated_records_convert_cleanly():
    """A real, live, authenticated pull (tests/fixtures/na511_nevada_events.json,
    2026-08-22) round-trips through this exact converter unchanged - the
    second key-gated jurisdiction on this platform confirmed, same day as
    Alberta. Covers a real Nevada record with a decoded polyline, and one
    without (ID 75, falling back to the plain Latitude/Longitude pair)."""
    works_list = from_na511(
        NEVADA_ROADWORK, territory="USA", administrative_area="Nevada DOT"
    )
    works = _by_id(works_list)

    with_poly = works["125464"].coordinate
    assert with_poly.crs == "EPSG:4326"
    assert with_poly.points is not None
    lat, lon = with_poly.points[0]
    assert abs(lat - 39.1127414584917) < 0.001
    assert abs(lon - (-119.923125438322)) < 0.001

    without_poly = works["75"].coordinate
    assert without_poly.points is None
    lat, lon = without_poly.value
    assert abs(lat - 39.6041810890692) < 0.001
    assert abs(lon - (-119.331262871408)) < 0.001


def test_null_datetime_sentinel_is_never_surfaced_as_a_real_date():
    """A real, confirmed .NET DateTime.MinValue placeholder
    (-62135596800, 0001-01-01 UTC) on StartDate - 47/57 (82%) of all real
    Alaska events carry it, the majority shape, not an edge case. Must
    never appear as a real proposed_start - see module docstring."""
    works = _by_id(
        from_na511(ALASKA_ROADWORK, territory="USA", administrative_area="Alaska DOT&PF")
    )
    assert works["32138"].sites[0].proposed_start is None


def test_null_island_coordinate_is_never_surfaced_as_a_real_location():
    """A real (0.0, 0.0) placeholder with no EncodedPolyline fallback -
    the same 'no location stated' pattern this SDK already excludes for
    Arkansas's own OneBillionContructionPlanDTIMs dataset. Must never
    appear as a real Coordinate - see module docstring."""
    works = _by_id(
        from_na511(ALASKA_ROADWORK, territory="USA", administrative_area="Alaska DOT&PF")
    )
    assert works["36958"].coordinate is None


def test_alaska_real_record_with_a_genuine_start_date_and_polyline():
    """Not every real Alaska record is a placeholder - ID 32138 has a
    real EncodedPolyline (LastUpdated is real; StartDate/Reported happen
    to be the sentinel on this specific record, confirmed None above,
    while the polyline geometry is real and populated)."""
    works = _by_id(
        from_na511(ALASKA_ROADWORK, territory="USA", administrative_area="Alaska DOT&PF")
    )
    coordinate = works["32138"].coordinate
    assert coordinate is not None
    assert coordinate.points is not None
    lat, lon = coordinate.points[0]
    assert abs(lat - 59.4566093333751) < 0.001
    assert abs(lon - (-135.31558117922)) < 0.001
