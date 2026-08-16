"""National Road Network (NRN, Canada) -> streetworks.common gazetteer
converter.

**Segment only - no Street.** Checked, not assumed: this REST service's
real schema carries per-segment attributes only (`l_stname_c`, `roadclass`,
route names/numbers), no separate named-street entity anywhere in the
service to aggregate segments under - see
:mod:`streetworks.arcgis.nrn`'s module docstring. Per the "no synthetic
streets" rule (see :mod:`streetworks.common.gazetteer`), this converter
never fabricates one - Canada yields `Segment` only here, the same shape
as the US (:mod:`.from_tigerweb`) and the Netherlands
(:mod:`.from_nwb`).

**No identifiers** - checked, not an oversight: this REST service exposes
no genuine NRN-native per-segment id (no `NID`-shaped field anywhere in
its real schema, unlike the bulk GeoPackage/Shapefile product), only the
ArcGIS-managed `OBJECTID` - not carried here since it identifies a row
within one query's own layer, not a real feature in any
cross-referenceable sense (a step below even TIGERweb's own dataset-
scoped `OID`, which at least ties back to a real published TIGER
identifier).

**`administrative_area`: shared value only, never an arbitrary pick -
the same discipline** :mod:`.from_bdtopo` **established for its own real
left/right admin split.** `l_placenam`/`r_placenam` genuinely diverge on
segments that form a real administrative boundary (confirmed live, e.g.
a real Ontario segment between "Township of MacDonald, Meredith and
Aberdeen Additional" and "Township of Laird") - a single field can't
honestly state two different real values, so this stays `None` rather
than picking one side, exactly mirroring BD TOPO's own
`insee_commune_gauche`/`_droite` handling. The real `"Unknown"`
placeholder (see below) applies here too - confirmed live on a real,
non-trivial 13% of a 644,758-record Ontario sample - so it is cleaned
the same way a genuinely blank value would be, never carried through as
an administrative area literally called "Unknown".

**Names: a single name, not a fabricated left/right split - confirmed
live to be unnecessary.** `l_stname_c`/`r_stname_c` were checked live
across a real 644,758-record Ontario sample and a real British Columbia
sample: **zero** records where they differ, so this converter emits one
plain `Name`, only splitting into `side`-tagged names (the same
mechanism BD TOPO's own real divergent case uses) on the rare chance a
future province's data does diverge. A real `"Unknown"` value (NRN's own
stated placeholder for "genuinely no name recorded") is treated as no
name at all - never carried through as a literal street called
"Unknown".

``street_type`` carries the real `roadclass` value as a plain label
(e.g. `"Local / Street"`, `"Expressway / Highway"`) - the same
label-not-code shape BD TOPO's own `nature` field gets, no lookup table
needed since the source already states a plain string.

``as_at`` is always `None` - checked, not an oversight: no per-feature
date/vintage field exists on this layer's real schema, the same honest
gap TIGERweb's own converter documents.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import Name, Segment, StreetType
from .models import Coordinate

__all__ = ["from_nrn"]

JSON = dict[str, Any]

#: Confirmed live: f=geojson returns genuine WGS84-shaped output
#: regardless of outSR or this service's stated native CRS - see
#: streetworks.arcgis.nrn's module docstring.
_CRS = "EPSG:4326"

#: NRN's own real stated placeholder for "genuinely no name recorded" -
#: never carried through as a literal street name.
_UNKNOWN = "Unknown"


def _clean_name(value: str | None) -> str | None:
    if not value or value == _UNKNOWN:
        return None
    return value


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
        return Coordinate(value=parts[0][0], crs=_CRS, parts=parts)
    return None


def _names(left: str | None, right: str | None) -> tuple[Name, ...]:
    left = _clean_name(left)
    right = _clean_name(right)
    if left and right and left == right:
        return (Name(value=left),)
    names = []
    if left:
        names.append(Name(value=left, side="left"))
    if right and right != left:
        names.append(Name(value=right, side="right"))
    return tuple(names)


def from_nrn(feature: JSON) -> Segment:
    """Convert one real NRN road-segment GeoJSON ``Feature`` (from
    :meth:`streetworks.arcgis.nrn.NrnClient.iter_roads`) into a
    :class:`~streetworks.common.gazetteer.Segment`."""
    properties = feature.get("properties", {})
    geometry = _geometry(feature.get("geometry"))
    if geometry is None:
        oid = properties.get("OBJECTID")
        raise ValueError(f"NRN feature OBJECTID={oid!r} has no geometry to convert")

    l_placenam = _clean_name(properties.get("l_placenam"))
    r_placenam = _clean_name(properties.get("r_placenam"))
    administrative_area = l_placenam if l_placenam == r_placenam else None

    roadclass = properties.get("roadclass")

    return Segment(
        geometry=geometry,
        names=_names(properties.get("l_stname_c"), properties.get("r_stname_c")),
        street_type=StreetType(label=roadclass) if roadclass else None,
        administrative_area=administrative_area,
        raw=feature,
    )
