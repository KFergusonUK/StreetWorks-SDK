"""Tests for the Stockholm (Trafikkontoret) scaffold.

**Phase 0 - even less confirmed than Trafikverket's own scaffold**, see
the module docstring in ``streetworks.stockholm.client``. No real
response has ever been seen from this platform - every real surface
tested (WFS/WMS ``GetCapabilities``) 401s before any schema is revealed.
These tests exercise only the one real, confirmed request shape this
client can build without guessing a dataset/layer name.
"""

import httpx
import pytest
import respx

from streetworks.stockholm import BASE_URL, StockholmClient


def test_requires_an_api_key():
    with pytest.raises(ValueError):
        StockholmClient(api_key="")


@respx.mock
def test_get_wfs_capabilities_requests_the_real_confirmed_endpoint():
    route = respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, text="<WFS_Capabilities/>")
    )
    with StockholmClient(api_key="my-key") as stockholm:
        text = stockholm.get_wfs_capabilities()
    assert text == "<WFS_Capabilities/>"
    params = route.calls[0].request.url.params
    assert params["service"] == "WFS"
    assert params["request"] == "GetCapabilities"
    assert params["apiKey"] == "my-key"
