"""TrafficWatchNI -> streetworks.common converter.

A traveller-information RSS feed, not a works register - each item is a
thin :class:`~streetworks.common.Works` wrapping exactly one
:class:`~streetworks.common.WorksSite` (there's no umbrella reference
grouping multiple sites the way Street Manager or SRWR have). Dates are
best-effort regex extractions from prose, never verified, so
``date_confidence`` is always :attr:`~streetworks.common.DateConfidence.UNKNOWN`
- an item never claims to know an *actual* start from RSS text.
"""

from __future__ import annotations

from datetime import date, datetime

from ..trafficwatchni.client import RoadworksItem
from .models import DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_trafficwatchni"]


def _as_datetime(value: date | None) -> datetime | None:
    """RoadworksItem dates are date-only (no time component observed in the
    feed); midnight is a placeholder, not an observed time."""
    return datetime.combine(value, datetime.min.time()) if value is not None else None


def from_trafficwatchni(item: RoadworksItem) -> Works:
    """Convert one TrafficWatchNI :class:`~streetworks.trafficwatchni.RoadworksItem`
    into a :class:`~streetworks.common.Works` wrapping a single site."""
    location_description = ", ".join(p for p in (item.road, item.town) if p) or None
    site = WorksSite(
        works_type=item.closure_type,
        location_description=location_description,
        proposed_start=_as_datetime(item.start_date),
        proposed_end=_as_datetime(item.end_date),
        date_confidence=DateConfidence.UNKNOWN,
        operating_window=item.operating_times,
        traffic_management="Diversion in place" if item.diversion else None,
        source_grade=SourceGrade.TRAVELLER_INFO,
        raw=item,
    )
    return Works(
        # TrafficWatchNI's feed carries no geometry, so `coordinate` stays unset.
        promoter=item.promoter,
        territory="Northern Ireland",
        # administrative_area stays unset - DfI TICC is territory-wide, the
        # feed carries no sub-national authority to report.
        source_grade=SourceGrade.TRAVELLER_INFO,
        sites=(site,),
        raw=item,
    )
