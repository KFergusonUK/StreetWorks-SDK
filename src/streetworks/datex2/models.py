"""Typed model for DATEX II situation data (roadworks profile).

These classes hold the subset of the DATEX II Situation publication that the
EU roadworks profile uses: the situation/record lifecycle, validity, cause,
impact, comments, and location. Fields that a given feed doesn't populate are
simply ``None``/empty - national profiles vary.

Coordinates in DATEX II feeds are WGS84 latitude/longitude (per the standard's
ETRS89/WGS84 convention) - **not** the British National Grid eastings/northings
used by the UK providers in this SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

__all__ = ["Situation", "SituationRecord", "Validity", "Period", "Location"]

ROADWORKS_TYPES = frozenset({"MaintenanceWorks", "ConstructionWorks"})


@dataclass(frozen=True)
class Period:
    start: datetime | None
    end: datetime | None


@dataclass(frozen=True)
class Validity:
    status: str | None = None
    overall_start: datetime | None = None
    overall_end: datetime | None = None
    periods: tuple[Period, ...] = ()


@dataclass(frozen=True)
class Location:
    """A record's location, normalised across referencing methods.

    ``points`` holds (latitude, longitude) pairs: one for a point location,
    the vertex list for a linear one (from ``gmlLineString``/``posList``).
    Alert-C and other non-coordinate references are preserved in
    ``alert_c_location`` / ``road_number`` where present rather than decoded.
    """

    kind: str | None = None  # e.g. PointLocation, LinearLocation
    points: tuple[tuple[float, float], ...] = ()
    carriageway: str | None = None
    road_number: str | None = None
    alert_c_location: str | None = None

    @property
    def point(self) -> tuple[float, float] | None:
        """The first (latitude, longitude) pair, if any."""
        return self.points[0] if self.points else None


@dataclass
class SituationRecord:
    """One SituationRecord - a works item, traffic measure, or event."""

    id: str
    record_type: str  # xsi:type local name, e.g. "MaintenanceWorks"
    version: str | None = None
    creation_time: datetime | None = None
    version_time: datetime | None = None
    probability_of_occurrence: str | None = None
    source_name: str | None = None
    validity: Validity = field(default_factory=Validity)
    location: Location = field(default_factory=Location)
    cause_type: str | None = None
    cause_description: str | None = None
    comments: tuple[str, ...] = ()
    impact_delay_band: str | None = None
    operator_action_status: str | None = None
    urgent: bool | None = None
    # Roadworks specifics (whichever the type carries):
    road_maintenance_type: str | None = None
    construction_work_type: str | None = None
    subject_type_of_works: str | None = None

    @property
    def is_roadworks(self) -> bool:
        return self.record_type in ROADWORKS_TYPES


@dataclass
class Situation:
    """A Situation: one real-world occurrence and its records."""

    id: str
    version_time: datetime | None = None
    overall_severity: str | None = None
    records: list[SituationRecord] = field(default_factory=list)

    @property
    def roadworks(self) -> list[SituationRecord]:
        """The MaintenanceWorks/ConstructionWorks records."""
        return [r for r in self.records if r.is_roadworks]

    @property
    def measures(self) -> list[SituationRecord]:
        """The non-works records (lane closures, reroutings, speed limits...)."""
        return [r for r in self.records if not r.is_roadworks]

    def __repr__(self) -> str:
        return f"<Situation {self.id}: {len(self.roadworks)} works, {len(self.measures)} measures>"
