"""Traffic Wales -> streetworks.common converter.

Like TrafficWatchNI, a traveller-information RSS feed rather than a works
register - one thin :class:`~streetworks.common.Works` wrapping a single
:class:`~streetworks.common.WorksSite` per item, ``date_confidence`` always
:attr:`~streetworks.common.DateConfidence.UNKNOWN`. Unlike NI, Traffic
Wales' upgraded parser (:mod:`streetworks.trafficwales`) gives a WGS84
``georss:point``, so ``Works.coordinate`` is populated where the feed
carries one.
"""

from __future__ import annotations

from ..trafficwales.client import FeedItem
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_trafficwales"]


def from_trafficwales(item: FeedItem) -> Works:
    """Convert one Traffic Wales :class:`~streetworks.trafficwales.FeedItem`
    into a :class:`~streetworks.common.Works` wrapping a single site."""
    coordinate = (
        Coordinate(value=item.coordinate, crs="EPSG:4326")
        if item.coordinate is not None
        else None
    )
    site = WorksSite(
        works_type=item.work_type,
        # `severity` isn't a lifecycle status (RSS items have none) - it
        # only ever describes traffic impact, so it's folded into
        # traffic_management below rather than forced into `status`.
        location_description=", ".join(
            p for p in (item.road, item.direction, item.location_from_to) if p
        )
        or None,
        coordinate=coordinate,
        proposed_start=item.start,
        proposed_end=item.end,
        date_confidence=DateConfidence.UNKNOWN,
        operating_window=item.operating_window,
        traffic_management=" - ".join(p for p in (item.restriction, item.severity) if p)
        or None,
        source_grade=SourceGrade.TRAVELLER_INFO,
        raw=item,
    )
    return Works(
        coordinate=coordinate,
        promoter=item.source,
        source_grade=SourceGrade.TRAVELLER_INFO,
        sites=(site,),
        raw=item,
    )
