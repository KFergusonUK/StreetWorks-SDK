"""Wales motorway/trunk road data via Traffic Wales open RSS (Welsh Government).

Credential-free. Attribution required: Traffic Wales must be credited as the
data source.
"""

from .client import ATTRIBUTION, Feed, FeedItem, Language, TrafficWalesClient, parse_feed

__all__ = [
    "TrafficWalesClient",
    "Feed",
    "Language",
    "FeedItem",
    "parse_feed",
    "ATTRIBUTION",
]
