"""DATEX II -> streetworks.common converter.

Serves all three DATEX adapters unchanged - NDW (Netherlands, XML),
National Highways (England SRN, JSON), and Digitraffic (Finland, its own
Simple-JSON - see :mod:`streetworks.datex2.digitraffic` for why it still
produces this same model despite not being DATEX-shaped itself) all
normalise onto the same
:class:`~streetworks.datex2.Situation`/:class:`~streetworks.datex2.SituationRecord`
models, so one converter covers all of them; ``source_grade`` is always
:attr:`~streetworks.common.SourceGrade.OPERATOR` for DATEX per the spec's
provider table.

One :class:`~streetworks.common.WorksSite` per roadworks record
(``situation.roadworks`` - ``MaintenanceWorks``/``ConstructionWorks``); the
non-works measure records (lane closures, reroutings, speed limits...) are
deliberately left out of the common model, per spec - they're traffic-
management consequences, not works sites, and stay reachable natively via
``situation.measures``.

``territory``/``administrative_area`` can't be derived from a ``Situation``
alone - none of the three adapters' Situations state their own country, and
National Highways'/Digitraffic's ``source_name`` values aren't authority
names - so the caller states them explicitly rather than the converter
guessing which adapter produced the Situation:

- NDW: ``from_datex2(situation, territory="Netherlands")`` -
  ``administrative_area`` defaults to ``source_name`` (e.g.
  ``"Provincie Limburg"``), which is genuinely a province name there.
- National Highways: ``from_datex2(situation, territory="England",
  administrative_area="National Highways")`` - the operator IS the
  data-owning authority, so it's passed explicitly rather than trusting
  ``source_name`` (which is just the generic label ``"roadworks"``).
- Digitraffic (Finland): ``from_datex2(situation, territory="Finland",
  administrative_area=streetworks.datex2.digitraffic.provinces(payload).get(situation.id))`` -
  ``source_name`` there is a Fintraffic traffic-centre name, not a
  province, so relying on the default would be wrong; ``date_confidence``
  will come out ``UNKNOWN`` for every Finland site, honestly - Digitraffic
  has no active/planned/suspended-equivalent field for ``validity.status``
  to carry.
"""

from __future__ import annotations

from datetime import datetime

from ..datex2.models import Situation, SituationRecord
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_datex2"]

#: validityStatus values that describe a real, already-committed occurrence
#: (genuine validity dates, not indicative ones) - confirmed against the
#: real National Highways fixture, which carries all three observed values.
#: "suspended" means temporarily paused, not that the dates are estimates,
#: so it's named here rather than falling through an unlabelled else.
_VERIFIED_STATUSES = frozenset({"active", "suspended"})
_ESTIMATED_STATUSES = frozenset({"planned"})


def _date_confidence(status: str | None) -> DateConfidence:
    if status in _VERIFIED_STATUSES:
        return DateConfidence.VERIFIED
    if status in _ESTIMATED_STATUSES:
        return DateConfidence.ESTIMATED
    return DateConfidence.UNKNOWN


def _location_description(record: SituationRecord) -> str | None:
    parts = [record.location.road_number, record.location.carriageway]
    text = ", ".join(p for p in parts if p)
    return text or None


def _to_site(record: SituationRecord) -> WorksSite:
    status = record.validity.status
    confidence = _date_confidence(status)
    overall_start = record.validity.overall_start
    overall_end = record.validity.overall_end
    point = record.location.point
    # A "verified" status confirms the site has genuinely started; the end
    # is still just the validity window's expectation either way, so only
    # actual_start (never actual_end) is inferred from it.
    actual_start: datetime | None = (
        overall_start if confidence is DateConfidence.VERIFIED else None
    )
    works_type = (
        record.road_maintenance_type or record.construction_work_type or record.record_type
    )

    return WorksSite(
        reference=record.id,
        works_type=works_type,
        status=status,
        location_description=_location_description(record),
        coordinate=Coordinate(value=point, crs="EPSG:4326") if point is not None else None,
        proposed_start=overall_start,
        proposed_end=overall_end,
        actual_start=actual_start,
        date_confidence=confidence,
        traffic_management=", ".join(record.comments) or None,
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_datex2(
    situation: Situation,
    *,
    territory: str | None = None,
    administrative_area: str | None = None,
) -> Works:
    """Convert one DATEX II :class:`~streetworks.datex2.Situation` (from
    either the NDW or National Highways adapter) into a
    :class:`~streetworks.common.Works`. See module docstring for
    ``territory``/``administrative_area`` - they can't be derived from the
    Situation alone, so pass them explicitly."""
    roadworks = situation.roadworks
    first = roadworks[0] if roadworks else None
    return Works(
        reference=situation.id,
        promoter=first.source_name if first else None,
        coordinate=Coordinate(value=first.location.point, crs="EPSG:4326")
        if first is not None and first.location.point is not None
        else None,
        territory=territory,
        administrative_area=(
            administrative_area
            if administrative_area is not None
            else (first.source_name if first else None)
        ),
        source_grade=SourceGrade.OPERATOR,
        sites=tuple(_to_site(record) for record in roadworks),
        raw=situation,
    )
