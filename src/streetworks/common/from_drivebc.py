"""DriveBC (British Columbia) Open511 -> streetworks.common converter.
See :mod:`streetworks.drivebc.client`'s own module docstring for the full
investigation - in particular the two real, mutually-exclusive schedule
shapes this converter has to reconcile into one ``WorksSite`` window
each.

**No grouping** - each event already stands alone; ``roads`` is always a
single-element list on every one of 246 real events checked live, so
there's no umbrella/multi-segment structure to preserve.

**Two schedule shapes, tried in order.** ``schedule.intervals`` (222/246
real events) is one or more ISO-8601 time-interval strings
(``"start/end"`` or open-ended ``"start/"``) - the *first* interval's
start and the *last* interval's end become ``proposed_start``/
``proposed_end`` (matching how a caller reading "when is this active"
would use multiple intervals - the full list stays on ``.raw``, not
lost). ``schedule.recurring_schedules`` (the other 24) is a genuinely
different shape - day-of-week list + daily start/end time + an overall
date range - with no single start/end datetime stated directly;
``_from_recurring`` combines ``start_date``+``daily_start_time`` and
``end_date``+``daily_end_time`` into the overall bounding window. The
day-of-week/daily-time detail itself isn't forced into a field that
doesn't fit it - it stays on ``.raw``, the same "simplify the canonical
type, keep everything on raw" choice already made for Berlin's
``severity``/lane-count fields.

**Interval date-times are parsed naive, not silently given a UTC
offset.** DriveBC's jurisdiction resource states
``"timezone": "America/Vancouver"``, so these are almost certainly local
BC time, but that's an inference the interval strings themselves don't
state - see the client module docstring.

**``street_ref`` is never populated** - ``roads[]`` is free-text
(``name``/``from``/``to``/``direction``), confirmed no join key exists.

**``date_confidence`` is uniformly ``ESTIMATED``** - ``status`` (always
``"ACTIVE"`` on every event this client's ``iter_roadworks`` yields, by
construction of the live query) describes the event's own lifecycle
state, not independent confirmation that work is physically happening,
the same distinction drawn for Berlin's ``objectState`` and Madrid's
``incid_estado``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_drivebc"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Canada"
_ADMINISTRATIVE_AREA = "Province of British Columbia (DriveBC)"


def _parse_naive(value: str | None) -> datetime | None:
    """A bare ISO-8601 datetime with no UTC offset - see module
    docstring for why one isn't attached here."""
    if not value:
        return None
    return parse_iso8601(value)


def _from_intervals(intervals: list[str]) -> tuple[datetime | None, datetime | None]:
    if not intervals:
        return None, None
    first_start = intervals[0].split("/", 1)[0]
    last_end = intervals[-1].split("/", 1)[-1]
    return _parse_naive(first_start), _parse_naive(last_end)


def _from_recurring(recurring: list[JSON]) -> tuple[datetime | None, datetime | None]:
    if not recurring:
        return None, None
    first, last = recurring[0], recurring[-1]
    start = None
    if first.get("start_date"):
        start = _parse_naive(f"{first['start_date']}T{first.get('daily_start_time', '00:00')}")
    end = None
    if last.get("end_date"):
        end = _parse_naive(f"{last['end_date']}T{last.get('daily_end_time', '00:00')}")
    return start, end


def _schedule_window(schedule: JSON) -> tuple[datetime | None, datetime | None]:
    if "intervals" in schedule:
        return _from_intervals(schedule["intervals"])
    if "recurring_schedules" in schedule:
        return _from_recurring(schedule["recurring_schedules"])
    return None, None


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    geometry_type = geometry.get("type")
    if geometry_type == "Point":
        lon, lat = geometry["coordinates"]
        return Coordinate(value=(lat, lon), crs=_CRS)
    if geometry_type == "LineString":
        coords = geometry.get("coordinates") or []
        if not coords:
            return None
        points = tuple((c[1], c[0]) for c in coords)
        return Coordinate(value=points[0], crs=_CRS, points=points)
    return None


def _location_description(record: JSON) -> str | None:
    roads = record.get("roads") or []
    if not roads:
        return None
    road = roads[0]
    name = road.get("name")
    from_, to = road.get("from"), road.get("to")
    span = " to ".join(p for p in (from_, to) if p)
    if name and span:
        return f"{name}, {span}"
    return name or span or None


def _works_type(record: JSON) -> str | None:
    subtypes = record.get("event_subtypes") or []
    if subtypes:
        return ", ".join(subtypes)
    return record.get("event_type")


def _to_site(record: JSON) -> WorksSite:
    start, end = _schedule_window(record.get("schedule") or {})
    return WorksSite(
        reference=record.get("id"),
        works_type=_works_type(record),
        location_description=_location_description(record),
        coordinate=_coordinate(record.get("geography")),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=record.get("severity"),
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_drivebc(records: list[JSON]) -> list[Works]:
    """Convert real DriveBC Open511 event dicts (from
    :meth:`streetworks.drivebc.DriveBCClient.iter_events`/
    ``iter_roadworks``) into :class:`~streetworks.common.Works`. No
    grouping - one ``Works`` per event, see module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=record.get("id"),
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
