"""Pure-Python ETRS89 / UTM zone 33N (EPSG:25833) -> WGS84 (EPSG:4326)
transform, for Saxony's (Germany) Hauskoordinaten bulk export - the
only CRS this resource states (a real `zone` column, confirmed live to
always read `33`), with no server-side reprojection option (a plain
bulk text-file download, not a WFS with an `srsName` parameter).

**Deliberately not** ``pyproj`` **- the same stdlib-plus-httpx
constraint** :mod:`streetworks.common._web_mercator`,
:mod:`streetworks.common._bng`, and :mod:`streetworks.common._utm32n`
(Denmark's DAR) all state. As with DAR's own UTM32N case, no Helmert
datum step is needed - ETRS89 and WGS84 are coincident at this SDK's
stated accuracy. What follows is the same closed-form ellipsoidal
Transverse Mercator inverse (the Redfearn series) as
:mod:`streetworks.common._utm32n`, here with UTM zone 33N's own
published central meridian (15 deg E, one zone east of zone 32N's 9 deg
E) - every other constant (scale factor, false easting, no false
northing) is identical, since both are standard UTM zones on the same
ellipsoid.

Cross-checked against a real sample point before shipping: Saxony's own
address export states `(328618.634, 5654060.693)` for a real address in
Dolsenhain (Frohburg, Landkreis Leipzig) - this module's own inverse
places it at approximately 12.56 deg E, 51.01 deg N, genuinely inside
Saxony's real geographic extent (roughly 12-15 deg E, 50.2-51.7 deg N)
and consistent with Frohburg's own real location near Leipzig - unlike
Lithuania's own UTM-family source, this one's axis order is the
standard `(Easting, Northing)`, confirmed by the same bounds check
(no swap needed).
"""

from __future__ import annotations

import math

__all__ = ["utm33n_to_wgs84"]

_A = 6_378_137.0
_B = 6_356_752.314245

_F0 = 0.9996
_PHI0 = 0.0
_LAMBDA0 = math.radians(15.0)
_E0 = 500_000.0
_N0 = 0.0

_CONVERGENCE_TOL_M = 0.00001


def utm33n_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """ETRS89 / UTM zone 33N (EPSG:25833) ``(easting, northing)`` in
    metres -> WGS84 ``(lon, lat)`` in degrees, matching GeoJSON axis
    order (the same convention
    :func:`streetworks.common._utm32n.utm32n_to_wgs84` uses)."""
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
    parameterised for zone 33N's own central meridian."""
    dphi = lat - _PHI0
    sphi = lat + _PHI0
    ma = (1 + n + 1.25 * n2 + 1.25 * n3) * dphi
    mb = (3 * n + 3 * n2 + 2.625 * n3) * math.sin(dphi) * math.cos(sphi)
    mc = (1.875 * n2 + 1.875 * n3) * math.sin(2 * dphi) * math.cos(2 * sphi)
    md = (35.0 / 24.0 * n3) * math.sin(3 * dphi) * math.cos(3 * sphi)
    return _B * _F0 * (ma - mb + mc - md)
