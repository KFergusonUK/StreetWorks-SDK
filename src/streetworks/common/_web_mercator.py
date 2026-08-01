"""Shared Web Mercator (EPSG:3857) <-> WGS84 (EPSG:4326) helper for the
ArcGIS-family AU providers whose services declare a native Web Mercator
spatial reference (WA's Main Roads WebEOC layer, South Australia's Traffic
SA layer) and whose GeoJSON output strips any per-feature CRS statement, so
a caller can't trust that a prior ``outSR=4326`` request was actually
honoured - see :mod:`streetworks.arcgis.client`'s own module docstring for
why: some real ArcGIS Server deployments silently ignore ``outSR`` (Jersey's
RoadWorks layer, confirmed live), while others honour it correctly (WA,
confirmed live) - the request alone never proves which happened.

Extracted here after the second real consumer (South Australia) needed the
identical formula - first built for, and still used by,
:mod:`streetworks.common.from_au_wa_mainroads`, see that module's own
docstring for the full reasoning behind the design choice below.

**Deliberately a closed-form spherical-Mercator inverse, not** ``pyproj``
**- the exact algebraic inverse of how EPSG:3857 itself is defined**, not
an approximation: Web Mercator is a spherical, not ellipsoidal, projection
by specification, so there is nothing a fuller geodetic library would add
in accuracy for this specific coordinate pair. Chosen to preserve this
SDK's explicit, repeatedly-stated standard-library-plus-httpx design
constraint (the same reasoning :class:`~streetworks.arcgis.client.ArcGISFeatureClient`'s
own module docstring states for why it exists in the first place).
"""

from __future__ import annotations

import math

__all__ = ["web_mercator_to_wgs84", "reproject_if_projected"]

#: Half the Web Mercator (EPSG:3857) world circumference in metres - the
#: standard constant for the spherical Mercator inverse.
_ORIGIN_SHIFT = 20037508.342789244


def web_mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """The exact closed-form inverse of EPSG:3857 (spherical Web Mercator).
    Returns ``(lon, lat)``, matching GeoJSON axis order."""
    lon = x / _ORIGIN_SHIFT * 180.0
    lat_rad = 2 * math.atan(math.exp(y / _ORIGIN_SHIFT * math.pi)) - math.pi / 2
    return lon, math.degrees(lat_rad)


def reproject_if_projected(x: float, y: float) -> tuple[float, float]:
    """**The runtime coordinate guard**: GeoJSON strips any per-feature CRS
    statement, so this never trusts that a prior ``outSR=4326`` request was
    actually honoured - any point outside plausible WGS84 degree range
    (``abs(x) > 180`` or ``abs(y) > 90``) is treated as unreprojected Web
    Mercator metres and converted explicitly via :func:`web_mercator_to_wgs84`;
    a point already in plausible WGS84 range is passed through unchanged.
    Never silently guesses either way."""
    if abs(x) > 180 or abs(y) > 90:
        return web_mercator_to_wgs84(x, y)
    return x, y
