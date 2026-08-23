"""CNAIR (Romania) -> streetworks.common converter. See
:mod:`streetworks.romania.client`'s own module docstring for the full
investigation, including the real HTML-scraping caveat this source
carries.

**``works_type`` comes from the real section title the record was
collected from** - ``"Lucrări de scurtă durată"`` (short-duration
works) or ``"Reabilitare, modernizare, întreținere și reparații"``
(rehabilitation/modernization/maintenance/repair works) - a real,
source-declared two-value discriminator, not decoded from free text.

**``traffic_management`` prefers the real ``"CAUZA"`` field, falling
back to ``"LUCRĂRI"``** - the two sections use different real column
names for the same descriptive role (cause vs. work description); the
paired ``"MASURI DE REMEDIERE"``/``"VARIANTE DE OCOLIRE"`` field is
kept on ``.raw`` only, not combined into one string.

**No coordinates anywhere in this schema** - a genuine, confirmed gap,
not a parsing failure; ``coordinate`` is always ``None``.

**``reference`` is always ``None``** - the real ``"NR. CRT."`` field
(e.g. ``"6.15"``) is a positional row number, renumbered on every
re-render, not a stable id.

**Dates are real ``"YYYY-MM-DD HH:MM:SS"`` strings, no timezone
stated** - parsed naive, the same discipline
:mod:`.from_necompass`/:mod:`.from_brussels` already document.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_romania"]

JSON = dict[str, Any]

_TERRITORY = "Romania"
_ADMINISTRATIVE_AREA = (
    "Compania Națională de Administrare a Infrastructurii Rutiere (CNAIR)"
)

#: Real section title -> a short, human works_type - see module docstring.
_WORKS_TYPES = {
    "1.1. Lucrări de scurtă durată:": "Lucrări de scurtă durată",
    (
        "6. Drumuri naționale, drumuri expres și autostrăzi pe care se "
        "efectueaza lucrări de reabilitare, modernizări, întretinere și "
        "reparații:"
    ): "Reabilitare, modernizare, întreținere și reparații",
}


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return parse_iso8601(value.replace(" ", "T"))


def _location_description(record: JSON) -> str | None:
    road = record.get("INDICATIV DRUM")
    localities = record.get("ÎNTRE LOCALITĂȚILE")
    if road and localities:
        return f"{road}: {localities}"
    return road or localities


def _to_site(record: JSON) -> WorksSite:
    return WorksSite(
        reference=None,
        works_type=_WORKS_TYPES.get(record.get("section", "")),
        location_description=_location_description(record),
        coordinate=None,
        proposed_start=_parse_date(record.get("DE LA DATA")),
        proposed_end=_parse_date(record.get("PÂNĂ LA DATA")),
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=record.get("CAUZA") or record.get("LUCRĂRI"),
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_romania(records: list[JSON]) -> list[Works]:
    """Convert real CNAIR dispatch-board records (from
    :meth:`streetworks.romania.RomaniaClient.iter_roadworks`) into
    :class:`~streetworks.common.Works`. No grouping - one ``Works`` per
    record, see module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=None,
                coordinate=None,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
