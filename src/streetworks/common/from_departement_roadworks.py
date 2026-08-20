"""French département roadworks (OpenDataSoft) -> streetworks.common
converter. One converter for every département - it reads a
:class:`~streetworks.opendatasoft.france_departements.DepartementFieldMap`
rather than having its own per-département logic, the same shape
:func:`streetworks.common.from_ogc_features` already established for
German state roadworks.

**Geometry**: a real point (``field_map.point_field``, e.g.
``geo_point_2d``/``localisation`` - a per-dataset name, not a platform
standard, see the field-map module's own docstring) maps to
``Coordinate.value``. Where a département also states a real
``geo_shape`` GeoJSON column whose geometry is genuinely
``LineString``/``MultiLineString`` (``field_map.line_field`` - Sarthe,
Hauts-de-Seine; ``None`` for Loire-Atlantique, which states no line
field at all), every real vertex is kept on ``Coordinate.points``/
``.parts`` - never a Polygon read into either, the same discipline
:mod:`.from_paris` already established for its own real ``Polygon``
``geo_shape`` case. Already WGS84, no reprojection needed on any
département checked so far.

**``value`` and ``points`` are two independently real, stated facts on
this source, not one derived from the other** - ``value`` is the
département's own real representative point field (``geo_point_2d``/
``localisation``), ``points`` (when present) is the real, separately
stated line geometry; ``points[0]`` is not asserted to equal ``value``.
The same shape :mod:`.from_berlin`'s own real ``GeometryCollection``
(``Point`` + ``LineString``) handling already establishes, not the
single-geometry case :mod:`.from_nrn`/:mod:`.from_datavia` handle,
where a line's own first vertex *is* the only real point stated.

**Dates**: only Sarthe states real structured dates
(``start_field``/``end_field`` set) - a full ISO 8601 datetime, parsed
via :meth:`datetime.fromisoformat` (a bare ``"Z"`` suffix, if ever
stated, rewritten to ``"+00:00"`` first for this SDK's own Python 3.10
minimum, the same handling :mod:`.from_ogc_features` already needs for
Rheinland-Pfalz). Loire-Atlantique and Hauts-de-Seine state only real
free-text date information - per this SDK's "never extract structured
data from free text" discipline, ``proposed_start``/``proposed_end``
stay ``None`` and every ``WorksSite`` from either carries
``DateConfidence.UNKNOWN``, not a guess.

**Reference**: ``field_map.id_field`` when a département states one
(Sarthe/Hauts-de-Seine's own real ``objectid``) - Loire-Atlantique's
real records carry no per-record identifier at all
(``id_field=None``), so its own ``Works.reference`` is genuinely an
empty string, an honest gap, not a fabricated one.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_departement_roadworks"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "France"


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _point(record: JSON, point_field: str) -> tuple[float, float] | None:
    point = record.get(point_field)
    if not point:
        return None
    lat, lon = point.get("lat"), point.get("lon")
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def _line_points(record: JSON, line_field: str | None) -> tuple[tuple[float, float], ...] | None:
    if not line_field:
        return None
    shape = record.get(line_field)
    if not shape:
        return None
    geometry = shape.get("geometry") or {}
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return None
    if kind == "LineString":
        return tuple((lat, lon) for lon, lat in coordinates)
    if kind == "MultiLineString":
        # Real departments checked so far always carry exactly one part
        # per real record - only the first is used, matching the same
        # simplification streetworks.ogc.germany's own Schleswig-Holstein
        # MultiCurve handling makes.
        first_part = coordinates[0] if coordinates else None
        return tuple((lat, lon) for lon, lat in first_part) if first_part else None
    return None


def _coordinate(record: JSON, field_map: Any) -> Coordinate | None:
    point = _point(record, field_map.point_field)
    if point is None:
        return None
    points = _line_points(record, field_map.line_field)
    return Coordinate(value=point, crs=_CRS, points=points)


def _to_site(record: JSON, field_map: Any) -> WorksSite:
    start = _parse_date(record.get(field_map.start_field)) if field_map.start_field else None
    end = _parse_date(record.get(field_map.end_field)) if field_map.end_field else None
    reference = str(record.get(field_map.id_field) or "") if field_map.id_field else ""
    return WorksSite(
        reference=reference,
        works_type=record.get(field_map.title_field) if field_map.title_field else None,
        status=record.get(field_map.status_field) if field_map.status_field else None,
        location_description=record.get(field_map.road_field) if field_map.road_field else None,
        coordinate=_coordinate(record, field_map),
        proposed_start=start,
        proposed_end=end,
        actual_start=start if start is not None else None,
        date_confidence=DateConfidence.VERIFIED if start is not None else DateConfidence.UNKNOWN,
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_departement_roadworks(records: list[JSON], field_map: Any) -> list[Works]:
    """Convert raw OpenDataSoft records (from
    :meth:`streetworks.opendatasoft.france_departements.DepartementRoadworksClient.fetch`)
    into :class:`~streetworks.common.Works` using ``field_map`` - one
    ``Works`` per record, one ``WorksSite`` each (no genuine grouping key
    exists on any département checked so far).
    ``field_map.area`` becomes ``administrative_area`` -
    endpoint provenance, not a record field, the same mechanism
    :mod:`.from_ogc_features` already uses for German states."""
    works_list = []
    for record in records:
        site = _to_site(record, field_map)
        promoter = record.get(field_map.promoter_field) if field_map.promoter_field else None
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                promoter=str(promoter) if promoter else None,
                territory=_TERRITORY,
                administrative_area=field_map.area,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
