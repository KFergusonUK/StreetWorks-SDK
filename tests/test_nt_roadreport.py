"""Tests for the Northern Territory (Road Report NT) documented scaffold.

This is not a functional adapter - see the module docstring in
``streetworks.au.nt``. No fixture exists because there is nothing real to
parse: ``RoadReportNtClient`` always raises
``ProviderUnavailableError`` immediately, with no network call.
"""

from __future__ import annotations

import pytest

from streetworks.au.nt import RoadReportNtClient
from streetworks.exceptions import ProviderUnavailableError
from streetworks.registry import _REGISTRY, get_provider


def _get_entry(key: str):
    return next(e for e in _REGISTRY if e.key == key)


def test_client_raises_provider_unavailable_on_construction():
    with pytest.raises(ProviderUnavailableError):
        RoadReportNtClient()


def test_raise_happens_regardless_of_arguments_passed():
    """No credential/config combination makes this work - the blocker is
    the total absence of a published API, not a missing key."""
    with pytest.raises(ProviderUnavailableError):
        RoadReportNtClient(api_key="anything", base_url="https://example.test")


def test_error_message_explains_the_real_finding_not_just_that_it_failed():
    with pytest.raises(ProviderUnavailableError) as excinfo:
        RoadReportNtClient()
    message = str(excinfo.value)
    assert "SignalR" in message
    assert "no published" in message.lower() or "no published" in message


def test_no_network_call_is_made():
    """A raise on construction, before anything resembling an HTTP client
    is built, is itself the guarantee - nothing here to mock and confirm
    unreached, unlike every other client's respx-backed test."""
    import inspect

    source = inspect.getsource(RoadReportNtClient)
    assert "httpx" not in source
    assert "requests" not in source


# --------------------------------------------------------------------------- #
# Registry consistency - nt is registered honestly, not silently omitted.
# --------------------------------------------------------------------------- #


def test_nt_is_registered_and_unverified():
    entry = _get_entry("nt")
    assert entry.verified is False
    assert entry.client is RoadReportNtClient


def test_nt_client_construction_raises_even_via_the_registry():
    entry = _get_entry("nt")
    with pytest.raises(ProviderUnavailableError):
        entry.client()


def test_get_provider_resolves_nt_but_raises_on_use():
    NtClient = get_provider("nt")
    assert NtClient is RoadReportNtClient
    with pytest.raises(ProviderUnavailableError):
        NtClient()
