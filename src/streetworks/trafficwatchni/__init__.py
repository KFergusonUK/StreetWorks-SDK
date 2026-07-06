"""Northern Ireland roadworks via TrafficWatchNI RSS (DfI TICC).

Credential-free. Attribution required: credit the DfI Traffic Information
and Control Centre as the source and preserve item URLs.
"""

from .client import (
    ATTRIBUTION,
    Feed,
    Region,
    RoadworksItem,
    TrafficWatchNIClient,
    extract_fields,
    parse_feed,
)

__all__ = [
    "TrafficWatchNIClient",
    "Feed",
    "Region",
    "RoadworksItem",
    "parse_feed",
    "extract_fields",
    "ATTRIBUTION",
]
