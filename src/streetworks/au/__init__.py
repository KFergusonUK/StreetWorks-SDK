"""Australia - state traffic-disruption feeds, one file per state/territory
(the same cluster shape as :mod:`streetworks.datex2`/:mod:`streetworks.ogc`).

There is no Australian equivalent of the UK's Street Manager: no national,
promoter-submitted statutory permit register exists as open data. Each
state/territory road authority instead publishes its own live traffic-
disruption feed - roadworks alongside incidents, fires, floods and other
hazards - so this cluster is a set of state adapters, not one national
client, and **not every state necessarily shares one shape**: NSW's six
hazard types share a single real schema (see :mod:`streetworks.au.nsw`),
but Victoria publishes two genuinely different, independently-versioned
APIs for planned vs. unplanned disruptions (see :mod:`streetworks.au.vic`,
which covers planned only). Both members are **Credentials-wanted
scaffolds**, pending live verification, grouped with Norway/Sweden/Denmark
(see the README's Credentials wanted section) - Victoria more
speculative than NSW, since no real Victorian sample has been seen
anywhere.
"""

from .nsw import BASE_URL as NSW_BASE_URL
from .nsw import LAYERS as NSW_LAYERS
from .nsw import NswLiveTrafficClient
from .nsw import parse_features as parse_nsw_features
from .vic import BASE_URL as VIC_BASE_URL
from .vic import VicDisruptionsClient
from .vic import parse_features as parse_vic_features

__all__ = [
    "NswLiveTrafficClient",
    "NSW_BASE_URL",
    "NSW_LAYERS",
    "parse_nsw_features",
    "VicDisruptionsClient",
    "VIC_BASE_URL",
    "parse_vic_features",
]
