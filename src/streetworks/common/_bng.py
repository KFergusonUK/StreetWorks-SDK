"""Pure-Python WGS84 (EPSG:4326) <-> British National Grid (EPSG:27700)
transform, for write paths that must state Street Manager's own coordinate
convention - ``works_coordinates`` is documented as GeoJSON but is BNG
easting/northing, not WGS84 lon/lat (non-conformant GeoJSON, deliberately -
see :mod:`streetworks.common.from_streetmanager`'s ``_coordinate()`` for the
read-side mirror of this).

**Deliberately not** ``pyproj`` **- the same stdlib-plus-httpx constraint**
:mod:`streetworks.common._web_mercator` states for EPSG:3857<->4326. Unlike
that spherical Mercator case, though, WGS84<->BNG genuinely is an ellipsoidal
+ datum problem (WGS84/GRS80 ellipsoid to the Airy 1830 ellipsoid via a
Helmert datum shift, then an ellipsoidal Transverse Mercator projection) -
there is no algebraic shortcut that sidesteps real geodesy here. What follows
is Ordnance Survey's own published closed-form algorithm: *"A Guide to
Coordinate Systems in Great Britain"*, Annexes B, C and D
(https://www.ordnancesurvey.co.uk/documents/resources/guide-coordinate-systems-great-britain.pdf).

**Accuracy, stated honestly**: this is the seven-parameter Helmert
transform, not the OSTN15 correction grid OS recommends for survey-grade
work. OS's own guide states this Helmert-only route is good to within
roughly a few metres (their published figure: "not recommended for
applications requiring better than 3.5 m (95%) accuracy") - entirely
adequate for siting a street-works extent, not a substitute for a real
survey. Shipping the OSTN15 grid (a multi-megabyte binary correction
dataset) would also violate the no-large-data-files convention every other
module in this SDK follows.

The Helmert transform's *inverse* (``bng_to_wgs84``, used to sample back
from OSGB36 to WGS84) is the standard small-angle approximate inverse
(negate the translation/rotation/scale terms rather than a true matrix
inverse) - the same approximation OS's own guide documents as adequate,
since the rotation/scale parameters are tiny enough (arcseconds, parts per
million) that the terms this drops are second-order and sub-centimetre.
"""

from __future__ import annotations

import math
from typing import Any

__all__ = ["wgs84_to_bng", "bng_to_wgs84", "reproject_geojson_to_bng"]

# --------------------------------------------------------------------------- #
# Ellipsoids (Annex A.1)
# --------------------------------------------------------------------------- #

_WGS84_A, _WGS84_B = 6_378_137.000, 6_356_752.3141
_AIRY1830_A, _AIRY1830_B = 6_377_563.396, 6_356_256.909

# --------------------------------------------------------------------------- #
# WGS84 -> OSGB36 Helmert transform parameters (the guide's own published
# table for this pair - translations in metres, rotations in arcseconds,
# scale in parts per million).
# --------------------------------------------------------------------------- #

_TX, _TY, _TZ = -446.448, 125.157, -542.060
_HELMERT_SCALE_PPM = 20.4894
_S = _HELMERT_SCALE_PPM * 1e-6

_ARCSEC_TO_RAD = math.pi / (180.0 * 3600.0)
_RX = -0.1502 * _ARCSEC_TO_RAD
_RY = -0.2470 * _ARCSEC_TO_RAD
_RZ = -0.8421 * _ARCSEC_TO_RAD

# --------------------------------------------------------------------------- #
# National Grid Transverse Mercator projection constants (Annex A.2)
# --------------------------------------------------------------------------- #

_F0 = 0.9996012717
_PHI0 = math.radians(49.0)
_LAMBDA0 = math.radians(-2.0)
_E0 = 400_000.0
_N0 = -100_000.0

_CONVERGENCE_TOL_M = 0.00001  # 0.01mm - the guide's own stated iteration stop


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def wgs84_to_bng(lon: float, lat: float, height: float = 0.0) -> tuple[float, float]:
    """WGS84 ``(lon, lat)`` in degrees (plus optional ellipsoidal height in
    metres) -> British National Grid ``(easting, northing)`` in metres.

    ``height`` defaults to 0.0 - applicant-drawn 2D extents never carry one,
    and the Helmert step's sensitivity to height is far below this
    transform's own stated accuracy (see module docstring).
    """
    lat_r, lon_r = math.radians(lat), math.radians(lon)
    x, y, z = _latlon_to_cartesian(lat_r, lon_r, height, _WGS84_A, _WGS84_B)
    x2, y2, z2 = _helmert_wgs84_to_osgb36(x, y, z)
    lat_osgb36, lon_osgb36, _height = _cartesian_to_latlon(x2, y2, z2, _AIRY1830_A, _AIRY1830_B)
    return _latlon_to_national_grid(lat_osgb36, lon_osgb36)


