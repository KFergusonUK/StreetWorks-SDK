"""Tests for the USDOT WZDx feed registry helper.

The fixture is a trimmed real slice of the Socrata registry response
(2026-07-09), including the one inactive entry in the live registry
(Michigan DOT) - its ``url`` field is malformed/absent, unlike every active
entry, a useful real edge case for the defensive parsing.
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.wzdx.registry import REGISTRY_URL, list_feeds

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "wzdx_registry_sample.json").read_text(
        encoding="utf-8"
    )
)


@respx.mock
def test_list_feeds_defaults_to_active_only():
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    entries = list_feeds()
    assert len(entries) == 4  # the inactive Michigan DOT row is excluded
    assert all(e.active for e in entries)
    wsdot = next(e for e in entries if e.feed_name == "wsdot")
    assert wsdot.url == "https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed"
    assert wsdot.version == "4.2"
    assert wsdot.organization == "Washington State DOT"


@respx.mock
def test_list_feeds_active_only_false_includes_inactive():
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    entries = list_feeds(active_only=False)
    assert len(entries) == 5
    inactive = next(e for e in entries if not e.active)
    assert inactive.feed_name == "michigandot"
    assert inactive.url is None  # malformed/absent in the live registry - handled, not crashed on
