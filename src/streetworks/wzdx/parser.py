"""WZDx (Work Zone Data Exchange) GeoJSON parser, version-tolerant.

Verified against 12 live agency feeds spanning WZDx v3.1-v4.2 (2026-07):
version differences aren't cleanly gated by the ``version`` string. The
``core_details`` wrapper is a v4-only convention - v3.1 feeds (e.g. Québec)
have every field flat on ``properties`` instead - so every feature is read
through a dict that merges ``properties`` with ``properties.core_details``
(the latter overriding on key collision, though none were observed), and
every downstream field lookup goes through that merged view regardless of
which layout the source used.

Two different real cross-reference mechanisms were observed, and neither is
canonicalised here (per design intent - preserved as data, not resolved
into a grouping): ``properties.relationship.parents``/``.children``
(Québec v3.1, linking a work-zone to a companion detour) and
``core_details.related_road_events`` (NY/TRANSCOM v4.1, a list of
``{"type": "next-occurrence", "id": ...}`` objects - occurrence-chaining,
not the directional-pair link its name suggests).

Every field read is defensive: real feeds have placeholder dates (observed
live: a "current" feed with start/end years spanning 2019-2040), whole
schedules embedded in (sometimes non-English) description prose, and
pervasive empty arrays. Nothing here raises on a malformed record - it
degrades to ``None``/``()`` and the original Feature is always kept on
``RoadEvent.raw``.
"""

from __future__ import annotations

from typing import Any

from .._dt import parse_iso8601 as _dt
from .models import Geometry, Relationship, RoadEvent

__all__ = ["parse_road_events"]

JSON = dict[str, Any]


def _merged_properties(feature: JSON) -> JSON:
    """v4 nests identity/description fields under ``core_details``; v3 has
    them flat on ``properties`` directly. Merge so field reads don't care
    which layout the source used."""
    properties = feature.get("properties") or {}
    core_details = properties.get("core_details") or {}
    return {**properties, **core_details}


def _type_names(types_of_work: Any) -> tuple[str, ...]:
    if not isinstance(types_of_work, list):
        return ()
    return tuple(
        entry["type_name"]
        for entry in types_of_work
        if isinstance(entry, dict) and entry.get("type_name")
    )


def _parse_relationship(value: Any) -> Relationship:
    if not isinstance(value, dict):
        return Relationship()
    parents = value.get("parents")
    children = value.get("children")
    return Relationship(
        parents=tuple(parents) if isinstance(parents, list) else (),
        children=tuple(children) if isinstance(children, list) else (),
    )


def _flatten_ring_points(coordinates: Any) -> list[tuple[float, float]]:
    """``coordinates`` for MultiPoint/LineString is already a flat list of
    ``[lon, lat]`` pairs; Polygon/MultiLineString nest one level deeper
    (rings), MultiPolygon two. Not observed live - handled defensively
    rather than assumed absent."""
    points: list[tuple[float, float]] = []
    if not coordinates:
        return points
    # A coordinate pair looks like [number, number]; anything nested
    # deeper is a list of rings/polygons - recurse until pairs are found.
    first = coordinates[0]
    if isinstance(first, list) and first and isinstance(first[0], list):
        for nested in coordinates:
            points.extend(_flatten_ring_points(nested))
        return points
    for pair in coordinates:
        if isinstance(pair, list) and len(pair) >= 2:
            points.append((float(pair[0]), float(pair[1])))
    return points


def _parse_geometry(geometry: JSON | None) -> Geometry:
    if not geometry:
        return Geometry()
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return Geometry(kind=kind)
    try:
        if kind == "Point":
            points = [(float(coordinates[0]), float(coordinates[1]))]
        else:
            points = _flatten_ring_points(coordinates)
    except (TypeError, ValueError, IndexError):
        return Geometry(kind=kind)
    return Geometry(kind=kind, points=tuple(points))


def _parse_feature(feature: JSON) -> RoadEvent:
    merged = _merged_properties(feature)
    return RoadEvent(
        id=feature.get("id") or merged.get("id"),
        event_type=merged.get("event_type"),
        road_names=tuple(merged.get("road_names") or ()),
        direction=merged.get("direction"),
        name=merged.get("name"),
        description=merged.get("description"),
        data_source_id=merged.get("data_source_id"),
        creation_date=_dt(merged.get("creation_date")),
        update_date=_dt(merged.get("update_date")),
        start_date=_dt(merged.get("start_date")),
        end_date=_dt(merged.get("end_date")),
        is_start_date_verified=merged.get("is_start_date_verified"),
        is_end_date_verified=merged.get("is_end_date_verified"),
        start_date_accuracy=merged.get("start_date_accuracy"),
        end_date_accuracy=merged.get("end_date_accuracy"),
        event_status=merged.get("event_status"),
        vehicle_impact=merged.get("vehicle_impact"),
        location_method=merged.get("location_method"),
        works_ref=merged.get("works_ref") or merged.get("worksRef"),
        types_of_work=_type_names(merged.get("types_of_work")),
        lanes=tuple(merged.get("lanes") or ()),
        relationship=_parse_relationship(merged.get("relationship")),
        related_road_events=tuple(merged.get("related_road_events") or ()),
        geometry=_parse_geometry(feature.get("geometry")),
        raw=feature,
    )


def parse_road_events(payload: JSON) -> list[RoadEvent]:
    """Parse a WZDx GeoJSON FeatureCollection into :class:`RoadEvent`
    objects - one per Feature, in feed order. ``payload`` is an
    already-decoded JSON document (e.g. ``response.json()``), not a raw
    stream - WZDx feeds are single in-memory documents (largest observed
    live: ~8.7 MB), unlike DATEX's streamed-XML case."""
    features = payload.get("features") or []
    return [_parse_feature(f) for f in features if isinstance(f, dict)]
