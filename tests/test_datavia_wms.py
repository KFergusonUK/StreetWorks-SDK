"""Tests for DataVIA WMS support (GetMap / GetFeatureInfo / capabilities)."""

import httpx
import pytest
import respx

from streetworks.datavia import AsyncDataViaClient, DataViaClient, Layer
from streetworks.datavia.client import BASIC_SERVICE_URL
from streetworks.exceptions import APIError

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def _client() -> DataViaClient:
    return DataViaClient(username="u", password="p")


@respx.mock
def test_get_map_builds_wms_130_request_and_returns_image():
    route = respx.get(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
    )
    with _client() as dv:
        image = dv.get_map(
            [Layer.STREET_LINES, "ms:ESUStreets"],
            (424000, 533800, 426000, 535200),
            width=512,
            height=256,
        )
    assert image == PNG
    q = route.calls[0].request.url.params
    assert q["service"] == "WMS" and q["version"] == "1.3.0" and q["request"] == "GetMap"
    # WMS layer names are unprefixed (live-verified); the ms: WFS namespace
    # is stripped from enum values and passed-through strings alike
    assert q["layers"] == "StreetLines,ESUStreets"
    assert q["crs"] == "EPSG:27700" and "srs" not in q
    assert q["bbox"] == "424000,533800,426000,535200"
    assert q["width"] == "512" and q["height"] == "256"
    assert q["transparent"] == "TRUE"


@respx.mock
def test_get_map_version_111_uses_srs():
    route = respx.get(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
    )
    with _client() as dv:
        dv.get_map(Layer.STREET_LINES, (1, 2, 3, 4), version="1.1.1")
    q = route.calls[0].request.url.params
    assert q["srs"] == "EPSG:27700" and "crs" not in q


@respx.mock
def test_get_map_raises_on_service_exception_xml():
    """WMS servers report errors as XML with HTTP 200; that must not be
    silently returned as 'image' bytes."""
    respx.get(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(
            200,
            content=b'<?xml version="1.0"?><ServiceExceptionReport>'
            b"<ServiceException>Layer not defined</ServiceException>"
            b"</ServiceExceptionReport>",
            headers={"content-type": "application/vnd.ogc.se_xml"},
        )
    )
    with _client() as dv:
        with pytest.raises(APIError, match="Layer not defined"):
            dv.get_map(Layer.STREET_LINES, (1, 2, 3, 4))


@respx.mock
def test_get_feature_info_130_uses_i_j_and_parses_json():
    route = respx.get(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(
            200, json={"type": "FeatureCollection", "features": [{"id": "s1"}]}
        )
    )
    with _client() as dv:
        info = dv.get_feature_info(
            Layer.STREET_LINES, (1, 2, 3, 4), i=100, j=200, width=256, height=256
        )
    assert info["features"][0]["id"] == "s1"
    q = route.calls[0].request.url.params
    assert q["request"] == "GetFeatureInfo"
    assert q["query_layers"] == "StreetLines"
    assert q["i"] == "100" and q["j"] == "200" and "x" not in q
    assert q["info_format"] == "application/json"
    assert "format" not in q and "transparent" not in q


@respx.mock
def test_get_feature_info_111_uses_x_y():
    route = respx.get(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(200, json={"features": []})
    )
    with _client() as dv:
        dv.get_feature_info(
            Layer.STREET_LINES, (1, 2, 3, 4), i=10, j=20, version="1.1.1"
        )
    q = route.calls[0].request.url.params
    assert q["x"] == "10" and q["y"] == "20" and "i" not in q


@respx.mock
def test_wms_capabilities():
    respx.get(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(200, text="<WMS_Capabilities/>")
    )
    with _client() as dv:
        assert "WMS_Capabilities" in dv.wms_capabilities()


@respx.mock
async def test_async_get_map():
    respx.get(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
    )
    async with AsyncDataViaClient(username="u", password="p") as dv:
        image = await dv.get_map(Layer.STREET_LINES, (1, 2, 3, 4))
    assert image.startswith(b"\x89PNG")


@respx.mock
def test_wms_aggregate_layer_string_passes_through():
    """The WMS-only aggregate layers (e.g. "Streets") have no prefix and must
    pass through untouched."""
    route = respx.get(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
    )
    with _client() as dv:
        dv.get_map("Streets", (1, 2, 3, 4))
    assert route.calls[0].request.url.params["layers"] == "Streets"
