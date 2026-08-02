"""G-NAF + National Roads (Australia, over the Digital Atlas of Australia)
-> streetworks.common gazetteer converter. This SDK's first Australian
gazetteer coverage.

``from_gnaf_address`` (National Address Points) ->
:class:`~streetworks.common.gazetteer.Address`. ``from_gnaf_road``
(National Roads) -> :class:`~streetworks.common.gazetteer.Segment` only -
**never** :class:`~streetworks.common.gazetteer.Street`. ``road_id`` is a
real, segment-scoped identifier ("Persistent identifier for a roads
feature", per the layer's own field description), not an aggregated
named-street id, and no separate named-street layer was found alongside
it - so emitting a synthetic ``Street`` by grouping same-named segments
would violate this model's own "no synthetic streets" rule (see
:mod:`streetworks.common.gazetteer`'s module docstring and
:mod:`streetworks.common.from_nwb`, which reaches the identical
conclusion for the Netherlands).

**``street_name`` is built, not sourced pre-combined** - unlike
``ban``/``bag``/``kartverket``/``linz``, this dataset's address layer has
no single "street name" field, only ``STREET_NAME``/``STREET_TYPE``/
``STREET_SUFFIX`` decomposed. ``from_gnaf_address`` joins the populated
parts with spaces (e.g. ``"WENLOCK"`` + ``"STREET"`` ->
``"WENLOCK STREET"``) - confirmed to match the source's own
``COMPLETE_ADDRESS`` formatting for the street portion on every real
record checked.

**No stated join between addresses and roads** - see
:mod:`streetworks.gnaf.client`'s own module docstring for the full
finding. ``Address.street_links``/``Segment.street_refs`` both stay empty
here; there is nothing stated to point them at.

**Real gaps kept on ``.raw`` only, not modelled**: ``NUMBER_FIRST_PREFIX``
and the whole ``NUMBER_LAST*`` triple (a real address-range concept - a
single G-NAF address can be a public open ``"NUMBER_FIRST-NUMBER_LAST"``
range, e.g. a block of shops - :class:`~streetworks.common.gazetteer.Address`
has no range concept, only :class:`~streetworks.common.gazetteer.AddressRange`,
which is segment-scoped); ``STATE``/``POSTCODE`` (no canonical field);
``CONFIDENCE`` (a real G-NAF geocode-quality score); on the roads side,
``status`` (real values seen: ``"OPERATIONAL"``, ``"PROPOSED"`` - a
**genuinely real distinction this converter does not filter on**, since
:meth:`streetworks.gnaf.client.GnafClient.iter_roads` is the raw network,
not a curated "built roads only" view; callers wanting current
infrastructure only should filter ``where="status='OPERATIONAL'"``
themselves), ``surface``/``speed``/``one_way``/``trafficability``/
``feature_type``.

**Geometry axis order**: this SDK's standing convention for
``EPSG:4326`` - ``(lat, lon)`` - applied here via the same flip-on-4326
rule as :mod:`streetworks.common.from_linz`/:mod:`streetworks.common.from_ogc_features`.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import Address, Name, Segment, StreetType
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_gnaf_address", "from_gnaf_road"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Australia"


def _point(geometry: JSON | None) -> Coordinate | None:
    if not geometry or (geometry.get("type") or "").upper() != "POINT":
        return None
    coords = geometry.get("coordinates")
    if not coords:
        return None
    lon, lat = float(coords[0]), float(coords[1])
    return Coordinate(value=(lat, lon), crs=_CRS)


def _line(geometry: JSON | None) -> Coordinate | None:
    """``LineString``/``MultiLineString`` - both real on National Roads
    (ArcGIS ``paths`` with more than one part become ``MultiLineString`` -
    see :mod:`streetworks.arcgis.client`)."""
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


def _street_name(properties: JSON) -> str | None:
    parts = [
        properties.get("STREET_NAME"),
        properties.get("STREET_TYPE"),
        properties.get("STREET_SUFFIX"),
    ]
    joined = " ".join(part for part in parts if part)
    return joined or None


def from_gnaf_address(feature: JSON) -> Address:
    """Convert one real National Address Points feature into an
    :class:`~streetworks.common.gazetteer.Address`."""
    properties = feature.get("properties") or {}
    address_detail_pid = properties.get("ADDRESS_DETAIL_PID")
    number_first = properties.get("NUMBER_FIRST")
    geometry = _point(feature.get("geometry"))
    if geometry is None:
        raise ValueError("Address has no geometry to convert")
    return Address(
        geometry=geometry,
        identifiers=(
            (Identifier(scheme="address_detail_pid", value=str(address_detail_pid)),)
            if address_detail_pid
            else ()
        ),
        housenumber=str(number_first) if number_first is not None else None,
        suffix=properties.get("NUMBER_FIRST_SUFFIX") or None,
        street_name=_street_name(properties),
        territory=_TERRITORY,
        administrative_area=properties.get("LOCALITY_NAME"),
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )


def from_gnaf_road(feature: JSON) -> Segment:
    """Convert one real National Roads feature into a
    :class:`~streetworks.common.gazetteer.Segment`. Raises ``ValueError``
    if the feature has no geometry - a real road_id with no geometry
    would be unusable as a gazetteer segment, the same discipline
    :mod:`streetworks.common.from_linz`'s ``from_linz_road_section``
    already established."""
    properties = feature.get("properties") or {}
    road_id = properties.get("road_id")
    full_street_name = properties.get("full_street_name")
    street_type = properties.get("street_type")
    street_type_label = properties.get("street_type_label")
    geometry = _line(feature.get("geometry"))
    if geometry is None:
        raise ValueError("Road segment has no geometry to convert")
    return Segment(
        geometry=geometry,
        identifiers=(Identifier(scheme="road_id", value=str(road_id)),) if road_id else (),
        names=(Name(value=full_street_name),) if full_street_name else (),
        street_type=(
            StreetType(code=street_type, label=street_type_label)
            if street_type or street_type_label
            else None
        ),
        administrative_area=properties.get("state"),
        raw=feature,
    )
