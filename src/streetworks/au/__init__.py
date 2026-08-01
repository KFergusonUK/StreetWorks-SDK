"""Australia - state traffic-disruption feeds, one file per state/territory
(the same cluster shape as :mod:`streetworks.datex2`/:mod:`streetworks.ogc`).

There is no Australian equivalent of the UK's Street Manager: no national,
promoter-submitted statutory permit register exists as open data. Each
state/territory road authority instead publishes its own live traffic-
disruption feed - roadworks alongside incidents, fires, floods and other
hazards - so this cluster is a set of state adapters, not one national
client, and **not every state necessarily shares one shape**: NSW's six
hazard types share a single real schema (see :mod:`streetworks.au.nsw`);
Victoria publishes two genuinely different, independently-versioned APIs
for planned vs. unplanned disruptions (see :mod:`streetworks.au.vic`,
which covers planned only); Western Australia is a single ArcGIS REST
``FeatureServer`` layer, a third distinct client protocol, not just a
third schema (see :mod:`streetworks.au.wa`); Queensland is a single
typed feed like NSW's, but with no server-side type filter and a genuinely
richer, per-record authority split - see :mod:`streetworks.au.qld`. NSW
and Victoria are **Phase 2 confirmed** (2026-07-30, against real
credentialed pulls - see each module's own docstring); WA and QLD are
**credential-free** (QLD via a real public API key, never a private one)
and shipped live-verified with a real fixture from day one, never
Credentials-wanted scaffolds.
"""

from .nsw import BASE_URL as NSW_BASE_URL
from .nsw import LAYERS as NSW_LAYERS
from .nsw import NswLiveTrafficClient
from .nsw import parse_features as parse_nsw_features
from .qld import BASE_URL as QLD_BASE_URL
from .qld import EVENT_TYPES as QLD_EVENT_TYPES
from .qld import PUBLIC_API_KEY as QLD_PUBLIC_API_KEY
from .qld import QldTrafficClient
from .vic import BASE_URL as VIC_BASE_URL
from .vic import VicDisruptionsClient
from .vic import parse_features as parse_vic_features
from .wa import BASE_URL as WA_BASE_URL
from .wa import ROADWORKS_LAYER as WA_ROADWORKS_LAYER
from .wa import WaMainRoadsClient

__all__ = [
    "NswLiveTrafficClient",
    "NSW_BASE_URL",
    "NSW_LAYERS",
    "parse_nsw_features",
    "VicDisruptionsClient",
    "VIC_BASE_URL",
    "parse_vic_features",
    "WaMainRoadsClient",
    "WA_BASE_URL",
    "WA_ROADWORKS_LAYER",
    "QldTrafficClient",
    "QLD_BASE_URL",
    "QLD_EVENT_TYPES",
    "QLD_PUBLIC_API_KEY",
]
