"""Pure-Python LKS-94 / Lithuanian Coordinate System 1994 (EPSG:3346) ->
WGS84 (EPSG:4326) transform, for Registrų centras' (Lithuania) street
register - the only CRS its bulk street-centerline dataset states, with
no server-side reprojection option (a plain REST/JSON download, not a
WFS with an ``srsName`` parameter to request).

**Deliberately not** ``pyproj`` **- the same stdlib-plus-httpx
constraint** :mod:`streetworks.common._web_mercator`,
:mod:`streetworks.common._bng`, and :mod:`streetworks.common._utm32n`
(Denmark's DAR) all state. **No Helmert datum step is needed here, for
the same reason DAR's own UTM32N case needed none** - LKS-94 is defined
directly on the ETRS89/GRS80 ellipsoid, coincident with WGS84 at this
SDK's stated accuracy. What follows is the standard ellipsoidal
Transverse Mercator inverse (the Redfearn series), the same formula
family :mod:`streetworks.common._utm32n` already uses, here with LKS-94's
own published constants (central meridian 24 deg E, scale factor 0.9998,
false easting 500,000 m, no false northing).

**A real, confirmed axis-order quirk, found live and worth stating
plainly: this source's own WKT states coordinates as (Northing,
Easting), not the standard WKT/GeoJSON (Easting, Northing) = (X, Y)
order.** Confirmed by bounds-checking a real sample point both ways -
LKS-94's real easting range for Lithuania is roughly 300,000-720,000 m
and its real northing range is roughly 5,990,000-6,265,000 m; a real
fixture point's first WKT ordinate (~6,107,030) only falls inside the
*northing* range, never the easting one, and reprojecting with the
ordinates swapped lands the point inside Lithuania's real geographic
extent (confirmed: ~22.7 deg E, ~55.1 deg N for that same point), while
reprojecting them in literal WKT order lands near Sri Lanka. See
:mod:`streetworks.common.from_registrucentras`'s own docstring for how
the converter applies this swap.
"""

from __future__ import annotations

import math

__all__ = ["lks94_to_wgs84"]

_A = 6_378_137.0
_B = 6_356_752.314245

_F0 = 0.9998
_PHI0 = 0.0
_LAMBDA0 = math.radians(24.0)
_E0 = 500_000.0
_N0 = 0.0

_CONVERGENCE_TOL_M = 0.00001


def lks94_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """LKS-94 (EPSG:3346) ``(easting, northing)`` in metres -> WGS84
    ``(lon, lat)`` in degrees, matching GeoJSON axis order (the same
    convention :func:`streetworks.common._utm32n.utm32n_to_wgs84` uses).
    Callers must pass true easting/northing - see the module docstring
    for the real axis-order swap this source's own WKT needs first."""
    e2 = 1 - (_B * _B) / (_A * _A)
    n = (_A - _B) / (_A + _B)
    n2, n3 = n * n, n * n * n

    lat = _PHI0
    while True:
        m = _meridional_arc(lat, n, n2, n3)
        if abs(northing - _N0 - m) < _CONVERGENCE_TOL_M:
            break
        lat = lat + (northing - _N0 - m) / (_A * _F0)

    cos_lat, sin_lat = math.cos(lat), math.sin(lat)
    tan_lat = math.tan(lat)
    sec_lat = 1 / cos_lat

    nu = _A * _F0 / math.sqrt(1 - e2 * sin_lat**2)
    rho = _A * _F0 * (1 - e2) / (1 - e2 * sin_lat**2) ** 1.5
    eta2 = nu / rho - 1

    vii = tan_lat / (2 * rho * nu)
    viii = tan_lat / (24 * rho * nu**3) * (5 + 3 * tan_lat**2 + eta2 - 9 * tan_lat**2 * eta2)
    ix = tan_lat / (720 * rho * nu**5) * (61 + 90 * tan_lat**2 + 45 * tan_lat**4)
    x = sec_lat / nu
    xi = sec_lat / (6 * nu**3) * (nu / rho + 2 * tan_lat**2)
    xii = sec_lat / (120 * nu**5) * (5 + 28 * tan_lat**2 + 24 * tan_lat**4)
    xiia = (
        sec_lat / (5040 * nu**7) * (61 + 662 * tan_lat**2 + 1320 * tan_lat**4 + 720 * tan_lat**6)
    )

    de = easting - _E0
    final_lat = lat - vii * de**2 + viii * de**4 - ix * de**6
    final_lon = _LAMBDA0 + x * de - xi * de**3 + xii * de**5 - xiia * de**7
    return math.degrees(final_lon), math.degrees(final_lat)


def _meridional_arc(lat: float, n: float, n2: float, n3: float) -> float:
    """Meridional arc from the equator to ``lat`` - the same series
    :func:`streetworks.common._utm32n._meridional_arc` uses,
    parameterised for LKS-94's own scale factor."""
    dphi = lat - _PHI0
    sphi = lat + _PHI0
    ma = (1 + n + 1.25 * n2 + 1.25 * n3) * dphi
    mb = (3 * n + 3 * n2 + 2.625 * n3) * math.sin(dphi) * math.cos(sphi)
    mc = (1.875 * n2 + 1.875 * n3) * math.sin(2 * dphi) * math.cos(2 * sphi)
    md = (35.0 / 24.0 * n3) * math.sin(3 * dphi) * math.cos(3 * sphi)
    return _B * _F0 * (ma - mb + mc - md)
