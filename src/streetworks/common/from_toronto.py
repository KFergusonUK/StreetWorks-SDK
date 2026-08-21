"""Toronto (Road Restrictions/Closures) -> streetworks.common converter.
See :mod:`streetworks.toronto.client` for the full live investigation.

One :class:`~streetworks.common.Works` per record, each with a single
:class:`~streetworks.common.WorksSite` - ``id`` is already a real,
unique per-record identifier, no grouping key found linking separate
records into one project.

``status`` is ``type`` (``"CONSTRUCTION"``/``"ROAD_CLOSED"`` - the real,
clean top-level classification; ``subType`` states
``"ROAD_CLOSED_CONSTRUCTION"`` in the latter case, confirmed live to
mean the same "genuinely construction-caused" thing, so it isn't
promoted separately). ``works_type`` is ``workEventType`` - real, and
often rich (organisation names, activity descriptions), but confirmed
live to hold a genuine, known placeholder string on ~42% of real
records (a real export defect - see module docstring), carried through
as-is rather than filtered. ``promoter`` is ``contractor`` - real and
populated on the overwhelming majority (2,214/2,274) of real records,
richer than most roadworks sources this SDK has.

**``date_confidence`` is uniformly ``ESTIMATED``** - ``expired`` is
always ``0`` on every real record this feed returns (it appears to only
ever publish currently-valid closures), which describes the record's
own lifecycle state, not independent confirmation the work is
physically happening, the same distinction :mod:`.from_drivebc`/
:mod:`.from_quebec` already draw for their own comparable live feeds.
Dates are real Unix epoch **milliseconds**.

Geometry prefers the real decoded ``geoPolyline`` (Toronto's own bespoke
string format, not JSON array syntax or a Google Encoded Polyline) when
present; falls back to the plain ``latitude``/``longitude`` pair
otherwise - both are confirmed live to be populated on effectively
every real record (0/2,274 missing lat/lon; geoPolyline likewise).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..toronto.client import parse_polyline
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_toronto"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Canada"
_ADMINISTRATIVE_AREA = "City of Toronto"


def _epoch_millis_to_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _coordinate(record: JSON) -> Coordinate | None:
    points = parse_polyline(record.get("geoPolyline"))
    flipped = tuple((lat, lon) for lon, lat in points)
    lat, lon = record.get("latitude"), record.get("longitude")
    if flipped:
        return Coordinate(value=flipped[0], crs=_CRS, points=flipped)
    if lat is None or lon is None:
        return None
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def _to_site(record: JSON) -> WorksSite:
    return WorksSite(
        reference=record.get("id"),
        works_type=record.get("workEventType"),
        status=record.get("type"),
        location_description=record.get("name"),
        coordinate=_coordinate(record),
        proposed_start=_epoch_millis_to_dt(record.get("startTime")),
        proposed_end=_epoch_millis_to_dt(record.get("endTime")),
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=record.get("description"),
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_toronto(records: list[JSON]) -> list[Works]:
    """Convert real Toronto Road Restrictions/Closures records (from
    :meth:`streetworks.toronto.TorontoClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - one per record, each with a
    single ``WorksSite``. See module docstring."""
    works_list: list[Works] = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                promoter=record.get("contractor"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
