"""Vienna (verkehrswirksame Baustellen) - this SDK's second Austria
roadworks coverage, alongside the separate national ASFINAG motorway
feed (:mod:`streetworks.datex2.austria`). See
:mod:`streetworks.vienna.client` for the full investigation, including
why the real point and line layers are both needed (genuinely disjoint,
not redundant) and the real source_grade correction from the
investigation brief's own "operator" assumption.
"""

from .client import BASE_URL, CRS, LINE_TYPE_NAME, POINT_TYPE_NAME, ViennaClient

__all__ = ["BASE_URL", "CRS", "LINE_TYPE_NAME", "POINT_TYPE_NAME", "ViennaClient"]
