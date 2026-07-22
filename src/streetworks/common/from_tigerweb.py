"""TIGERweb -> streetworks.common gazetteer converter.

**Segment only - no Street.** Checked, not assumed: TIGERweb's real road
layers publish flat segment records (``BASENAME``/``NAME``/``MTFCC``/
``OID``/...) with no separate named-street entity anywhere in the service
(no layer anywhere under ``TIGERweb/`` aggregates segments under one named
street the way BD TOPO's ``voie_nommee`` or NVDB's ``VegAdresse`` do - see
:mod:`streetworks.arcgis.tigerweb`'s module docstring). Per the
"no synthetic streets" rule (see :mod:`streetworks.common.gazetteer`), this
converter never fabricates one - the US yields ``Segment`` only here, the
same shape as the Netherlands (:mod:`streetworks.common.from_nwb`).

``identifiers`` uses the real ``OID`` field (a TIGER/Line TLID-shaped
numeric string, e.g. ``"110431686451"``) under the scheme ``"tiger_oid"``,
deliberately not a scheme name implying national authority - TIGER is a
statistical/cartographic product, not a legal street register, and this
id is only meaningful within this Census Bureau dataset (see the module
docstring in :mod:`streetworks.arcgis.tigerweb` for the full context on
why this SDK's ``Identifier.scope`` concept exists for exactly this kind
of case).

``street_type`` carries the real ``MTFCC`` value undecoded (``"S1100"``
primary, ``"S1200"`` secondary, ``"S1400"`` local, and others observed live
e.g. ``"S1630"`` for a ramp) - no lookup table bundled, per this SDK's
standing rule.

``as_at`` is always ``None`` - checked, not an oversight: no per-feature
date/vintage field exists on this layer's real schema. A TIGERweb
service's vintage is a property of *which* service URL you queried
(``tigerWMS_Current``, ``tigerWMS_ACS2024``, ...), not a per-record field
this converter could read.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import Name, Segment, StreetType
from .models import Coordinate, Identifier

__all__ = ["from_tigerweb"]

JSON = dict[str, Any]

#: Confirmed live: f=geojson returns genuine WGS84 here regardless of
#: outSR or the layer's stated native CRS (Web Mercator) - see
#: streetworks.arcgis.tigerweb's module docstring.
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
        return Coordinate(value=parts[0][0], crs=_CRS, parts=parts)
    return None


def from_tigerweb(feature: JSON) -> Segment:
    """Convert one real TIGERweb road-segment GeoJSON ``Feature`` (from
    :meth:`streetworks.arcgis.tigerweb.TIGERwebClient.iter_roads`) into a
    :class:`~streetworks.common.gazetteer.Segment`."""
    properties = feature.get("properties", {})
    geometry = _geometry(feature.get("geometry"))
    if geometry is None:
        oid = properties.get("OID") or properties.get("OBJECTID")
        raise ValueError(f"TIGERweb feature OID={oid!r} has no geometry to convert")

    oid = properties.get("OID")
    mtfcc = properties.get("MTFCC")
    name = properties.get("NAME")

    return Segment(
        geometry=geometry,
        identifiers=(Identifier(scheme="tiger_oid", value=str(oid)),) if oid else (),
        names=(Name(value=name),) if name else (),
        street_type=StreetType(code=mtfcc) if mtfcc else None,
        raw=feature,
    )
