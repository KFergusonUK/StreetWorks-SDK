"""CCISS (Italy) -> streetworks.common converter.

Like TrafficWatchNI/Traffic Wales, a traveller-information RSS feed
rather than a works register - one thin :class:`~streetworks.common.Works`
wrapping a single :class:`~streetworks.common.WorksSite` per item,
``date_confidence`` always :attr:`~streetworks.common.DateConfidence.UNKNOWN`.

**Never filters** - the same discipline as ``from_trafficwatchni``/
``from_trafficwales``: this feed mixes roadworks with weather, breakdowns,
accidents and demonstrations in one stream (unlike NI/Wales, which
already serve a roadworks-only feed), so filtering to roadworks only
happens at the caller's own choice via ``item.is_roadworks`` - see
:mod:`streetworks.cciss.client`.

**No geometry** - confirmed live, the real feed carries no coordinates
(see :mod:`streetworks.cciss.client`'s own module docstring for the
correction to an earlier, wrong AI-generated claim that it did).
"""

from __future__ import annotations

from ..cciss.client import BulletinItem
from .models import DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_cciss"]

_TERRITORY = "Italy"


def from_cciss(item: BulletinItem) -> Works:
    """Convert one real CCISS :class:`~streetworks.cciss.BulletinItem`
    into a :class:`~streetworks.common.Works` wrapping a single site."""
    location_bits = [
        item.road,
        item.location_from,
        item.location_to,
        item.location_at,
        item.direction,
    ]
    site = WorksSite(
        works_type=item.event_type,
        location_description=" - ".join(p for p in location_bits if p) or None,
        proposed_start=item.start,
        proposed_end=item.end,
        date_confidence=DateConfidence.UNKNOWN,
        operating_window=item.operating_window,
        source_grade=SourceGrade.TRAVELLER_INFO,
        raw=item,
    )
    return Works(
        territory=_TERRITORY,
        # administrative_area stays unset - the feed carries no
        # sub-national authority to report, the same gap Wales has.
        source_grade=SourceGrade.TRAVELLER_INFO,
        sites=(site,),
        raw=item,
    )
