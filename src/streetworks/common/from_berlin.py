"""Berlin VIZ (merged Landesmeldestelle/Verkehrsredaktion) ->
streetworks.common converter. See
:mod:`streetworks.berlin.client`'s own module docstring for the full
investigation behind every claim below - in particular the finding that
corrects the source brief's assumption that Verkehrsredaktion is simply
a detail-enriched subset of Landesmeldestelle (live data shows real,
non-overlapping content on both sides, hence the client's own merge
logic).

**No grouping - deliberately, unlike NYC/Chicago/Paris.** Every record
this client yields (whether matched, Landesmeldestelle-only, or
Verkehrsredaktion-only) already stands alone as one worksite/closure -
there is no umbrella-application/chantier field anywhere in either real
feed. So ``from_berlin`` produces exactly one ``Works`` with exactly one
``WorksSite`` per record, the same 1:1 shape
:mod:`streetworks.ogc.germany`'s own Brandenburg entry uses (that
module's own docstring records a real grouping signal it deliberately
did *not* act on, for the same reason: no independent corroborating
field, per this project's record-identity discipline).

**``street_ref`` is never populated** - no segment/street identifier
field exists on either feed, only free-text ``street``/``section``.

**``date_confidence`` is uniformly ``ESTIMATED``, never ``VERIFIED``** -
neither feed states anything closer to "confirmed to have happened" than
a validity window; ``objectState`` (e.g. ``"modified"``) describes the
record's own edit history, not the work's.

**Two date formats, tried in order.** Verkehrsredaktion's
``validity.from``/``.to`` are near-ISO (``"2025-07-23T07:00"``, parsed by
the shared :func:`~streetworks._dt.parse_iso8601`); Landesmeldestelle's
are German ``"DD.MM.YYYY HH:MM"`` (parsed by a small private
``_parse_de_date``, the same per-source bespoke-format pattern
:mod:`streetworks.common.from_jersey` already uses for its own non-ISO
dates). A blank ``from`` (confirmed real, 130/373 real Landesmeldestelle
records at investigation time) parses to ``None`` either way.

**Geometry: the representative point, plus real line vertices when
present.** A plain ``Point`` maps straight to ``Coordinate.value``. A
``GeometryCollection`` (``Point`` + one or more real ``LineString``
entries - the affected road segment) maps its ``Point`` to
``Coordinate.value`` and its *first* ``LineString``'s vertices to
``Coordinate.points`` - exactly what ``.points`` is documented for (real
line-geometry vertices), unlike Paris's polygon-ring case which didn't
fit that contract. Multiple ``LineString`` entries have been observed
live (a real Verkehrsredaktion-only record had 2) - only the first is
used, a deliberate simplification since ``Coordinate`` supports one line
per point, not multiple.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_berlin"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Germany"
_ADMINISTRATIVE_AREA = "Land Berlin - VIZ"


def _parse_de_date(value: str) -> datetime | None:
    """Landesmeldestelle's own ``DD.MM.YYYY HH:MM`` format - not ISO-8601,
    so the shared parser can't handle it. Blank/unparseable input returns
    ``None``, never raises - source data is never guaranteed clean."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y %H:%M")
    except ValueError:
        return None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return parse_iso8601(value) or _parse_de_date(value)


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    geometry_type = geometry.get("type")
    if geometry_type == "Point":
        lon, lat = geometry["coordinates"]
        return Coordinate(value=(lat, lon), crs=_CRS)
    if geometry_type == "GeometryCollection":
        geometries = geometry.get("geometries") or []
        point = next((g for g in geometries if g.get("type") == "Point"), None)
        if point is None:
            return None
        lon, lat = point["coordinates"]
        line = next((g for g in geometries if g.get("type") == "LineString"), None)
        points = (
            tuple((c[1], c[0]) for c in line["coordinates"]) if line is not None else None
        )
        return Coordinate(value=(lat, lon), crs=_CRS, points=points)
    return None


def _location_description(properties: JSON) -> str | None:
    street = properties.get("street")
    section = properties.get("section")
    if street and section and section != street:
        return f"{street} - {section}"
    return street or section


def _to_site(record: JSON) -> WorksSite:
    properties = record["properties"]
    validity = properties.get("validity") or {}
    return WorksSite(
        reference=properties.get("id"),
        works_type=properties.get("content"),
        location_description=_location_description(properties),
        coordinate=_coordinate(record.get("geometry")),
        proposed_start=_parse_date(validity.get("from")),
        proposed_end=_parse_date(validity.get("to")),
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=properties.get("severity"),
        source_grade=SourceGrade.TRAVELLER_INFO,
        raw=record,
    )


def from_berlin(records: list[JSON]) -> list[Works]:
    """Convert real Berlin VIZ records (plain GeoJSON Feature dicts from
    :meth:`streetworks.berlin.BerlinClient.iter_landesmeldestelle`/
    ``iter_verkehrsredaktion``/``iter_roadworks``) into
    :class:`~streetworks.common.Works`. No grouping - one ``Works`` per
    record, see module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=record["properties"].get("id"),
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.TRAVELLER_INFO,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
