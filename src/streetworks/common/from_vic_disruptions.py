"""Victoria (DTP Planned Disruptions - Road) -> streetworks.common
converter. This SDK's second Australian coverage.

One :class:`~streetworks.common.Works` per feature, each with a single
:class:`~streetworks.common.WorksSite` - no grouping key is documented in
this feed linking separate disruptions into one project, the same
one-to-one shape :mod:`.from_nsw_livetraffic`/:mod:`.from_vialietuva` use.

**``administrative_area="Department of Transport and Planning"``, not
``localGovernmentArea``** - see :mod:`streetworks.au.vic`'s own module
docstring for why: ``administrative_area`` is documented as data
*ownership*, not geography, and DTP (not the LGA a disruption happens to
sit in) is the publishing authority. ``localGovernmentArea`` is folded
into ``WorksSite.location_description`` instead, alongside the road-name
fields, where it belongs as a geography detail.

**``Works.promoter`` comes from ``source.sourceName``** - its presence
hints this feed aggregates more than one upstream source behind "DTP,"
the same do-not-deduplicate signal already applied to DGT/Consell de
Mallorca's real republication case.

See :mod:`streetworks.au.vic`'s own module docstring for the full set of
open questions this mapping is built under (unconfirmed coordinate order,
unconfirmed timestamp format, ``string``-typed "numeric" impact fields) -
not re-derived here.
"""

from __future__ import annotations

from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_vic_disruptions"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_ADMINISTRATIVE_AREA = "Department of Transport and Planning"


def _coordinate(feature: JSON) -> Coordinate | None:
    geometry = feature.get("geometry") or {}
    # The confirmed real shape (format=GeoJson, the default): a
    # GeometryCollection wrapping one or more Point/LineString entries -
    # see module docstring. Handled defensively for a bare geometry too,
    # in case a caller passed format=GeoJsonPoint/GeoJsonLine - unconfirmed
    # shape, never verified.
    candidates = geometry.get("geometries")
    if candidates is None:
        candidates = [geometry] if geometry.get("type") else []

    line: JSON | None = None
    point: JSON | None = None
    for candidate in candidates:
        kind = (candidate.get("type") or "").upper()
        if kind in ("LINESTRING", "MULTILINESTRING") and line is None:
            line = candidate
        elif kind == "POINT" and point is None:
            point = candidate

    chosen = line or point
    if chosen is None:
        return None
    coords = chosen.get("coordinates")
    if not coords:
        return None
    if line is not None:
        points = tuple((float(vertex[0]), float(vertex[1])) for vertex in coords)
        return Coordinate(value=points[0], crs=_CRS, points=points)
    value = (float(coords[0]), float(coords[1]))
    return Coordinate(value=value, crs=_CRS)


def _location_description(properties: JSON) -> str | None:
    parts = [
        properties.get("closedRoadName"),
        properties.get("startIntersectionRoadName"),
        properties.get("startIntersectionLocality"),
        properties.get("localGovernmentArea"),
    ]
    text = ", ".join(p for p in parts if p)
    return text or None


def _operating_window(duration: JSON) -> str | None:
    recurrences = duration.get("recurrences") or []
    if not recurrences:
        return None
    parts = []
    for recurrence in recurrences:
        if recurrence.get("allDay"):
            parts.append(f"{recurrence.get('startDay', '')} all day".strip())
            continue
        day = recurrence.get("startDay") or ""
        start = recurrence.get("startTime") or ""
        span = recurrence.get("duration") or ""
        if day or start or span:
            parts.append(" ".join(p for p in (day, start, span) if p))
    return "; ".join(parts) or None


def _traffic_management(properties: JSON) -> str | None:
    impact = properties.get("impact") or {}
    # All string-typed in the real schema, even the numeric-looking ones -
    # carried through as-is, never coerced to a number, see module docstring.
    parts = [
        impact.get("impactType"),
        impact.get("direction"),
        impact.get("delay"),
        impact.get("numberLanesImpacted"),
        impact.get("speedLimitOnSite"),
        properties.get("description"),
    ]
    text = " - ".join(p for p in parts if p)
    return text or None


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    duration = properties.get("duration") or {}
    start = parse_iso8601(duration.get("start"))
    end = parse_iso8601(duration.get("end"))
    reference = properties.get("id")
    return WorksSite(
        reference=str(reference) if reference is not None else None,
        works_type=properties.get("eventType"),
        status=properties.get("status"),
        location_description=_location_description(properties),
        coordinate=_coordinate(feature),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN,
        operating_window=_operating_window(duration),
        traffic_management=_traffic_management(properties),
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_vic_disruptions(features: list[JSON]) -> list[Works]:
    """Convert real DTP planned-disruption features (from
    :meth:`streetworks.au.vic.VicDisruptionsClient.iter_planned_disruptions`)
    into :class:`~streetworks.common.Works` - one per feature, each with a
    single ``WorksSite``. See module docstring."""
    works_list: list[Works] = []
    for feature in features:
        properties = feature.get("properties") or {}
        source = properties.get("source") or {}
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                promoter=source.get("sourceName"),
                territory="Australia",
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=feature,
            )
        )
    return works_list
