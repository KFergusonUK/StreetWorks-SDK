"""Tests for streetworks.common.from_jersey_streets.

Fixture is real Jersey Street Gazetteer data
(tests/fixtures/jersey_streets_real.json), captured live 2026-08-16 -
Jersey's data is open for public consumption (per instruction), so real
records are committed here, the same basis jersey_roadworks_real.json
shipped on. Polygon rings are trimmed to 4 real vertices + the closing
one (fixture size only - the converter never reads ring geometry, so
this doesn't affect what's under test). Covers: a real FEATURE='Road' row
with a stated USRN_XY1/XY2 pair (geometry present), a real FEATURE='Road'
row with no stated pair (geometry absent), and two real FEATURE='Pavement'
rows sharing a USRN with the geometry-absent 'Road' row (proving the
default filter genuinely excludes them at the client level, not here -
this converter itself never filters).
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_jersey_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "jersey_streets_real.json").read_text(encoding="utf-8")
)

_FEATURES = {f["properties"]["OBJECTID"]: f for f in FIXTURE["features"]}


def test_real_stated_xy_pair_becomes_a_two_point_line_geometry():
    street = from_jersey_street(_FEATURES[2])  # La Ruelle du Coin
    assert street.name == "La Ruelle du Coin"
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry.crs == "EPSG:3109"
    assert street.geometry.value == (35752.0, 69684.0)
    assert street.geometry.points == ((35752.0, 69684.0), (35800.0, 69778.0))


def test_blank_xy_pair_is_absent_not_a_fabricated_centroid():
    street = from_jersey_street(_FEATURES[1])  # Road Off La Rue de la Piece Mauger
    assert street.geometry is None
    assert street.geometry_grade is GeometryGrade.ABSENT
    # The real polygon is still preserved, unmodified, in raw.
    assert street.raw["geometry"]["type"] == "Polygon"


def test_real_usrn_and_bkstoid_identifiers():
    street = from_jersey_street(_FEATURES[2])
    by_scheme = {i.scheme: i for i in street.identifiers}
    assert by_scheme["usrn"].value == "40000338"
    assert by_scheme["usrn"].scope == "Jersey"
    assert by_scheme["bkstoid"].value == "AREA000000142348"


def test_real_parish_becomes_administrative_area():
    street = from_jersey_street(_FEATURES[2])
    assert street.administrative_area == "St. Ouen"
    assert street.territory == "Jersey"


def test_a_blank_real_name_pavement_row_carries_no_name():
    # A real FEATURE='Pavement' row - excluded by the client's default
    # filter, but this converter itself never filters, so it must still
    # convert honestly: no fabricated name from a blank REAL_NAME.
    street = from_jersey_street(_FEATURES[248])
    assert street.names == ()
    assert street.name is None
