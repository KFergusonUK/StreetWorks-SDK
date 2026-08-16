"""Tests for streetworks.common.from_gibraltar.

Fixture is real Gibraltar Street Gazetteer data
(tests/fixtures/gibraltar_streets_real.json), captured live 2026-08-16
on the project owner's explicit instruction (see the module docstring
in streetworks.gibraltar.client for the real licence situation).
MultiLineString coordinate lists are trimmed to at most 4 real vertices
per part (fixture size only - the converter carries every vertex given).
Covers: a real single-part street, a real 6-part street sharing one
inspireId, a real triple-named segment (name/collname1/collname2 all
populated), and a real record with a null name (only collname1 stated).
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_gibraltar_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "gibraltar_streets_real.json").read_text(
        encoding="utf-8"
    )
)

_FEATURES = {f["properties"]["inspireId"]: f for f in FIXTURE["features"]}


def test_single_part_geometry_uses_points():
    street = from_gibraltar_street(_FEATURES[269])  # Reclamation Road
    assert street.name == "Reclamation Road"
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry.crs == "EPSG:4326"
    assert street.geometry.parts is None
    assert street.geometry.points is not None


def test_genuine_multi_part_geometry_uses_parts_not_first_line_only():
    street = from_gibraltar_street(_FEATURES[123])  # Lathbury Road, 6 real parts
    assert street.geometry.parts is not None
    assert len(street.geometry.parts) == 6


def test_composed_label_never_read_three_real_names_kept_separate():
    # label = "Queensway - Dockyard Road - Dockyard Approach Road" -
    # never fused into one Name.
    street = from_gibraltar_street(_FEATURES[73])
    values = [n.value for n in street.names]
    assert values == ["Queensway", "Dockyard Road", "Dockyard Approach Road"]


def test_null_name_falls_back_to_real_collname1():
    street = from_gibraltar_street(_FEATURES[276])
    assert street.name == "La Marcha Atras"
    assert len(street.names) == 1


def test_real_inspire_id_identifier_scoped_to_gibraltar():
    street = from_gibraltar_street(_FEATURES[269])
    identifier = street.identifiers[0]
    assert identifier.scheme == "inspire_id"
    assert identifier.value == "269"
    assert identifier.scope == "Gibraltar"


def test_territory_is_gibraltar():
    street = from_gibraltar_street(_FEATURES[269])
    assert street.territory == "Gibraltar"
