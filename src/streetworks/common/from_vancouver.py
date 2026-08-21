"""Vancouver ("Road Ahead") -> streetworks.common converter. See
:mod:`streetworks.vancouver.client` for the full live investigation.

One :class:`~streetworks.common.Works` per record, each with a single
:class:`~streetworks.common.WorksSite` - no grouping key is stated
linking separate records into one project, the same one-to-one shape
:mod:`.from_drivebc`/:mod:`.from_quebec` already use for their own
comparable live traveller-information feeds.

**``status``/``date_confidence`` are explicit caller-supplied arguments,
not derived** - none of Vancouver's three real datasets (current
closures, under construction, upcoming) states its own tier as a
per-record field; the tier is real but only stated at the dataset level
(see module docstring), the same reasoning that already makes
``territory``/``administrative_area`` explicit arguments on
:func:`~streetworks.common.from_wzdx`. Only ``comp_date`` (a real
completion date) is ever populated - there is no start-date field at
all, a genuine, confirmed source gap - so only ``proposed_end``/
``actual_end`` are ever set, never a start.

``location_description`` uses ``location`` only - confirmed live to
always equal ``project`` byte-for-byte (0 real differences found), so
``project`` is redundant, not separately carried. ``street`` is real but
confirmed always null on every record sampled, so it's never read.

Geometry always has a real representative point (``geo_point_2d``,
confirmed live to never be absent) as ``Coordinate.value``; real
``LineString``/``MultiLineString`` geometry is additionally carried as
``.points`` when present. The real but structurally mixed
``GeometryCollection`` shape (LineStrings and Polygons in one record) is
deliberately not decomposed - too varied to handle generically without
guessing - so those records still get their real point, just no
``.points``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_vancouver"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Canada"
_ADMINISTRATIVE_AREA = "City of Vancouver"
_VANCOUVER_TZ = ZoneInfo("America/Vancouver")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=_VANCOUVER_TZ)


def _line_points(geometry: JSON) -> tuple[tuple[float, float], ...] | None:
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return None
    if kind == "LineString":
        return tuple((float(lat), float(lon)) for lon, lat in coords)
    if kind == "MultiLineString":
        flat = [pair for line in coords for pair in line]
        return tuple((float(lat), float(lon)) for lon, lat in flat)
    return None


def _coordinate(record: JSON) -> Coordinate | None:
    point = record.get("geo_point_2d")
    if not point or point.get("lat") is None or point.get("lon") is None:
        return None
    value = (float(point["lat"]), float(point["lon"]))
    geometry = (record.get("geom") or {}).get("geometry") or {}
    points = _line_points(geometry)
    return Coordinate(value=value, crs=_CRS, points=points)


def _to_site(record: JSON, *, status: str, date_confidence: DateConfidence) -> WorksSite:
    end = _parse_date(record.get("comp_date"))
    is_verified = date_confidence is DateConfidence.VERIFIED
    return WorksSite(
        reference=None,
        status=status,
        location_description=record.get("location"),
        coordinate=_coordinate(record),
        proposed_end=None if is_verified else end,
        actual_end=end if is_verified else None,
        date_confidence=date_confidence,
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_vancouver(
    records: list[JSON], *, status: str, date_confidence: DateConfidence
) -> list[Works]:
    """Convert real Vancouver "Road Ahead" records (from one of
    :meth:`streetworks.vancouver.VancouverClient`'s three iterators) into
    :class:`~streetworks.common.Works` - one per record, each with a
    single ``WorksSite``. ``status``/``date_confidence`` apply to every
    record this call converts - see module docstring for why they're
    explicit rather than derived."""
    works_list: list[Works] = []
    for record in records:
        site = _to_site(record, status=status, date_confidence=date_confidence)
        works_list.append(
            Works(
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
