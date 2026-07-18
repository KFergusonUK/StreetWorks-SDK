"""OGC geodata (WFS / OGC API Features / direct GeoJSON) - a generic fetch
client plus declarative per-source field maps.

:class:`OGCFeaturesClient` is deliberately not roadworks-specific - it
only fetches GeoJSON. :mod:`streetworks.ogc.germany` is the first
consumer (German state roadworks); the same client is intended to
underpin future gazetteer work over the same kind of German-state WFS
endpoints, so keep new code here generic (GeoJSON in, features out,
CRS-aware) rather than roadworks-locked.
"""

from .client import OGCFeaturesClient

__all__ = ["OGCFeaturesClient"]
