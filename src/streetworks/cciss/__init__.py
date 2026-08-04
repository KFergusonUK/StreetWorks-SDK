"""Italy: CCISS real-time traffic bulletin RSS - Italy's confirmed
official RTTI/SRTI National Access Point, reached via its real, public,
keyless RSS feed. See :mod:`streetworks.cciss.client` for the full
investigation.
"""

from .client import RSS_URL, BulletinItem, CcissClient, parse_feed

__all__ = ["RSS_URL", "BulletinItem", "CcissClient", "parse_feed"]
