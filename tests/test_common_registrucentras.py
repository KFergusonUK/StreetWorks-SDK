"""Tests for streetworks.common.from_registrucentras.

Fixture is real Registrų centras street data
(tests/fixtures/registrucentras_streets_real.json), captured live
2026-08-20 from Lithuania's national open-data portal
(get.data.gov.lt). Geometry is trimmed to a handful of real vertices per
part (fixture size only).
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_registrucentras_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "registrucentras_streets_real.json").read_text(
        encoding="utf-8"
    )
)

_RECORDS = {r["gat_kodas"]: r for r in FIXTURE}


def test_real_name_and_identifier():
    street = from_registrucentras_street(_RECORDS[16036])
    assert street.name == "Smukučių g."
    identifier = street.identifiers[0]
    assert identifier.scheme == "gat_kodas"
    assert identifier.value == "16036"
    assert identifier.scope == "Lithuania"


def test_geometry_axis_order_is_swapped_from_the_real_northing_easting_wkt():
    street = from_registrucentras_street(_RECORDS[16036])
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    lat, lon = street.geometry.value
    # Real Lithuanian geography - confirmed live against the same point
    # via a bounds-check on LKS-94's real easting/northing ranges.
    assert 55.0 < lat < 55.2
    assert 22.6 < lon < 22.8


def test_multilinestring_becomes_coordinate_parts():
    street = from_registrucentras_street(_RECORDS[16490])
    assert street.geometry.parts is not None
    assert len(street.geometry.parts) == 2


def test_administrative_area_never_populated():
    street = from_registrucentras_street(_RECORDS[16036])
    assert street.administrative_area is None
    assert street.territory == "Lithuania"
    # The real settlement reference is preserved raw, not silently dropped.
    assert street.raw["gyvenamoji_vietove"]["_id"] == "9d749b46-d228-4a51-b318-0f80c33303fe"
