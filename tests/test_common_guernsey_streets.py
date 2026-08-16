"""Tests for streetworks.common.from_guernsey_streets.

Fixture is real Guernsey Street Gazetteer data
(tests/fixtures/guernsey_streets_real.json), captured live 2026-08-16 -
the same open-for-public-consumption basis Jersey's own fixtures ship on.
Polygon rings are trimmed to 4 real vertices + the closing one (fixture
size only - this converter never reads ring geometry). Covers: a real
whole-number USRN, a real genuine fractional-subdivision family (parent
20216 plus real children 20216.01/20216.02 - Clos du Falla, Castel), and
the same real street name recurring under three different real parishes
with three completely different USRN magnitudes (Candie Road).
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_guernsey_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "guernsey_streets_real.json").read_text(
        encoding="utf-8"
    )
)

_FEATURES = FIXTURE["features"]


def _by_road_and_parish(road: str, parish: str):
    return next(
        f
        for f in _FEATURES
        if f["properties"]["ROAD"] == road and f["properties"]["PARISH"] == parish
    )


def test_geometry_is_always_absent_never_a_fabricated_centroid():
    feature = _by_road_and_parish("CANDIE ROAD", "CASTEL")
    street = from_guernsey_street(feature)
    assert street.geometry is None
    assert street.geometry_grade is GeometryGrade.ABSENT
    # The real polygon is still preserved, unmodified, in raw.
    assert street.raw["geometry"]["type"] == "Polygon"


def test_real_whole_number_usrn_formats_without_a_decimal():
    feature = _by_road_and_parish("CANDIE ROAD", "CASTEL")
    street = from_guernsey_street(feature)
    usrn = next(i for i in street.identifiers if i.scheme == "usrn")
    assert usrn.value == "20011"
    assert usrn.scope == "Guernsey"


def test_real_fractional_usrn_subdivision_family():
    parent = from_guernsey_street(_by_road_and_parish("CLOS DU FALLA", "CASTEL"))
    children = [
        f["properties"]["USRN"]
        for f in _FEATURES
        if f["properties"]["ROAD"] == "CLOS DU FALLA" and f["properties"]["USRN"] != 20216
    ]
    assert sorted(children) == [20216.01, 20216.02]

    fractional_feature = next(
        f for f in _FEATURES if f["properties"].get("USRN") == 20216.01
    )
    fractional_street = from_guernsey_street(fractional_feature)
    usrn = next(i for i in fractional_street.identifiers if i.scheme == "usrn")
    # Masks real IEEE-754 float-encoding noise (20216.01 can arrive as
    # 20216.010000000002-shaped) rather than passing it through raw.
    assert usrn.value == "20216.01"
    assert parent.name == fractional_street.name == "CLOS DU FALLA"


def test_real_uprn_and_class_carried_through():
    street = from_guernsey_street(_by_road_and_parish("CANDIE ROAD", "CASTEL"))
    uprn = next(i for i in street.identifiers if i.scheme == "uprn")
    assert uprn.value == "200111"
    assert street.street_type.code == "MPT"


def test_same_street_name_different_parishes_different_identifiers():
    castel = from_guernsey_street(_by_road_and_parish("CANDIE ROAD", "CASTEL"))
    st_andrew = from_guernsey_street(_by_road_and_parish("CANDIE ROAD", "ST. ANDREW"))
    st_peter_port = from_guernsey_street(_by_road_and_parish("CANDIE ROAD", "ST. PETER PORT"))

    usrns = {
        next(i.value for i in s.identifiers if i.scheme == "usrn")
        for s in (castel, st_andrew, st_peter_port)
    }
    assert usrns == {"20011", "50015", "265"}
    areas = {castel.administrative_area, st_andrew.administrative_area}
    areas.add(st_peter_port.administrative_area)
    assert areas == {"CASTEL", "ST. ANDREW", "ST. PETER PORT"}
