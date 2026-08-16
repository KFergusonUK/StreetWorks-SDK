"""Tests for streetworks.common.from_monaghan.

Fixture is real Monaghan County Council road-network data
(tests/fixtures/monaghan_roads_real.json), captured live 2026-08-16 -
no explicit licence document found, built on the project owner's
explicit instruction, the same basis Jersey's own fixtures ship on.
LineStrings are trimmed to at most 4 real vertices (fixture size only).
Covers one real feature from each of the three official road classes
(National, Regional, Local) - National_Roads has no Municipal_District
field at all, checked here rather than assumed present.
"""

import json
from pathlib import Path

from streetworks.common import from_monaghan_road

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "monaghan_roads_real.json").read_text(encoding="utf-8")
)

_FEATURES = {f["properties"]["Road_Name"]: f for f in FIXTURE["features"]}


def test_names_are_always_empty_real_roads_have_no_name():
    # The whole point of this converter: a real route number is not a
    # street name, and this SDK never fabricates one.
    for feature in _FEATURES.values():
        segment = from_monaghan_road(feature)
        assert segment.names == ()


def test_real_route_number_becomes_a_scoped_identifier():
    segment = from_monaghan_road(_FEATURES["L-31011-0"])
    identifier = segment.identifiers[0]
    assert identifier.scheme == "road_number"
    assert identifier.value == "L-31011-0"
    assert identifier.scope == "Monaghan"


def test_real_road_class_becomes_street_type_label():
    local = from_monaghan_road(_FEATURES["L-31011-0"])
    regional = from_monaghan_road(_FEATURES["R-183-12"])
    national = from_monaghan_road(_FEATURES["N-12-0"])
    assert local.street_type.label == "Local Tertiary"
    assert regional.street_type.label == "Regional"
    assert national.street_type.label == "National Primary"


def test_national_roads_has_no_municipal_district_field_at_all():
    # Checked, not assumed - National_Roads' real schema has no
    # Municipal_District field, unlike Regional_Roads/Local_Roads.
    national = from_monaghan_road(_FEATURES["N-12-0"])
    regional = from_monaghan_road(_FEATURES["R-183-12"])
    assert national.administrative_area is None
    assert regional.administrative_area == "Ballybay - Clones"


def test_geometry_carries_real_multi_vertex_line():
    segment = from_monaghan_road(_FEATURES["L-31011-0"])
    assert segment.geometry.crs == "EPSG:4326"
    assert segment.geometry.points is not None


def test_start_at_finish_at_preserved_in_raw_only():
    feature = _FEATURES["L-31011-0"]
    segment = from_monaghan_road(feature)
    assert segment.raw["properties"]["Start_At"] == "Creeve - 4 Roads"
