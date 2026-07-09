"""Generic WZDx feed client.

WZDx isn't one API - it's a schema published independently by ~40+ US
agencies (state DOTs, MPOs, tolling authorities...), each at their own URL,
mostly credential-free. So unlike the other clients in this SDK,
:class:`WZDxClient` has no fixed base URL: :meth:`WZDxClient.fetch` takes
the full feed URL each call. Use :mod:`streetworks.wzdx.registry` to
discover feed URLs from the USDOT registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from .._dt import parse_iso8601 as _dt
from .._transport import RetryConfig, SyncTransport
from .models import RoadEvent
from .parser import parse_road_events

__all__ = ["WZDxClient", "WZDxFeed"]

JSON = dict[str, Any]


@dataclass
class WZDxFeed:
    """One fetched feed: its road events plus the feed-level metadata a
    caller needs to know what they're looking at - WZDx versions differ
    (v3.1-v4.2 observed live), so callers should check ``version`` rather
    than assume."""

    version: str | None
    publisher: str | None
    update_date: datetime | None
    road_events: tuple[RoadEvent, ...]
    raw: JSON


def _feed_info(payload: JSON) -> JSON:
    """The feed-info key itself varies live: most v4.1 feeds use
    ``feed_info``, but two v4.0 feeds observed use the older
    ``road_event_feed_info`` name, and one v4.2 feed emits both at once -
    so this isn't a clean version-string branch, both are checked."""
    return payload.get("feed_info") or payload.get("road_event_feed_info") or {}


class WZDxClient:
    """Fetch and parse any WZDx feed URL. No credentials required.

    >>> from streetworks.wzdx import WZDxClient
    >>> with WZDxClient() as wzdx:
    ...     feed = wzdx.fetch("https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed")
    ...     print(feed.version, len(feed.road_events))
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def fetch(self, feed_url: str) -> WZDxFeed:
        """Fetch and parse one WZDx feed. ``feed_url`` is the feed's own
        URL (from the registry, or an agency's documentation) - there's no
        shared base URL to combine it with."""
        response = self._transport.request("GET", feed_url)
        payload = response.json()
        info = _feed_info(payload)
        return WZDxFeed(
            version=info.get("version"),
            publisher=info.get("publisher"),
            update_date=_dt(info.get("update_date")),
            road_events=tuple(parse_road_events(payload)),
            raw=payload,
        )

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> WZDxClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
