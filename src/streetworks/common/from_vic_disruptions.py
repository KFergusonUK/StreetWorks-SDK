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
open questions this mapping is built under (unconfirmed timestamp format,
``string``-typed "numeric" impact fields) - not re-derived here.

**``Coordinate.value``/``points`` are ``(lat, lon)``** - this SDK's stated
convention for every EPSG:4326 ``Coordinate`` (see ``from_sct``/
``from_wzdx``/``from_autobahn``'s own docstrings), flipped from the
confirmed-live raw GeoJSON ``[lon, lat]`` order (see
:mod:`streetworks.au.vic`'s own module docstring) - the same fix
``from_au_wa_mainroads`` needed once a live pull showed real points
plotting near Antarctica.
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
    """**Prefers the Point, not the LineString** - the reverse of this
    module's first-version design. That design assumed a GeometryCollection's
    Point/LineString pair were coarse-vs-precise views of the *same* site,
    the DATEX/WZDx shape. A real feature disproved this for Victoria: its
    LineString spanned ~150km end to end (matching ``srns: "M31,B400"`` -
    the whole Hume Freeway corridor), while its Point sat at the actual
    disruption site within that span - a route-context line, not a
    precise extent. Promoting it to ``Coordinate.points`` would silently
    replace one worksite with an entire highway, so it isn't used at all
    here - ``Coordinate.points`` stays ``None`` even when a LineString is
    present. See module docstring."""
    geometry = feature.get("geometry") or {}
    # The confirmed real shape (format=GeoJson, the default): a
    # GeometryCollection wrapping a Point and/or LineString entry. Handled
    # defensively for a bare geometry too, in case a caller passed
    # format=GeoJsonPoint/GeoJsonLine - unconfirmed shape, never verified.
    candidates = geometry.get("geometries")
    if candidates is None:
        candidates = [geometry] if geometry.get("type") else []

    point: JSON | None = None
    line: JSON | None = None
    for candidate in candidates:
        kind = (candidate.get("type") or "").upper()
        if kind == "POINT" and point is None:
            point = candidate
        elif kind in ("LINESTRING", "MULTILINESTRING") and line is None:
            line = candidate

    chosen = point or line
    if chosen is None:
        return None
    coords = chosen.get("coordinates")
    if not coords:
        return None
    if point is not None:
        value = (float(coords[1]), float(coords[0]))
        return Coordinate(value=value, crs=_CRS)
    # No Point at all (unconfirmed to happen live) - fall back to the
    # line's first vertex rather than return nothing.
    points = tuple((float(vertex[1]), float(vertex[0])) for vertex in coords)
    return Coordinate(value=points[0], crs=_CRS, points=points)


def _location_description(properties: JSON) -> str | None:
    # endIntersection* confirmed live (2026-07-30): populated on 461/500
    # real features in one pull (92%) - genuinely common, not a rare
    # extra, so included alongside the fields the source investigation
    # brief's own schema summary named.
    parts = [
        properties.get("closedRoadName"),
        properties.get("startIntersectionRoadName"),
        properties.get("startIntersectionLocality"),
        properties.get("endIntersectionRoadName"),
        properties.get("endIntersectionLocality"),
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
