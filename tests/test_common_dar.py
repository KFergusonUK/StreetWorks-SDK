"""Tests for streetworks.common.from_dar.

Fixture is real DAR (Danmarks Adresseregister) Navngivenvej data
(tests/fixtures/dar_streets_real.json), captured live 2026-08-18 from
Datafordeleren's real, keyless REST endpoint. Coordinate values are
trimmed (fewer vertices per line/ring) but real - not fabricated
points - and cross-checked against DAWA's own real WGS84 output for the
same road (Halvdansvej) before trimming; see
streetworks.dar.client's own module docstring.
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_dar_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "dar_streets_real.json").read_text(encoding="utf-8")
)

_RECORDS = {r["id_lokalId"]: r for r in FIXTURE}


def test_real_name_and_multipart_line_geometry():
    street = from_dar_street(_RECORDS["00008748-e0ee-4cb3-83b7-167455a2efaf"])
    assert street.name == "Halvdansvej"
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry is not None
    assert street.geometry.parts is not None
    assert len(street.geometry.parts) == 2
    # (lat, lon) convention - real coordinates cross-checked against DAWA.
    lat, lon = street.geometry.value
    assert 56.0 < lat < 56.1
    assert 12.4 < lon < 12.5


def test_administrative_area_is_the_raw_kommune_code():
    street = from_dar_street(_RECORDS["00008748-e0ee-4cb3-83b7-167455a2efaf"])
    assert street.administrative_area == "0217"
    assert street.territory == "Denmark"


def test_point_fallback_when_no_line_is_stated():
    street = from_dar_street(_RECORDS["03adbd7e-5541-4e6f-9396-105f3cce7d3a"])
    assert street.name == "Højby Have"
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry is not None
    assert street.geometry.points is None
    assert street.geometry.parts is None
    # The real polygon is preserved unmodified in raw, never read into Coordinate.
    assert "POLYGON" in street.raw["vejnavnebeliggenhed_vejnavneområde"]


def test_no_line_no_point_no_polygon_is_genuinely_absent():
    street = from_dar_street(_RECORDS["07f648f5-bf05-4ead-aef6-e13fb566b3ea"])
    assert street.name == "Danfoss-Nordre Ringvej"
    assert street.geometry is None
    assert street.geometry_grade is GeometryGrade.ABSENT


def test_missing_name_is_never_fabricated():
    street = from_dar_street(_RECORDS["040d9520-5dd4-433c-ad82-d34a52f2675b"])
    assert street.names == ()
    assert street.name is None
    # Still has a real point fallback despite carrying no name.
    assert street.geometry_grade is GeometryGrade.PUBLISHED
