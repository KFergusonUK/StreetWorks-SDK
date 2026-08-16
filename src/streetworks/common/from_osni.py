"""OSNI (Northern Ireland Streetnames) -> streetworks.common gazetteer
converter.

A genuinely thinner shape than this SDK's other `Street` sources - name
plus one representative point, nothing else (see
:mod:`streetworks.osni.client`'s own module docstring for why: no ASD-
style attribute richness, no street geometry beyond the single point,
and no confirmed cross-reference to GB's national USRN/NSG scheme).
"""

from __future__ import annotations

from ..osni.models import Streetname
from .gazetteer import GeometryGrade, Name, Street
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_osni"]

#: Confirmed by coordinate-value plausibility, not read from a live
#: spatialReference response - see streetworks.osni.client's own module
#: docstring for why.
_CRS = "EPSG:29903"


def from_osni(streetname: Streetname) -> Street:
    """Convert one real :class:`~streetworks.osni.models.Streetname` into
    a :class:`~streetworks.common.gazetteer.Street`.

    ``usrn`` becomes a real :class:`~streetworks.common.Identifier`,
    scoped to ``"OSNI"`` rather than presented as a GB-national USRN -
    Northern Ireland is outside that scheme, see
    :class:`~streetworks.osni.models.Streetname`'s own docstring. Geometry
    is always present (every real feature carries a point) so
    ``geometry_grade`` is always :attr:`~streetworks.common.gazetteer.GeometryGrade.PUBLISHED`.
    """
    return Street(
        identifiers=(
            Identifier(scheme="usrn", value=str(streetname.usrn), scope="OSNI"),
            Identifier(scheme="objectid", value=str(streetname.objectid), scope="OSNI"),
        ),
        names=(Name(value=streetname.streetname),),
        geometry=Coordinate(value=(streetname.easting, streetname.northing), crs=_CRS),
        geometry_grade=GeometryGrade.PUBLISHED,
        territory="Northern Ireland",
        source_grade=SourceGrade.REGISTER,
        raw=streetname,
    )
