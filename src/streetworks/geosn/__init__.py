"""Germany (Saxony) - GeoSN's statewide Hauskoordinaten export,
deduplicated to streets. See :mod:`streetworks.geosn.client` for the
full picture."""

from __future__ import annotations

from .client import BASE_URL, GeoSNStreetsClient

__all__ = ["BASE_URL", "GeoSNStreetsClient"]
