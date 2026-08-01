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
richer, per-record authority split - see :mod:`streetworks.au.qld`; South
Australia is an ArcGIS **MapServer** (see :mod:`streetworks.au.sa`), a
Phase 1 scaffold; the Australian Capital Territory (see
:mod:`streetworks.au.act`) is the first with genuine **municipal/local-
street** coverage - every other member, including the big five, is
state-network only; Tasmania (see :mod:`streetworks.au.tas`) is the first
with real **line geometry**, not just points, and a genuinely different
native CRS (GDA94/MGA zone 55, not Web Mercator) from WA/SA's own ArcGIS
services. NSW and Victoria are **Phase 2 confirmed** (2026-07-30, against
real credentialed pulls - see each module's own docstring); WA, QLD, ACT,
and TAS are **credential-free** (QLD via a real public API key, never a
private one) and shipped live-verified with a real fixture from day one,
never Credentials-wanted scaffolds - TAS ships with a genuinely
unconfirmed licence, the same basis :mod:`streetworks.arcgis.jersey` uses,
distinct from being blocked; **South Australia is a Phase 1 scaffold,
blocked on two access gates - a token-gated query endpoint and a
geo-restricted host - see :mod:`streetworks.au.sa`'s own module
docstring** and the README's Credentials wanted section.

**The Northern Territory was investigated and is registered as a
documented, honestly-unavailable scaffold** (see :mod:`streetworks.au.nt`)
- not silently skipped, but not a working client either: Road Report NT's
real backend is not a REST/GeoJSON API at all - it's a SignalR real-time
hub (confirmed live, reverse-engineered from the site's own minified
Angular bundle: a genuine ``roadsReportingHub`` connection invoking hub
methods like ``GetAllMajorRoadObstructions``), a materially different,
undocumented client protocol this SDK has never needed elsewhere, on top
of the investigation brief's own already-flagged concerns (roadworks is a
minor subset of a road-condition system dominated by closures/flooding,
and the licence is unspecified). ``RoadReportNtClient()`` always raises
:class:`~streetworks.exceptions.ProviderUnavailableError` rather than
dressing that inference up as a stable contract - revisit if a documented
REST equivalent ever surfaces.
"""

from .act import BASE_URL as ACT_BASE_URL
from .act import ROADWORKS_LAYER as ACT_ROADWORKS_LAYER
from .act import ActTtmClient
from .nsw import BASE_URL as NSW_BASE_URL
from .nsw import LAYERS as NSW_LAYERS
from .nsw import NswLiveTrafficClient
from .nsw import parse_features as parse_nsw_features
from .nt import RoadReportNtClient
from .qld import BASE_URL as QLD_BASE_URL
from .qld import EVENT_TYPES as QLD_EVENT_TYPES
from .qld import PUBLIC_API_KEY as QLD_PUBLIC_API_KEY
from .qld import QldTrafficClient
from .sa import BASE_URL as SA_BASE_URL
from .sa import CLOSURES_LAYER as SA_CLOSURES_LAYER
from .sa import ROADWORKS_AND_INCIDENTS_LAYER as SA_ROADWORKS_AND_INCIDENTS_LAYER
from .sa import TrafficSaClient
from .tas import BASE_URL as TAS_BASE_URL
from .tas import ROADWORKS_LAYER as TAS_ROADWORKS_LAYER
from .tas import TasRoadworksClient
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
    "TrafficSaClient",
    "SA_BASE_URL",
    "SA_ROADWORKS_AND_INCIDENTS_LAYER",
    "SA_CLOSURES_LAYER",
    "ActTtmClient",
    "ACT_BASE_URL",
    "ACT_ROADWORKS_LAYER",
    "TasRoadworksClient",
    "TAS_BASE_URL",
    "TAS_ROADWORKS_LAYER",
    "RoadReportNtClient",
]
