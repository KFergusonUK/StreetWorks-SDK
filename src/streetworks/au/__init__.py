"""Australia - state traffic-disruption feeds, one file per state/territory
(the same cluster shape as :mod:`streetworks.datex2`/:mod:`streetworks.ogc`).

There is no Australian equivalent of the UK's Street Manager: no national,
promoter-submitted statutory permit register exists as open data. Each
state/territory road authority instead publishes its own live traffic-
disruption feed - roadworks alongside incidents, fires, floods and other
hazards - so this cluster is a set of state adapters, not one national
client. See :mod:`streetworks.au.nsw` for the first member (New South
Wales, TfNSW's Live Traffic Hazards API) - **a Credentials-wanted
scaffold**, pending live verification, grouped with Norway/Sweden/Denmark
(see the README's Credentials wanted section).
"""

from .nsw import BASE_URL as NSW_BASE_URL
from .nsw import NswLiveTrafficClient
from .nsw import parse_features as parse_nsw_features

__all__ = ["NswLiveTrafficClient", "NSW_BASE_URL", "parse_nsw_features"]
