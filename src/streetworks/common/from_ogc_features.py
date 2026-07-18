"""German state roadworks (OGC WFS/Features GeoJSON) -> streetworks.common
converter.

One converter for every state - it reads a
:class:`~streetworks.ogc.germany.StateFieldMap` rather than having its own
per-state logic, so adding a state to
:data:`~streetworks.ogc.germany.FIELD_MAPS` is enough; nothing here
changes. ``source_grade`` is :attr:`~streetworks.common.SourceGrade.OPERATOR`
for every state - this is mapping-authority open geodata (each state's own
Landesbetrieb/geoportal), not a statutory works register the way Street
Manager or SRWR are.

**1:1, no grouping** - these feeds carry no genuine works/phase grouping
key confirmed strongly enough to build on. One
:class:`~streetworks.common.Works` per feature, carrying exactly one
:class:`~streetworks.common.WorksSite`. Both Brandenburg's ``ID`` field
(prefix/suffix structure, but only ~81-88% agreement within a group -
far short of Autobahn's verified 100%) and Saxony's ``ID`` field (1,531
features, only 1,133 distinct values) show a real pattern - raised in
:mod:`streetworks.ogc.germany`'s docstring, not acted on, per this
project's record-identity discipline.

**Geometry**: ``Point`` (Hamburg) and ``LineString`` (Brandenburg, Saxony)
are both handled - a real line keeps every vertex on
``Coordinate.points``, never collapsed to just its first vertex, same
rule as WZDx/DATEX line geometry.

**CRS is read from the field map, not assumed** - GeoJSON's native axis
order is ``(x, y)``; for EPSG:4326 that means ``(lon, lat)``, flipped
here to this SDK's ``(lat, lon)`` convention, same as ``from_wzdx``/
``from_autobahn``. Saxony's real data has no WGS84 source at all
(``EPSG:25833``/UTM33N only, confirmed exhaustively - see
:mod:`streetworks.ogc.germany`) - for that, ``(x, y)`` is carried through
as ``(easting, northing)`` unchanged, no flip, exactly how
``from_streetmanager`` already handles British National Grid elsewhere in
this SDK. ``Coordinate.crs`` always states which convention applies -
never silently reprojected, per this SDK's standing policy.

**Dates**: every state states real, structured start/end dates (never
free-text extraction, unlike Autobahn) - Hamburg and Saxony both
``DD.MM.YYYY``, Brandenburg alone bare ISO - every one date-only (no time
component in any state's real data). Represented as midnight
Europe/Berlin via :mod:`zoneinfo`, same convention as Autobahn's
date-only fields, so every datetime in this SDK stays comparable (never a
naive one mixed in).

**``date_confidence`` is a judgement call, documented rather than
asserted**: neither state has anything like DATEX's ``validityStatus`` or
Autobahn's ``startTimestamp``-vs-parsed-text split to key off. Since every
date here comes from a genuine structured field - a road authority's own
stated schedule, not estimated/inferred text - a present, parseable start
date maps to :attr:`~streetworks.common.DateConfidence.VERIFIED`; a
missing or unparseable one maps to
:attr:`~streetworks.common.DateConfidence.UNKNOWN`. There is no
``ESTIMATED`` tier for this converter - unlike Autobahn's free-text dates,
nothing here is a lower-confidence extraction. Revisit if a state turns up
a genuine planned-vs-active signal.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..ogc.germany import StateFieldMap
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_ogc_features"]

JSON = dict[str, Any]

_BERLIN = ZoneInfo("Europe/Berlin")


#: Saxony's "de"-format dates sometimes carry an hour suffix -
#: ``"16.08.2026  08 Uhr"`` - confirmed live across the whole feed (2,423
#: plain-date, 639 with this suffix, 0 unmatched - no third shape exists).
#: Real stated information (an actual hour, not just midnight), so it's
#: parsed rather than dropped - not the same kind of exception Autobahn's
#: free-text extraction is, since this is still a small formatting
#: variant on one structured field, not prose.
_DE_DATE_WITH_HOUR = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})\s+(\d{1,2})\s*Uhr$")


def _parse_date(value: str | None, date_format: str) -> datetime | None:
    """Date-only fields, both formats - represented as midnight
    Europe/Berlin unless a real hour is stated (see
    :data:`_DE_DATE_WITH_HOUR`), never a naive datetime (see module
    docstring)."""
    if not value:
        return None
    if date_format == "de":
        if m := _DE_DATE_WITH_HOUR.match(value):
            day, month, year, hour = (int(g) for g in m.groups())
            try:
                return datetime(year, month, day, hour, tzinfo=_BERLIN)
            except ValueError:
                return None
        try:
            day, month, year = (int(p) for p in value.split("."))
        except ValueError:
            return None
    else:
        try:
            year, month, day = (int(p) for p in value.split("-"))
        except ValueError:
            return None
    try:
        return datetime(year, month, day, tzinfo=_BERLIN)
    except ValueError:
        return None


def _coordinate(geometry: JSON | None, crs: str) -> Coordinate | None:
    """EPSG:4326 sources state GeoJSON's native ``(lon, lat)`` - flipped to
    this SDK's ``(lat, lon)`` convention, same as ``from_wzdx``/
    ``from_autobahn``. Anything else (Saxony: EPSG:25833/UTM33N) is
    carried through unchanged - ``(x, y)`` as the source states it, no
    flip, matching how ``from_streetmanager`` handles British National
    Grid: a non-4326 CRS has no "wrong way round" to correct, so this SDK
    never guesses at one."""
    if not geometry:
        return None
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return None
    flip = crs == "EPSG:4326"
    try:
        if kind == "Point":
            x, y = coordinates
            value = (float(y), float(x)) if flip else (float(x), float(y))
            return Coordinate(value=value, crs=crs)
        if kind == "LineString":
            points = tuple(
                (float(y), float(x)) if flip else (float(x), float(y)) for x, y in coordinates
            )
            if not points:
                return None
            return Coordinate(
                value=points[0], crs=crs, points=points if len(points) > 1 else None
            )
    except (TypeError, ValueError):
        return None
    return None


def _to_works(feature: JSON, field_map: StateFieldMap) -> Works:
    properties = feature.get("properties") or {}
    start = _parse_date(
        properties.get(field_map.start.field) if field_map.start else None,
        field_map.start.format if field_map.start else "iso",
    )
    end = _parse_date(
        properties.get(field_map.end.field) if field_map.end else None,
        field_map.end.format if field_map.end else "iso",
    )
    confidence = DateConfidence.VERIFIED if start is not None else DateConfidence.UNKNOWN
    coordinate = _coordinate(feature.get("geometry"), field_map.crs)
    road = properties.get(field_map.road_field) if field_map.road_field else None
    works_type = properties.get(field_map.title_field) if field_map.title_field else None
    status = properties.get(field_map.status_field) if field_map.status_field else None
    promoter = properties.get(field_map.promoter_field) if field_map.promoter_field else None
    # Prefer a real `ID` property when one exists (Brandenburg: the
    # meaningful "267201193_3"-style identifier) over the GeoJSON
    # feature's own `id` (an opaque WFS-assigned one, e.g.
    # "baustelleninfo_1199") - falling back to the latter only when no
    # `ID` property exists at all (Hamburg, whose feature `id` - e.g.
    # "DE.HH.UP_BAUSTELLE_916925" - is itself the meaningful identifier).
    reference = str(properties.get("ID") or feature.get("id") or "")

    site = WorksSite(
        reference=reference,
        works_type=works_type,
        status=status,
        location_description=str(road) if road is not None else None,
        coordinate=coordinate,
        proposed_start=start,
        proposed_end=end,
        actual_start=start if confidence is DateConfidence.VERIFIED else None,
        date_confidence=confidence,
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )
    return Works(
        reference=reference,
        coordinate=coordinate,
        promoter=str(promoter) if promoter is not None else None,
        territory="Germany",
        administrative_area=field_map.state,
        source_grade=SourceGrade.OPERATOR,
        sites=(site,),
        raw=feature,
    )


def from_ogc_features(features: list[JSON], field_map: StateFieldMap) -> list[Works]:
    """Convert raw GeoJSON Feature dicts (from
    :meth:`streetworks.ogc.germany.GermanRoadworksClient.fetch`) into
    :class:`~streetworks.common.Works` using ``field_map`` - one ``Works``
    per feature, one ``WorksSite`` each (see module docstring for why).
    ``field_map.state`` becomes ``territory="Germany"``,
    ``administrative_area=field_map.state`` on every result."""
    return [_to_works(feature, field_map) for feature in features]
