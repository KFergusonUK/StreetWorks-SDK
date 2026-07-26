"""Servei Català de Trànsit (SCT, Catalonia) -> streetworks.common converter.

One ``Works`` per real incident, one ``WorksSite`` each - the source
states no grouping/phase key. ``territory="Spain"``,
``administrative_area="Servei Català de Trànsit"`` - the authority is the
data-owning operator, the same rule already applied to DGT/National
Highways/Consell de Mallorca, not something the caller states.

**No proposed/actual dates are populated - deliberately, not an
oversight.** See :mod:`streetworks.sct.models`'s own docstring: this feed
states exactly one timestamp per record (``data``), which reads as "when
this record was last reported," not a works schedule - there is no
start/end validity window anywhere in the real data, confirmed live. Since
nothing here states a genuine start or end, ``date_confidence`` is always
``UNKNOWN`` and ``proposed_start``/``proposed_end``/``actual_start``/
``actual_end`` all stay ``None`` - never inferring a start date from a
report timestamp, which would misrepresent when the record was last
observed as when the works began. ``data`` itself is preserved on
``.raw``, not lost.

``works_type`` is ``causa`` (the specific free-text cause, e.g. "Treballs
de manteniment", "Senyalització vertical") when stated, falling back to
``descripcio_tipus`` (always ``"Obres"`` for anything reaching this
converter via :meth:`~streetworks.sct.SCTClient.iter_roadworks`) - ``causa``
is the finer, more informative classification the source actually states,
the same "prefer the specific field" choice already made for DGT's
``road_maintenance_type`` over its bare ``record_type``.
"""

from __future__ import annotations

from ..sct.models import Incident
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_sct"]


def _location_description(incident: Incident) -> str | None:
    if not incident.carretera:
        return None
    if incident.pk_inici is not None and incident.pk_fi is not None:
        return f"{incident.carretera} (km {incident.pk_inici}-{incident.pk_fi})"
    return incident.carretera


def _to_works(incident: Incident) -> Works:
    coordinate = (
        Coordinate(value=incident.point, crs="EPSG:4326") if incident.point else None
    )
    works_type = incident.causa or incident.descripcio_tipus

    site = WorksSite(
        reference=incident.identificador,
        works_type=works_type,
        location_description=_location_description(incident),
        coordinate=coordinate,
        date_confidence=DateConfidence.UNKNOWN,
        traffic_management=incident.descripcio,
        source_grade=SourceGrade.OPERATOR,
        raw=incident,
    )
    return Works(
        reference=incident.identificador,
        coordinate=coordinate,
        territory="Spain",
        administrative_area="Servei Català de Trànsit",
        source_grade=SourceGrade.OPERATOR,
        sites=(site,),
        raw=incident,
    )


def from_sct(incidents: list[Incident]) -> list[Works]:
    """Convert :class:`~streetworks.sct.models.Incident` records (from
    :meth:`~streetworks.sct.SCTClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - one per incident, each with a
    single ``WorksSite``. See module docstring for why no dates are
    populated."""
    return [_to_works(incident) for incident in incidents]
