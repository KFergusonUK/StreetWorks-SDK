"""WZDx -> streetworks.common converter.

**Provenance note**: unlike the UK converters, this mapping is inferred
from the WZDx schema plus 12 live agency feeds sampled 2026-07 - not from
operational experience running against the US system. Two things worth
weighing before leaning on it:

1. **Data-quality variance is real and wide**, confirmed at scale rather
   than assumed: one live feed's "current" records span start/end years
   2019-2040, including a record both date-confidence encodings flagged
   "verified" with an end_date of 2028-12-30 - a verified-looking
   placeholder. ``source_grade`` is still :attr:`~streetworks.common.SourceGrade.OPERATOR`
   (WZDx agencies are road operators, same tier as DATEX), but that grade
   says nothing about an individual record's plausibility - grade is about
   *who published it*, not *how clean it is*.
2. ``core_details.works_ref`` - the field that would give a real ``Works``
   umbrella grouping multiple sites - was not observed on any of the 12
   live feeds sampled. It's real WZDx v4 schema and still handled here,
   but in practice today almost every event converts to a **thin** Works
   (one event, one site). This mapping doesn't move if that's wrong; it's
   flagged tentative on purpose.

Only ``event_type == "work-zone"`` records become :class:`~streetworks.common.WorksSite`
objects - ``detour``/``device``/``restriction`` events are WZDx's analogue
of DATEX measure records (traffic-management consequences, not works
sites) and stay native/raw only, per the same design principle DATEX
measures follow.
"""

from __future__ import annotations

from collections import defaultdict

from ..wzdx.models import Geometry, RoadEvent
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_wzdx"]

_ACCURACY_TO_CONFIDENCE = {
    "verified": DateConfidence.VERIFIED,
    "estimated": DateConfidence.ESTIMATED,
}


def _date_confidence(event: RoadEvent) -> DateConfidence:
    """Prefer the accuracy enum where it's a recognised value; else fall
    back to the boolean flag (a date exists but isn't confirmed reads as
    ESTIMATED, matching the "proposed but not actual" semantics used
    elsewhere); else UNKNOWN. Based on the *start* side only, matching how
    every other converter derives one overall value from "has this
    genuinely begun" - end-side accuracy stays reachable via ``.raw``."""
    mapped = _ACCURACY_TO_CONFIDENCE.get((event.start_date_accuracy or "").lower())
    if mapped is not None:
        return mapped
    if event.is_start_date_verified is True:
        return DateConfidence.VERIFIED
    if event.is_start_date_verified is False:
        return DateConfidence.ESTIMATED
    return DateConfidence.UNKNOWN


def _coordinate(geometry: Geometry) -> Coordinate | None:
    """WZDx geometry is native GeoJSON (longitude, latitude); every other
    EPSG:4326 Coordinate in this SDK (see from_datex2) is (latitude,
    longitude), traced directly from how DATEX's own XML lat/lon elements
    populate Location.points with no flip. Swap the pair here - not just
    relabel it - so Coordinate.value means the same thing everywhere."""
    point = geometry.point
    if point is None:
        return None
    lon, lat = point
    return Coordinate(value=(lat, lon), crs="EPSG:4326")


def _location_description(event: RoadEvent) -> str | None:
    road = ", ".join(event.road_names) or None
    parts = [p for p in (road, event.direction) if p]
    return " - ".join(parts) or None


def _to_site(event: RoadEvent) -> WorksSite:
    confidence = _date_confidence(event)
    return WorksSite(
        reference=event.id,
        works_type=" / ".join(event.types_of_work) or None,
        status=event.event_status,
        location_description=_location_description(event),
        coordinate=_coordinate(event.geometry),
        proposed_start=event.start_date,
        proposed_end=event.end_date,
        actual_start=event.start_date if confidence is DateConfidence.VERIFIED else None,
        date_confidence=confidence,
        traffic_management=event.vehicle_impact,
        source_grade=SourceGrade.OPERATOR,
        raw=event,
    )


def from_wzdx(road_events: list[RoadEvent]) -> list[Works]:
    """Convert WZDx :class:`~streetworks.wzdx.RoadEvent` objects into
    :class:`~streetworks.common.Works`. Non-work-zone events (detours,
    devices, restrictions) are silently skipped, not converted."""
    work_zones = [e for e in road_events if e.is_work_zone]

    grouped: dict[str, list[RoadEvent]] = defaultdict(list)
    thin: list[RoadEvent] = []
    for event in work_zones:
        if event.works_ref:
            grouped[event.works_ref].append(event)
        else:
            thin.append(event)

    works_list = [
        Works(
            reference=works_ref,
            coordinate=_coordinate(events[0].geometry),
            source_grade=SourceGrade.OPERATOR,
            sites=tuple(_to_site(e) for e in events),
            raw=events,
        )
        for works_ref, events in grouped.items()
    ]
    works_list.extend(
        Works(
            coordinate=_coordinate(event.geometry),
            source_grade=SourceGrade.OPERATOR,
            sites=(_to_site(event),),
            raw=event,
        )
        for event in thin
    )
    return works_list
