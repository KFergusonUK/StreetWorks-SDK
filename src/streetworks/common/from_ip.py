"""Infraestruturas de Portugal (IP) Condicionamentos -> streetworks.common
converter. See :mod:`streetworks.arcgis.ip`'s own module docstring for the
full investigation.

**No grouping** - each feature already stands alone; there is no
umbrella/case field, the same shape as every other municipal/operator
feed in this SDK.

**A real "no defined end" placeholder in ``datafim``** - a fabricated
far-future sentinel (``2556143999000``, 2050-12-31 23:59:59 UTC),
confirmed live on 3/34 real non-null ``datafim`` values, means "no end
stated," not a real scheduled date - :func:`_epoch_ms_to_end` never
surfaces it as ``proposed_end``.

**``date_confidence`` is uniformly ``ESTIMATED``** - ``estado`` is real
but uniformly ``"ativo"`` in the live data, no independent
verified/status flag exists, the same reasoning
:mod:`streetworks.common.from_srwr`/``from_quebec`` already document for
their own comparable "live self-reported, no independent verification"
feeds.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_ip"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Portugal"
_ADMINISTRATIVE_AREA = "Infraestruturas de Portugal (IP)"

#: A real, confirmed "no defined end" sentinel (2050-12-31 23:59:59 UTC) -
#: see module docstring. Never surfaced as a real date.
_NO_END_SENTINEL = 2556143999000


def _epoch_ms_to_dt(value: Any) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _epoch_ms_to_end(value: Any) -> datetime | None:
    if value == _NO_END_SENTINEL:
        return None
    return _epoch_ms_to_dt(value)


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry or geometry.get("type") != "Point":
        return None
    coordinates = geometry.get("coordinates")
    if not coordinates or len(coordinates) < 2:
        return None
    lon, lat = coordinates[0], coordinates[1]
    return Coordinate(value=(lat, lon), crs=_CRS)


def _location_description(properties: JSON) -> str | None:
    parts = [properties.get("description")]
    pk = properties.get("pkbegin")
    if pk is not None:
        parts.append(f"PK {pk}")
    direction = properties.get("direction")
    if direction:
        parts.append(f"({direction})")
    text = " ".join(p for p in parts if p)
    place = ", ".join(p for p in (properties.get("concelho"), properties.get("distrito")) if p)
    if text and place:
        return f"{text} — {place}"
    return text or place or None


def _to_site(record: JSON) -> WorksSite:
    properties = record.get("properties") or {}
    return WorksSite(
        reference=str(properties.get("objectid")) if properties.get("objectid") else None,
        works_type=properties.get("tipo"),
        status=properties.get("estado"),
        location_description=_location_description(properties),
        coordinate=_coordinate(record.get("geometry")),
        proposed_start=_epoch_ms_to_dt(properties.get("datainicio")),
        proposed_end=_epoch_ms_to_end(properties.get("datafim")),
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=properties.get("commentsummary"),
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_ip(records: list[JSON]) -> list[Works]:
    """Convert real IP Condicionamentos feature dicts (from
    :meth:`streetworks.arcgis.ip.IPRoadworksClient.iter_roadworks`) into
    :class:`~streetworks.common.Works`. No grouping - one ``Works`` per
    feature, see module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
