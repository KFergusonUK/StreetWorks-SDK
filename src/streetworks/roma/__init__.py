"""Roma: "Roma si trasforma" civic-interventions feed - this SDK's
second Italy provider and first Rome-municipal source. See
:mod:`streetworks.roma.client` for the full investigation, including why
the source brief's proposed ArcGIS source doesn't exist.
"""

from .client import INTERVENTI_URL, RomaClient

__all__ = ["INTERVENTI_URL", "RomaClient"]
