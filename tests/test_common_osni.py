"""Tests for streetworks.common.from_osni - built directly against
:class:`~streetworks.osni.models.Streetname` objects, no HTTP mocking
needed here."""

from __future__ import annotations

from streetworks.common import from_osni
from streetworks.common.gazetteer import GeometryGrade
from streetworks.common.models import Coordinate, Identifier, SourceGrade
from streetworks.osni.models import Streetname

_REAL_STREETNAME = Streetname(
    streetname="ABBACY ROAD",
    usrn=16884,
    objectid=2,
    easting=358572.0,
    northing=355614.0,
    raw={"STREETNAME": "ABBACY ROAD", "USRN": 16884, "OBJECTID": 2},
)


def test_from_osni_converts_a_real_streetname():
    street = from_osni(_REAL_STREETNAME)

    assert street.name == "ABBACY ROAD"
    assert street.territory == "Northern Ireland"
    assert street.source_grade == SourceGrade.REGISTER
    assert street.geometry_grade == GeometryGrade.PUBLISHED
    assert street.geometry == Coordinate(value=(358572.0, 355614.0), crs="EPSG:29903")
    assert street.raw is _REAL_STREETNAME


def test_from_osni_scopes_usrn_to_osni_not_the_gb_national_scheme():
    street = from_osni(_REAL_STREETNAME)

    by_scheme = {i.scheme: i for i in street.identifiers}
    assert by_scheme["usrn"] == Identifier(scheme="usrn", value="16884", scope="OSNI")
    assert by_scheme["objectid"] == Identifier(scheme="objectid", value="2", scope="OSNI")


def test_from_osni_never_reprojects_the_irish_grid_coordinate():
    street = from_osni(_REAL_STREETNAME)
    assert street.geometry is not None
    assert street.geometry.crs == "EPSG:29903"
    assert street.geometry.value == (358572.0, 355614.0)


def test_from_osni_never_emits_segment_refs():
    # A name+point gazetteer only - no street geometry beyond the point,
    # so there is nothing to reference as a segment.
    street = from_osni(_REAL_STREETNAME)
    assert street.segment_refs == ()
