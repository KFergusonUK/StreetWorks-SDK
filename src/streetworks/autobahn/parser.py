"""Autobahn GmbH roadworks JSON parser.

**Deliberate, documented exception to "never infer, only take what's
stated"**: this API has no end-date field anywhere, and no start-date
field at all for ``SHORT_TERM_ROADWORKS`` (confirmed live: 0/1,184 real
short-term records carry ``startTimestamp``, vs. 1,689/1,689 long-term
``ROADWORKS`` records that do). Dates for everything except a verified
``ROADWORKS`` start therefore come from parsing ``description[]`` -
machine-generated, consistently-formatted text, not human prose, so this
is extraction rather than inference - but it is still an exception, and
:attr:`~streetworks.autobahn.models.Roadworks.is_start_verified` exists
specifically so callers (and
:func:`streetworks.common.from_autobahn`) can tell verified apart from
estimated rather than trusting every date equally.

Five real text shapes are handled, all confirmed against a full 113-road
live fetch (2,873 records):

1. ``"Beginn: 04.05.26 um 00:00 Uhr"`` / ``"Ende: 31.08.26 um 00:00 Uhr"``
   - the long-term phase's own start/end. Present on 1,689/1,689 real
   ``ROADWORKS`` records (100%) - redundant with the verified
   ``startTimestamp`` for the start side, the *only* source for the end
   side (no end-date field exists, verified or not).
2. ``"(Ende der Gesamtmaßnahme: 09.10.26)"`` - the *overall measure's* end,
   a coarser date shared by every phase of one works (see
   :attr:`~streetworks.autobahn.models.Roadworks.identifier_prefix`).
3. ``"23.06.26 von 08:30 bis 13:30 Uhr"`` - single-day short-term. Covers
   757/1,184 real ``SHORT_TERM_ROADWORKS`` records (64%) alone.
4. ``"22.07.26 20:00 bis zum 23.07.26 05:00 Uhr."`` (also seen with "Uhr"
   after the first time, and ``"24:00"`` as a real end-of-day value) -
   overnight/multi-day short-term. An additional 276 records.
5. ``"Jeden Dienstag, Mittwoch und Donnerstag zwischen dem 21.07.26 und dem
   23.07.26 von 09:00 bis 15:00 Uhr."`` - a recurring weekly pattern; only
   the outer bounding window is kept (first occurrence's start to last
   occurrence's end), the same "collapse periods to overall start/end, keep
   the source text on ``.raw`` for the fine detail" trade-off DATEX's
   ``Validity`` makes. An additional 148 records.

Together, shapes 3-5 cover 1,181/1,184 real short-term records (99.7%) -
the remaining 3 use free-form "valid except these days" text that isn't
safely extractable without guessing, and are left with ``start``/``end``
unset, per the project rule: if a line doesn't match a known shape, leave
the date unset and keep the raw text, never partially parse.

Dates are ``DD.MM.YY`` (two-digit year, +2000) and ``HH:MM`` 24-hour.
Timezone is Europe/Berlin via :mod:`zoneinfo`, not a fixed offset - the
real ``startTimestamp`` field shows both ``+01:00`` and ``+02:00`` across
a live sample, so DST is genuinely observed, not assumed.
``"24:00"`` (seen live) means the end of that day - rolled to
``00:00`` the following day, not rejected as an invalid hour.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .._dt import parse_iso8601 as _dt
from .models import Roadworks

__all__ = ["parse_roadworks"]

JSON = dict[str, Any]

_BERLIN = ZoneInfo("Europe/Berlin")

_RE_BEGINN = re.compile(r"^Beginn:\s*(\d{2}\.\d{2}\.\d{2})\s*um\s*(\d{2}:\d{2})\s*Uhr\s*$")
_RE_ENDE = re.compile(r"^Ende:\s*(\d{2}\.\d{2}\.\d{2})\s*um\s*(\d{2}:\d{2})\s*Uhr\s*$")
_RE_GESAMT = re.compile(r"^\(Ende der Gesamtmaßnahme:\s*(\d{2}\.\d{2}\.\d{2})\)\s*$")
_RE_SHORT = re.compile(
    r"^(\d{2}\.\d{2}\.\d{2})\s*von\s*(\d{2}:\d{2})\s*bis\s*(\d{2}:\d{2})\s*Uhr\.?\s*$"
)
_RE_OVERNIGHT = re.compile(
    r"^(\d{2}\.\d{2}\.\d{2})\s*(\d{2}:\d{2})\s*(?:Uhr\s*)?"
    r"bis\s*zum\s*(\d{2}\.\d{2}\.\d{2})\s*(\d{2}:\d{2})\s*Uhr\.?\s*$"
)
_RE_RECURRING = re.compile(
    r"^Jeden\s+.+?\s+zwischen\s+dem\s+(\d{2}\.\d{2}\.\d{2})\s+und\s+dem\s+"
    r"(\d{2}\.\d{2}\.\d{2})\s+von\s+(\d{2}:\d{2})\s+bis\s+(\d{2}:\d{2})\s+Uhr\.?\s*$"
)


def _parse_de_datetime(date_str: str, time_str: str) -> datetime | None:
    try:
        day, month, year = (int(p) for p in date_str.split("."))
        hour, minute = (int(p) for p in time_str.split(":"))
    except ValueError:
        return None
    year += 2000
    roll_to_next_day = hour == 24
    if roll_to_next_day:
        hour = 0
    try:
        result = datetime(year, month, day, hour, minute, tzinfo=_BERLIN)
    except ValueError:
        return None
    return result + timedelta(days=1) if roll_to_next_day else result


def _parse_dates(
    description: tuple[str, ...],
) -> tuple[datetime | None, datetime | None, datetime | None]:
    """Returns ``(start, end, overall_end)`` extracted from ``description``
    text - see module docstring for the five shapes tried. The first
    matching line of each kind wins; ``overall_end`` is searched
    independently of ``start``/``end`` on every line regardless of which
    (if any) other shape matched."""
    start: datetime | None = None
    end: datetime | None = None
    overall_end: datetime | None = None
    for raw_line in description:
        line = raw_line.strip()
        if not line:
            continue
        if overall_end is None and (m := _RE_GESAMT.match(line)):
            overall_end = _parse_de_datetime(m.group(1), "00:00")
            continue
        if start is None and (m := _RE_BEGINN.match(line)):
            start = _parse_de_datetime(*m.groups())
            continue
        if end is None and (m := _RE_ENDE.match(line)):
            end = _parse_de_datetime(*m.groups())
            continue
        if start is not None or end is not None:
            continue  # long-term phase already found; short-term shapes can't apply
        if m := _RE_SHORT.match(line):
            date_part, start_time, end_time = m.groups()
            start = _parse_de_datetime(date_part, start_time)
            end = _parse_de_datetime(date_part, end_time)
        elif m := _RE_OVERNIGHT.match(line):
            start_date, start_time, end_date, end_time = m.groups()
            start = _parse_de_datetime(start_date, start_time)
            end = _parse_de_datetime(end_date, end_time)
        elif m := _RE_RECURRING.match(line):
            start_date, end_date, start_time, end_time = m.groups()
            start = _parse_de_datetime(start_date, start_time)
            end = _parse_de_datetime(end_date, end_time)
    return start, end, overall_end


def _parse_bool_string(value: Any) -> bool | None:
    """``isBlocked`` is the string ``"true"``/``"false"``, not a JSON
    boolean - confirmed live (2,873/2,873 real records: a string, always
    ``"false"`` in the sample, but the schema allows ``"true"``)."""
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def _parse_coordinate(value: JSON | None) -> tuple[float, float] | None:
    if not value:
        return None
    lat, lon = value.get("lat"), value.get("long")
    if lat is None or lon is None:
        return None
    try:
        return (float(lat), float(lon))
    except (TypeError, ValueError):
        return None


def _parse_points(geometry: JSON | None) -> tuple[tuple[float, float], ...]:
    """Native GeoJSON ``(lon, lat)`` order - confirmed live, every real
    record (2,873/2,873) is a ``LineString``; ``Point`` is handled
    defensively though never observed."""
    if not geometry:
        return ()
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return ()
    try:
        if kind == "Point":
            return ((float(coordinates[0]), float(coordinates[1])),)
        return tuple(
            (float(pair[0]), float(pair[1]))
            for pair in coordinates
            if isinstance(pair, list) and len(pair) >= 2
        )
    except (TypeError, ValueError, IndexError):
        return ()


def _parse_item(item: JSON, road: str) -> Roadworks:
    description = tuple(item.get("description") or ())
    text_start, text_end, overall_end = _parse_dates(description)

    # ROADWORKS carries a real startTimestamp - verified-grade and preferred
    # over the text-derived one; SHORT_TERM_ROADWORKS never has this key at
    # all (confirmed live, 0/1,184), so text_start (estimated) is all there is.
    start_timestamp = _dt(item.get("startTimestamp"))
    start = start_timestamp if start_timestamp is not None else text_start
    is_start_verified = start_timestamp is not None

    impact = item.get("impact") or {}
    future = item.get("future")

    return Roadworks(
        identifier=item.get("identifier") or "",
        road=road,
        title=item.get("title"),
        subtitle=item.get("subtitle"),
        description=description,
        display_type=item.get("display_type"),
        is_blocked=_parse_bool_string(item.get("isBlocked")),
        future=future if isinstance(future, bool) else None,
        impact_lower=impact.get("lower"),
        impact_upper=impact.get("upper"),
        # Real records mix in `null` entries among the lane-symbol strings
        # (confirmed live) - an unlabelled lane position in the diagram,
        # presumably; filtered rather than kept as a symbol.
        impact_symbols=tuple(s for s in (impact.get("symbols") or ()) if isinstance(s, str)),
        coordinate=_parse_coordinate(item.get("coordinate")),
        points=_parse_points(item.get("geometry")),
        start=start,
        is_start_verified=is_start_verified,
        end=text_end,
        overall_end=overall_end,
        raw=item,
    )


def parse_roadworks(payload: JSON, road: str) -> list[Roadworks]:
    """Parse one road's ``{"roadworks": [...]}`` response into
    :class:`~streetworks.autobahn.models.Roadworks` objects. ``road`` is the
    road id the payload was fetched for (e.g. ``"A1"``) - there's no
    road-number field on the items themselves, see module docstring."""
    items = payload.get("roadworks") or []
    return [_parse_item(item, road) for item in items if isinstance(item, dict)]
