"""LINZ (Toitū Te Whenua, New Zealand) -> streetworks.common gazetteer
converter. This SDK's first New Zealand gazetteer coverage.

Three real, related layers, three canonical types - ``from_linz_address``
(NZ Addresses, 123113) -> :class:`~streetworks.common.gazetteer.Address`,
``from_linz_road`` (NZ Addresses: Roads, 123110, aggregated centrelines)
-> :class:`~streetworks.common.gazetteer.Street`, ``from_linz_road_section``
(NZ Addresses: Road Sections, 123109, individual geometries) ->
:class:`~streetworks.common.gazetteer.Segment`. Three separate functions,
not one dispatching on type the way :func:`~streetworks.common.from_nvdb.from_nvdb`
does - LINZ's native shape is plain GeoJSON feature dicts (see
:mod:`streetworks.linz.client`), not distinct Python types to dispatch on.

**``road_id`` is the real, shared join key across all three** - carried
as ``street_links``/``identifiers``/``street_refs`` respectively. See
:mod:`streetworks.linz.client`'s own module docstring for the honest
caveat: the field name is confirmed identical across all three layers'
schemas, but whether the *values* genuinely cross-reference has not been
verified against a real WFS response (Roads/Road Sections need a real LDS
key this build doesn't have).

**A real gap this model's own docstring already anticipated**: LINZ
states a genuine ``unit``/flat concept (e.g. ``"2"`` in ``"2/49 Pigeon
Mountain Road"``) that :class:`~streetworks.common.gazetteer.Address`
itself documents as "no built source has" - confirmed live, 50/500 real
addresses in one pull. There is still no canonical field for it, so it
stays on ``.raw`` only; ``housenumber``/``suffix`` come from the real,
separately-decomposed ``address_number``/``address_number_suffix``
fields, not the composite ``full_address_number`` string.

**Geometry axis order**: this SDK's standing convention for
``EPSG:4326`` - ``(lat, lon)``, matching every DATEX/German-state OGC
provider (see :mod:`streetworks.common.from_ogc_features`) - applied here
too, via the same flip-on-4326 rule.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import Address, GeometryGrade, Name, Segment, Street, StreetType
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_linz_address", "from_linz_road", "from_linz_road_section"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "New Zealand"


def _point(geometry: JSON | None) -> Coordinate | None:
    if not geometry or (geometry.get("type") or "").upper() != "POINT":
        return None
    coords = geometry.get("coordinates")
    if not coords:
        return None
    lon, lat = float(coords[0]), float(coords[1])
    return Coordinate(value=(lat, lon), crs=_CRS)


def _line(geometry: JSON | None) -> Coordinate | None:
    """``LineString``/``MultiLineString`` - the latter genuinely possible
    for the aggregated Roads layer (the source's own documentation notes
    some centrelines are made of disjoint parts sharing one name). Never
    tested against a real response - see :mod:`streetworks.linz.client`."""
    if not geometry:
        return None
    kind = (geometry.get("type") or "").upper()
    coords = geometry.get("coordinates")
    if not coords:
        return None
    if kind == "LINESTRING":
        points = tuple((float(lat), float(lon)) for lon, lat in coords)
        if not points:
            return None
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
    if kind == "MULTILINESTRING":
        parts = tuple(
            tuple((float(lat), float(lon)) for lon, lat in part) for part in coords if part
        )
        if not parts:
            return None
        return Coordinate(value=parts[0][0], crs=_CRS, parts=parts)
    return None


def from_linz_address(feature: JSON) -> Address:
    """Convert one real NZ Addresses (123113) feature into a
    :class:`~streetworks.common.gazetteer.Address`."""
    properties = feature.get("properties") or {}
    address_id = properties.get("address_id")
    road_id = properties.get("road_id")
    address_number = properties.get("address_number")
    geometry = _point(feature.get("geometry"))
    if geometry is None:
        raise ValueError("Address has no geometry to convert")
    return Address(
        geometry=geometry,
        identifiers=(
            (Identifier(scheme="address_id", value=str(address_id)),) if address_id else ()
        ),
        housenumber=str(address_number) if address_number is not None else None,
        suffix=properties.get("address_number_suffix") or None,
        street_name=properties.get("full_road_name"),
        street_links=(
            (Identifier(scheme="road_id", value=str(road_id)),) if road_id is not None else ()
        ),
        territory=_TERRITORY,
        administrative_area=properties.get("territorial_authority"),
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )


def from_linz_road(feature: JSON) -> Street:
    """Convert one real NZ Addresses: Roads (123110) feature - an
    aggregated centreline - into a
    :class:`~streetworks.common.gazetteer.Street`."""
    properties = feature.get("properties") or {}
    road_id = properties.get("road_id")
    full_name = properties.get("full_road_name")
    geometry = _line(feature.get("geometry"))
    return Street(
        identifiers=(
            (Identifier(scheme="road_id", value=str(road_id)),) if road_id is not None else ()
        ),
        names=(Name(value=full_name),) if full_name else (),
        street_type=(
            StreetType(label=properties.get("road_name_type"))
            if properties.get("road_name_type")
            else None
        ),
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        territory=_TERRITORY,
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )


def from_linz_road_section(feature: JSON) -> Segment:
    """Convert one real NZ Addresses: Road Sections (123109) feature -
    an individual, non-aggregated section geometry - into a
    :class:`~streetworks.common.gazetteer.Segment`. ``secondary_road_name``/
    ``tertiary_road_name`` (real, non-primary names a section can carry
    per the source's own field list) become extra
    :class:`~streetworks.common.gazetteer.Name` entries where present."""
    properties = feature.get("properties") or {}
    road_id = properties.get("road_id")
    geometry = _line(feature.get("geometry"))
    if geometry is None:
        raise ValueError("Road section has no geometry to convert")
    names = []
    for field in ("full_road_name", "secondary_road_name", "tertiary_road_name"):
        value = properties.get(field)
        if value:
            names.append(Name(value=value))
    return Segment(
        geometry=geometry,
        identifiers=(
            (Identifier(scheme="road_section_id", value=str(properties["road_section_id"])),)
            if properties.get("road_section_id") is not None
            else ()
        ),
        names=tuple(names),
        street_refs=(
            (Identifier(scheme="road_id", value=str(road_id)),) if road_id is not None else ()
        ),
        street_type=(
            StreetType(label=properties.get("road_name_type"))
            if properties.get("road_name_type")
            else None
        ),
        administrative_area=properties.get("territorial_authority"),
        raw=feature,
    )
