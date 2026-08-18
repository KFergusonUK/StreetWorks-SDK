"""swisstopo (Switzerland, Amtliches Verzeichnis der Strassen) ->
streetworks.common converter.

**A genuine ``Street``, one per real row - 100% carry a real name,
confirmed against the complete national dataset (224,985 rows), the
cleanest coverage this SDK has built.** Unlike Ireland's Monaghan pilot
or TIGERweb/NRN, this register's own subject is street *names*, not an
unlabelled segment network.

**Geometry is a real, single stated point - never treated as a computed
centroid, and never swapped.** ``STR_EASTING``/``STR_NORTHING`` are a
genuinely projected CRS (``EPSG:2056``, Swiss LV95), so this SDK's
``(lat, lon)`` swap convention doesn't apply - stored as plain
``(x, y)``, the same discipline ``from_oslo``/``from_canton_zurich``
already apply to their own projected sources. This is real, stated
geometry, just point-only rather than the live API's own richer
``LineString`` - see :mod:`streetworks.swisstopo.client`'s own docstring
for why the bulk CSV (this converter's source) doesn't carry the line.

**``STR_STATUS``/``STR_OFFICIAL`` are kept raw-only, never used to
filter or grade.** 112/224,985 real rows are ``STR_STATUS="planned"``
(not yet built) and 3,654 are ``STR_OFFICIAL="false"`` (declared but not
yet official) - both real, live-confirmed states this converter passes
through rather than silently dropping; a caller that only wants
current/official streets can filter on ``.raw`` itself.

``street_type`` carries the real ``STR_TYPE`` value (``Street``/
``Area``/``Place``) directly - already a plain-language label, no lookup
table needed. ``administrative_area`` carries the real ``COM_NAME``
(municipality name) - the canton (``COM_CANTON``) is also real and
stated but has no second home on this model, so it stays raw-only.
"""

from __future__ import annotations

from .gazetteer import GeometryGrade, Name, Street, StreetType
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_swisstopo_street"]

JSON = dict[str, str]

#: Real Swiss LV95, stated by this resource's own filename convention -
#: see streetworks.swisstopo.client's own docstring.
_CRS = "EPSG:2056"


def from_swisstopo_street(row: JSON) -> Street:
    """Convert one real swisstopo Amtliches Verzeichnis der Strassen CSV
    row (from
    :meth:`streetworks.swisstopo.SwisstopoStreetsClient.iter_streets`)
    into a :class:`~streetworks.common.gazetteer.Street`."""
    name = row.get("STN_LABEL")
    names = (Name(value=name),) if name and name.strip() else ()

    identifiers = []
    esid = row.get("STR_ESID")
    if esid:
        identifiers.append(Identifier(scheme="str_esid", value=esid, scope="Switzerland"))

    street_type_label = row.get("STR_TYPE")

    easting = row.get("STR_EASTING")
    northing = row.get("STR_NORTHING")
    geometry = None
    if easting and northing:
        geometry = Coordinate(value=(float(easting), float(northing)), crs=_CRS)

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        street_type=StreetType(label=street_type_label) if street_type_label else None,
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        territory="Switzerland",
        administrative_area=row.get("COM_NAME") or None,
        source_grade=SourceGrade.REGISTER,
        raw=row,
    )
