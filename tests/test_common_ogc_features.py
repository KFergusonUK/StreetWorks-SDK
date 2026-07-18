"""Tests for streetworks.common.from_ogc_features.

Uses the same real trimmed Hamburg/Brandenburg fixtures as
test_ogc_germany.py - notably the three real records sharing Brandenburg
works ID prefix "267201193", which is exactly what exercises the
deliberate no-grouping decision (see from_ogc_features's module
docstring for why).
"""

import json
from pathlib import Path

from streetworks.common import DateConfidence, SourceGrade, from_ogc_features
from streetworks.ogc.germany import BRANDENBURG, HAMBURG, StateFieldMap

FIXTURES = Path(__file__).parent / "fixtures"
HAMBURG_PAYLOAD = json.loads((FIXTURES / "ogc_hamburg_baustellen.json").read_text())
BRANDENBURG_PAYLOAD = json.loads(
    (FIXTURES / "ogc_brandenburg_baustelleninfo.json").read_text()
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


def test_date_confidence_unknown_when_no_start_field_mapped():
    no_dates = StateFieldMap(
        state="Test", base_url="https://example.test", type_name="x:y", start=None, end=None
    )
    feature = {"id": "1", "geometry": None, "properties": {}}
    works = from_ogc_features([feature], no_dates)
    assert works[0].sites[0].date_confidence is DateConfidence.UNKNOWN
    assert works[0].sites[0].proposed_start is None
    assert works[0].sites[0].actual_start is None
