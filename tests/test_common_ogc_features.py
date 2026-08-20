"""Tests for streetworks.common.from_ogc_features.

Uses the same real trimmed Hamburg/Brandenburg/Saxony fixtures as
test_ogc_germany.py - notably the three real records sharing Brandenburg
works ID prefix "267201193" (and Saxony's own equivalent, ID
"LRABZ2026B00285"), which is exactly what exercises the deliberate
no-grouping decision (see from_ogc_features's module docstring for why).
"""

import json
from pathlib import Path

from streetworks.common import DateConfidence, SourceGrade, from_ogc_features
from streetworks.ogc.germany import (
    BADEN_WUERTTEMBERG,
    BRANDENBURG,
    GERMANY_LAT_RANGE,
    GERMANY_LON_RANGE,
    HAMBURG,
    SAXONY,
    SCHLESWIG_HOLSTEIN,
    StateFieldMap,
    _parse_lbv_sh_gml,
)

FIXTURES = Path(__file__).parent / "fixtures"
HAMBURG_PAYLOAD = json.loads((FIXTURES / "ogc_hamburg_baustellen.json").read_text())
BRANDENBURG_PAYLOAD = json.loads(
    (FIXTURES / "ogc_brandenburg_baustelleninfo.json").read_text()
)
SAXONY_PAYLOAD = json.loads((FIXTURES / "ogc_saxony_sperrungen.json").read_text())
BW_PAYLOAD = json.loads((FIXTURES / "ogc_bw_roadworks.json").read_text())
SH_FEATURES = _parse_lbv_sh_gml(
    (FIXTURES / "ogc_sh_baustellen.xml").read_bytes(), SCHLESWIG_HOLSTEIN.type_name
)


def test_hamburg_de_date_format_and_point_geometry():
    works = from_ogc_features(HAMBURG_PAYLOAD["features"], HAMBURG)
    w = next(w for w in works if w.reference == "DE.HH.UP_BAUSTELLE_916925")
    site = w.sites[0]

    assert w.territory == "Germany"
    assert w.administrative_area == "Hamburg"  # endpoint provenance, not a record field
    assert w.promoter == "Landesbetrieb Straßen, Brücken und Gewässer"
    assert w.source_grade is SourceGrade.OPERATOR
    assert str(site.proposed_start) == "2024-08-05 00:00:00+02:00"  # DD.MM.YYYY parsed
    assert str(site.proposed_end) == "2026-07-31 00:00:00+02:00"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert site.location_description is None  # no road field exists for Hamburg
    # Point geometry - one coordinate, native GeoJSON (lon, lat) flipped to (lat, lon).
    assert w.coordinate.value == (53.62984929345569, 10.037271111591924)
    assert w.coordinate.points is None


def test_brandenburg_iso_date_format_and_road_field():
    works = from_ogc_features(BRANDENBURG_PAYLOAD["features"], BRANDENBURG)
    w = next(w for w in works if w.reference == "267201193_3")
    site = w.sites[0]

    assert w.administrative_area == "Brandenburg"
    assert site.works_type == "Sperrung"
    assert site.location_description == "L40"  # the real field, Straßenummner (sic)
    assert str(site.proposed_start) == "2026-07-13 00:00:00+02:00"
    assert str(site.proposed_end) == "2026-08-07 00:00:00+02:00"
    assert site.status == "Fahrstreifen gesperrt"


def test_brandenburg_linestring_geometry_survives_whole():
    works = from_ogc_features(BRANDENBURG_PAYLOAD["features"], BRANDENBURG)
    w = next(w for w in works if w.reference == "267100895_3")
    # The real 390-vertex line, not collapsed to a point.
    assert len(w.coordinate.points) == 390
    assert w.coordinate.value == w.coordinate.points[0]


def test_no_grouping_despite_shared_id_prefix():
    # 267201193_1/_2/_3 are real records sharing a works ID prefix, but
    # this converter deliberately doesn't group them - see module
    # docstring for why (agreement too weak, no corroborating field).
    works = from_ogc_features(BRANDENBURG_PAYLOAD["features"], BRANDENBURG)
    refs = {w.reference for w in works if w.reference.startswith("267201193")}
    assert refs == {"267201193_1", "267201193_2", "267201193_3"}
    for ref in refs:
        w = next(w for w in works if w.reference == ref)
        assert len(w.sites) == 1  # each is its own Works with exactly one site


def test_missing_optional_property_does_not_crash():
    works = from_ogc_features(BRANDENBURG_PAYLOAD["features"], BRANDENBURG)
    w = next(w for w in works if w.reference == "266800551_3")
    assert "Anzahl_Fahrstreifen" not in w.raw["properties"]
    assert w.sites[0].works_type == "Sperrung"  # unaffected fields still map fine


def test_saxony_utm_coordinate_is_not_flipped():
    # EPSG:25833 (UTM33N) has no "wrong way round" to correct - (easting,
    # northing) as the source states it, same treatment as British
    # National Grid elsewhere in this SDK (from_streetmanager). Eastings
    # in this zone are ~200k-800k; northings are ~5.5-5.8 million - a
    # flip would put a million-scale number where the easting belongs.
    works = from_ogc_features(SAXONY_PAYLOAD["features"], SAXONY)
    w = next(w for w in works if w.reference == "5243002026B00234")
    assert w.coordinate.crs == "EPSG:25833"
    easting, northing = w.coordinate.value
    assert 200_000 < easting < 800_000
    assert 5_500_000 < northing < 5_800_000


