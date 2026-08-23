"""New England Compass (NEC) C2C XML -> streetworks.common converter.
See :mod:`streetworks.necompass.client`'s own module docstring for the
full investigation.

**No grouping** - each real record already stands alone, the same shape
as every other municipal/operator feed in this SDK.

**``netId`` states the real state directly** - ``territory``/
``administrative_area`` are derived from it here, not passed in by the
caller, since (unlike :mod:`streetworks.na511`, which serves several
genuinely separate real deployments from different base URLs) this is
one shared deployment whose own data already states which of the three
real states each record belongs to.

**Two real date shapes, not one** - ``laneClosure``-kind records state
``start_date``/``start_time``/``end_date``/``end_time``;
``incident``-kind records state only ``confirmed_date``/
``confirmed_time``, with no end date at all (a real, confirmed gap, not
an oversight - see module docstring). ``proposed_start`` prefers
``start_date``/``start_time``, falling back to ``confirmed_date``/
``confirmed_time`` when absent; ``proposed_end`` only ever comes from
``end_date``/``end_time``, so it stays ``None`` for every real
``incident``-kind record. Dates are parsed naive (no timezone stated on
these specific fields, unlike the real ISO-8601-with-offset
``created_timestamp``/``last_updated_timestamp``, which stay `.raw`-
only) - the same "don't silently attach an inferred timezone" discipline
:mod:`.from_drivebc` already documents for its own comparable case.

**``date_confidence`` is uniformly ``ESTIMATED``** - ``status`` is real
(``Opened``/``Unknown``/``Verified``/``Detected``) but doesn't cleanly
map to a physically-confirmed/scheduled distinction, the same reasoning
:mod:`.from_drivebc`/:mod:`.from_quebec` already document for their own
comparable live self-reported feeds.

**Geometry: a genuine LineString from real ``start_location`` +
``midpoints`` + ``end_location``**, in that order - richer than almost
any other provider in this SDK (one real Maine record has 25 real
midpoint vertices). Falls back to a single point (``start_location``
alone) when ``end_location`` is absent - a real, confirmed shape on some
records, not assumed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_necompass"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"

#: Real netId -> (territory, administrative_area) - see module docstring.
_NETWORKS = {
    "Maine": ("USA", "Maine Department of Transportation (MaineDOT)"),
    "NewHampshire": ("USA", "New Hampshire Department of Transportation (NHDOT)"),
    "Vermont": ("USA", "Vermont Agency of Transportation (VTrans)"),
}


def _territory(net_id: object) -> tuple[str, str | None]:
    if isinstance(net_id, str) and net_id in _NETWORKS:
        return _NETWORKS[net_id]
    return "USA", net_id if isinstance(net_id, str) else None


def _parse_date(date: str | None, time: str | None) -> datetime | None:
    if not date:
        return None
    # Real dates are M/D/YYYY; real times are HH:MM:SS or absent.
    try:
        month, day, year = (int(part) for part in date.split("/"))
    except ValueError:
        return None
    iso_date = f"{year:04d}-{month:02d}-{day:02d}"
    return parse_iso8601(f"{iso_date}T{time or '00:00:00'}")


def _coordinate(record: JSON) -> Coordinate | None:
    start = record.get("start_location")
    if not start or start.get("lat") is None or start.get("lon") is None:
        return None
    start_point = (start["lat"], start["lon"])
    end = record.get("end_location")
    midpoints = record.get("midpoints") or []
    if end and end.get("lat") is not None and end.get("lon") is not None:
        points = (start_point, *midpoints, (end["lat"], end["lon"]))
        return Coordinate(value=start_point, crs=_CRS, points=points)
    return Coordinate(value=start_point, crs=_CRS)


def _location_description(record: JSON) -> str | None:
    start = record.get("start_location") or {}
    parts = [start.get("roadway"), start.get("direction")]
    text = " ".join(p for p in parts if p)
    place = ", ".join(p for p in (start.get("city"), start.get("county")) if p)
    if text and place:
        return f"{text} — {place}"
    return text or place or None


def _to_site(record: JSON) -> WorksSite:
    start = _parse_date(record.get("start_date"), record.get("start_time")) or _parse_date(
        record.get("confirmed_date"), record.get("confirmed_time")
    )
    end = _parse_date(record.get("end_date"), record.get("end_time"))
    return WorksSite(
        reference=record.get("id"),
        works_type=record.get("type"),
        status=record.get("status"),
        location_description=_location_description(record),
        coordinate=_coordinate(record),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=record.get("affected_lanes_description"),
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_necompass(records: list[JSON]) -> list[Works]:
    """Convert real New England Compass C2C records (from
    :meth:`streetworks.necompass.NECompassClient.iter_roadworks`) into
    :class:`~streetworks.common.Works`. No grouping - one ``Works`` per
    record, see module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        territory, administrative_area = _territory(record.get("net_id"))
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                territory=territory,
                administrative_area=administrative_area,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
