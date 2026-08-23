"""LTA DataMall (Singapore) -> streetworks.common converter. **Pending
live verification** - see :mod:`streetworks.singapore.client`'s own
module docstring for the full investigation; no real authenticated
response has been seen, this is built from LTA's own official spec.

**Three real, differently-shaped record kinds, tagged by the client** -
``road_works``/``road_openings`` (``EventID``/``StartDate``/``EndDate``/
``SvcDept``/``RoadName``/``Other``, no coordinates) and ``incident``
(``Type``/``Latitude``/``Longitude``/``Message``, no id, no dates). No
grouping - one ``Works`` per record.

**``promoter`` comes from ``SvcDept``** on ``road_works``/
``road_openings`` records - the real field states "the department or
company performing this road work", the same applicant-style role
Vienna's/NYC DOT's own promoter fields already play in this SDK.
``incident``-kind records never populate ``promoter`` - no comparable
field exists in that shape.

**``works_type`` distinguishes the three kinds** - ``"Approved Road
Works"``/``"Planned Road Openings"`` (derived from which real dataset the
record came from, since neither states its own type per-record) or the
real ``Type`` value (``"Roadwork"``, the only value
:func:`~streetworks.singapore.client.SingaporeClient.iter_roadworks`
ever passes through) for ``incident``-kind records.

**Coordinates only exist on ``incident``-kind records** - a genuine,
confirmed gap on ``road_works``/``road_openings``, not a parsing
omission (LTA's own spec states no location field for either).

**Dates only exist on ``road_works``/``road_openings``** -
``kisei``-style split, the opposite direction from most other feeds in
this SDK: ``incident``-kind records have no date field at all, so
``date_confidence`` is ``UNKNOWN`` for those (the same "no date field
exists, not inferred" discipline :mod:`.from_roma` already documents),
and ``ESTIMATED`` for ``road_works``/``road_openings`` (approved/planned,
not independently verified - the same reasoning
:mod:`.from_necompass`/:mod:`.from_brussels` already document for their
own comparable feeds).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_singapore"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Singapore"
_ADMINISTRATIVE_AREA = "Land Transport Authority (LTA)"

_WORKS_TYPES = {
    "road_works": "Approved Road Works",
    "road_openings": "Planned Road Openings",
}


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return parse_iso8601(value)


def _coordinate(record: JSON) -> Coordinate | None:
    lat, lon = record.get("Latitude"), record.get("Longitude")
    if lat is None or lon is None:
        return None
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def _to_site(record: JSON) -> WorksSite:
    kind = record.get("kind")
    if kind == "incident":
        return WorksSite(
            reference=None,
            works_type=record.get("Type"),
            coordinate=_coordinate(record),
            date_confidence=DateConfidence.UNKNOWN,
            traffic_management=record.get("Message"),
            source_grade=SourceGrade.OPERATOR,
            raw=record,
        )
    return WorksSite(
        reference=record.get("EventID"),
        works_type=_WORKS_TYPES.get(kind) if isinstance(kind, str) else None,
        location_description=record.get("RoadName"),
        coordinate=None,
        proposed_start=_parse_date(record.get("StartDate")),
        proposed_end=_parse_date(record.get("EndDate")),
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=record.get("Other"),
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_singapore(records: list[JSON]) -> list[Works]:
    """Convert real LTA DataMall records (from
    :meth:`streetworks.singapore.SingaporeClient.iter_roadworks`) into
    :class:`~streetworks.common.Works`. No grouping - one ``Works`` per
    record, see module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                promoter=record.get("SvcDept"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
