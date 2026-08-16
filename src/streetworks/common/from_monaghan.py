"""Monaghan County Council road network -> streetworks.common converter.
This SDK's first Irish gazetteer coverage - a pilot for the real,
genuine county-council fan-out (see
:mod:`streetworks.arcgis.monaghan`'s own module docstring), and the
direct answer to the live investigation that ruled out a national
named-street source for Ireland (see ``docs/providers/pending.md``).

**Segment only - never a fabricated Street.** Real Irish rural roads
genuinely have no name - `Road_Name` is Ireland's own official route
number (`"L-31011-0"`, not a street name), confirmed live, not a gap in
this build. Per the "no synthetic streets" rule (see
:mod:`streetworks.common.gazetteer`), this converter never invents one
- `names` is **always the empty tuple** on every real
:class:`~streetworks.common.gazetteer.Segment` this module produces.
The real route number becomes `Segment`'s own :class:`~streetworks.common.models.Identifier`
instead (scheme ``"road_number"``, scoped ``"Monaghan"``) - a real,
stated, official reference, carried honestly as what it is rather than
misrepresented as a name.

(For anyone wondering why a converter needed to spell this out twice -
some of these roads genuinely have no name, and no one you ask will be
able to tell you either.)

``street_type`` carries the real `Road_Class` value as a plain label
(`"Local Tertiary"`, `"Regional"`, `"National Primary"`) - the same
label-not-code shape BD TOPO's own `nature` field gets.

``administrative_area`` uses the real `Municipal_District` where stated
(absent on every real `National_Roads` record, present on
`Regional_Roads`/`Local_Roads`).

**`Start_At`/`Finish_At` stay on `.raw` only, deliberately.** Real,
genuine junction/townland descriptions (e.g. `"Creeve - 4 Roads"`) -
how these roads are actually identified in practice - but there's no
canonical field for a described (rather than coordinate) endpoint pair
in this SDK's gazetteer model, and inventing one from a single real
source would be premature; see the module's own "trim test" rule.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import Segment, StreetType
from .models import Coordinate, Identifier

__all__ = ["from_monaghan_road"]

JSON = dict[str, Any]

#: Confirmed live: this service's real f=geojson output is WGS84
#: regardless of outSR - see streetworks.arcgis.monaghan's module
#: docstring.
_CRS = "EPSG:4326"


def _geometry(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    coords = geometry.get("coordinates")
    kind = geometry.get("type")
    if kind == "LineString" and coords:
        points = tuple(tuple(c) for c in coords)
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
    if kind == "MultiLineString" and coords:
        parts = tuple(tuple(tuple(c) for c in line) for line in coords if line)
        if not parts:
            return None
        if len(parts) == 1:
            points = parts[0]
            return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
        return Coordinate(value=parts[0][0], crs=_CRS, parts=parts)
    return None


def from_monaghan_road(feature: JSON) -> Segment:
    """Convert one real Monaghan road-segment GeoJSON ``Feature`` (from
    :meth:`streetworks.arcgis.monaghan.MonaghanRoadsClient.iter_roads`)
    into a :class:`~streetworks.common.gazetteer.Segment` - never a
    `Street`, and never a fabricated name. See module docstring."""
    properties = feature.get("properties", {})
    geometry = _geometry(feature.get("geometry"))
    if geometry is None:
        road_name = properties.get("Road_Name")
        raise ValueError(f"Monaghan feature Road_Name={road_name!r} has no geometry to convert")

    road_name = properties.get("Road_Name")
    identifiers = (
        (Identifier(scheme="road_number", value=road_name, scope="Monaghan"),)
        if road_name
        else ()
    )

    road_class = properties.get("Road_Class")
    municipal_district = properties.get("Municipal_District")

    return Segment(
        geometry=geometry,
        identifiers=identifiers,
        street_type=StreetType(label=road_class) if road_class else None,
        administrative_area=municipal_district or None,
        raw=feature,
    )
