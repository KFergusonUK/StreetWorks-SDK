"""New Zealand: NZTA (Waka Kotahi) Highway Information - this SDK's first
New Zealand coverage, the works strand of the NZ cluster (see also
:mod:`streetworks.linz` for the gazetteer strand). See
:mod:`streetworks.nzta.client` for the full investigation.
"""

from .client import BASE_URL, ROAD_AREA_EVENTS_LAYER, ROAD_EVENTS_LAYER, NztaClient

__all__ = ["BASE_URL", "ROAD_EVENTS_LAYER", "ROAD_AREA_EVENTS_LAYER", "NztaClient"]
