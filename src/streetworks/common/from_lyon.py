"""Lyon (Métropole de Lyon) -> streetworks.common roadworks converter.
See :mod:`streetworks.lyon.client` for the full live investigation.

**Geometry: real ``MultiPolygon`` only - the first ring's first vertex
used as the representative point, never a computed centroid.** The
same "one real, arbitrarily-chosen-but-genuinely-stated point"
discipline this SDK's own gazetteer converters (``from_oslo``,
``from_canton_zurich``, ``from_geosn``) already establish for their own
polygon-only sources, applied here to a roadworks record. The real
polygon is preserved unmodified in ``.raw`` - never forced into
``Coordinate.points``/``.parts``, which are documented for real line
vertices only.

**Dates are date-only** (``"2026-08-17"``) - represented as midnight
Europe/Paris via :mod:`zoneinfo`, the same date-only convention this
SDK's other European clusters already use.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_lyon"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "France"
_ADMINISTRATIVE_AREA = "Métropole de Lyon"
_PARIS = ZoneInfo("Europe/Paris")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=_PARIS)


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry or geometry.get("type") != "MultiPolygon":
        return None
    coordinates = geometry.get("coordinates") or []
    if not coordinates:
        return None
    first_polygon = coordinates[0]
    if not first_polygon:
        return None
    first_ring = first_polygon[0]
    if not first_ring:
        return None
    lon, lat = first_ring[0]
    return Coordinate(value=(lat, lon), crs=_CRS)


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties", {})
    start = _parse_date(properties.get("debutchantier"))
    end = _parse_date(properties.get("finchantier"))
    return WorksSite(
        reference=str(properties.get("gid") or ""),
        works_type=properties.get("nomchantier"),
        status=properties.get("typeperturbation"),
        location_description=properties.get("nom"),
        coordinate=_coordinate(feature.get("geometry")),
        proposed_start=start,
        proposed_end=end,
        actual_start=start if start is not None else None,
        date_confidence=DateConfidence.VERIFIED if start is not None else DateConfidence.UNKNOWN,
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_lyon(features: list[JSON]) -> list[Works]:
    """Convert real Lyon GeoJSON ``Feature`` dicts (from
    :meth:`streetworks.lyon.LyonClient.iter_roadworks`) into
    :class:`~streetworks.common.Works`. One ``Works`` per feature, one
    ``WorksSite`` each - no genuine grouping key exists on this feed."""
    works_list = []
    for feature in features:
        properties = feature.get("properties", {})
        site = _to_site(feature)
        promoter = properties.get("intervenant")
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                promoter=promoter or None,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=feature,
            )
        )
    return works_list
