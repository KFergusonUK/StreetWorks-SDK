"""Dortmund (NRW) -> streetworks.common roadworks converter. See
:mod:`streetworks.dortmund.client` for the full live investigation.

**No clean street field - the same honest gap NYC/Chicago/Paris's own
permit registers already carry.** ``art_der_baumassnahme`` combines
street, works type, and restriction in one real free-text field (e.g.
``"Stiegenweg 12 - Kanalreparatur // Vollsperrung"``); per this SDK's
"never extract structured data from free text" discipline, it maps to
``works_type`` whole, never split. ``stadtbezirk`` (a real Dortmund
city district, e.g. ``"Hörde"``) maps to ``location_description`` - a
real, coarser-than-street location fact, not an endpoint-provenance
``administrative_area`` (which stays the constant ``"Dortmund"``, the
same "endpoint provenance, not a record field" discipline
:mod:`streetworks.ogc.germany`'s own state field maps already use).

**Dates are date-only, no time component** (``"2026-08-20"``) -
represented as midnight Europe/Berlin via :mod:`zoneinfo`, the same
convention this SDK's other German date-only sources already use.

**``status`` carries the real, literal source value**
(``"tagesaktuell"``/``"geplant"``) rather than being translated or
collapsed - both are genuine structured facts about the record (current
vs planned), not free text.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_dortmund"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Germany"
_ADMINISTRATIVE_AREA = "Dortmund"
_BERLIN = ZoneInfo("Europe/Berlin")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=_BERLIN)


def _coordinate(fields: JSON) -> Coordinate | None:
    point = fields.get("geografische_koordinate")
    if not point:
        return None
    lat, lon = point.get("lat"), point.get("lon")
    if lat is None or lon is None:
        return None
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def _to_site(record: JSON) -> WorksSite:
    fields = record.get("fields") or {}
    start = _parse_date(fields.get("von"))
    end = _parse_date(fields.get("bis"))
    return WorksSite(
        reference=str(record.get("id") or ""),
        works_type=fields.get("art_der_baumassnahme"),
        status=fields.get("status"),
        location_description=fields.get("stadtbezirk"),
        coordinate=_coordinate(fields),
        proposed_start=start,
        proposed_end=end,
        actual_start=start if fields.get("status") == "tagesaktuell" else None,
        date_confidence=DateConfidence.VERIFIED if start is not None else DateConfidence.UNKNOWN,
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_dortmund(records: list[JSON]) -> list[Works]:
    """Convert real Dortmund records (from
    :meth:`streetworks.dortmund.DortmundClient.iter_roadworks`) into
    :class:`~streetworks.common.Works`. One ``Works`` per record, one
    ``WorksSite`` each - no genuine grouping key exists on this feed."""
    works_list = []
    for record in records:
        fields = record.get("fields") or {}
        site = _to_site(record)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                promoter=fields.get("auftraggeber"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
