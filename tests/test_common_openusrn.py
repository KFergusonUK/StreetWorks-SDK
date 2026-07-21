"""Tests for streetworks.common.from_openusrn."""

from streetworks.common import GeometryGrade, Identifier, from_openusrn
from streetworks.openusrn.reader import UsrnStreet


def test_real_street_converts_with_published_geometry():
    # usrn=33909869 is real - Carr Street, Spennymoor, Durham - verified
    # live against DataVIA this session (see docs/gazetteer-field-dump.md).
    street = from_openusrn(
        UsrnStreet(usrn=33909869, geometry="LINESTRING (-1.611 54.702, -1.612 54.703)"),
        territory="England",
    )
    assert street.identifiers == (Identifier(scheme="usrn", value="33909869"),)
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry.crs == "EPSG:27700"
    assert street.territory == "England"
    assert street.names == ()  # OS Open USRN states no name at all


def test_real_null_geometry_row_is_absent_not_an_error():
    # This SDK's own openusrn test fixture models usrn=84202034 with a
    # real NULL geometry as a deliberate case, not hypothetical.
    street = from_openusrn(UsrnStreet(usrn=84202034, geometry=None))
    assert street.geometry is None
    assert street.geometry_grade is GeometryGrade.ABSENT
