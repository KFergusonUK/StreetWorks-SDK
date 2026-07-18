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
key (no works reference, no identifier prefix that's actually corroborated
by a second field). One :class:`~streetworks.common.Works` per feature,
carrying exactly one :class:`~streetworks.common.WorksSite`. Brandenburg's
``ID`` field does have real prefix/suffix structure, but agreement within
a group is only ~81-88% on dates/type/road - far short of Autobahn's
verified 100% - and nothing else corroborates it, so it's left alone; see
:mod:`streetworks.ogc.germany` for the full investigation.

**Geometry**: ``Point`` (Hamburg) and ``LineString`` (Brandenburg) are both
handled - a real line keeps every vertex on ``Coordinate.points``, never
collapsed to just its first vertex, same rule as WZDx/DATEX line geometry.
GeoJSON's native axis order is ``(lon, lat)``; every other EPSG:4326
``Coordinate`` in this SDK is ``(lat, lon)`` - flipped here explicitly,
same as ``from_wzdx``/``from_autobahn``.

**Dates**: both states state real, structured start/end dates (never
free-text extraction, unlike Autobahn) - Hamburg ``DD.MM.YYYY``,
Brandenburg bare ISO dates, both date-only (no time component in either
state's real data). Represented as midnight Europe/Berlin via
:mod:`zoneinfo`, same convention as Autobahn's date-only fields, so every
datetime in this SDK stays comparable (never a naive one mixed in).

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

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..ogc.germany import StateFieldMap
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_ogc_features"]

JSON = dict[str, Any]

_BERLIN = ZoneInfo("Europe/Berlin")


def _parse_date(value: str | None, date_format: str) -> datetime | None:
    """Date-only fields, both formats - represented as midnight
    Europe/Berlin, never a naive datetime (see module docstring)."""
    if not value:
        return None
    try:
        if date_format == "de":
            day, month, year = (int(p) for p in value.split("."))
        else:
            year, month, day = (int(p) for p in value.split("-"))
        return datetime(year, month, day, tzinfo=_BERLIN)
    except (ValueError, TypeError):
        return None


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return None
    try:
        if kind == "Point":
            lon, lat = coordinates
            return Coordinate(value=(float(lat), float(lon)), crs="EPSG:4326")
        if kind == "LineString":
            points = tuple((float(lat), float(lon)) for lon, lat in coordinates)
            if not points:
                return None
            return Coordinate(
                value=points[0], crs="EPSG:4326", points=points if len(points) > 1 else None
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
    coordinate = _coordinate(feature.get("geometry"))
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
