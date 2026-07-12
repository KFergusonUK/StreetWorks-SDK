"""WZDx (Work Zone Data Exchange) - the US standard for work zone data.

A parser for WZDx GeoJSON road events (v3.1-v4.2, version-tolerant), a
generic client that fetches any agency's feed URL (WZDx is published
independently by ~40+ agencies, not one central API), and a helper to
discover feed URLs from the USDOT feed registry.
"""

from .client import WZDxClient, WZDxFeed
from .models import WORK_ZONE_EVENT_TYPES, Geometry, Relationship, RoadEvent
from .parser import parse_road_events
from .registry import REGISTRY_URL, RegistryEntry, list_feeds

__all__ = [
    "RoadEvent",
    "Geometry",
    "Relationship",
    "WORK_ZONE_EVENT_TYPES",
    "parse_road_events",
    "WZDxClient",
    "WZDxFeed",
    "RegistryEntry",
    "list_feeds",
    "REGISTRY_URL",
]
