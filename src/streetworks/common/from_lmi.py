"""Landmælingar Íslands (Iceland) IS 50V road network ->
streetworks.common converter.

**Real names on 84.0% of features (confirmed against the complete real
dataset - see `streetworks.lmi.client`'s own module docstring for why a
naive `IS NOT NULL` check overstated this at 99.98%) - a genuine
`Street`, not a `Segment`.** Unlike Ireland's Monaghan pilot (real
roads, genuinely no name) or TIGERweb/NRN (segment-only, no aggregating
entity), this layer's own real `nafnfitju` field is a real per-feature
street name (`"Laugavegur"`, `"Gnúpverjavegur"`) on the large majority
of records - so this converter produces `Street`, one per real WFS
feature, the same 1:1 (no grouping/dedupe) treatment Jersey's own
multi-row-per-USRN streets get. A real blank (a literal single-space
string, not just `NULL`) is treated as no name, never fabricated.

``identifiers`` carries the real `uuid` (scheme `"uuid"`, scoped
`"Iceland"`) and, where stated, the real route/section number
(`vegnr`/`kaflanr`, scheme `"road_number"`) - a real, *additional*
Vegagerðin reference alongside the name, not a replacement for one
(the Irish L-road/N-road/R-road situation this SDK already built
Monaghan against).

``street_type`` carries the real `vegflokkun_text_is` label (e.g.
`"Tengivegur"` - connecting road) - the source's own plain-language
classification, no lookup table needed since it's already decoded.

``administrative_area`` is never populated - checked, not an
oversight: no municipality/sveitarfélag field exists on this
particular layer (Landmælingar Íslands publishes municipal boundaries
as a separate layer, not joined here).
"""

from __future__ import annotations

from typing import Any

from .gazetteer import GeometryGrade, Name, Street, StreetType
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_lmi_street"]

JSON = dict[str, Any]

#: Confirmed live: this service's real f=json output is WGS84 by
#: default - see streetworks.lmi.client's module docstring.
_CRS = "EPSG:4326"


def _geometry(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    coords = geometry.get("coordinates")
    kind = geometry.get("type")
    if kind == "MultiLineString" and coords:
        parts = tuple(tuple(tuple(c) for c in line) for line in coords if line)
        if not parts:
            return None
        if len(parts) == 1:
            points = parts[0]
            return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
        return Coordinate(value=parts[0][0], crs=_CRS, parts=parts)
    if kind == "LineString" and coords:
        points = tuple(tuple(c) for c in coords)
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
    return None


def from_lmi_street(feature: JSON) -> Street:
    """Convert one real IS 50V road-segment GeoJSON ``Feature`` (from
    :meth:`streetworks.lmi.LmiStreetsClient.iter_streets`) into a
    :class:`~streetworks.common.gazetteer.Street`."""
    properties = feature.get("properties", {})
    geometry = _geometry(feature.get("geometry"))
    if geometry is None:
        uuid = properties.get("uuid")
        raise ValueError(f"LMI feature uuid={uuid!r} has no geometry to convert")

    name = properties.get("nafnfitju")
    names = (Name(value=name),) if name and name.strip() else ()

    identifiers = []
    uuid = properties.get("uuid")
    if uuid:
        identifiers.append(Identifier(scheme="uuid", value=uuid, scope="Iceland"))
    vegnr = properties.get("vegnr")
    kaflanr = properties.get("kaflanr")
    if vegnr:
        road_number = f"{vegnr}-{kaflanr}" if kaflanr else vegnr
        identifiers.append(Identifier(scheme="road_number", value=road_number, scope="Iceland"))

    street_type_label = properties.get("vegflokkun_text_is")

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        street_type=StreetType(label=street_type_label) if street_type_label else None,
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED,
        territory="Iceland",
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )
