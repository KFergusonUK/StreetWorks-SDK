"""Tests for streetworks.digiroad - wiring only. See
streetworks.digiroad.client's module docstring for the live evidence
behind the pagination/bbox/CRS choices this module makes.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.digiroad import BASE_URL, STREETS_TYPE_NAME, DigiroadClient


def _page(features: list[dict], *, matched: int) -> dict:
    return {
        "type": "FeatureCollection",
        "features": features,
        "numberMatched": matched,
        "numberReturned": len(features),
    }


@respx.mock
def test_iter_streets_requests_the_real_layer_and_crs():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=_page([], matched=0)))
    with DigiroadClient() as digiroad:
        list(digiroad.iter_streets())
    params = route.calls[0].request.url.params
    assert params.get("TYPENAMES") == STREETS_TYPE_NAME
    assert params.get("SRSNAME") == "EPSG:4326"


@respx.mock
def test_iter_streets_passes_bbox_as_a_real_bbox_param():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=_page([], matched=0)))
    with DigiroadClient() as digiroad:
        list(digiroad.iter_streets(bbox=(24.90, 60.14, 25.00, 60.22)))
    params = route.calls[0].request.url.params
    assert params.get("BBOX") == "24.9,60.14,25.0,60.22,EPSG:4326"


@respx.mock
def test_iter_streets_pages_past_the_real_per_request_cap():
    feature = {"type": "Feature", "geometry": None, "properties": {"link_id": "a:1"}}
    page1 = _page([feature] * 3, matched=5)
    page2 = _page([feature] * 2, matched=5)
    responses = [httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
    route = respx.get(BASE_URL).mock(side_effect=responses)
    with DigiroadClient() as digiroad:
        features = list(digiroad.iter_streets())
    assert len(features) == 5
    assert route.calls[1].request.url.params.get("STARTINDEX") == "3"
