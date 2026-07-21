"""Geoplace DataVIA -> streetworks.common gazetteer converter.

DataVIA has no typed native model (raw GeoJSON `dict` pass-through, see
:mod:`streetworks.datavia.client`), so this converter takes a single GeoJSON
``Feature`` dict from either of the two real, ``DescribeFeatureType``-confirmed
layers this SDK's fixtures cover, and dispatches on which fields are
present: ``"usrn"`` (no ``"esuid"``) is a ``StreetLines`` record ->
:class:`~streetworks.common.gazetteer.Street`; ``"esuid"`` is an
``ESUStreets`` record -> :class:`~streetworks.common.gazetteer.Segment`.
The two schemas are disjoint by construction (confirmed live via
``DescribeFeatureType``), so this is a safe dispatch, not a guess.

``crs`` defaults to the exact URN DataVIA's own WFS response states
(``"urn:ogc:def:crs:OGC:1.3:CRS84"`` - confirmed on every real response
captured this session) rather than silently relabelling to ``"EPSG:4326"``;
override it if you queried with a different ``srsName``.

**A real, load-bearing finding this converter encodes rather than hides**:
``ESUStreets`` carries *no name field at all* - confirmed via the real
schema - so ``Segment.names`` is always empty for DataVIA, and a real named
sub-part of a street sharing a USRN (e.g. "Anchorage Terrace", a real local
name for part of Church Street, USRN 11713561) is not recoverable from this
source at any level. Investigated live, not assumed - see
``docs/gazetteer-field-dump.md``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .gazetteer import GeometryGrade, Name, Segment, Street, StreetType
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_datavia"]

_CRS84 = "urn:ogc:def:crs:OGC:1.3:CRS84"


def _date(value: str | None) -> date | None:
    """DataVIA's own date fields are ``"YYYY/MM/DD HH:MM:SS"`` strings -
    confirmed on every real ``street_start_date``/``record_entry_date``/
    ``last_update_date`` value captured this session."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y/%m/%d %H:%M:%S").date()
    except ValueError:
        return None


def _ids(value: str | None) -> tuple[str, ...]:
    """DataVIA states multi-valued references as a semicolon-delimited
    string (``esuids`` on ``StreetLines``, ``usrns`` on ``ESUStreets``) -
    never a real JSON array. Deduplicated, order preserved: a real
    ``usrns`` value observed live repeats each id twice
    (``"11713562;11713561;11713562;11713561"``) with no second distinct
    fact encoded in the repeat."""
    if not value:
        return ()
    seen: dict[str, None] = {}
    for part in value.split(";"):
        part = part.strip()
        if part:
            seen.setdefault(part, None)
    return tuple(seen)


def _geometry(geometry: dict[str, Any] | None, *, crs: str) -> Coordinate | None:
    if not geometry:
        return None
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "LineString" and coords:
        points = tuple(tuple(c) for c in coords)
        return Coordinate(value=points[0], crs=crs, points=points if len(points) > 1 else None)
    if kind == "MultiLineString" and coords:
        parts = tuple(tuple(tuple(c) for c in line) for line in coords if line)
        if not parts:
            return None
        return Coordinate(value=parts[0][0], crs=crs, parts=parts)
    if kind == "Point" and coords:
        return Coordinate(value=tuple(coords), crs=crs)
    return None


def _street(properties: dict[str, Any], geometry: Coordinate | None) -> Street:
    names = []
    if properties.get("street_descriptor_eng"):
        names.append(Name(value=properties["street_descriptor_eng"], language="eng"))
    if properties.get("street_descriptor_cym"):
        names.append(Name(value=properties["street_descriptor_cym"], language="cym"))
    return Street(
        identifiers=(Identifier(scheme="usrn", value=str(int(properties["usrn"]))),),
        names=tuple(names),
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        segment_refs=tuple(
            Identifier(scheme="esu", value=esu) for esu in _ids(properties.get("esuids"))
        ),
        as_at=_date(properties.get("last_update_date")),
        administrative_area=properties.get("administrative_area"),
        source_grade=SourceGrade.REGISTER,
        raw=properties,
    )


def _segment(properties: dict[str, Any], geometry: Coordinate | None) -> Segment:
    if geometry is None:
        raise ValueError(
            f"ESUStreets feature esuid={properties.get('esuid')!r} has no geometry - "
            "every real ESUStreets record checked carries a LineString; this converter "
            "does not fabricate one"
        )
    road_classification = properties.get("road_classification") or None
    return Segment(
        geometry=geometry,
        identifiers=(Identifier(scheme="esu", value=str(int(properties["esuid"]))),),
        street_refs=tuple(
            Identifier(scheme="usrn", value=usrn) for usrn in _ids(properties.get("usrns"))
        ),
        street_type=StreetType(code=road_classification) if road_classification else None,
        as_at=_date(properties.get("last_update_date")),
        raw=properties,
    )


def from_datavia(feature: dict[str, Any], *, crs: str = _CRS84) -> Street | Segment:
    """Convert one real GeoJSON ``Feature`` from DataVIA's ``StreetLines``
    or ``ESUStreets`` layer into a :class:`~streetworks.common.gazetteer.Street`
    or :class:`~streetworks.common.gazetteer.Segment` respectively - see the
    module docstring for the dispatch rule."""
    properties = feature.get("properties", {})
    geometry = _geometry(feature.get("geometry"), crs=crs)
    if "esuid" in properties:
        return _segment(properties, geometry)
    return _street(properties, geometry)
