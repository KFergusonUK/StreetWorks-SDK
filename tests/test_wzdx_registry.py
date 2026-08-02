"""Tests for the USDOT WZDx feed registry helper.

The fixture is a trimmed real slice of the Socrata registry response
(2026-08-02): the one inactive entry in the live registry (Michigan DOT,
also missing ``version`` - a useful real edge case for the defensive
parsing), a real Quebec City (Canada, non-US) row, a real
``needapikey: true`` row (Colorado DOT's WZDx feed), and its real CWZ
sibling (``cdot_cwz``, ``version == "CWZ 1.0"``) - the real WZDx/CWZ
discriminator, confirmed live to NOT be the ``format`` field (see
``streetworks.wzdx.registry``'s own module docstring).
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
def test_list_feeds_defaults_to_active_and_wzdx_only():
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    entries = list_feeds()
    # Active: 6/7. WZDx-only additionally drops the real CWZ sibling: 5.
    assert len(entries) == 5
    assert all(e.active for e in entries)
    assert all(e.is_supported_wzdx for e in entries)
    assert "cdot_cwz" not in {e.feed_name for e in entries}
    wsdot = next(e for e in entries if e.feed_name == "wsdot")
    assert wsdot.url == "https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed"
    assert wsdot.version == "4.2"
    assert wsdot.organization == "Washington State DOT"


@respx.mock
def test_list_feeds_active_only_false_includes_inactive():
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    entries = list_feeds(active_only=False, wzdx_only=False)
    assert len(entries) == 7
    inactive = next(e for e in entries if not e.active)
    assert inactive.feed_name == "michigandot"
    assert inactive.url is None  # malformed/absent in the live registry - handled, not crashed on
    assert inactive.version is None  # a real, confirmed-live gap - not just hypothetical


@respx.mock
def test_wzdx_only_false_includes_cwz():
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    entries = list_feeds(wzdx_only=False)
    cwz = next(e for e in entries if e.feed_name == "cdot_cwz")
    assert cwz.version == "CWZ 1.0"
    assert cwz.is_supported_wzdx is False


@respx.mock
def test_needapikey_and_apikeyurl_are_parsed():
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    entries = list_feeds()
    cdot = next(e for e in entries if e.feed_name == "cdot")
    assert cdot.needapikey is True
    assert cdot.apikeyurl == "https://maps.cotrip.org/help/section/for-developers.html"


@respx.mock
def test_needapikey_defaults_to_false_when_absent():
    """27/41 real rows simply omit needapikey rather than stating false -
    absence means no key required, confirmed live. See module docstring."""
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    entries = list_feeds()
    wsdot = next(e for e in entries if e.feed_name == "wsdot")
    assert wsdot.needapikey is False
    assert wsdot.apikeyurl is None


@respx.mock
def test_registry_is_not_us_only():
    """A real, live, active Quebec City (Canada) row - confirmed, not
    hypothetical. Callers wanting US-only coverage filter on state/
    organization themselves; this module doesn't assume "US" is the only
    real value."""
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    entries = list_feeds()
    quebec = next(e for e in entries if e.feed_name == "quebec")
    assert quebec.state == "n/a"
    assert quebec.organization == "Quebec City"


@respx.mock
def test_new_york_feed_needs_no_credentials():
    """511NY (NYSDOT) - the first concrete verified US feed. Confirmed
    live: no needapikey field on its real registry row at all."""
    respx.get(REGISTRY_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    entries = list_feeds()
    nysdot = next(e for e in entries if e.feed_name == "nysdot")
    assert nysdot.url == "https://511ny.org/api/wzdx"
    assert nysdot.needapikey is False
    assert nysdot.version == "4.1"
