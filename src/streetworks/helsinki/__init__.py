"""Helsinki (Kaivuilmoitus excavation notifications) - this SDK's third
Nordic roadworks coverage. See :mod:`streetworks.helsinki.client` for the
full investigation, including how it resolves the Nordic-capitals
investigation brief's own unconfirmed claim about Helsinki's data.
"""

from .client import BASE_URL, CRS, TYPE_NAME, HelsinkiClient

__all__ = ["BASE_URL", "CRS", "TYPE_NAME", "HelsinkiClient"]
