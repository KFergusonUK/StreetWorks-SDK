"""ArcGIS REST (MapServer/FeatureServer) - a generic fetch client plus
per-source clients built on it.

:class:`~streetworks.arcgis.client.ArcGISFeatureClient` is deliberately not
roadworks- or gazetteer-specific - it only knows how to fetch/page GeoJSON
out of an ArcGIS REST layer. :mod:`streetworks.arcgis.jersey` (roadworks
and streets), :mod:`streetworks.arcgis.guernsey` (streets),
:mod:`streetworks.arcgis.nrn` (streets, Canada),
:mod:`streetworks.arcgis.monaghan` (segments, Ireland),
:mod:`streetworks.arcgis.lisboa` (streets, Portugal),
:mod:`streetworks.arcgis.tigerweb` (streets),
:mod:`streetworks.arcgis.dc` (roadworks, Washington DC) and
:mod:`streetworks.arcgis.ip` (roadworks, Portugal - national, distinct
from :mod:`streetworks.lisboa`'s municipal feed) are its real consumers
so far; keep new code here generic so a future ArcGIS source
(e.g. a UK local authority's own roadworks service, published the same
way West Berkshire's is) can reuse it.
"""

from .client import ArcGISFeatureClient, LayerInfo

__all__ = ["ArcGISFeatureClient", "LayerInfo"]