def bng_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """British National Grid ``(easting, northing)`` in metres -> WGS84
    ``(lon, lat)`` in degrees, matching GeoJSON axis order (the same
    convention :func:`streetworks.common._web_mercator.web_mercator_to_wgs84`
    uses). Height is not recoverable from a National Grid reference and is
    assumed 0 for the Helmert step - see module docstring on accuracy.
    """
    lat_osgb36, lon_osgb36 = _national_grid_to_latlon(easting, northing)
    x, y, z = _latlon_to_cartesian(lat_osgb36, lon_osgb36, 0.0, _AIRY1830_A, _AIRY1830_B)
    x2, y2, z2 = _helmert_osgb36_to_wgs84(x, y, z)
    lat_r, lon_r, _height = _cartesian_to_latlon(x2, y2, z2, _WGS84_A, _WGS84_B)
    return math.degrees(lon_r), math.degrees(lat_r)


def reproject_geojson_to_bng(geometry: dict[str, Any]) -> dict[str, Any]:
    """Reproject a WGS84 GeoJSON ``Point``/``LineString``/``Polygon`` to the
    BNG easting/northing GeoJSON shape Street Manager's ``works_coordinates``
    expects - exactly the three geometry types its own schema permits (see
    ``WorkCreateRequest.works_coordinates``'s docstring). No ``"crs"`` member
    is added to the output, matching Street Manager's own convention of an
    implicit, undeclared BNG CRS on that field (see
    :mod:`streetworks.common.from_streetmanager`'s read-side ``_coordinate()``,
    which likewise never inspects a ``"crs"`` key).

    Raises ``ValueError`` for any other geometry type (``MultiPoint``,
    ``GeometryCollection``, ...) rather than silently mishandling it -
    Street Manager's schema doesn't accept those here either.
    """
    geometry_type = geometry.get("type")
    coordinates = geometry["coordinates"]
    if geometry_type == "Point":
        return {"type": "Point", "coordinates": list(wgs84_to_bng(coordinates[0], coordinates[1]))}
    if geometry_type == "LineString":
        return {
            "type": "LineString",
            "coordinates": [list(wgs84_to_bng(x, y)) for x, y in coordinates],
        }
    if geometry_type == "Polygon":
        return {
            "type": "Polygon",
            "coordinates": [
                [list(wgs84_to_bng(x, y)) for x, y in ring] for ring in coordinates
            ],
        }
    raise ValueError(f"Unsupported geometry type for BNG reprojection: {geometry_type!r}")


# --------------------------------------------------------------------------- #
# Private internals - each independently testable (established house
# convention, e.g. tests/test_wa_mainroads.py importing _coordinate directly).
# --------------------------------------------------------------------------- #


def _latlon_to_cartesian(
    lat: float, lon: float, height: float, a: float, b: float
) -> tuple[float, float, float]:
    """Geodetic lat/lon/height (radians, radians, metres) -> ECEF Cartesian
    (Annex B.1)."""
    e2 = 1 - (b * b) / (a * a)
    nu = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    x = (nu + height) * math.cos(lat) * math.cos(lon)
    y = (nu + height) * math.cos(lat) * math.sin(lon)
    z = ((1 - e2) * nu + height) * math.sin(lat)
    return x, y, z


def _cartesian_to_latlon(
    x: float, y: float, z: float, a: float, b: float
) -> tuple[float, float, float]:
    """ECEF Cartesian -> geodetic lat/lon (radians) + height (metres),
    iterative (Annex B.2)."""
    e2 = 1 - (b * b) / (a * a)
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1 - e2))
    for _ in range(10):
        nu = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        lat_new = math.atan2(z + e2 * nu * math.sin(lat), p)
        if abs(lat_new - lat) < 1e-14:
            lat = lat_new
            break
        lat = lat_new
    nu = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    lon = math.atan2(y, x)
    height = p / math.cos(lat) - nu
    return lat, lon, height


