"""Madrid: INFORMO municipal traffic-incidents feed - the fourth Spanish
provider (after DGT, SCT, Mallorca) and this SDK's first Madrid-city
source. See :mod:`streetworks.madrid.client` for the full investigation.
"""

from .client import INCIDENCIAS_URL, MadridClient, parse_incidencias

__all__ = ["INCIDENCIAS_URL", "MadridClient", "parse_incidencias"]
