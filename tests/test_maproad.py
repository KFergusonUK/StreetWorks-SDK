"""Tests for the Ireland (MapRoad Roadworks Licensing) documented
scaffold.

This is not a functional adapter - see the module docstring in
``streetworks.maproad.client``. No fixture exists because there is
nothing publicly documented to parse: ``MapRoadClient`` always raises
``ProviderUnavailableError`` immediately, with no network call.
"""

from __future__ import annotations

import pytest

from streetworks.exceptions import ProviderUnavailableError
from streetworks.maproad import MapRoadClient
from streetworks.registry import _REGISTRY, get_provider


def _get_entry(key: str):
    return next(e for e in _REGISTRY if e.key == key)


def test_client_raises_provider_unavailable_on_construction():
    with pytest.raises(ProviderUnavailableError):
        MapRoadClient()


def test_raise_happens_regardless_of_arguments_passed():
    """No credential/config combination makes this work - the blocker is
    a formal data-sharing arrangement, not a missing key."""
    with pytest.raises(ProviderUnavailableError):
        MapRoadClient(api_key="anything", base_url="https://example.test")


def test_error_message_explains_the_real_finding_not_just_that_it_failed():
    with pytest.raises(ProviderUnavailableError) as excinfo:
        MapRoadClient()
    message = str(excinfo.value)
    assert "Data Sharing" in message
    assert "rmo.ie" in message


def test_no_network_call_is_made():
    """A raise on construction, before anything resembling an HTTP client
    is built, is itself the guarantee - nothing here to mock and confirm
    unreached, unlike every other client's respx-backed test."""
    import inspect

    source = inspect.getsource(MapRoadClient)
    assert "httpx" not in source
    assert "requests" not in source


# --------------------------------------------------------------------------- #
# Registry consistency - maproad is registered honestly, not silently omitted.
# --------------------------------------------------------------------------- #


def test_maproad_is_registered_and_unverified():
    entry = _get_entry("maproad")
    assert entry.verified is False
    assert entry.client is MapRoadClient


def test_maproad_client_construction_raises_even_via_the_registry():
    entry = _get_entry("maproad")
    with pytest.raises(ProviderUnavailableError):
        entry.client()


def test_get_provider_resolves_maproad_but_raises_on_use():
    MapRoadClientResolved = get_provider("maproad")
    assert MapRoadClientResolved is MapRoadClient
    with pytest.raises(ProviderUnavailableError):
        MapRoadClientResolved()