def _helmert_wgs84_to_osgb36(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Forward seven-parameter Helmert transform, WGS84 ECEF -> OSGB36 ECEF."""
    scale = 1 + _S
    x2 = _TX + scale * (x - _RZ * y + _RY * z)
    y2 = _TY + scale * (_RZ * x + y - _RX * z)
    z2 = _TZ + scale * (-_RY * x + _RX * y + z)
    return x2, y2, z2


def _helmert_osgb36_to_wgs84(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Approximate inverse of :func:`_helmert_wgs84_to_osgb36` - negate and
    reapply, first order in the (tiny) rotation/scale terms. See module
    docstring for why this is adequate at this transform's own accuracy."""
    dx, dy, dz = x - _TX, y - _TY, z - _TZ
    x2 = dx - _S * dx + _RZ * dy - _RY * dz
    y2 = dy - _S * dy - _RZ * dx + _RX * dz
    z2 = dz - _S * dz + _RY * dx - _RX * dy
    return x2, y2, z2


def _latlon_to_national_grid(lat: float, lon: float) -> tuple[float, float]:
    """OSGB36 lat/lon (radians) -> National Grid (easting, northing) in
    metres - ellipsoidal Transverse Mercator on Airy 1830 (Annex C.1).
    Variable names (``I``..``VI``) match the guide's own notation."""
    a, b = _AIRY1830_A, _AIRY1830_B
    e2 = 1 - (b * b) / (a * a)
    n = (a - b) / (a + b)
    n2, n3 = n * n, n * n * n

    cos_lat, sin_lat = math.cos(lat), math.sin(lat)
    tan_lat = math.tan(lat)

    nu = a * _F0 / math.sqrt(1 - e2 * sin_lat**2)
    rho = a * _F0 * (1 - e2) / (1 - e2 * sin_lat**2) ** 1.5
    eta2 = nu / rho - 1

    m = _meridional_arc(lat, n, n2, n3, b)

    grid_i = m + _N0
    grid_ii = nu / 2 * sin_lat * cos_lat
    grid_iii = nu / 24 * sin_lat * cos_lat**3 * (5 - tan_lat**2 + 9 * eta2)
    grid_iiia = nu / 720 * sin_lat * cos_lat**5 * (61 - 58 * tan_lat**2 + tan_lat**4)
    grid_iv = nu * cos_lat
    grid_v = nu / 6 * cos_lat**3 * (nu / rho - tan_lat**2)
    grid_vi = (
        nu
        / 120
        * cos_lat**5
        * (5 - 18 * tan_lat**2 + tan_lat**4 + 14 * eta2 - 58 * tan_lat**2 * eta2)
    )

    dlon = lon - _LAMBDA0
    northing = grid_i + grid_ii * dlon**2 + grid_iii * dlon**4 + grid_iiia * dlon**6
    easting = _E0 + grid_iv * dlon + grid_v * dlon**3 + grid_vi * dlon**5
    return easting, northing


def _national_grid_to_latlon(easting: float, northing: float) -> tuple[float, float]:
    """National Grid (easting, northing) -> OSGB36 lat/lon (radians),
    iterative (Annex C.2). Variable names (``VII``..``XIIA``) match the
    guide's own notation."""
    a, b = _AIRY1830_A, _AIRY1830_B
    e2 = 1 - (b * b) / (a * a)
    n = (a - b) / (a + b)
    n2, n3 = n * n, n * n * n

    lat = _PHI0
    while True:
        m = _meridional_arc(lat, n, n2, n3, b)
        if abs(northing - _N0 - m) < _CONVERGENCE_TOL_M:
            break
        lat = lat + (northing - _N0 - m) / (a * _F0)

    cos_lat, sin_lat = math.cos(lat), math.sin(lat)
    tan_lat = math.tan(lat)
    sec_lat = 1 / cos_lat

    nu = a * _F0 / math.sqrt(1 - e2 * sin_lat**2)
    rho = a * _F0 * (1 - e2) / (1 - e2 * sin_lat**2) ** 1.5
    eta2 = nu / rho - 1

    grid_vii = tan_lat / (2 * rho * nu)
    grid_viii = (
        tan_lat / (24 * rho * nu**3) * (5 + 3 * tan_lat**2 + eta2 - 9 * tan_lat**2 * eta2)
    )
    grid_ix = tan_lat / (720 * rho * nu**5) * (61 + 90 * tan_lat**2 + 45 * tan_lat**4)
    grid_x = sec_lat / nu
    grid_xi = sec_lat / (6 * nu**3) * (nu / rho + 2 * tan_lat**2)
    grid_xii = sec_lat / (120 * nu**5) * (5 + 28 * tan_lat**2 + 24 * tan_lat**4)
    grid_xiia = (
        sec_lat
        / (5040 * nu**7)
        * (61 + 662 * tan_lat**2 + 1320 * tan_lat**4 + 720 * tan_lat**6)
    )

    de = easting - _E0
    final_lat = lat - grid_vii * de**2 + grid_viii * de**4 - grid_ix * de**6
    final_lon = _LAMBDA0 + grid_x * de - grid_xi * de**3 + grid_xii * de**5 - grid_xiia * de**7
    return final_lat, final_lon


def _meridional_arc(lat: float, n: float, n2: float, n3: float, b: float) -> float:
    """Meridional arc from the true origin to ``lat`` (shared by the forward
    and inverse National Grid projections - Annex C's own ``M``)."""
    dphi = lat - _PHI0
    sphi = lat + _PHI0
    ma = (1 + n + 1.25 * n2 + 1.25 * n3) * dphi
    mb = (3 * n + 3 * n2 + 2.625 * n3) * math.sin(dphi) * math.cos(sphi)
    mc = (1.875 * n2 + 1.875 * n3) * math.sin(2 * dphi) * math.cos(2 * sphi)
    md = (35.0 / 24.0 * n3) * math.sin(3 * dphi) * math.cos(3 * sphi)
    return b * _F0 * (ma - mb + mc - md)
