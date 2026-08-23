"""GDDKiA (Poland's national roads/motorways authority) ->
streetworks.common converter. See :mod:`streetworks.poland.client`'s
own module docstring for the full investigation.

**No grouping, ``reference`` always ``None``** - no native id field
exists anywhere in this schema (checked, confirmed absent); a composite
of ``nr_drogi``/``km``/``data_powstania`` is close to unique but not
proven so (380/383 distinct on a real live pull) - not used as a
synthetic key, the same honest choice :mod:`.from_vancouver`/
:mod:`.from_quebec` already make for their own comparable feeds.

**``works_type`` is the real ``rodzaj/poz`` code** (e.g. ``"U33"``) -
kept as the source states it, not decoded into prose (no official
published code table was found; sample values were decoded by reading
real ``objazd`` text alongside them, see the client's own module
docstring).

**``location_description`` combines the real road number and section
name** (``nr_drogi``, ``nazwa_odcinka``) - the closest thing to a
human-readable location this schema states; ``woj`` (voivodeship) is
kept on ``.raw`` only, not promoted to ``administrative_area`` (see
below).

**``traffic_management`` is the real ``objazd`` free text** - genuine,
specific description of the disruption/detour, the richest field in
this schema.

**Dates use a real non-colon UTC offset** (``"...+0200"``), rejected by
``datetime.fromisoformat`` on this SDK's minimum-supported Python 3.10 -
a colon is inserted before parsing.

**``date_confidence`` is uniformly ``ESTIMATED``** - a live,
GDDKiA-operated feed with no separate physically-confirmed/scheduled
distinction stated anywhere in the schema, the same reasoning
:mod:`.from_necompass`/:mod:`.from_brussels` already document for their
own comparable feeds.

**Real per-record restriction/traffic-management booleans and fields**
(``ruch_wahadlowy``, ``sygnalizacja_swietlna``, ``awaria_mostu``,
``ruch_2_kierunkowy``, ``droga_zamknieta``, ``ogr_predkosc``,
``ogr_szerokosc``, ``ogr_nosnosc``, ``ogr_nacisk``,
``ogr_skrajnia_pozioma``, ``ogr_skrajnia_pionowa``) are preserved on
``.raw`` only, none forced into the common model - the same discipline
Hamburg's own six independent boolean flags already establish.

**``administrative_area`` is the operator, not the real per-record
``woj`` (voivodeship) field** - GDDKiA is one national authority
regardless of region, unlike Spain's own genuinely separate
``provinces()``; ``woj`` stays on ``.raw``.

**Coordinates are real, already true lat/lon** (not swapped, unlike
Roma) - missing on 38/383 (10%) of real records, a genuine, confirmed
gap; ``coordinate=None`` rather than guessed.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_poland"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Poland"
_ADMINISTRATIVE_AREA = "Generalna Dyrekcja Dróg Krajowych i Autostrad (GDDKiA)"

_OFFSET_NO_COLON = re.compile(r"([+-]\d{2})(\d{2})$")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = _OFFSET_NO_COLON.sub(r"\1:\2", value)
    return parse_iso8601(value)


def _coordinate(record: JSON) -> Coordinate | None:
    lat, lon = record.get("geo_lat"), record.get("geo_long")
    if not lat or not lon:
        return None
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def _location_description(record: JSON) -> str | None:
    road, section = record.get("nr_drogi"), record.get("nazwa_odcinka")
    if road and section:
        return f"{road}: {section}"
    return road or section


def _to_site(record: JSON) -> WorksSite:
    return WorksSite(
        reference=None,
        works_type=record.get("rodzaj_poz"),
        location_description=_location_description(record),
        coordinate=_coordinate(record),
        proposed_start=_parse_date(record.get("data_powstania")),
        proposed_end=_parse_date(record.get("data_likwidacji")),
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=record.get("objazd"),
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_poland(records: list[JSON]) -> list[Works]:
    """Convert real GDDKiA disruption records (from
    :meth:`streetworks.poland.PolandClient.iter_roadworks`) into
    :class:`~streetworks.common.Works`. No grouping - one ``Works`` per
    record, see module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=None,
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
