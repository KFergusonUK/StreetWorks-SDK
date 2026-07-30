"""New South Wales (TfNSW Live Traffic Hazards) -> streetworks.common
converter. This SDK's first Australian coverage.

One :class:`~streetworks.common.Works` per feature, each with a single
:class:`~streetworks.common.WorksSite` - no grouping key exists in this
feed linking separate hazards into one project (unlike Jersey's
``PROJID``), the same one-to-one shape :mod:`.from_vialietuva` uses.
``territory="Australia"``, ``administrative_area="Transport for NSW"`` -
the state road authority IS the data-owning operator, the same rule
already applied to Autobahn GmbH/Via Lietuva/National Highways.

**``Works.reference`` is the composite ``f"{layerName}:{id}"``, never the
bare ``id``** - confirmed from the Developer Guide's own property table,
``id`` is unique only *within* a layer, so a real roadwork ``82681`` and a
real major-event ``82681`` are not guaranteed distinct once a caller
fetches both :meth:`~streetworks.au.nsw.NswLiveTrafficClient.iter_roadworks`
and :meth:`~streetworks.au.nsw.NswLiveTrafficClient.iter_major_events` and
converts them together. ``layerName`` is attached to every feature by
:func:`streetworks.au.nsw.parse_features` - never re-derived here.

See :mod:`streetworks.au.nsw`'s own module docstring for the full set of
real findings this mapping is built from (the sentinel-value convention,
the ``"null"``-string footgun, the missing gazetteer join key, why dates
land on ``proposed_*``/``ESTIMATED`` rather than ``actual_*``, and the
``[lon, lat]`` axis order) - not re-derived here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Coordinate, DateConfidence, Notice, SourceGrade, Works, WorksSite

__all__ = ["from_nsw_livetraffic"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"


def _epoch_millis_to_dt(value: int | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _decode_polyline(encoded: str, *, precision: int = 5) -> tuple[tuple[float, float], ...]:
    """Google's Encoded Polyline Algorithm Format - the standard published
    algorithm, not reverse-engineered from a real TfNSW sample (the one
    real fixture record has no ``encodedPolylines`` - see
    :mod:`streetworks.au.nsw`'s module docstring). Returns ``(lat, lon)``
    pairs, per the algorithm's own convention (distinct from this
    module's GeoJSON ``(lon, lat)`` geometry axis order - flagged, not
    silently reconciled, since callers reading ``Coordinate.points`` need
    to know which convention they're getting)."""
    factor = 10**precision
    coordinates: list[tuple[float, float]] = []
    index = lat = lon = 0
    length = len(encoded)
    while index < length:
        for is_lat in (True, False):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if is_lat:
                lat += delta
            else:
                lon += delta
        coordinates.append((lat / factor, lon / factor))
    return tuple(coordinates)


def _coordinate(feature: JSON) -> Coordinate | None:
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    kind = (geometry.get("type") or "").upper()
    if kind != "POINT" or not coords:
        return None
    value = (float(coords[0]), float(coords[1]))
    points: tuple[tuple[float, float], ...] | None = None
    encoded_polylines = (feature.get("properties") or {}).get("encodedPolylines") or []
    if encoded_polylines:
        # Decoded as (lat, lon) per the polyline algorithm's own convention -
        # distinct from this Coordinate's (lon, lat) value/geometry axis
        # order, see streetworks.au.nsw._decode_polyline's own docstring.
        first = encoded_polylines[0]
        polyline_text = first.get("points") if isinstance(first, dict) else first
        if isinstance(polyline_text, str):
            points = _decode_polyline(polyline_text)
    return Coordinate(value=value, crs=_CRS, points=points)


def _location_description(properties: JSON) -> str | None:
    roads = properties.get("roads") or []
    if not roads:
        return None
    road = roads[0]
    parts = [
        road.get("mainStreet"),
        road.get("locationQualifier"),
        road.get("crossStreet") or road.get("secondLocation"),
        road.get("suburb"),
    ]
    text = " ".join(p for p in parts if p)
    return text or None


def _operating_window(properties: JSON) -> str | None:
    periods = properties.get("periods") or []
    if not periods:
        return None
    parts = []
    for period in periods:
        day = period.get("fromDay") or ""
        start = period.get("startTime") or ""
        finish = period.get("finishTime") or ""
        if day and start and finish:
            parts.append(f"{day} {start}-{finish}")
    return "; ".join(parts) or None


def _traffic_management(properties: JSON) -> str | None:
    other_advice = properties.get("otherAdvice")
    if other_advice:
        return other_advice
    advice = [properties.get(f"advice{letter}") for letter in "ABC"]
    joined = ", ".join(a for a in advice if a)
    return joined or None


def _notices(properties: JSON) -> tuple[Notice, ...]:
    links = properties.get("webLinks") or []
    return tuple(
        Notice(text=link.get("linkText"), raw=link) for link in links if link.get("linkText")
    )


def _reference(feature: JSON) -> str | None:
    """``f"{layerName}:{id}"`` - see module docstring for why the bare
    ``id`` alone is not safe once more than one layer is in play."""
    id_ = feature.get("id")
    if id_ is None:
        return None
    layer_name = feature.get("layerName")
    return f"{layer_name}:{id_}" if layer_name else str(id_)


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    start = _epoch_millis_to_dt(properties.get("start"))
    end = _epoch_millis_to_dt(properties.get("end"))
    return WorksSite(
        reference=_reference(feature),
        works_type=properties.get("mainCategory"),
        status="ended" if properties.get("ended") else "active",
        location_description=_location_description(properties),
        coordinate=_coordinate(feature),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN,
        operating_window=_operating_window(properties),
        traffic_management=_traffic_management(properties),
        notices=_notices(properties),
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_nsw_livetraffic(features: list[JSON]) -> list[Works]:
    """Convert real TfNSW roadwork/major-event features (from
    :meth:`streetworks.au.nsw.NswLiveTrafficClient.iter_roadworks`/
    :meth:`~streetworks.au.nsw.NswLiveTrafficClient.iter_major_events`)
    into :class:`~streetworks.common.Works` - one per feature, each with a
    single ``WorksSite``. Safe to call with a combined list from both
    layers - see module docstring for the composite-reference handling
    that makes that safe."""
    works_list: list[Works] = []
    for feature in features:
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                territory="Australia",
                administrative_area="Transport for NSW",
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=feature,
            )
        )
    return works_list
