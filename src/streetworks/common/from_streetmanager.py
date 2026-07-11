"""Street Manager -> streetworks.common converter.

Groups ``reporting.permits()``/``reporting.iter_permits()`` rows by
``work_reference_number`` into one :class:`~streetworks.common.Works` per
group. Within a group, rows are split by the record-identity rule: a PAA
(``work_category == "paa"``) is a planning artifact and becomes a
:class:`~streetworks.common.WorksPlanning`, not a site - live sandbox data
confirms a PAA and the permit(s) that eventually supersede it share the
same ``work_reference_number`` (e.g. ``UG27724003165-01`` PAA,
``UG27724003165-02`` the major permit that followed it). Everything else
becomes a :class:`~streetworks.common.WorksSite`.

``reporting.forward_plans()`` rows are also PAA-like planning artifacts by
the same rule. The design spec assumed Forward Plans are always
free-floating (no linked work reference) until converted to a permit, but
real sandbox data shows ``ForwardPlanSummaryResponse.work_reference_number``
is already populated well before any permit exists under it - so a forward
plan lands in the matching Works' ``plannings`` where one exists, and only
falls back to a free-standing :class:`~streetworks.common.WorksPlanning`
(no ``Works`` at all) if it doesn't.

``territory`` is hardcoded ``"England"`` - Street Manager is DfT's service
and no field in the reporting response states which UK nation a permit is
in, so there's nothing to key off if Welsh authorities also report through
it. ``administrative_area`` comes straight off ``highway_authority``, which
every observed row carries.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksPlanning, WorksSite

__all__ = ["from_streetmanager"]

JSON = dict[str, Any]


def _dt(value: str | datetime | None) -> datetime | None:
    """Reporting rows come straight off the wire as JSON (``reporting.permits()``
    calls ``response.json()`` directly, not the generated pydantic models),
    so date fields are ISO-8601 strings (e.g. ``"2026-06-03T00:00:00.000Z"``,
    consistently 3-digit milliseconds in observed data) rather than
    ``datetime`` objects - parsed here rather than assumed. Already-parsed
    ``datetime`` values (e.g. from a caller who did validate through the
    pydantic models) pass through unchanged."""
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _coordinate(works_coordinates: JSON | None) -> Coordinate | None:
    """``works_coordinates`` is BNG GeoJSON - a ``Point`` or a ``LineString``
    observed live. A LineString collapses to its first vertex (the same
    "first point stands for the location" convention DATEX's own
    ``Location.point`` uses for linear locations) - full geometry stays
    reachable via ``.raw``."""
    if not works_coordinates:
        return None
    coordinates = works_coordinates.get("coordinates")
    geometry_type = works_coordinates.get("type")
    if geometry_type == "Point" and coordinates:
        return Coordinate(value=(coordinates[0], coordinates[1]), crs="EPSG:27700")
    if geometry_type == "LineString" and coordinates:
        first = coordinates[0]
        return Coordinate(value=(first[0], first[1]), crs="EPSG:27700")
    return None


def _date_confidence(
    actual_start: datetime | None, proposed_start: datetime | None
) -> DateConfidence:
    if actual_start is not None:
        return DateConfidence.VERIFIED
    if proposed_start is not None:
        return DateConfidence.ESTIMATED
    return DateConfidence.UNKNOWN


def _to_site(row: JSON) -> WorksSite:
    actual_start = _dt(row.get("actual_start_date"))
    proposed_start = _dt(row.get("proposed_start_date"))
    return WorksSite(
        reference=row.get("permit_reference_number"),
        works_type=row.get("activity_type_string") or row.get("work_category_string"),
        status=row.get("status_string") or row.get("work_status_string"),
        location_usrn=str(row["usrn"]) if row.get("usrn") is not None else None,
        location_description=row.get("location_description") or row.get("street"),
        coordinate=_coordinate(row.get("works_coordinates")),
        proposed_start=proposed_start,
        proposed_end=_dt(row.get("proposed_end_date")),
        actual_start=actual_start,
        actual_end=_dt(row.get("actual_end_date")),
        date_confidence=_date_confidence(actual_start, proposed_start),
        traffic_management=row.get("traffic_management_type_string"),
        source_grade=SourceGrade.REGISTER,
        raw=row,
    )


def _to_planning(row: JSON, *, kind: str) -> WorksPlanning:
    return WorksPlanning(
        kind=kind,
        works_reference=row.get("work_reference_number"),
        indicative_start=_dt(row.get("proposed_start_date")),
        indicative_end=_dt(row.get("proposed_end_date")),
        source_grade=SourceGrade.REGISTER,
        raw=row,
    )


def from_streetmanager(
    permits: list[JSON], forward_plans: list[JSON] | None = None
) -> list[Works]:
    """Convert Street Manager Reporting rows into :class:`~streetworks.common.Works`.

    ``permits`` are ``PermitSummaryResponse``-shaped rows (from
    ``reporting.permits()``/``iter_permits()``); ``forward_plans`` are
    ``ForwardPlanSummaryResponse``-shaped rows (from
    ``reporting.forward_plans()``/``iter_forward_plans()``), both as plain
    dicts (JSON straight off the wire, or ``model_dump()`` from the
    generated pydantic models).
    """
    by_reference: dict[str, list[JSON]] = defaultdict(list)
    for row in permits:
        by_reference[row["work_reference_number"]].append(row)

    works_list: list[Works] = []
    for reference, rows in by_reference.items():
        sites = [_to_site(r) for r in rows if r.get("work_category") != "paa"]
        plannings = [_to_planning(r, kind="paa") for r in rows if r.get("work_category") == "paa"]
        header = rows[0]
        works_list.append(
            Works(
                reference=reference,
                location_usrn=str(header["usrn"]) if header.get("usrn") is not None else None,
                coordinate=_coordinate(header.get("works_coordinates")),
                promoter=header.get("promoter_organisation"),
                territory="England",
                administrative_area=header.get("highway_authority"),
                source_grade=SourceGrade.REGISTER,
                sites=tuple(sites),
                plannings=tuple(plannings),
                raw=rows,
            )
        )

    by_reference_works = {w.reference: w for w in works_list}
    free_standing_plannings: list[WorksPlanning] = []
    free_standing_rows: list[JSON] = []
    for row in forward_plans or []:
        planning = _to_planning(row, kind="forward_plan")
        works = by_reference_works.get(planning.works_reference)
        if works is not None:
            works.plannings = (*works.plannings, planning)
        else:
            free_standing_plannings.append(planning)
            free_standing_rows.append(row)

    if free_standing_plannings:
        works_list.append(
            Works(
                territory="England",
                administrative_area=free_standing_rows[0].get("highway_authority"),
                source_grade=SourceGrade.REGISTER,
                plannings=tuple(free_standing_plannings),
                raw=free_standing_plannings,
            )
        )

    return works_list
