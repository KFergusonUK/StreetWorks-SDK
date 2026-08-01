"""Queensland (QLDTraffic Events, TMR) -> streetworks.common converter.
This SDK's fourth Australian coverage.

One :class:`~streetworks.common.Works` per feature, each with a single
:class:`~streetworks.common.WorksSite` - no grouping key is stated in this
feed linking separate events into one project, the same one-to-one shape
:mod:`.from_nsw_livetraffic`/:mod:`.from_vic_disruptions`/
:mod:`.from_au_wa_mainroads` use. ``Works.reference`` is the bare ``id`` -
confirmed live to be globally unique across the *whole* feed (458/458
distinct across every real event_type in one pull, not just within
Roadworks), unlike NSW's per-layer id, so no composite key is needed here.

**``territory="Australia"``, ``administrative_area`` is per-record from
``source.provided_by``** - a real, deliberate departure from every other
AU converter in this SDK, which each hardcode one operator name.
``provided_by`` is confirmed live to be the genuine, specific, data-owning
authority per record (100% populated, 17 distinct real values in one
pull: "Department of Transport and Main Roads" the plurality, but also a
private tollway operator, "Transurban", and 15 different Queensland local
government/disaster-management authorities) - richer and more accurate
than a single hardcoded value would be, and exactly what
``administrative_area`` is documented to mean (see
:mod:`streetworks.common.models`). Falls back to ``source.source_name``
only in the unobserved case ``provided_by`` is ever absent.
``promoter`` is ``source.source_name`` (``EPS``/``Guardian``/``TfNSW``/
``Asignit``/``MBRC``, confirmed live to be a real, if undocumented-beyond-
three-values, enum - see :mod:`streetworks.au.qld`'s own docstring) - the
publishing *system*, distinct from the owning *authority* in
``administrative_area``, the same role Victoria's ``source.sourceName``
plays in :mod:`.from_vic_disruptions`.

See :mod:`streetworks.au.qld`'s own module docstring for the full set of
real findings this mapping is built from (the two spec-vs-reality
mismatches, the ``area_alert`` exclusion, the real GDA2020 CRS, why
LineString geometry is carried through rather than dropped) - not
re-derived here.
"""

from __future__ import annotations

from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, Notice, SourceGrade, Works, WorksSite

__all__ = ["from_au_qld_qldtraffic"]

JSON = dict[str, Any]
Point = tuple[float, float]

#: Real coordinates are GDA2020, confirmed live on every feature's own
#: embedded GeoJSON ``crs`` member - not WGS84/EPSG:4326, see
#: streetworks.au.qld's module docstring for why this isn't just relabelled.
_CRS = "EPSG:7844"

_TERRITORY = "Australia"


def _geometries(feature: JSON) -> tuple[list[Point], list[list[Point]]]:
    """Real points and real line vertex-lists for this feature, excluding
    the ``area_alert`` polygon when flagged. Handles all three real
    top-level shapes confirmed live - ``GeometryCollection`` (2.2% of a
    real pull), bare ``MultiPoint`` (29.5%), bare ``MultiLineString``
    (68.3%) - not just the spec's own (wrong) always-``GeometryCollection``
    claim; see streetworks.au.qld's module docstring."""
    geometry = feature.get("geometry") or {}
    kind = geometry.get("type")
    properties = feature.get("properties") or {}

    if kind == "GeometryCollection":
        geoms = list(geometry.get("geometries") or [])
        # The last entry is the area-alert polygon when flagged - confirmed
        # live against the one real example (a Point+Polygon pair) - never
        # part of the event's own works geometry.
        if properties.get("area_alert") and geoms:
            geoms = geoms[:-1]
        points = [
            (float(g["coordinates"][0]), float(g["coordinates"][1]))
            for g in geoms
            if g.get("type") == "Point" and g.get("coordinates")
        ]
        lines = [
            [(float(v[0]), float(v[1])) for v in g["coordinates"]]
            for g in geoms
            if g.get("type") == "LineString" and g.get("coordinates")
        ]
        return points, lines

    if kind == "MultiPoint":
        coords = geometry.get("coordinates") or []
        return [(float(c[0]), float(c[1])) for c in coords], []

    if kind == "MultiLineString":
        coords = geometry.get("coordinates") or []
        lines = [[(float(v[0]), float(v[1])) for v in line] for line in coords if line]
        return [], lines

    return [], []


