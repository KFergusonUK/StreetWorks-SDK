"""Saarland (Landesbetrieb für Straßenbau) -> streetworks.common
roadworks converter. See :mod:`streetworks.saarland.client` for the
full live investigation.

**Geometry: real ``MultiLineString`` - every real vertex kept, not
collapsed to a point.** Native GeoJSON ``(lon, lat)``, flipped to this
SDK's ``(lat, lon)`` convention, the same choice ``from_berlin``/
``from_lisboa`` already make for their own real GeoJSON-native sources.
Only the first real part is used for ``Coordinate.points`` - every real
feature checked live carries exactly one ``MultiLineString`` part, so
this is a description of what's actually there, not a simplification of
something richer.

**Dates are genuinely naive - no UTC offset stated at all**
(``"2022-11-28T00:00"``), unlike Baden-Württemberg's own real
``+02:00``-suffixed dates on the same shared cluster. Parsed via
:meth:`datetime.fromisoformat` then localised to Europe/Berlin via
:mod:`zoneinfo`, the same date-only-state convention this SDK's German
roadworks cluster already uses throughout.

**``roadclosed`` is a real string ``"true"``/``"false"``, not a JSON
boolean** - confirmed live (every one of 38 real records at
investigation time states the literal string ``"false"``); parsed here
rather than trusted blindly, since a source that states booleans as
strings could plausibly state ``"True"``/``"1"`` elsewhere too.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_saarland"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Germany"
_ADMINISTRATIVE_AREA = "Saarland"
_BERLIN = ZoneInfo("Europe/Berlin")


def _parse_date(value: str | None) -> datetime | None:
    """Genuinely naive ISO datetimes (no UTC offset stated at all) -
    localised to Europe/Berlin, never left naive (see module
    docstring)."""
    if not value:
        return None
    try:
        naive = datetime.fromisoformat(value)
    except ValueError:
        return None
    return naive.replace(tzinfo=_BERLIN)


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry or geometry.get("type") != "MultiLineString":
        return None
    coordinates = geometry.get("coordinates") or []
    if not coordinates:
        return None
    first_part = coordinates[0]
    if not first_part:
        return None
    points = tuple((lat, lon) for lon, lat in first_part)
    return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties", {})
    start = _parse_date(properties.get("starttime"))
    end = _parse_date(properties.get("endtime"))
    return WorksSite(
        reference=str(properties.get("recordid") or feature.get("id") or ""),
        works_type=properties.get("description"),
        status="closed" if properties.get("roadclosed") == "true" else None,
        location_description=properties.get("roadname") or None,
        coordinate=_coordinate(feature.get("geometry")),
        proposed_start=start,
        proposed_end=end,
        actual_start=start if start is not None else None,
        date_confidence=DateConfidence.VERIFIED if start is not None else DateConfidence.UNKNOWN,
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_saarland(features: list[JSON]) -> list[Works]:
    """Convert real Saarland LfS GeoJSON ``Feature`` dicts (from
    :meth:`streetworks.saarland.SaarlandClient.iter_roadworks`) into
    :class:`~streetworks.common.Works`. One ``Works`` per feature, one
    ``WorksSite`` each - no genuine grouping key exists on this feed."""
    works_list = []
    for feature in features:
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=feature,
            )
        )
    return works_list
