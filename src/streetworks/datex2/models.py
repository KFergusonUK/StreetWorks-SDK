"""Typed model for DATEX II situation data (roadworks profile).

These classes hold the subset of the DATEX II Situation publication that the
EU roadworks profile uses: the situation/record lifecycle, validity, cause,
impact, comments, and location. Fields that a given feed doesn't populate are
simply ``None``/empty - national profiles vary.

Coordinates in DATEX II feeds are WGS84 latitude/longitude (per the standard's
ETRS89/WGS84 convention) - **not** the British National Grid eastings/northings
used by the UK providers in this SDK.

``raw`` on both ``Situation`` and ``SituationRecord`` points back at the
source object - a dict for the JSON-sourced adapters (National Highways,
Digitraffic), matching the ``.raw`` pattern used elsewhere in this SDK
(WZDx's ``RoadEvent``, SRWR's ``Record``). It's ``None`` for the streaming
XML parser (:mod:`streetworks.datex2.parser`, serving NDW and any raw
DATEX v2/v3 XML) - a deliberate trade-off, not an oversight: that parser
clears each XML element after yielding it to keep memory bounded on huge
feeds (~170 MB uncompressed, ~35 MB memory, verified against the real NDW
feed), so a stored ``Element`` reference would go stale under the caller.
Keeping ``raw`` unset there preserves that verified characteristic instead
of silently regressing it for a field most callers use rarely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

__all__ = ["Situation", "SituationRecord", "Validity", "Period", "Location"]

ROADWORKS_TYPES = frozenset({"MaintenanceWorks", "ConstructionWorks", "Roadworks"})


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
    # RoadOrCarriagewayOrLaneManagement's own type field - see is_roadworks
    # for why this is a second, independent roadworks signal from Spain's.
    road_or_carriageway_or_lane_management_type: str | None = None
    raw: Any = None

    @property
    def is_roadworks(self) -> bool:
        # Most profiles use a dedicated MaintenanceWorks/ConstructionWorks
        # xsi:type. Spain/DGT has neither - it publishes roadworks as a
        # generic record (RoadOrCarriagewayOrLaneManagement, mostly, but also
        # SpeedManagement/AbnormalTraffic) discriminated only by
        # `cause/causeType=roadMaintenance` +
        # `detailedCauseType/roadMaintenanceType=roadworks` - confirmed live,
        # 391/391 real roadworks records across all three record types, zero
        # MaintenanceWorks/ConstructionWorks records in the whole feed. This
        # check is additive (never true for a feed that never sets
        # `cause_type`/`road_maintenance_type` this way - confirmed against
        # every other adapter's fixtures, none use a `cause` element at all).
        #
        # Belgium (Flanders) surfaced a second, independent generic-record
        # case: 67/195 real roadworks-relevant records in one live pull were
        # `RoadOrCarriagewayOrLaneManagement` with
        # `roadOrCarriagewayOrLaneManagementType=newRoadworksLayout` - a real
        # DATEX II v3 standard enum value (not Belgium-specific), unambiguous
        # by name, sitting alongside 61 other records of the same xsi:type
        # with genuinely non-works values (`narrowLanes`, `roadClosed`,
        # `contraflow`, `singleAlternateLineTraffic`) that are deliberately
        # NOT matched here - those can arise from accidents/events, not just
        # works, so treating the whole xsi:type as roadworks the way Spain's
        # fix does would over-match. Confirmed this exact value doesn't
        # appear in any other adapter's real fixture (DGT's own 7 real
        # RoadOrCarriagewayOrLaneManagement records use different values
        # entirely), so this is additive here too.
        #
        # Bulgaria (LIMA/datasheet.api.bg) surfaced a third dedicated
        # xsi:type, distinct from both siblings above: real records use the
        # bare abstract name `Roadworks` as their own concrete xsi:type
        # (14/14 in one live pull, all also carrying
        # `roadworks/maintenanceWorks/roadMaintenanceType=roadworks` a level
        # too deep for the direct-child lookup that populates
        # `road_maintenance_type` to reach) rather than instantiating
        # `MaintenanceWorks`/`ConstructionWorks` directly - not schema-typical,
        # but real, live data. Added straight to `ROADWORKS_TYPES` rather than
        # as another generic-value check since it's already an unambiguous
        # dedicated type by name; confirmed no other adapter's real fixture
        # uses `xsi:type="Roadworks"` for anything.
        return (
            self.record_type in ROADWORKS_TYPES
            or (self.cause_type == "roadMaintenance" and self.road_maintenance_type == "roadworks")
            or self.road_or_carriageway_or_lane_management_type == "newRoadworksLayout"
        )


@dataclass
class Situation:
    """A Situation: one real-world occurrence and its records."""

    id: str
    version_time: datetime | None = None
    overall_severity: str | None = None
    records: list[SituationRecord] = field(default_factory=list)
    raw: Any = None

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
