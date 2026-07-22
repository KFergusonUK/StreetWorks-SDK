"""ArcGIS REST (MapServer/FeatureServer) - a generic fetch client plus
per-source clients built on it.

:class:`~streetworks.arcgis.client.ArcGISFeatureClient` is deliberately not
roadworks- or gazetteer-specific - it only knows how to fetch/page GeoJSON
out of an ArcGIS REST layer. :mod:`streetworks.arcgis.jersey` (roadworks)
and :mod:`streetworks.arcgis.tigerweb` (streets) are its first two
consumers; keep new code here generic so a future ArcGIS source (e.g. a UK
local authority's own roadworks service, published the same way West
Berkshire's is) can reuse it.
"""

from .client import ArcGISFeatureClient, LayerInfo

__all__ = ["ArcGISFeatureClient", "LayerInfo"]
