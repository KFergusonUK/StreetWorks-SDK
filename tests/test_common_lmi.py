"""Tests for streetworks.common.from_lmi.

Fixture is real Landmælingar Íslands IS 50V data
(tests/fixtures/lmi_streets_real.json), captured live 2026-08-17 -
Creative Commons Attribution 4.0 International, confirmed live from
Landmælingar Íslands' own licence page. LineStrings are trimmed to at
most 4 real vertices per part (fixture size only). Covers: a real rural
road with a stated route number (Gnúpverjavegur), a real urban street
with no route number (Laugavegur, Reykjavík's main shopping street), a
real genuinely multi-part feature (Virkisás), and a real record whose
name is a literal single-space string, not NULL (objectid 90918).
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_lmi_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "lmi_streets_real.json").read_text(encoding="utf-8")
)

_FEATURES = {f["properties"]["objectid"]: f for f in FIXTURE["features"]}


def test_real_name_and_route_number():
    street = from_lmi_street(_FEATURES[119297])  # Gnúpverjavegur
    assert street.name == "Gnúpverjavegur"
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry.crs == "EPSG:4326"
    road_number = next(i for i in street.identifiers if i.scheme == "road_number")
    assert road_number.value == "325-01"
    assert road_number.scope == "Iceland"


def test_urban_street_has_no_route_number():
    # Laugavegur - a real urban street, genuinely no vegnr/kaflanr,
    # unlike rural connecting roads.
    street = from_lmi_street(_FEATURES[75723])
    assert street.name == "Laugavegur"
    assert not any(i.scheme == "road_number" for i in street.identifiers)
    assert any(i.scheme == "uuid" for i in street.identifiers)


def test_genuine_multi_part_geometry_uses_parts():
    street = from_lmi_street(_FEATURES[119192])
    assert street.geometry.parts is not None
    assert len(street.geometry.parts) == 3


def test_single_space_name_treated_as_no_name_not_fabricated():
    # A real record where nafnfitju is a literal " " - not NULL, and
    # never carried through as a blank-looking but non-empty name.
    street = from_lmi_street(_FEATURES[90918])
    assert street.names == ()
    assert street.name is None


def test_territory_and_source_grade():
    street = from_lmi_street(_FEATURES[119297])
    assert street.territory == "Iceland"