def _coordinate(feature: JSON) -> Coordinate | None:
    """**A deliberate departure from Victoria's "prefer the Point, drop
    the LineString" precedent** - see streetworks.au.qld's module
    docstring for the real evidence this is built on (88.5% of real
    Roadworks events have no Point at all; dropping the LineString would
    leave them with no geometry whatsoever, not a safe simplification).

    When a real Point exists, it's used alone - matching Victoria's own
    precedent for the case a source actually supplies one (only 2/244 real
    events do; with several real Points and a line together in one of the
    two, which point is "the" site marker isn't determinable from that
    small a sample, so the first is used and the co-present line is left
    on ``.raw`` rather than guessed at). When no Point exists, the real
    LineString(s) become the site's own geometry - a single line via
    ``points``, several real non-contiguous segments via ``parts`` -
    labelled honestly as what the source itself states (*"a set of
    geometries indicating the affected roads"*), not upgraded into a false
    precision claim. Either way, ``value``/``points[0]``/``parts[0][0]``
    stay consistent with :class:`~streetworks.common.Coordinate`'s own
    documented invariants."""
    points, lines = _geometries(feature)
    if points:
        return Coordinate(value=points[0], crs=_CRS)
    if not lines:
        return None
    if len(lines) == 1:
        line = lines[0]
        return Coordinate(value=line[0], crs=_CRS, points=tuple(line))
    parts = tuple(tuple(line) for line in lines)
    return Coordinate(value=parts[0][0], crs=_CRS, parts=parts)


def _location_description(properties: JSON) -> str | None:
    road_summary = properties.get("road_summary") or {}
    parts = [
        road_summary.get("road_name"),
        road_summary.get("locality"),
        road_summary.get("local_government_area"),
    ]
    text = ", ".join(p for p in parts if p)
    return text or None


def _traffic_management(properties: JSON) -> str | None:
    impact = properties.get("impact") or {}
    # delay is real but sometimes a genuine empty string, not null
    # (confirmed live, a real Guardian/Somerset Regional Council record) -
    # treated as absent, same "disregard empty, not just null" rule NSW's
    # own _clean_properties applies.
    parts = [
        impact.get("impact_type"),
        impact.get("impact_subtype"),
        impact.get("delay") or None,
        properties.get("advice"),
        properties.get("description"),
    ]
    text = " - ".join(p for p in parts if p)
    return text or None


def _operating_window(duration: JSON) -> str | None:
    recurrences = duration.get("recurrences") or []
    descriptions = [r.get("description") for r in recurrences if r.get("description")]
    return "; ".join(descriptions) or None


def _notices(properties: JSON) -> tuple[Notice, ...]:
    web_link = properties.get("web_link")
    if not web_link:
        return ()
    return (Notice(raw=web_link),)


def _administrative_area(source: JSON) -> str | None:
    return source.get("provided_by") or source.get("source_name")


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    duration = properties.get("duration") or {}
    start = parse_iso8601(duration.get("start"))
    end = parse_iso8601(duration.get("end"))
    event_id = properties.get("id")
    return WorksSite(
        reference=str(event_id) if event_id is not None else None,
        works_type=properties.get("event_subtype"),
        status=properties.get("status"),
        location_description=_location_description(properties),
        coordinate=_coordinate(feature),
        proposed_start=start,
        proposed_end=end,
        # No real "confirmed active" signal exists in this feed (status is
        # publication lifecycle - Published/Reopened - not works progress,
        # see streetworks.au.qld's module docstring) - never promoted past
        # ESTIMATED, the same discipline NSW/Victoria/WA apply.
        date_confidence=DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN,
        operating_window=_operating_window(duration),
        traffic_management=_traffic_management(properties),
        notices=_notices(properties),
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_au_qld_qldtraffic(features: list[JSON]) -> list[Works]:
    """Convert real QLDTraffic events (from
    :meth:`streetworks.au.qld.QldTrafficClient.iter_roadworks`, or any
    ``event_type`` slice of :meth:`~streetworks.au.qld.QldTrafficClient.iter_events`)
    into :class:`~streetworks.common.Works` - one per feature, each with a
    single ``WorksSite``. Not restricted to ``event_type == "Roadworks"``
    itself - the caller's own filtering decides what's passed in - see
    module docstring."""
    works_list: list[Works] = []
    for feature in features:
        properties = feature.get("properties") or {}
        source = properties.get("source") or {}
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                promoter=source.get("source_name"),
                territory=_TERRITORY,
                administrative_area=_administrative_area(source),
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=feature,
            )
        )
    return works_list
