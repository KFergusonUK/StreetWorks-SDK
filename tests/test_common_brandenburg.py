"""Tests for streetworks.common.from_brandenburg.

Fixture rows are parsed directly from the same real GML bundled in
tests/fixtures/brandenburg_streets_real.xml, the same way
streetworks.brandenburg.BrandenburgStreetsClient.iter_streets does -
see tests/test_brandenburg.py and streetworks.brandenburg.client's own
module docstring for the live evidence behind each.
"""

from pathlib import Path

from streetworks.brandenburg.client import _parse_feature_collection
from streetworks.common import GeometryGrade, from_brandenburg_street

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "brandenburg_streets_real.xml"
_RECORDS = {r["strassenname"]: r for r in _parse_feature_collection(FIXTURE_PATH.read_bytes())}


def test_real_name_and_identifier():
    street = from_brandenburg_street(_RECORDS["Am Feuerwerkslaboratorium"])
    assert street.name == "Am Feuerwerkslaboratorium"
    identifier = street.identifiers[0]
    assert identifier.scheme == "gml_id"
    assert identifier.value == "BB_STR_1"
    assert identifier.scope == "Germany"


def test_geometry_is_always_absent_never_a_forced_polygon():
    street = from_brandenburg_street(_RECORDS["Am Feuerwerkslaboratorium"])
    assert street.geometry is None
    assert street.geometry_grade is GeometryGrade.ABSENT
    # The real polygon is preserved unmodified in raw, never read into Coordinate.
    assert "gml:Polygon" in street.raw["geographicExtent_gml"]


def test_administrative_area_reconstructed_from_two_real_fields():
    street = from_brandenburg_street(_RECORDS["Am Feuerwerkslaboratorium"])
    assert street.administrative_area == "Brandenburg an der Havel"
    assert street.territory == "Germany"


def test_missing_ortsnamepost_leaves_administrative_area_none():
    # A real Berlin (land=11) record with genuinely empty ortsnamePost.
    street = from_brandenburg_street(_RECORDS["Simmelstraße"])
    assert street.administrative_area is None
    assert street.raw["land"] == "11"
    assert street.territory == "Germany"
