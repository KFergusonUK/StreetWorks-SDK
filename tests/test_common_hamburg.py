"""Tests for streetworks.common.from_hamburg.

Fixture is real Hamburg street data (tests/fixtures/hamburg_streets_real.json),
captured live 2026-08-20 from Hamburg's real, keyless OGC API Features
service (Zentraler AdressService Hamburg / GAGES).
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_hamburg_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "hamburg_streets_real.json").read_text(
        encoding="utf-8"
    )
)

_FEATURES = {f["id"]: f for f in FIXTURE["features"]}


def test_real_name_and_identifier():
    street = from_hamburg_street(_FEATURES["00002"])
    assert street.name == "Wasserpark Dove-Elbe"
    identifier = street.identifiers[0]
    assert identifier.scheme == "id"
    assert identifier.value == "00002"
    assert identifier.scope == "Hamburg"


def test_geometry_is_a_real_wgs84_point_swapped_to_lat_lon():
    street = from_hamburg_street(_FEATURES["00002"])
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    lat, lon = street.geometry.value
    assert 53.4 < lat < 53.6
    assert 9.9 < lon < 10.2


def test_administrative_area_is_the_constant_hamburg():
    street = from_hamburg_street(_FEATURES["00001"])
    assert street.administrative_area == "Hamburg"
    assert street.territory == "Germany"
    # The real, finer Ortsteil identifier is preserved raw, never parsed out.
    assert "OT 0603" in street.raw["properties"]["geographicidentifier"]
