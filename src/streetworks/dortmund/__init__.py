"""Dortmund: the City of Dortmund's own roadworks register - this SDK's
first German municipal roadworks provider. See
:mod:`streetworks.dortmund.client` for the full investigation.
"""

from .client import GEPLANT_URL, TAGESAKTUELL_URL, DortmundClient

__all__ = ["GEPLANT_URL", "TAGESAKTUELL_URL", "DortmundClient"]
