"""Request-assembly for Section 50 licence works submitted to Street Manager
under the highway authority's own promoter account.

This is **not** a new endpoint wrapper - ``WorkAPI.create_work``,
``.start_work``, ``.stop_work`` and ``LookupAPI.street_by_usrn`` (see
``streetmanager/client.py``) already exist as generic, working JSON-in/
JSON-out wrappers. What's missing, and what this module provides, is the
S50-specific request-assembly and identity-stamping layer in front of them:
reproject the applicant-drawn geometry, stamp the two SWA codes and the
``section_50``/``planned`` pinning, pass everything else the applicant
stated straight through. **Transport plus identity injection only** - this
is deliberately not an S50 rules engine; it trusts the applicant's stated
inputs and Street Manager's own server-side validation. That pass-through
already covers ``file_ids`` (real evidence-attachment ids from
``WorkAPI.upload_file``, e.g. insurance/accreditation copies) with no
change needed here - it's just another key in ``applicant_fields``, not a
connector-owned one, so this module never has to learn what a file is any
more than it learns what a bond is; see
``examples/streetmanager_section_50.py``'s own docstring for the real,
sandbox-verified upload-then-attach sequence this enables.

Scope is the three verbs a Section 50 licence needs: apply, start, stop.
Reinstatement (Cat C inspection, bond release, guarantee period) is
deliberately out of scope and stays council-side.

**The submitting Street Manager account must hold a Promoter registration,
not Highway Authority - live-confirmed, not assumed.** A Street Manager
login is registered under one organisation with one role; an account can't
hold both. This module stamps ``promoter_swa_code`` and
``highway_authority_swa_code`` to the *same* SWA code (see
``build_work_create_request``'s own docstring on why), which describes
whose identity the work is filed under - a separate concern from which
login's *role* is authorised to call ``WorkAPI.create_work`` in the first
place. An HA-role login - the kind every read-only Street Manager example
elsewhere in this repo uses - cannot submit works; it needs a Promoter-role
account, even one still ultimately representing the same highway authority.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from ...common._bng import reproject_geojson_to_bng

__all__ = ["build_work_create_request", "build_work_start_update", "build_work_stop_update"]

#: Fields this connector owns and stamps itself - an applicant-supplied
#: value here is rejected rather than silently overwritten, since these are
#: exactly the fields the brief this module implements says the connector
#: must control, not the applicant.
_CONNECTOR_OWNED_FIELDS = frozenset(
    {
        "promoter_swa_code",
        "highway_authority_swa_code",
        "activity_type",
        "work_type",
        "usrn",
        "works_coordinates",
        "immediate_risk",
    }
)

#: WorkCreateRequest.workstream_prefix: "Must consist of 3 positive whole
#: numbers" - the real mistake this guards against is prefixing with an org
#: code like "UG" (see this module's own brief).
_WORKSTREAM_PREFIX_RE = re.compile(r"^\d{3}$")

#: Date/time fields on WorkCreateRequest that are AwareDatetime - httpx's
#: JSON encoder can't serialise a raw datetime, so any of these passed in as
#: real datetime objects need normalising to ISO-8601 strings before the
#: payload is handed to WorkAPI.create_work.
_DATETIME_FIELDS = (
    "proposed_start_date",
    "proposed_start_time",
    "proposed_end_date",
    "proposed_end_time",
)


def build_work_create_request(
    applicant_fields: dict[str, Any],
    *,
    ha_swa_code: str,
    host_usrn: int | float,
    geometry: dict[str, Any],
    additional_usrns: Sequence[int | float] = (),
    workstream_prefix: str | None = None,
    host_usrn_geometry: dict[str, Any] | None = None,
    extent_nudge_threshold_m: float = 50.0,
) -> tuple[dict[str, Any], list[str]]:
    """Assemble a ``WorkCreateRequest``-shaped payload for an S50 licence.

    ``applicant_fields`` is the pass-through bag: everything the applicant
    stated that this connector never reasons about (contact details, dates,
    description, traffic management, closures, ...) - copied through
    verbatim. Supplying any connector-owned field here (see
    ``_CONNECTOR_OWNED_FIELDS``) raises ``ValueError`` naming the offending
    key(s), rather than being silently overwritten.

    ``ha_swa_code`` is stamped onto *both* ``promoter_swa_code`` and
    ``highway_authority_swa_code`` - a single parameter, not two, because an
    S50 has no separate licensee field: the highway authority is the
    promoter for a licensed third party's works, so both identity slots are
    always the same value. The real licensee's identity lives in
    ``applicant_fields["secondary_contact"]``/``["secondary_contact_number"]``.

    ``host_usrn`` is the one USRN ``WorkCreateRequest.usrn`` (singular,
    required) is set to. If the works genuinely span more than one street
    (rare for an S50 - length-limited by cost), list the others in
    ``additional_usrns``; they're appended as free text to
    ``works_location_description`` rather than dropped, since the drawn
    geometry remains the true extent regardless of which USRN is filed
    against.

    ``geometry`` is the applicant-drawn extent as WGS84 GeoJSON
    (``Point``/``LineString``/``Polygon``); reprojected to the BNG
    easting/northing GeoJSON Street Manager expects via
    :func:`streetworks.common._bng.reproject_geojson_to_bng`.

    ``application_type`` defaults to ``"permit"`` if not given in
    ``applicant_fields`` - **unconfirmed**: Street Manager doesn't surface
    this literal in its UI, only on a GET of the work record, but the
    observed deem-clock behaviour on a live S50 sandbox record strongly
    implies ``"permit"`` over ``"notice"``. Stated here rather than hidden,
    so a caller who later confirms the literal via a GET can override it.

    If ``host_usrn_geometry`` (BNG GeoJSON, e.g. straight from
    ``LookupAPI.street_by_usrn``) is supplied, a soft consistency check runs:
    if the drawn extent sits further than ``extent_nudge_threshold_m`` from
    the USRN's own geometry, a human-readable string is appended to the
    returned ``warnings`` list. This **never raises and never changes the
    payload** - a genuine corner job or verge-and-carriageway spread can
    legitimately sit off the named street's centreline; it's a nudge, not a
    gate. The distance used is point-to-*segment* (nearest point on any
    stretch of the USRN's line, not nearest vertex) - a long, straight USRN
    segment has sparse vertices, so a vertex-only distance would
    systematically over-report on correctly-sited works. Skipped entirely
    (no warning, no error) if ``host_usrn_geometry`` is omitted - this
    function makes no HTTP calls itself, so it's the caller's job to fetch
    the USRN geometry first if it wants the check.

    Returns ``(work_create_request_payload, warnings)``.
    """
    owned_fields_present = _CONNECTOR_OWNED_FIELDS & applicant_fields.keys()
    if owned_fields_present:
        raise ValueError(
            "applicant_fields must not set connector-owned field(s): "
            f"{', '.join(sorted(owned_fields_present))}"
        )

    if workstream_prefix is not None and not _WORKSTREAM_PREFIX_RE.match(workstream_prefix):
        raise ValueError(
            f"workstream_prefix must be exactly 3 digits (e.g. '050', not 'UG050'), "
            f"got {workstream_prefix!r}"
        )

    payload: dict[str, Any] = dict(applicant_fields)
    for field in _DATETIME_FIELDS:
        if field in payload:
            payload[field] = _iso(payload[field])

    payload["promoter_swa_code"] = ha_swa_code
    payload["highway_authority_swa_code"] = ha_swa_code
    payload["activity_type"] = "section_50"
    payload["work_type"] = "planned"
    payload.setdefault("application_type", "permit")
    payload["usrn"] = host_usrn

    if additional_usrns:
        if "works_location_description" not in payload:
            raise ValueError(
                "applicant_fields must include works_location_description to "
                "record additional_usrns as free text"
            )
        usrn_list = ", ".join(str(int(usrn)) for usrn in additional_usrns)
        payload["works_location_description"] = (
            f"{payload['works_location_description']} Also spans USRN(s): {usrn_list}."
        )

    payload["works_coordinates"] = reproject_geojson_to_bng(geometry)

    if workstream_prefix is not None:
        payload["workstream_prefix"] = workstream_prefix

    warnings: list[str] = []
    if host_usrn_geometry is not None:
        distance = _extent_distance_m(payload["works_coordinates"], host_usrn_geometry)
        if distance > extent_nudge_threshold_m:
            warnings.append(
                f"Drawn extent is {distance:.1f}m from USRN {host_usrn}'s own geometry "
                f"(threshold {extent_nudge_threshold_m:.0f}m) - check this is intended "
                "(e.g. a corner job or verge/carriageway spread), not a mis-pick."
            )

    return payload, warnings


def build_work_start_update(actual_start_date: datetime | str) -> dict[str, Any]:
    """A ``WorkStartUpdateRequest``-shaped payload keyed on
    ``work_reference_number`` (not the permit reference)."""
    return {"actual_start_date": _iso(actual_start_date)}


def build_work_stop_update(actual_stop_date: datetime | str) -> dict[str, Any]:
    """A ``WorkStopUpdateRequest``-shaped payload keyed on
    ``work_reference_number`` (not the permit reference)."""
    return {"actual_stop_date": _iso(actual_stop_date)}


def _iso(value: datetime | str) -> str:
    return value.isoformat() if isinstance(value, datetime) else value


def _iter_points(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    """Flatten a BNG GeoJSON Point/LineString/Polygon (or a raw
    ``street_by_usrn`` response's geometry) to a flat list of (x, y) points."""
    coordinates = geometry.get("coordinates")
    geometry_type = geometry.get("type")
    if coordinates is None:
        return []
    if geometry_type == "Point":
        return [(coordinates[0], coordinates[1])]
    if geometry_type == "LineString":
        return [(p[0], p[1]) for p in coordinates]
    if geometry_type == "Polygon":
        return [(p[0], p[1]) for ring in coordinates for p in ring]
    if geometry_type == "MultiLineString":
        return [(p[0], p[1]) for part in coordinates for p in part]
    return []


def _point_to_segment_distance(
    point: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
) -> float:
    """Shortest distance from ``point`` to the segment ``a``-``b``."""
    px, py = point
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    nearest_x, nearest_y = ax + t * dx, ay + t * dy
    return ((px - nearest_x) ** 2 + (py - nearest_y) ** 2) ** 0.5


def _extent_distance_m(drawn_geometry: dict[str, Any], usrn_geometry: dict[str, Any]) -> float:
    """Minimum point-to-segment distance between every point of the drawn
    extent and every segment of the USRN geometry - a deliberately simple
    heuristic for a soft nudge, not a true line-to-line minimum distance
    (e.g. it doesn't need to handle segment-segment crossing cases exactly).
    Uses point-to-segment (not nearest-vertex) specifically so a long,
    straight, sparsely-vertexed USRN line doesn't systematically over-report
    distance for works sitting genuinely close to its middle."""
    drawn_points = _iter_points(drawn_geometry)
    usrn_points = _iter_points(usrn_geometry)
    if not drawn_points or len(usrn_points) < 2:
        return 0.0
    segments = list(zip(usrn_points, usrn_points[1:], strict=False))
    return min(
        _point_to_segment_distance(point, a, b) for point in drawn_points for a, b in segments
    )
