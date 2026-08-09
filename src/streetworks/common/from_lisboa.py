"""Lisboa (CML) Condicionamentos de Trânsito -> streetworks.common
converter. See :mod:`streetworks.lisboa.client`'s own module docstring
for the full investigation - in particular how the real endpoint was
found (not documented anywhere public) and the freshness check that
ruled out the catalogue's stale metadata.

**No grouping** - each feature already stands alone; there is no
umbrella/case field beyond ``pedido`` itself (already the per-feature
reference), the same shape as every other municipal feed in this SDK.

**Multiple periods, reconciled into one window.** ``periodos_
condicionamentos`` is a *list* (665/694 real features have exactly one,
but up to 4 real periods exist) - each with `date_min`/`date_max` (bare
dates) and separate `hour_min`/`hour_max` (daily time-of-day). The
*first* period's start and the *last* period's end become
``proposed_start``/``proposed_end`` - the same multi-interval handling
already used for DriveBC's ``schedule.intervals``. The per-period
``is_interrupted`` flag (real, majority-``True`` in live data - "not
currently in effect within its own window," not an edge case) isn't
forced into a field that doesn't fit it; it stays on ``.raw``.

**Geometry: only the first `MultiLineString` sub-line is used.** 666/694
real features have exactly one sub-line; a handful have up to 7.
:class:`~streetworks.common.models.Coordinate` supports one line per
point, not several - the same deliberate simplification
:func:`~streetworks.common.from_berlin` already makes for a
`GeometryCollection` carrying multiple `LineString` entries.

**``street_ref`` is never populated** - ``morada`` (address) is
free-text, confirmed no join key exists anywhere in the schema.

**``date_confidence`` is uniformly ``ESTIMATED``** - neither
``is_interrupted`` nor any other field confirms work physically
happening on the ground, only a scheduled window, the same distinction
already drawn for Madrid's ``incid_estado`` and DriveBC's ``status``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_lisboa"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Portugal"
_ADMINISTRATIVE_AREA = "Câmara Municipal de Lisboa"


def _parse_period_datetime(date: str | None, hour: str | None) -> datetime | None:
    if not date:
        return None
    return parse_iso8601(f"{date}T{hour or '00:00:00'}")


def _schedule_window(periods: list[JSON]) -> tuple[datetime | None, datetime | None]:
    if not periods:
        return None, None
    first, last = periods[0], periods[-1]
    start = _parse_period_datetime(first.get("date_min"), first.get("hour_min"))
    end = _parse_period_datetime(last.get("date_max"), last.get("hour_max"))
    return start, end


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry or geometry.get("type") != "MultiLineString":
        return None
    lines = geometry.get("coordinates") or []
    if not lines or not lines[0]:
        return None
    points = tuple((c[1], c[0]) for c in lines[0])
    return Coordinate(value=points[0], crs=_CRS, points=points)


def _location_description(properties: JSON) -> str | None:
    morada = properties.get("morada")
    freguesias = properties.get("freguesias")
    if morada and freguesias:
        return f"{morada} ({freguesias})"
    return morada or freguesias


def _to_site(record: JSON) -> WorksSite:
    properties = record.get("properties") or {}
    start, end = _schedule_window(properties.get("periodos_condicionamentos") or [])
    return WorksSite(
        reference=properties.get("pedido") or str(properties.get("id")),
        works_type=properties.get("motivo"),
        location_description=_location_description(properties),
        coordinate=_coordinate(record.get("geometry")),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=properties.get("restricao_circulacao"),
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_lisboa(records: list[JSON]) -> list[Works]:
    """Convert real Lisboa Condicionamentos de Trânsito feature dicts
    (from :meth:`streetworks.lisboa.LisboaClient.iter_condicionamentos`/
    ``iter_roadworks``) into :class:`~streetworks.common.Works`. No
    grouping - one ``Works`` per feature, see module docstring."""
    works_list = []
    for record in records:
        properties = record.get("properties") or {}
        site = _to_site(record)
        works_list.append(
            Works(
                reference=properties.get("pedido") or str(properties.get("id")),
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
