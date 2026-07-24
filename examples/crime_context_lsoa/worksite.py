"""Resolve a worksite - a point and a radius, or a USRN - to a buffered
working area, and find which LSOAs it intersects.

Two input modes, two coordinate systems, never mixed:

- **Point + radius** (the live-tested, dependency-light default): worked in
  an equirectangular local projection centred on the point's own latitude -
  the same "honest cheap, not the right one" approximation the
  neighbourhood-level example already uses for polygon area (see
  ``examples/crime_context/generate_map.py``'s ``ring_area_km2``). Adequate
  at the few-hundred-metre scale a worksite buffer needs; not a real
  geodetic buffer.
- **USRN**: resolved via :class:`streetworks.openusrn.reader.UsrnDatabase`
  against an already-downloaded OS Open USRN GeoPackage (confirmed live to
  be a real ~300MB product - too large to fetch as part of this example's
  own verification, so **this path is implemented but not live-tested
  end-to-end**). Its geometry is native British National Grid (EPSG:27700)
  metres; rather than implement a real OSGB36-to-WGS84 transform, this
  module keeps the whole USRN path in BNG metres and expects LSOA geometry
  requested the same way (``ons.fetch_lsoa_stats(..., out_sr=27700)``) -
  two self-consistent coordinate systems, never reprojected into each
  other.

Requires ``shapely`` (buffering and polygon intersection are the actual
point of this module - unlike the neighbourhood example, where shapely was
a nicety, it is not optional here).
"""

from __future__ import annotations

import math
from typing import Any

from shapely.geometry import Point, Polygon

from streetworks.openusrn.reader import UsrnDatabase

JSON = dict[str, Any]

_KM_PER_DEG_LAT = 110.574


def _local_projection(ref_lat: float) -> tuple[Any, Any]:
    """Returns ``(to_xy, to_lonlat)`` - a matched pair of forward/inverse
    equirectangular transforms in metres, centred on ``ref_lat``. See
    module docstring for why this, not a real geodetic projection."""
    km_per_deg_lng = 111.320 * math.cos(math.radians(ref_lat))

    def to_xy(lat: float, lng: float) -> tuple[float, float]:
        return (lng * km_per_deg_lng * 1000, lat * _KM_PER_DEG_LAT * 1000)

    def to_lonlat(x: float, y: float) -> tuple[float, float]:
        return (x / (km_per_deg_lng * 1000), y / (_KM_PER_DEG_LAT * 1000))

    return to_xy, to_lonlat


def worksite_from_point(lat: float, lng: float, radius_m: float) -> Polygon:
    """Buffers a point by ``radius_m`` metres, returned as a
    :class:`shapely.Polygon` in WGS84 ``(lon, lat)`` degrees - matching
    ``ons.fetch_lsoa_stats``'s default ``out_sr=4326``.

    A tight buffer is false precision: crime locations are snapped to
    anonymised points (data.police.uk's own documented practice), so a
    buffer much smaller than that snapping error claims an accuracy this
    data can't support. A few hundred metres is a sensible default for an
    actual worksite footprint plus working margin - not this function's
    business to pick for the caller, but worth stating here.
    """
    to_xy, to_lonlat = _local_projection(lat)
    origin_x, origin_y = to_xy(lat, lng)
    circle_xy = Point(origin_x, origin_y).buffer(radius_m)
    return Polygon([to_lonlat(x, y) for x, y in circle_xy.exterior.coords])


def worksite_from_usrn(usrn: int | str, geopackage_path: str, radius_m: float) -> Polygon:
    """Buffers a USRN's street geometry by ``radius_m`` metres, returned as
    a :class:`shapely.Polygon` in British National Grid (EPSG:27700)
    metres. See module docstring: **not live-tested end-to-end** - the OS
    Open USRN GeoPackage is a real, confirmed ~300MB download, out of scope
    for this session to fetch just to exercise this one path. Use
    ``ons.fetch_lsoa_stats(..., out_sr=27700)`` for LSOA geometry alongside
    this, never the default ``out_sr=4326`` - mixing the two coordinate
    systems would silently misplace every intersection test.
    """
    with UsrnDatabase(geopackage_path) as db:
        street = db.get(usrn)
    if street is None or street.geometry is None:
        raise ValueError(f"USRN {usrn} not found in {geopackage_path}")
    from shapely import wkt as shapely_wkt

    line = shapely_wkt.loads(street.geometry)
    return line.buffer(radius_m)


def find_intersecting_lsoas(
    worksite: Polygon, lsoa_stats: dict[str, JSON]
) -> list[str]:
    """LSOA codes whose boundary (from ``lsoa_stats[code]["rings"]``, in
    the same coordinate system as ``worksite`` - see module docstring)
    intersects the buffered worksite. Uses the outer ring only for
    multi-ring LSOAs' intersection test (a real, if rare, simplification -
    an LSOA split by a river tests as one combined shape, not per-part)."""
    matches = []
    for code, stats in lsoa_stats.items():
        rings = stats["rings"]
        if not rings:
            continue
        lsoa_polygon = Polygon(rings[0])
        if lsoa_polygon.intersects(worksite):
            matches.append(code)
    return matches
