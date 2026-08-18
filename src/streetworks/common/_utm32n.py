"""Pure-Python ETRS89 / UTM zone 32N (EPSG:25832) -> WGS84 (EPSG:4326)
transform, for Denmark's DAR (Danmarks Adresseregister) - the only real
CRS its ``Navngivenvej`` (named-road) REST endpoint returns; a bare
``srid=EPSG:4326`` request parameter was tried and rejected live (a real
``400``, "Parameter: srid unrecognized") - this endpoint has no
server-side reprojection option at all, unlike Digiroad's WFS
(``srsName=EPSG:4326``, genuinely honoured) or LMI's WFS (WGS84 by
default) - see :mod:`streetworks.dar.client`'s own module docstring.

**Deliberately not** ``pyproj`` **- the same stdlib-plus-httpx
constraint** :mod:`streetworks.common._web_mercator` and
:mod:`streetworks.common._bng` both state. **No Helmert datum step is
needed here, unlike BNG's WGS84<->OSGB36 case** - ETRS89 and WGS84 are,
by design, coincident to within a few centimetres at the current epoch
(they diverge only via slow tectonic drift of the Eurasian plate,
sub-decimetre even decades out), so this module treats them as the same
frame. What follows is the standard ellipsoidal Transverse Mercator
inverse (the Redfearn series) - the same formula family Ordnance
Survey's own guide uses for British National Grid, here with UTM's own
published constants for zone 32N (central meridian 9 deg E, scale factor
0.9996, false easting 500,000 m, no false northing in the northern
hemisphere) on the GRS80 ellipsoid (WGS84's ellipsoid to sub-millimetre
precision).
"""

from __future__ import annotations

import math

__all__ = ["utm32n_to_wgs84"]

# --------------------------------------------------------------------------- #
# GRS80 / WGS84 ellipsoid - identical to the precision this transform needs.
# --------------------------------------------------------------------------- #

_A = 6_378_137.0
_B = 6_356_752.314245

# --------------------------------------------------------------------------- #
# UTM zone 32N projection constants - standard, published UTM parameters,
# not specific to any one country's grid.
# --------------------------------------------------------------------------- #

_F0 = 0.9996
_PHI0 = 0.0
_LAMBDA0 = math.radians(9.0)
_E0 = 500_000.0
_N0 = 0.0

_CONVERGENCE_TOL_M = 0.00001  # 0.01mm, the same stop OS's own guide uses


def utm32n_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """ETRS89 / UTM zone 32N ``(easting, northing)`` in metres -> WGS84
    ``(lon, lat)`` in degrees, matching GeoJSON axis order (the same
    convention :func:`streetworks.common._web_mercator.web_mercator_to_wgs84`
    and :func:`streetworks.common._bng.bng_to_wgs84` use)."""
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
    :func:`streetworks.common._bng._meridional_arc` uses, parameterised
    for UTM's ``phi0=0`` true origin rather than BNG's 49 deg N."""
    dphi = lat - _PHI0
    sphi = lat + _PHI0
    ma = (1 + n + 1.25 * n2 + 1.25 * n3) * dphi
    mb = (3 * n + 3 * n2 + 2.625 * n3) * math.sin(dphi) * math.cos(sphi)
    mc = (1.875 * n2 + 1.875 * n3) * math.sin(2 * dphi) * math.cos(2 * sphi)
    md = (35.0 / 24.0 * n3) * math.sin(3 * dphi) * math.cos(3 * sphi)
    return _B * _F0 * (ma - mb + mc - md)
