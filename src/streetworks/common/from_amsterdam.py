"""Amsterdam (WIOR - Werken in de Openbare Ruimte) -> streetworks.common
converter.

**Flat 1:1 - one ``Works`` per real record, no grouping.** ``wiorNummer``
is confirmed live to be genuinely unique across a 1000-record sample (no
repeats) - unlike Oslo's own ``activity_id`` umbrella grouping or
Jersey's ``PROJID``, there is no real multi-row-per-project shape here to
collapse.

**Geometry: real ``Polygon``/``MultiPolygon`` only - genuinely no
Point/LineString rows found live.** The first ring's first vertex (of the
first polygon, for a ``MultiPolygon``) is used as ``Coordinate.value``
only - ``Coordinate.points``/``.parts`` are documented for line-geometry
vertices, not polygon rings, the same discipline ``from_oslo``/
``from_canton_zurich`` already apply to their own polygon case. The full
raw geometry is preserved in ``WorksSite.raw`` regardless. Coordinates
are real WGS84 (``EPSG:4326``, requested via a real, honoured
``Accept-Crs`` header - see :mod:`streetworks.amsterdam.client`'s own
docstring) so this SDK's ``(lat, lon)`` swap convention applies, the same
as ``from_copenhagen``.

**``hoofdstatus`` is treated as an open string, never validated against a
closed enum** - a real, live-confirmed data-quality quirk (one real
record carries ``"Yes"`` instead of a genuine Dutch status value) is kept
as-is rather than raising or silently coercing it. ``date_confidence`` is
``VERIFIED`` (and ``actual_start``/``actual_end`` populated) only when
``hoofdstatus == "Uitvoering"`` ("execution", confirmed live to be the
dominant real value, 774/1000 in a live sample) - every other value
(``"Projectaanpak"``/"Ontwerp"``/the real ``"Yes"`` anomaly) falls back
to ``ESTIMATED``, the same "only a confirmed-active status earns
VERIFIED" discipline this SDK applies everywhere else.

**``location_description`` carries the real ``projectnaam`` (project
name)** - confirmed live to usually embed real street/location context
in its own text (e.g. ``"Noordzeeweg (tussen Luvernes en Hornweg)..."``),
the closest real fit to an address field on a schema that has none.
``beschrijving`` (a free-text description of the work itself, not its
location) has no dedicated home in this model - kept `.raw`-only, never
silently dropped, the same "real field, no home" treatment Tasmania's own
``SITE_CONTACT`` gets.

**``promoter`` is never populated** - no organisation/contractor field
exists anywhere in this schema, the same real gap Kanton Zürich's own
schema has.

**``street_ref`` is never populated** - no street/segment identifier
exists, only free-text ``projectnaam``, the same discipline every other
municipal-permit converter in this SDK applies.
"""

from __future__ import annotations

from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_amsterdam"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Netherlands"
_ADMINISTRATIVE_AREA = "Gemeente Amsterdam"

#: Confirmed live: the dominant real hoofdstatus value meaning
#: work is genuinely in progress, not merely planned/designed. See
#: module docstring.
_IN_PROGRESS_STATUS = "Uitvoering"


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    coords = geometry.get("coordinates")
    kind = geometry.get("type")
    if not coords:
        return None
    if kind == "Polygon":
        ring = coords[0] if coords else None
        if not ring:
            return None
        lon, lat = ring[0]
        return Coordinate(value=(float(lat), float(lon)), crs=_CRS)
    if kind == "MultiPolygon":
        first_polygon = coords[0] if coords else None
        ring = first_polygon[0] if first_polygon else None
        if not ring:
            return None
        lon, lat = ring[0]
        return Coordinate(value=(float(lat), float(lon)), crs=_CRS)
    return None


def _to_works(record: JSON) -> Works:
    hoofdstatus = record.get("hoofdstatus")
    in_progress = hoofdstatus == _IN_PROGRESS_STATUS
    start = parse_iso8601(record.get("datumStartUitvoering"))
    end = parse_iso8601(record.get("datumEindeUitvoering"))
    coordinate = _coordinate(record.get("geometrie"))

    site = WorksSite(
        reference=record.get("wiorNummer"),
        works_type=record.get("typeWerkzaamheden"),
        status=hoofdstatus,
        location_description=record.get("projectnaam"),
        coordinate=coordinate,
        proposed_start=start,
        proposed_end=end,
        actual_start=start if in_progress else None,
        actual_end=end if in_progress else None,
        date_confidence=DateConfidence.VERIFIED if in_progress else DateConfidence.ESTIMATED,
        source_grade=SourceGrade.REGISTER,
        raw=record,
    )

    return Works(
        reference=record.get("wiorNummer"),
        coordinate=coordinate,
        territory=_TERRITORY,
        administrative_area=_ADMINISTRATIVE_AREA,
        source_grade=SourceGrade.REGISTER,
        sites=(site,),
        raw=record,
    )


def from_amsterdam(records: list[JSON]) -> list[Works]:
    """Convert real Amsterdam WIOR records (from
    :meth:`streetworks.amsterdam.AmsterdamClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - one per record, no grouping (see
    module docstring)."""
    return [_to_works(record) for record in records]