def test_saxony_linestring_geometry_survives_whole():
    works = from_ogc_features(SAXONY_PAYLOAD["features"], SAXONY)
    w = next(w for w in works if w.reference == "LRAERZ2026-0001075")
    assert len(w.coordinate.points) == 14
    assert w.coordinate.value == w.coordinate.points[0]


def test_saxony_date_with_hour_suffix_parsed():
    # "16.08.2026  08 Uhr" - a real secondary date shape (639/3,062 real
    # date fields), preserves the genuinely-stated hour rather than
    # collapsing to midnight.
    works = from_ogc_features(SAXONY_PAYLOAD["features"], SAXONY)
    w = next(w for w in works if w.reference == "LRAV2026V00001")
    assert str(w.sites[0].proposed_start) == "2026-08-16 08:00:00+02:00"
    assert str(w.sites[0].proposed_end) == "2026-08-16 18:00:00+02:00"
    assert w.sites[0].date_confidence is DateConfidence.VERIFIED


def test_saxony_promoter_and_status_fields():
    works = from_ogc_features(SAXONY_PAYLOAD["features"], SAXONY)
    w = next(w for w in works if w.reference == "LRAV2026V00001")
    assert w.promoter  # a real Behörde value
    assert w.sites[0].status == "Veranstaltung"  # Sperrung_Typ_Klartext


def test_no_grouping_despite_shared_id_saxony():
    # Three real segments of one closure share ID "LRABZ2026B00285" - not
    # grouped, same policy as Brandenburg's prefix pattern.
    works = from_ogc_features(SAXONY_PAYLOAD["features"], SAXONY)
    matching = [w for w in works if w.reference == "LRABZ2026B00285"]
    assert len(matching) == 3
    for w in matching:
        assert len(w.sites) == 1


def test_date_confidence_unknown_when_no_start_field_mapped():
    no_dates = StateFieldMap(
        state="Test", base_url="https://example.test", type_name="x:y", start=None, end=None
    )
    feature = {"id": "1", "geometry": None, "properties": {}}
    works = from_ogc_features([feature], no_dates)
    assert works[0].sites[0].date_confidence is DateConfidence.UNKNOWN
    assert works[0].sites[0].proposed_start is None
    assert works[0].sites[0].actual_start is None


def test_bw_iso_datetime_carries_real_time_of_day_and_dst_aware_offset():
    # Baden-Württemberg is the one state in this cluster with a genuine
    # time-of-day, not just a date - and the real UTC offset differs by
    # season (summer/winter), computed correctly via fromisoformat, not
    # hardcoded - see from_ogc_features's own module docstring.
    works = from_ogc_features(BW_PAYLOAD["features"], BADEN_WUERTTEMBERG)
    w = next(w for w in works if w.reference == "1487640-1487641-1487644-3508083-sperrung.001")
    assert str(w.sites[0].proposed_start) == "2015-06-01 00:00:00+02:00"
    assert str(w.sites[0].proposed_end) == "2026-12-31 23:59:00+01:00"
    assert w.sites[0].date_confidence is DateConfidence.VERIFIED


def test_bw_road_and_status_fields():
    works = from_ogc_features(BW_PAYLOAD["features"], BADEN_WUERTTEMBERG)
    w = next(w for w in works if w.reference == "1487640-1487641-1487644-3508083-sperrung.001")
    assert w.sites[0].location_description == "L154 Albbruck-St. Blasien"
    assert w.sites[0].status == "ROAD_CLOSED"
    assert w.sites[0].works_type == "L154 Albtalsperrung"


def test_sh_gml_multicurve_reprojected_to_wgs84_via_points():
    # Every real Baustellen_SH MultiCurve wraps exactly one curveMember -
    # unwrapped to a plain LineString, points surviving whole (not
    # collapsed to a single vertex) - see streetworks.ogc.germany's
    # module docstring for the live evidence.
    works = from_ogc_features(SH_FEATURES, SCHLESWIG_HOLSTEIN)
    w = next(w for w in works if w.sites[0].location_description == "L281")
    assert w.coordinate.crs == "EPSG:4326"
    assert len(w.coordinate.points) == 5
    lat, lon = w.coordinate.value
    assert GERMANY_LAT_RANGE[0] <= lat <= GERMANY_LAT_RANGE[1]
    assert GERMANY_LON_RANGE[0] <= lon <= GERMANY_LON_RANGE[1]


def test_sh_combined_date_field_split_into_start_and_end():
    # Baustellen_SH states one real combined "X bis Y" field, not two
    # separate ones - split client-side into synthetic properties before
    # this converter ever sees them (see streetworks.ogc.germany).
    works = from_ogc_features(SH_FEATURES, SCHLESWIG_HOLSTEIN)
    w = next(w for w in works if w.sites[0].location_description == "L281")
    assert str(w.sites[0].proposed_start) == "2026-08-03 23:00:00+02:00"
    assert str(w.sites[0].proposed_end) == "2026-09-11 22:59:00+02:00"
    assert w.sites[0].date_confidence is DateConfidence.VERIFIED


def test_sh_bare_g_prefixed_road_name_is_real_not_filtered():
    # A genuine, if low-information, real value - "G" (Gemeindestraße/
    # municipal road class), 466/1,116 real records at investigation
    # time - carried through like any other real Straßenname, never
    # filtered or second-guessed.
    works = from_ogc_features(SH_FEATURES, SCHLESWIG_HOLSTEIN)
    w = next(w for w in works if w.sites[0].location_description == "G")
    assert w.sites[0].works_type  # still a real Art_der_Maßnahme value
