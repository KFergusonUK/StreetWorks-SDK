"""USDOT WZDx Feed Registry - discover feed URLs.

The registry (`datahub.transportation.gov <https://datahub.transportation.gov/Roadways-and-Bridges/Work-Zone-Data-Feed-Registry/69qe-yiui/about_data>`_,
a Socrata dataset) lists every agency-published WZDx feed: URL, format,
version, and whether it's currently active. No credentials required. As of
2026-07 it lists ~40 feeds; most WZDx versions in the wild are v4.x, but
v3.1 and non-standard-versioned entries (e.g. "vCWZ 1.0") are present too -
:func:`list_feeds` doesn't filter on version, only on ``active``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["RegistryEntry", "list_feeds", "REGISTRY_URL"]

JSON = dict[str, Any]

REGISTRY_URL = "https://datahub.transportation.gov/resource/69qe-yiui.json"


@dataclass(frozen=True)
class RegistryEntry:
    """One registered feed."""

    state: str | None
    organization: str | None
    feed_name: str | None
    url: str | None
    format: str | None
    version: str | None
    active: bool | None
    raw: JSON


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return None


def _parse_entry(row: JSON) -> RegistryEntry:
    url_field = row.get("url")
    if isinstance(url_field, dict):
        url = url_field.get("url")
    elif isinstance(url_field, str):
        url = url_field
    else:
        url = None
    return RegistryEntry(
        state=row.get("state"),
        organization=row.get("issuingorganization"),
        feed_name=row.get("feedname"),
        url=url,
        format=row.get("format"),
        version=row.get("version"),
        active=_as_bool(row.get("active")),
        raw=row,
    )


def list_feeds(
    *,
    active_only: bool = True,
    registry_url: str = REGISTRY_URL,
    retry: RetryConfig | None = None,
    timeout: float = 30.0,
    client: httpx.Client | None = None,
) -> list[RegistryEntry]:
    """Fetch and parse the WZDx feed registry. ``active_only`` (default)
    drops entries the registry itself has flagged inactive - it does not
    verify the feed is actually reachable right now."""
    owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
    transport = SyncTransport(retry=retry or RetryConfig(), timeout=timeout, client=owned_client)
    try:
        response = transport.request("GET", registry_url, params={"$limit": 1000})
        entries = [_parse_entry(row) for row in response.json()]
    finally:
        transport.close()
    return [e for e in entries if e.active] if active_only else entries
