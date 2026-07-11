"""SRWR -> streetworks.common converter.

SRWR has no existing join between Phase (007, what/where/status) and
Undertaker-Phase (008, dates/traffic management) - :class:`~streetworks.srwr.reader.Activity`
only exposes flat ``.phases``/``.undertaker_phases``/``.notices`` lists. This
module adds that join, on ``phase_number``, to build one
:class:`~streetworks.common.WorksSite` per phase; matching Notice (006)
records (also keyed by ``phase_number``) are attached to
``WorksSite.notices``.

``administrative_area`` (the notified roads authority - SRWR's district
system) needs district *names*, not just the ``notifiable_district_id`` int
on the 001 Activity record - and District (099) records are explicitly
excluded from :func:`~streetworks.srwr.iter_activities`'s bundles (they're
file-section reference data, not activity data), so they can't be read off
``activity`` alone. Pass a ``district_id -> name`` mapping (built with
``iter_records(source, record_types=["099"])``) via ``districts``; without
one, the bare district ID is used - still genuinely provider-stated, just
undecoded, rather than left empty.
"""

from __future__ import annotations

from datetime import datetime

from ..srwr.codes import describe
from ..srwr.reader import Activity
from ..srwr.records import Record
from .models import DateConfidence, Notice, SourceGrade, Works, WorksSite

__all__ = ["from_srwr"]


def _date_confidence(
    actual_start: datetime | None, proposed_start: datetime | None
) -> DateConfidence:
    if actual_start is not None:
        return DateConfidence.VERIFIED
    if proposed_start is not None:
        return DateConfidence.ESTIMATED
    return DateConfidence.UNKNOWN


def _notice(record: Record) -> Notice:
    return Notice(
        notice_type=describe("notice_type", getattr(record, "notice_type", None)),
        text=getattr(record, "notice_text", None),
        date=getattr(record, "created", None),
        raw=record,
    )


def from_srwr(activity: Activity, *, districts: dict[int, str] | None = None) -> Works:
    """Convert one SRWR :class:`~streetworks.srwr.reader.Activity` bundle
    into a :class:`~streetworks.common.Works`. ``districts`` optionally maps
    ``notifiable_district_id -> district_description`` (see module
    docstring) to decode ``administrative_area`` to a name; omit it to get
    the bare district ID instead."""
    header = activity.activity
    notifiable_district_id = getattr(header, "notifiable_district_id", None)
    if notifiable_district_id is None:
        administrative_area = None
    elif districts and notifiable_district_id in districts:
        administrative_area = districts[notifiable_district_id]
    else:
        administrative_area = str(notifiable_district_id)
    undertaker_phases = {
        up.phase_number: up
        for up in activity.undertaker_phases
        if up.phase_number is not None
    }
    notices_by_phase: dict[int, list[Record]] = {}
    for notice in activity.notices:
        notices_by_phase.setdefault(notice.phase_number, []).append(notice)

    sites = []
    for phase in activity.phases:
        undertaker = undertaker_phases.get(phase.phase_number)
        proposed_start = getattr(undertaker, "proposed_start", None)
        proposed_end = getattr(undertaker, "estimated_end_proposed", None)
        actual_start = getattr(undertaker, "actual_start", None)
        actual_end = getattr(undertaker, "actual_end", None)
        site_notices = tuple(
            _notice(n) for n in notices_by_phase.get(phase.phase_number, [])
        )
        sites.append(
            WorksSite(
                reference=(
                    f"{activity.activity_id}-{phase.phase_number}"
                    if phase.phase_number is not None
                    else str(activity.activity_id)
                ),
                works_type=describe("works_type", getattr(phase, "works_type", None)),
                status=describe("activity_status", getattr(phase, "activity_status", None)),
                location_description=getattr(phase, "location", None),
                proposed_start=proposed_start,
                proposed_end=proposed_end,
                actual_start=actual_start,
                actual_end=actual_end,
                date_confidence=_date_confidence(actual_start, proposed_start),
                traffic_management=describe(
                    "traffic_management_type",
                    getattr(undertaker, "traffic_management_type", None),
                ),
                notices=site_notices,
                source_grade=SourceGrade.REGISTER,
                raw=(phase, undertaker) if undertaker is not None else (phase,),
            )
        )

    return Works(
        reference=getattr(header, "activity_reference", None),
        location_usrn=(
            str(header.usrn) if header is not None and header.usrn is not None else None
        ),
        territory="Scotland",
        administrative_area=administrative_area,
        source_grade=SourceGrade.REGISTER,
        sites=tuple(sites),
        raw=activity,
    )
