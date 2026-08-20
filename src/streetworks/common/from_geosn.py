"""Germany (Saxony/Sachsen, GeoSN Hauskoordinaten) -> streetworks.common
converter.

**A genuine ``Street``, one per real deduplicated (municipality, street)
combination - 100% carry a real name, confirmed against the complete
national dataset (990,090 real address rows, 42,824 real distinct
street combinations).** This source is address-point data, not a
dedicated street register - deduplication happens in
:meth:`streetworks.geosn.GeoSNStreetsClient.iter_streets`, this
converter only ever sees one already-representative row per street.

**Geometry is a real address point, reprojected client-side from
ETRS89/UTM zone 33N.** See :mod:`streetworks.geosn.client`'s own
docstring for why this is real, standard-order, no-swap-needed
UTM33N - unlike Lithuania's own UTM-family source. This SDK's
``(lat, lon)`` swap convention applies, the same as ``from_dar_street``.
The chosen point is the *first* real address row seen for that street -
a real, stated coordinate, not a computed centroid, the same
"arbitrary-but-real representative point" discipline
``from_oslo``/``from_canton_zurich``/``from_brandenburg_street`` already
apply to their own polygon-first-vertex case.

``administrative_area`` carries the real ``gmd`` (municipality name)
directly - already a resolved name, no lookup or reconstruction needed,
unlike Brandenburg's own two-field reconstruction. ``ott`` (Ortsteil
name), ``qua`` (a real quality flag), and the postal fields
(``postplz``/``postonm``) have no dedicated home on this model - kept
`.raw`-only.
"""

from __future__ import annotations

from ._utm33n import utm33n_to_wgs84
from .gazetteer import GeometryGrade, Name, Street
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_geosn_street"]

JSON = dict[str, str]

_CRS = "EPSG:4326"


def _geometry(row: JSON) -> Coordinate | None:
    easting = row.get("ostwert")
    northing = row.get("nordwert")
    if not easting or not northing:
        return None
    lon, lat = utm33n_to_wgs84(float(easting), float(northing))
    return Coordinate(value=(lat, lon), crs=_CRS)


def from_geosn_street(row: JSON) -> Street:
    """Convert one real, already-deduplicated GeoSN Hauskoordinaten row
    (from :meth:`streetworks.geosn.GeoSNStreetsClient.iter_streets`)
    into a :class:`~streetworks.common.gazetteer.Street`."""
    name = row.get("str")
    names = (Name(value=name),) if name and name.strip() else ()

    identifiers = []
    strschl = row.get("strschl")
    if strschl:
        identifiers.append(Identifier(scheme="strschl", value=strschl, scope="Germany"))

    geometry = _geometry(row)

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        territory="Germany",
        administrative_area=row.get("gmd") or None,
        source_grade=SourceGrade.REGISTER,
        raw=row,
    )
