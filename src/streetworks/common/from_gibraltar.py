"""Gibraltar Street Gazetteer -> streetworks.common converter. This
SDK's first British Overseas Territory streets coverage.

**Real ``MultiLineString`` geometry, genuinely multi-part on a real
majority of records - confirmed live, not assumed single-part from a
handful of samples.** 150 of 277 real features (54%) carry more than one
line within their ``MultiLineString`` (a real road drawn as several
disconnected pieces sharing one name/``inspireId``, e.g. where it's
crossed by a junction) - so this converter always populates
``Coordinate.parts``, the same real multi-part handling
:mod:`.from_tigerweb` already established for TIGERweb's own
``MultiLineString`` layers, never silently dropping every part but the
first.

``identifiers`` uses the real ``inspireId`` (scheme ``"inspire_id"``,
scoped ``"Gibraltar"`` - a small, real per-layer sequence, not a
national street-register number like a USRN, the same honest
"real but dataset-scoped" framing TIGERweb's own ``OID`` gets).

``street_type`` is never populated - the real ``type`` field is null on
every live record checked, no other classification field exists on this
layer.

``names``: **``label`` is a composed display string, not a single real
name - confirmed live across the full 277-record layer, not assumed
from a handful of samples that happened to agree.** ``label`` and
``name`` genuinely differ on 59/277 (21%) of real records, always in
the same real shape: ``label`` is ``"{name} - {collname1}[ -
{collname2}]"`` (e.g. real record `"Queensway - Dockyard Road - Dockyard
Approach Road"` has ``name="Queensway"``, ``collname1="Dockyard Road"``,
``collname2="Dockyard Approach Road"`` - three genuinely separate real
street names for one segment, often an English name alongside a real
Llanito/Spanish local name, e.g. ``"New Street"``/``"Calle Nueva"``).
Fusing ``label`` into one `Name` would merge these into an unsearchable
compound string, so this converter never does - ``name``, ``collname1``
and ``collname2`` each become their own
:class:`~streetworks.common.gazetteer.Name` where real and non-blank,
``label`` itself is never read. ``name`` is null on 2/277 real records
(a genuine gap, not fabricated) - the real alternate names still convert
normally in that case.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import GeometryGrade, Name, Street
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_gibraltar_street"]

JSON = dict[str, Any]

#: Confirmed live: this server genuinely honours a requested EPSG:4326
#: reprojection - see streetworks.gibraltar.client's module docstring.
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


def from_gibraltar_street(feature: JSON) -> Street:
    """Convert one real Gibraltar street GeoJSON ``Feature`` (from
    :meth:`streetworks.gibraltar.GibraltarStreetsClient.iter_streets`)
    into a :class:`~streetworks.common.gazetteer.Street`."""
    properties = feature.get("properties", {})
    geometry = _geometry(feature.get("geometry"))
    if geometry is None:
        inspire_id = properties.get("inspireId")
        raise ValueError(f"Gibraltar feature inspireId={inspire_id!r} has no geometry to convert")

    name = properties.get("name")
    collname1 = properties.get("collname1")
    collname2 = properties.get("collname2")
    names = []
    if name:
        names.append(Name(value=name))
    if collname1 and collname1 != name:
        names.append(Name(value=collname1))
    if collname2 and collname2 not in (name, collname1):
        names.append(Name(value=collname2))

    inspire_id = properties.get("inspireId")
    identifiers = (
        (Identifier(scheme="inspire_id", value=str(inspire_id), scope="Gibraltar"),)
        if inspire_id is not None
        else ()
    )

    return Street(
        identifiers=identifiers,
        names=tuple(names),
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED,
        territory="Gibraltar",
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )
