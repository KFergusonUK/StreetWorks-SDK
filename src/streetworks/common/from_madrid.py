"""Madrid INFORMO ("Tráfico. Incidencias en vía pública") ->
streetworks.common converter. See
:mod:`streetworks.madrid.client`'s own module docstring for the full
investigation behind every claim below - in particular the corrected
live URL, the ``es_obras`` filter (settling two questions the source
brief left open), and the live wire date format the portal's own PDF
documentation doesn't match.

**No grouping** - each ``Incidencia`` already stands alone; there is no
umbrella/application field anywhere in the schema, the same shape
:func:`~streetworks.common.from_berlin` found for VIZ. One ``Works`` with
exactly one ``WorksSite`` per record.

**``reference`` is ``id_incidencia``, not ``codigo``.** ``codigo`` (the
documented "año/número" field, e.g. ``"2026/894"``) is unique on 212/217
real records checked live, but 6 genuinely share the literal placeholder
value ``"2025/0"`` - a real data-quality gap in the source, not a fixture
artefact. ``id_incidencia`` is unique on all 217.

**``date_confidence`` is uniformly ``ESTIMATED``, never ``VERIFIED``.**
``incid_estado`` (``1`` "activa" / ``4`` "en espera") describes the
record's own status in Madrid's incident-management system, not
independent confirmation that work is physically happening on the
ground - the same distinction :func:`~streetworks.common.from_berlin`
draws for VIZ's ``objectState``. ``fh_inicio``/``fh_final`` are the only
date signal, so every site reads as an estimated window, never
confirmed.

**Two date formats tried, in order** - the shared
:func:`~streetworks._dt.parse_iso8601` first (in case the source ever
reverts to the documented ``+dd:00``-offset format), then
``_parse_madrid_date`` for the real live wire format actually seen on
every one of 217 records checked (no offset, seven fractional-second
digits - more than ``%f``'s six, so truncated rather than left to raise).

**Coordinates: the geographic pair, labelled EPSG:4258 (ETRS89), not
EPSG:4326 (WGS84).** The source states its UTM pair
(``utm_x``/``utm_y``) is EPSG:25830 (ETRS89 / UTM Zone 30N) explicitly;
``longitud``/``latitud`` come from the same reference frame. Relabelling
that WGS84 would be exactly the silent-reprojection-by-assumption this
SDK's data-integrity discipline rules out - see
:mod:`streetworks.ogc.mallorca`'s and :mod:`streetworks.arcgis.jersey`'s
own CRS notes for the same standing policy applied to other native-ETRS89
sources.

**``street_ref`` is never populated** - no street/segment identifier
field exists anywhere in the schema, only the free-text ``descripcion``
(which is also the richest location signal available, so it becomes
``location_description`` directly rather than being dropped in favour of
a thinner field).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_madrid"]

JSON = dict[str, Any]

_CRS = "EPSG:4258"
_TERRITORY = "Spain"
_ADMINISTRATIVE_AREA = "Ayuntamiento de Madrid"


def _parse_madrid_date(value: str) -> datetime | None:
    """Real live wire format (confirmed on all 217 records checked live) -
    no UTC offset, seven fractional-second digits, not the six ``%f``
    accepts, and not the portal's own (stale) documented ``+dd:00``-offset
    format. See module docstring."""
    base, sep, frac = value.partition(".")
    if not sep:
        return None
    try:
        return datetime.strptime(f"{base}.{frac[:6]}", "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        return None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return parse_iso8601(value) or _parse_madrid_date(value)


def _coordinate(record: JSON) -> Coordinate | None:
    longitud, latitud = record.get("longitud"), record.get("latitud")
    if not longitud or not latitud:
        return None
    try:
        return Coordinate(value=(float(latitud), float(longitud)), crs=_CRS)
    except ValueError:
        return None


def _to_site(record: JSON) -> WorksSite:
    return WorksSite(
        reference=record.get("id_incidencia"),
        works_type=record.get("nom_tipo_incidencia"),
        location_description=record.get("descripcion"),
        coordinate=_coordinate(record),
        proposed_start=_parse_date(record.get("fh_inicio")),
        proposed_end=_parse_date(record.get("fh_final")),
        date_confidence=DateConfidence.ESTIMATED,
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_madrid(records: list[JSON]) -> list[Works]:
    """Convert real Madrid INFORMO records (plain dicts from
    :meth:`streetworks.madrid.MadridClient.iter_incidencias`/
    ``iter_roadworks``) into :class:`~streetworks.common.Works`. No
    grouping - one ``Works`` per record, see module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=record.get("id_incidencia"),
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
