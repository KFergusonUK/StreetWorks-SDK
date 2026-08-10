"""Roma ("Roma si trasforma") -> streetworks.common converter. See
:mod:`streetworks.roma.client`'s own module docstring for the full
investigation - in particular why the real source isn't the one the
investigation brief named, and the real coordinate-field bug this
converter corrects rather than reproduces.

**No grouping** - each intervention already stands alone; ``nid`` is
already a stable per-record reference, and there's no umbrella/case
field grouping several records together.

**Coordinates: the source's own ``lon``/``lat`` field names are
swapped relative to true geography - corrected here, not reproduced.**
Every real coordinate checked live has its ``"lon"`` value in Rome's
real *latitude* band (~41.7-42.1) and its ``"lat"`` value in Rome's real
*longitude* band (~12.2-12.8). This function reads them into their
correct meaning rather than trusting the source's own key names -
deliberate, not an accidental swap-back-to-a-swap.

**No dates - deliberately, not an oversight.** No date field of any
kind exists in this schema; ``field_stato_lavori`` is a closed
project-lifecycle *category* (``Progettazione`` → ``Gara`` → ``Cantiere``
→ ``Fine lavori``), not a calendar value. ``date_confidence`` is always
``UNKNOWN`` and ``proposed_start``/``proposed_end`` are always ``None`` -
never inferred from the lifecycle stage, which would misrepresent a
category as a date, the same discipline already applied to SCT's
report-timestamp-only feed.

**``street_ref`` is never populated** - no street/segment identifier
exists anywhere in the schema, only free-text ``field_indirizzo``.
"""

from __future__ import annotations

from typing import Any

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_roma"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Italy"
_ADMINISTRATIVE_AREA = "Roma Capitale"


def _coordinate(record: JSON) -> Coordinate | None:
    position = record.get("field_posizione")
    if not position:
        return None
    # The source's own "lon"/"lat" keys are swapped relative to true
    # geography - see module docstring. true_lat comes from the
    # source's "lon" key, true_lon from its "lat" key, deliberately.
    true_lat = position.get("lon")
    true_lon = position.get("lat")
    if true_lat is None or true_lon is None:
        return None
    return Coordinate(value=(true_lat, true_lon), crs=_CRS)


def _location_description(record: JSON) -> str | None:
    title = record.get("title")
    address = record.get("field_indirizzo")
    if title and address and address not in title:
        return f"{title} ({address})"
    return title or address


def _to_site(record: JSON) -> WorksSite:
    tags = record.get("field_tag_temi") or []
    return WorksSite(
        reference=str(record.get("nid")) if record.get("nid") is not None else None,
        works_type=", ".join(tags) or None,
        location_description=_location_description(record),
        coordinate=_coordinate(record),
        date_confidence=DateConfidence.UNKNOWN,
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_roma(records: list[JSON]) -> list[Works]:
    """Convert real "Roma si trasforma" record dicts (from
    :meth:`streetworks.roma.RomaClient.iter_interventi`/
    ``iter_roadworks``) into :class:`~streetworks.common.Works`. No
    grouping - one ``Works`` per record, see module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
