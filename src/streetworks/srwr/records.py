"""Record definitions for the SRWR Open Data extract (format version 02).

The extract is a multi-record-type CSV: every line starts with the format
version and a three-digit Record Type code, and the remaining fields are
positional per type. This module maps each SRWR-applicable Record Type to
named, typed fields per the official specification ("Scottish Road Works
Register Data Extract v2.02").

Records for types with a registered field list expose their fields as
attributes (``record.activity_id``); every record also keeps the ``raw``
field list, so unregistered or future types remain fully accessible.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Any

__all__ = ["Record", "RECORD_TYPE_NAMES", "parse_row"]


# --------------------------------------------------------------------------- #
# Converters. The extract represents "no value" as an empty field; every
# converter maps that to None rather than guessing a default.
# --------------------------------------------------------------------------- #


def _int(value: str) -> int | None:
    return int(value) if value.strip() else None


def _num(value: str) -> float | None:
    return float(value) if value.strip() else None


def _bool(value: str) -> bool | None:
    if not value.strip():
        return None
    return value.strip().lower() == "true"


def _dt(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    # Spec: YYYY-MM-DD hh:mm:ss.SS (centiseconds)
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _str(value: str) -> str | None:
    return value if value else None


Converter = Callable[[str], Any]
Field = tuple[str, Converter]

# --------------------------------------------------------------------------- #
# Field registries: (snake_case name, converter) per Record Type, in the
# positional order defined by the specification, *excluding* the two common
# leading fields (Version, Record Type) which every record shares.
# --------------------------------------------------------------------------- #

_PHASE_FLAGS: list[Field] = [
    ("phase_traffic_sensitive", _bool),
    ("phase_protected_street", _bool),
    ("phase_lane_rental", _bool),
    ("phase_engineering_difficulty", _bool),
    ("phase_strategic_route", _bool),
    ("phase_other", _bool),
    ("street_traffic_sensitive", _bool),
    ("street_protected_street", _bool),
    ("street_lane_rental", _bool),
    ("street_engineering_difficulty", _bool),
    ("street_strategic_route", _bool),
    ("street_other", _bool),
]

FIELDS: dict[str, list[Field]] = {
    "000": [("text", _str)],
    "001": [
        ("activity_id", _int),
        ("created", _dt),
        ("last_updated", _dt),
        ("promoter_district_id", _int),
        ("activity_reference", _str),
        ("notifiable_district_id", _int),
        ("code_of_practice", _str),
        ("is_archive_ready", _bool),
        ("archive_relevant_date", _date),
        ("latest_phase", _int),
        ("usrn", _int),
        ("restricted", _bool),
    ],
    "002": [("activity_id", _int), ("project_reference", _str)],
    "003": [
        ("promoter_district_id", _int),
        ("project_reference", _str),
        ("project_description", _str),
    ],
    "004": [
        ("activity_id", _int),
        ("is_provisional", _bool),
        ("usrn", _str),
        ("provisional_street_details", _str),
    ],
    "006": [
        ("activity_id", _int),
        ("sending_district_id", _int),
        ("phase_number", _int),
        ("notice_type", _str),
        ("created", _dt),
        ("notice_text", _str),
        ("response_due", _date),
        ("in_response_to", _int),
        ("disapply", _bool),
        ("notice_sequence_number", _int),
        ("permit_application_status", _int),
        ("permit_application_status_date", _date),
        ("start_date", _dt),
        ("end_date", _dt),
    ],
    "007": [
        ("activity_id", _int),
        ("created", _dt),
        ("updated", _dt),
        ("latest_description", _str),
        ("location", _str),
        ("phase_number", _int),
        ("template", _str),
        ("works_type", _str),
        ("activity_status", _str),
        ("is_cancelled", _bool),
        ("geometry", _str),
        ("highest_carriageway_reinstatement_category", _str),
        ("highest_footway_reinstatement_category", _str),
        ("has_many_carriageway_reinstatement_categories", _bool),
        ("has_many_footway_reinstatement_categories", _bool),
        *_PHASE_FLAGS,
    ],
    "008": [
        ("activity_id", _int),
        ("phase_number", _int),
        ("proposed_start", _dt),
        ("has_proposed_start_time", _bool),
        ("actual_start", _dt),
        ("has_actual_start_time", _bool),
        ("estimated_end_proposed", _dt),
        ("actual_end", _dt),
        ("earliest_start_advance_planning", _dt),
        ("latest_start_advance_planning", _dt),
        ("earliest_start_proposed", _date),
        ("latest_start_proposed", _date),
        ("latest_possible_end", _date),
        ("reasonable_duration", _int),
        ("reasonable_end", _date),
        ("duration_challenge_estimate", _int),
        ("phase_type", _str),
        ("works_technique", _str),
        ("street_category", _int),
        ("traffic_management_type", _str),
        ("footway_closure", _bool),
        ("parking_suspensions", _bool),
        ("collaboration_type", _int),
        ("only_working_hours", _bool),
        ("within_restriction", _bool),
        ("permit_scheme", _bool),
        ("permit_reference", _str),
        ("permit_application_status", _int),
        ("permit_application_status_date", _date),
        ("inspection_units", _int),
        ("estimated_number_of_phases", _int),
        ("uses_automatic_inspection_units", _bool),
        # condition blocks (not applicable to SRWR, kept positional)
        ("promoter_condition_text", _str),
        ("promoter_condition_date_constraint", _bool),
        ("promoter_condition_time_constraint", _bool),
        ("promoter_condition_out_of_hours_work", _bool),
        ("promoter_condition_material_and_plant_storage", _bool),
        ("promoter_condition_road_occupation_dimensions", _bool),
        ("promoter_condition_traffic_space_dimensions", _bool),
        ("promoter_condition_road_closure", _bool),
        ("promoter_condition_light_signals_and_shuttle_working", _bool),
        ("promoter_condition_traffic_management_changes", _bool),
        ("promoter_condition_work_methodology", _bool),
        ("promoter_condition_consultation_and_publicity", _bool),
        ("promoter_condition_environmental", _bool),
        ("promoter_condition_local", _bool),
        ("authority_condition_text", _str),
        ("authority_condition_date_constraint", _bool),
        ("authority_condition_time_constraint", _bool),
        ("authority_condition_out_of_hours_work", _bool),
        ("authority_condition_material_and_plant_storage", _bool),
        ("authority_condition_road_occupation_dimensions", _bool),
        ("authority_condition_traffic_space_dimensions", _bool),
        ("authority_condition_road_closure", _bool),
        ("authority_condition_light_signals_and_shuttle_working", _bool),
        ("authority_condition_traffic_management_changes", _bool),
        ("authority_condition_work_methodology", _bool),
        ("authority_condition_consultation_and_publicity", _bool),
        ("authority_condition_environmental", _bool),
        ("authority_condition_local", _bool),
        ("revoke_or_undue_delay_response_deadline", _dt),
        ("earliest_start_potential", _dt),
        ("latest_start_potential", _dt),
        ("latest_permit_application", _int),
        ("latest_permit_response", _int),
        ("traffic_signal_application", _bool),
        ("interim_complete", _date),
        ("permanent_complete", _date),
        ("remedial_complete", _date),
        ("estimated_end_in_progress", _dt),
        ("actual_excavation_type", _str),
    ],
    "009": [
        ("activity_id", _int),
        ("phase_number", _int),
        ("is_applicable", _bool),
        ("special_designation_sequence_number", _int),
        ("special_designation_type", _str),
    ],
    "010": [
        ("activity_id", _int),
        ("phase_number", _int),
        ("site_number", _int),
        ("reinstatement_type", _str),
        ("location_text", _str),
        ("created", _dt),
        ("updated", _dt),
        ("site_location", _str),
        ("site_surface_type", _str),
        ("length", _num),
        ("width", _num),
        ("depth", _str),
        ("is_deleted", _bool),
        ("reinstated_date", _date),
        ("reset_warranty", _bool),
        ("interim_construction_method", _int),
        ("site_base_material", _str),
        ("qualification_reference", _str),
        ("geometry", _str),
        ("warranty_end_date", _date),
        ("registered", _bool),
    ],
    "012": [
        ("activity_id", _int),
        ("usrn", _int),
        ("promoter_district_id", _int),
        ("authority_district_id", _int),
        ("agreement_id", _int),
    ],
    "013": [("activity_id", _int), ("notice_id", _int), ("agreement_id", _int)],
    "014": [
        ("activity_id", _int),
        ("comment_type", _str),
        ("created", _dt),
        ("comment_text", _str),
        ("fixed_penalty_notice_id", _int),
        ("sending_district_id", _int),
    ],
    "015": [
        ("activity_id", _int),
        ("inspecting_district_id", _int),
        ("inspection_number", _int),
        ("inspection_sequence_number", _int),
        ("inspection_alpha_code", _str),
        ("inspector_name", _str),
        ("inspector_telephone", _str),
        ("inspector_email", _str),
        ("inspector_address1", _str),
        ("inspector_address2", _str),
        ("inspector_address3", _str),
        ("inspector_address4", _str),
        ("inspector_address5", _str),
        ("inspector_postcode", _str),
        ("inspector_text", _str),
        ("inspection_type", _str),
        ("has_done_time", _bool),
        ("done", _dt),
        ("has_logged_call_time", _bool),
        ("logged_call", _dt),
        ("inspection_result", _str),
        ("result_text", _str),
        ("geometry", _str),
        ("updated", _dt),
        ("inspection_status", _str),
        ("status_text", _str),
        ("site_informed", _bool),
        ("inspector_address", _str),
    ],
    "016": [
        ("activity_id", _int),
        ("inspection_number", _int),
        ("site_number", _int),
        ("result", _str),
        ("result_text", _str),
        ("defect_message", _str),
        ("signing_lighting_guarding_text", _str),
        ("is_selected_as_random_site", _bool),
        ("geometry", _str),
        ("works_phase", _int),
        ("inspecting_district_id", _int),
    ],
    "017": [
        ("activity_id", _int),
        ("inspection_number", _int),
        ("inspected_site", _int),
        ("inspection_question", _str),
        ("inspection_answer", _str),
        ("inspection_answer_text", _str),
        ("inspecting_district_id", _int),
    ],
    "019": [
        ("activity_id", _int),
        ("offence", _str),
        ("code_of_practice", _str),
        ("fpn_number", _str),
        ("fpn_id", _int),
        ("charge_id", _int),
        ("authorised_officer_name", _str),
        ("authorised_officer_telephone", _str),
        ("authorised_officer_email", _str),
        ("authorised_officer_address1", _str),
        ("authorised_officer_address2", _str),
        ("authorised_officer_address3", _str),
        ("authorised_officer_address4", _str),
        ("authorised_officer_address5", _str),
        ("authorised_officer_postcode", _str),
        ("fpn_officer_name", _str),
        ("fpn_status", _str),
        ("withdrawn", _dt),
        ("withdrawn_username_id", _str),
        ("withdrawn_text", _str),
        ("withdrawn_for_legal_action", _bool),
        ("offence_date", _date),
        ("offence_text", _str),
        ("hearing_result", _str),
        ("declined_text", _str),
        ("location_text", _str),
        ("authorised_officer_address", _str),
    ],
    "021": [
        ("activity_id", _int),
        ("inspection_id", _int),
        ("inspection_rate", _num),
        ("inspecting_district_id", _int),
        ("charge_id", _int),
    ],
    "022": [
        ("activity_id", _int),
        ("fixed_penalty_notice_id", _int),
        ("charge_id", _int),
        ("fpn_rate", _num),
        ("fpn_offence", _str),
        ("discount_charge", _num),
    ],
    "035": [
        ("activity_id", _int),
        ("target_district_id", _int),
        ("due", _dt),
        ("inspection_type", _str),
        ("text", _str),
    ],
    "036": [
        ("activity_id", _int),
        # Real extracts put the reference before the district ID (the spec
        # tables list them the other way around).
        ("activity_reference_of_accepted_by", _str),
        ("responsibility_accepted_by_district_id", _int),
    ],
    "037": [
        ("activity_id", _int),
        ("phase_number", _int),
        ("district_id", _int),
    ],
    "038": [
        ("activity_id", _int),
        ("restriction_start", _dt),
        ("restriction_end", _dt),
    ],
    "039": [
        ("activity_id", _int),
        ("restriction_start", _dt),
        ("is_carriageway_restriction", _bool),
        ("is_footway_restriction", _bool),
        ("carriageway_restriction_end", _date),
        ("footway_restriction_end", _date),
        ("restriction_duration_years", _int),
        ("restriction_response_deadline", _dt),
        ("sub_type", _str),
    ],
    "040": [
        ("activity_id", _int),
        ("actual_end", _dt),
        ("inspection_units", _int),
    ],
    "041": [
        ("activity_id", _int),
        ("discovered", _dt),
        ("sustained_by_organisation_id", _int),
        ("sustained_by_district_id", _int),
        ("done", _dt),
        ("done_by_organisation_id", _int),
        ("done_by_district_id", _int),
        ("done_by_activity_id", _int),
        ("remedial_works_activity_id", _int),
        ("plant_exposed", _bool),
        ("plans_available", _bool),
        ("plans_used", _bool),
        ("cable_locating_equipment_available", _bool),
        ("cable_locating_equipment_used", _bool),
    ],
    "042": [
        ("activity_id", _int),
        ("start_date", _dt),
        ("end_date", _dt),
        ("invoice_to", _str),
        ("hire_company_name", _str),
        ("hire_company_telephone", _str),
        ("hire_company_email", _str),
        ("hire_company_address1", _str),
        ("hire_company_address2", _str),
        ("hire_company_address3", _str),
        ("hire_company_address4", _str),
        ("hire_company_address5", _str),
        ("hire_company_postcode", _str),
        ("licence_sub_type", _str),
        ("hire_company_address", _str),
    ],
    "043": [
        ("activity_id", _int),
        ("object_type", _str),
        ("line_id", _int),
        ("object_description", _str),
        ("object_location", _str),
        ("inspection_number", _int),
    ],
    "098": [
        ("internal_reference", _int),
        ("organisation_id", _int),
        ("organisation_description", _str),
        ("organisation_prefix", _str),
    ],
    "099": [
        ("internal_reference", _int),
        ("organisation_id", _int),
        ("district_id", _int),
        ("district_description", _str),
        ("district_prefix", _str),
    ],
}

RECORD_TYPE_NAMES: dict[str, str] = {
    "000": "Licensing and Information",
    "001": "Activity",
    "002": "Project for Activity",
    "003": "Project",
    "004": "Street for Activity",
    "005": "Activity Contact",
    "006": "Notice",
    "007": "Phase",
    "008": "Undertaker Phase",
    "009": "Special Designation for Phase",
    "010": "Site",
    "011": "Agreement Records",
    "012": "Authority Agreement",
    "013": "Promoter Agreement",
    "014": "Comments",
    "015": "Inspected Detail",
    "016": "Inspected Site",
    "017": "Inspected Item",
    "019": "Fixed Penalty Notice",
    "020": "Charges",
    "021": "Inspection Charge",
    "022": "Fixed Penalty Notice Charge",
    "027": "Invoice",
    "028": "Traffic Signal Application",
    "035": "Inspection Dues",
    "036": "Unattributable Works/Defective Apparatus Phase",
    "037": "User Added Recipients",
    "038": "Diversionary Works Phase",
    "039": "Restriction Phase",
    "040": "Registration of Non-Notifiable Works Phase",
    "041": "Damage Report Phase",
    "042": "Permission/Event/Disruption/Road Closure/Works Licence",
    "043": "Objects",
    "044": "Additional Fields",
    "098": "Organisation",
    "099": "District",
}


class Record:
    """One line of the extract.

    Fields for registered Record Types are available as attributes with
    converted Python values (``record.activity_id``, ``record.created``).
    The unconverted field list (after Version and Record Type) is always
    available as ``record.raw``.
    """

    __slots__ = ("version", "record_type", "raw", "_named")

    def __init__(self, version: str, record_type: str, raw: list[str]):
        self.version = version
        self.record_type = record_type
        self.raw = raw
        named: dict[str, Any] = {}
        spec = FIELDS.get(record_type)
        if spec:
            for (name, convert), value in zip(spec, raw, strict=False):
                named[name] = convert(value)
            # Fields beyond the spec (future additions) stay in raw only.
        self._named = named

    @property
    def type_name(self) -> str:
        return RECORD_TYPE_NAMES.get(self.record_type, f"Unknown ({self.record_type})")

    @property
    def activity_id(self) -> int | None:
        """Activity ID if this record carries one (most types do)."""
        return self._named.get("activity_id")

    def __getattr__(self, name: str) -> Any:
        try:
            return self._named[name]
        except KeyError:
            raise AttributeError(f"{self.type_name!r} record has no field {name!r}") from None

    def to_dict(self) -> dict[str, Any]:
        """Named fields as a plain dict (converted values)."""
        return dict(self._named)

    def __repr__(self) -> str:
        aid = self._named.get("activity_id")
        aid_part = f" activity_id={aid}" if aid is not None else ""
        return f"<Record {self.record_type} {self.type_name}{aid_part}>"


def parse_row(row: list[str]) -> Record:
    """Build a :class:`Record` from a CSV row (as produced by ``csv.reader``)."""
    if len(row) < 2:
        raise ValueError(f"extract row has fewer than 2 fields: {row!r}")
    return Record(version=row[0], record_type=row[1], raw=row[2:])
