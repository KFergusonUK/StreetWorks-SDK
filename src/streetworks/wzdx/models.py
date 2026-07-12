"""Typed model for WZDx (Work Zone Data Exchange) road events.

WZDx has no DATEX-style Situation/SituationRecord nesting - every GeoJSON
Feature in a feed already stands alone as one complete road event, so
:func:`~streetworks.wzdx.parser.parse_road_events` yields a flat
:class:`RoadEvent` per feature, not a grouping wrapper.

Coordinates are WGS84, same as DATEX, but native GeoJSON order is
**(longitude, latitude)** - the reverse of DATEX's (latitude, longitude).
:class:`Geometry` keeps that native order (so raw WZDx geometry always
means what the feed said); ``streetworks.common.from_wzdx`` does the
explicit flip when building a CRS-labelled ``Coordinate``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

__all__ = ["Geometry", "Relationship", "RoadEvent", "WORK_ZONE_EVENT_TYPES"]

JSON = dict[str, Any]

WORK_ZONE_EVENT_TYPES = frozenset({"work-zone"})


@dataclass(frozen=True)
class Geometry:
    """A road event's geometry, normalised across GeoJSON types actually
    seen in live feeds (``Point``, ``MultiPoint``, ``LineString``).

    ``points`` holds ``(longitude, latitude)`` pairs in native GeoJSON
    order - not ``(latitude, longitude)``. An unrecognised geometry type
    (no Polygon/MultiLineString observed live) yields empty ``points``
    rather than guessing; the original GeoJSON geometry is always kept on
    the owning :class:`RoadEvent`'s ``raw``.
    """

    kind: str | None = None
    points: tuple[tuple[float, float], ...] = ()

    @property
    def point(self) -> tuple[float, float] | None:
        """The first ``(longitude, latitude)`` pair, if any."""
        return self.points[0] if self.points else None


@dataclass(frozen=True)
class Relationship:
    """``properties.relationship`` - parent/child event IDs (observed live
    on a Québec v3.1 feed linking a work-zone to a companion detour).
    Preserved as data, never resolved into a grouping - see the WZDx
    section of the common-models design notes for why."""

    parents: tuple[str, ...] = ()
    children: tuple[str, ...] = ()


@dataclass
class RoadEvent:
    """One WZDx road event (one GeoJSON Feature). Every field is optional -
    real feeds leave most of them out, and even populated fields (dates
    especially) are frequently placeholder/garbage values; nothing here is
    validated for plausibility, only for shape."""

    id: str | None = None
    event_type: str | None = None
    road_names: tuple[str, ...] = ()
    direction: str | None = None
    name: str | None = None
    description: str | None = None
    data_source_id: str | None = None
    creation_date: datetime | None = None
    update_date: datetime | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_start_date_verified: bool | None = None
    is_end_date_verified: bool | None = None
    start_date_accuracy: str | None = None
    end_date_accuracy: str | None = None
    event_status: str | None = None
    vehicle_impact: str | None = None
    location_method: str | None = None
    works_ref: str | None = None
    types_of_work: tuple[str, ...] = ()
    lanes: tuple[JSON, ...] = ()
    relationship: Relationship = field(default_factory=Relationship)
    related_road_events: tuple[JSON, ...] = ()
    geometry: Geometry = field(default_factory=Geometry)
    raw: JSON = field(default_factory=dict)

    @property
    def is_work_zone(self) -> bool:
        return self.event_type in WORK_ZONE_EVENT_TYPES
