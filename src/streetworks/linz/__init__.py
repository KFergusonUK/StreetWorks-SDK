"""New Zealand: LINZ (Toitū Te Whenua) - this SDK's first New Zealand
gazetteer coverage, the gazetteer strand of the NZ cluster (see also
:mod:`streetworks.nzta` for the works strand). See
:mod:`streetworks.linz.client` for the full investigation.
"""

from .client import (
    ADDRESSES_BASE_URL,
    ADDRESSES_LAYER,
    LDS_BASE_URL,
    ROAD_SECTIONS_LAYER_ID,
    ROADS_LAYER_ID,
    LinzClient,
)

__all__ = [
    "ADDRESSES_BASE_URL",
    "ADDRESSES_LAYER",
    "LDS_BASE_URL",
    "ROADS_LAYER_ID",
    "ROAD_SECTIONS_LAYER_ID",
    "LinzClient",
]
