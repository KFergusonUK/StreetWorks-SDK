"""Stadt Zürich (Aktuelle Tiefbauprojekte im öffentlichen Grund) - this
SDK's second Swiss roadworks coverage. See :mod:`streetworks.zurich.client`
for the full investigation, including the empty-DefaultSRS-but-
empirically-WGS84 finding and why this is deliberately not deduped
against Kanton Zürich (:mod:`streetworks.canton_zurich`).
"""

from .client import BASE_URL, CRS, TYPE_NAME, ZurichClient

__all__ = ["BASE_URL", "CRS", "TYPE_NAME", "ZurichClient"]
