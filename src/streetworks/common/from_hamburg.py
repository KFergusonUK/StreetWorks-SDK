"""Germany (Hamburg, Zentraler AdressService Hamburg / GAGES) ->
streetworks.common converter.

**A genuine ``Street``, one per real feature - 100% carry a real name,
confirmed against a live 1000-record sample (Hamburg's own subject is
named streets, not an unlabelled segment network).**

**Geometry is a real point, genuinely reprojected server-side to
WGS84 by this API's own default** - see
:mod:`streetworks.hamburg.client`'s own docstring. This SDK's ``(lat,
lon)`` swap convention applies, the same as ``from_copenhagen``/
``from_dar_street``.

``administrative_area`` is a per-provider constant, ``"Hamburg"`` - the
real per-feature ``geographicidentifier`` states a finer Ortsteil
(district) code inline, but no separate code-to-name lookup exists on
this API; the raw field is kept on ``.raw``, never parsed into a
fabricated field. ``strassenname_kurz`` (a real short-form name, often
literally ``"-"`` when no shortening is needed) and
``strname_normalisiert`` (a real normalised/search form) have no
dedicated home on this model - kept `.raw`-only.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import GeometryGrade, Name, Street
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_hamburg_street"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_ADMINISTRATIVE_AREA = "Hamburg"


def _geometry(geometry: JSON | None) -> Coordinate | None:
    if not geometry or geometry.get("type") != "Point":
        return None
    coords = geometry.get("coordinates")
    if not coords:
        return None
    lon, lat = coords[0], coords[1]
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def from_hamburg_street(feature: JSON) -> Street:
    """Convert one real Hamburg ``strassen`` GeoJSON ``Feature`` (from
    :meth:`streetworks.hamburg.HamburgStreetsClient.iter_streets`) into
    a :class:`~streetworks.common.gazetteer.Street`."""
    properties = feature.get("properties", {})
    geometry = _geometry(feature.get("geometry"))

    name = properties.get("strname")
    names = (Name(value=name),) if name and name.strip() else ()

    identifiers = []
    feature_id = feature.get("id")
    if feature_id:
        identifiers.append(Identifier(scheme="id", value=str(feature_id), scope="Hamburg"))

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        territory="Germany",
        administrative_area=_ADMINISTRATIVE_AREA,
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )
