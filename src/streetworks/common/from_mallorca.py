"""Consell de Mallorca (IDEmallorca) -> streetworks.common converter.

One ``Works`` per ``incidencies_icon`` feature (the spine - see
:mod:`streetworks.ogc.mallorca`'s own docstring), one ``WorksSite`` each.
``territory="Spain"``, ``administrative_area="Consell de Mallorca"`` - the
island authority is the data-owning operator, the same rule already
applied to Autobahn GmbH/National Highways/Via Lietuva - not "Mallorca" as
if it were a region, the Consell is the authority.

**The two-layer join, applied here**: each icon's own ``codi`` is looked
up in ``trams`` (keyed by their own ``codi``); when found, the tram's real
``MultiLineString`` becomes ``Coordinate.parts`` (each part is one line,
in source order - a real record, ``codi=19528``, genuinely has 2 parts,
not always 1). ``Coordinate.value`` is always the icon's own point - the
representative location - never the tram's first vertex, so point-only
incidents (no tram match - confirmed live, 1/17) still get a real,
non-fabricated ``Coordinate`` with ``parts=None``.

**CRS carried through unconverted, EPSG:25831 (UTM31N) - no axis flip.**
GeoJSON coordinates here are already ``(easting, northing)``, not
``(lon, lat)`` - unlike EPSG:4326 sources (``from_wzdx``/``from_autobahn``/
``from_ogc_features`` all flip GeoJSON's native ``(x, y)`` to this SDK's
``(lat, lon)`` for WGS84), a non-4326 CRS has no "wrong way round" to
correct, so it's taken as ``(x, y)`` as stated - the same rule
``from_streetmanager`` already applies to British National Grid and
``from_ogc_features`` applies to Saxony's UTM33N.

**Dates**: ``inici``/``fin`` are ``DD/MM/YYYY HH:MM``, confirmed 17/17 in
one live pull, no timezone stated - represented as midnight-or-stated-time
Europe/Madrid (Balearic Islands observe CET/CEST, same DST rule as
mainland Spain and Germany), never a naive datetime, matching the
Europe/Berlin convention ``from_ogc_features`` already uses for German
states. **``date_confidence`` follows the same judgement call
``from_ogc_features`` already makes for the German states**: there's no
DATEX-style ``validityStatus`` or Autobahn-style verified-timestamp split
here either - a road authority's own genuine structured schedule field, so
a present, parseable start maps to ``VERIFIED``, matching that precedent
rather than inventing a different rule for a structurally identical
situation.

**Fields not mapped to a canonical slot, preserved only on ``.raw``**:
``sentit``/``sentit_desc`` (direction - a real, decoded value, not opaque,
but no canonical field exists for it), ``restriccio`` (a real
restriction-type label, e.g. "Tall de carril" - distinct from ``tipoinc``,
no canonical slot), ``icon``/``color`` (viewer rendering hints),
``lastupd`` (a real last-updated timestamp, different date format
(``YYYY/MM/DD HH:MM``) from ``inici``/``fin`` - no canonical "last
updated" field exists on ``WorksSite``). None of these are lost - the
whole feature is always on ``WorksSite.raw``/``Works.raw``, per this
project's "canonicalise the shared, preserve the specific" rule.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_mallorca"]

JSON = dict[str, Any]

_MADRID = ZoneInfo("Europe/Madrid")

#: "DD/MM/YYYY HH:MM" - confirmed 17/17 real inici/fin values in one live
#: pull, no other shape seen.
_DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})$")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    match = _DATE_RE.match(value)
    if not match:
        return None
    day, month, year, hour, minute = (int(g) for g in match.groups())
    try:
        return datetime(year, month, day, hour, minute, tzinfo=_MADRID)
    except ValueError:
        return None


def _point(geometry: JSON | None) -> tuple[float, float] | None:
    if not geometry or geometry.get("type") != "Point":
        return None
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return None
    try:
        return (float(coordinates[0]), float(coordinates[1]))
    except (TypeError, ValueError, IndexError):
        return None


def _multilinestring_parts(
    geometry: JSON | None,
) -> tuple[tuple[tuple[float, float], ...], ...] | None:
    if not geometry or geometry.get("type") != "MultiLineString":
        return None
    coordinates = geometry.get("coordinates") or []
    parts = tuple(
        tuple((float(x), float(y)) for x, y in line) for line in coordinates if line
    )
    return parts or None


def _location_description(properties: JSON) -> str | None:
    road = properties.get("carretera")
    if not road:
        return None
    pk_from, pk_to = properties.get("pkinici"), properties.get("pkfin")
    if pk_from is not None and pk_to is not None:
        return f"{road} (km {pk_from}-{pk_to})"
    if pk_from is not None:
        return f"{road} (km {pk_from})"
    return str(road)


def _to_works(icon: JSON, tram: JSON | None) -> Works:
    properties = icon.get("properties") or {}
    point = _point(icon.get("geometry"))
    parts = _multilinestring_parts(tram.get("geometry")) if tram is not None else None
    coordinate = Coordinate(value=point, crs="EPSG:25831", parts=parts) if point else None

    start = _parse_date(properties.get("inici"))
    end = _parse_date(properties.get("fin"))
    confidence = DateConfidence.VERIFIED if start is not None else DateConfidence.UNKNOWN

    codi = properties.get("codi")
    reference = str(codi) if codi is not None else None

    site = WorksSite(
        reference=reference,
        works_type=properties.get("tipoinc"),
        location_description=_location_description(properties),
        coordinate=coordinate,
        proposed_start=start,
        proposed_end=end,
        actual_start=start if confidence is DateConfidence.VERIFIED else None,
        date_confidence=confidence,
        traffic_management=properties.get("observacions") or None,
        source_grade=SourceGrade.OPERATOR,
        raw={"icon": icon, "tram": tram},
    )
    return Works(
        reference=reference,
        coordinate=coordinate,
        territory="Spain",
        administrative_area="Consell de Mallorca",
        source_grade=SourceGrade.OPERATOR,
        sites=(site,),
        raw={"icon": icon, "tram": tram},
    )


def from_mallorca(icons: list[JSON], trams: list[JSON]) -> list[Works]:
    """Convert raw GeoJSON Feature dicts from
    :meth:`streetworks.ogc.mallorca.MallorcaClient.fetch_icons` (or
    :meth:`~streetworks.ogc.mallorca.MallorcaClient.fetch_roadworks_icons`)
    and :meth:`~streetworks.ogc.mallorca.MallorcaClient.fetch_trams` into
    :class:`~streetworks.common.Works` - one per icon, joined to its
    matching tram by ``codi`` where one exists (see module docstring for
    the point-only case)."""
    trams_by_codi = {
        tram["properties"]["codi"]: tram
        for tram in trams
        if (tram.get("properties") or {}).get("codi") is not None
    }
    return [
        _to_works(icon, trams_by_codi.get((icon.get("properties") or {}).get("codi")))
        for icon in icons
    ]
