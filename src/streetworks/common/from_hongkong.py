"""Hong Kong (Transport Department / Highways Department) Roadworks
Location -> streetworks.common converter. See
:mod:`streetworks.hongkong.client`'s own module docstring for the full
investigation.

**No grouping** - each real record already stands alone; ``roadworks_id``
is a real, stable, unique per-record reference (spec-stated ``Y``
mandatory, unique).

**Only the English-language fields are promoted** - every text field is
real and trilingual (bare/`_tc`/`_sc`), the same "one canonical language
promoted, others kept on `.raw`" choice :mod:`.from_brussels` already
makes for French/Dutch.

**Dates are real ``"YYYY-MM-DD HH:MM"`` strings, Hong Kong local time,
no timezone stated** - parsed naive, the same discipline
:mod:`.from_brussels`/:mod:`.from_necompass` already document.

**``worksstatus`` drives real VERIFIED-vs-ESTIMATED date confidence,
checked explicitly, not assumed constant** - the same
`is_active`-branches-into-actual-vs-proposed shape
:mod:`.from_tfl` already establishes. ``"In Progress"`` (the only value
seen in the live pull checked) means the works are genuinely
happening now - ``actual_start``/``actual_end`` populated,
``DateConfidence.VERIFIED``. ``"Under Preparation"`` (a real, documented
spec value, not observed live yet) means not yet started -
``proposed_start``/``proposed_end`` only, ``DateConfidence.ESTIMATED``.

**``location_description`` is ``locdesc`` alone** - real sample text
already includes the road name and bound naturally (e.g. "West Kowloon
Highway Southbound near Nam Cheong Station"), so ``roadname`` isn't
duplicated into it; both stay on ``.raw``.

**``traffic_management`` is ``remark``** - the one real free-text field
beyond the location description itself; genuinely optional
(spec-stated ``Mandatory: N``) and empty on every real record checked
so far, checked honestly rather than assumed populated.

**``promoter`` is ``datasource``** - a real, always-present field
naming who's actually running the works (currently constant
"Highways Department" across every real record checked, since this
feed's whole scope is HyD's own roadworks - not invented, a real field
that simply hasn't varied yet).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_hongkong"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Hong Kong"
_ADMINISTRATIVE_AREA = "Highways Department"

#: The one real status value confirmed live to mean "genuinely happening
#: now" - see module docstring. "Under Preparation" is the real,
#: documented sibling value for not-yet-started works.
_IN_PROGRESS_STATUS = "In Progress"


def _coordinate(record: JSON) -> Coordinate | None:
    lat, lon = record.get("latitude"), record.get("longitude")
    if lat is None or lon is None:
        return None
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return parse_iso8601(value.replace(" ", "T"))


def _date_confidence(
    actual_start: datetime | None, proposed_start: datetime | None
) -> DateConfidence:
    if actual_start is not None:
        return DateConfidence.VERIFIED
    if proposed_start is not None:
        return DateConfidence.ESTIMATED
    return DateConfidence.UNKNOWN


def _to_site(record: JSON) -> WorksSite:
    status = record.get("worksstatus")
    start = _parse_date(record.get("starttime"))
    end = _parse_date(record.get("endtime"))
    in_progress = status == _IN_PROGRESS_STATUS
    actual_start = start if in_progress else None
    actual_end = end if in_progress else None
    proposed_start = None if in_progress else start
    proposed_end = None if in_progress else end
    return WorksSite(
        reference=record.get("roadworks_id"),
        works_type=record.get("workstype"),
        status=status,
        location_description=record.get("locdesc") or None,
        coordinate=_coordinate(record),
        proposed_start=proposed_start,
        proposed_end=proposed_end,
        actual_start=actual_start,
        actual_end=actual_end,
        date_confidence=_date_confidence(actual_start, proposed_start),
        traffic_management=record.get("remark") or None,
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_hongkong(records: list[JSON]) -> list[Works]:
    """Convert real Hong Kong Roadworks Location records (from
    :meth:`streetworks.hongkong.HongKongClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - no grouping, one ``Works`` per
    record. See module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=record.get("roadworks_id"),
                coordinate=site.coordinate,
                promoter=record.get("datasource"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
