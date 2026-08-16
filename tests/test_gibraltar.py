"""Tests for streetworks.gibraltar - wiring only, including the real
GeoServer quirks this module works around (application/json-only output,
sortBy-required pagination). See streetworks.gibraltar.client's module
docstring for the live evidence behind each.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.exceptions import TruncatedResultError
from streetworks.gibraltar import BASE_URL, STREETS_TYPE_NAME, GibraltarStreetsClient


def _page(features: list[dict], *, matched: int) -> dict:
    return {
        "type": "FeatureCollection",
        "features": features,
        "totalFeatures": matched,
        "numberMatched": matched,
        "numberReturned": len(features),
    }


@respx.mock
def test_iter_streets_requests_plain_json_not_geo_json():
    route = respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json=_page([], matched=0))
    )
    with GibraltarStreetsClient() as gibraltar:
        list(gibraltar.iter_streets())
    params = route.calls[0].request.url.params
    assert params.get("OUTPUTFORMAT") == "application/json"
    assert params.get("SRSNAME") == "EPSG:4326"
    assert params.get("TYPENAMES") == STREETS_TYPE_NAME


@respx.mock
def test_iter_streets_sorts_by_inspireid_for_pagination():
    route = respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json=_page([], matched=0))
    )
    with GibraltarStreetsClient() as gibraltar:
        list(gibraltar.iter_streets())
    params = route.calls[0].request.url.params
    assert params.get("SORTBY") == "inspireId"


@respx.mock
def test_iter_streets_yields_real_features_in_one_page():
    feature = {
        "type": "Feature",
        "geometry": {"type": "MultiLineString", "coordinates": [[[-5.35, 36.14], [-5.34, 36.15]]]},
        "properties": {"inspireId": 1, "name": "Queensway"},
    }
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=_page([feature], matched=1)))
    with GibraltarStreetsClient() as gibraltar:
        features = list(gibraltar.iter_streets())
    assert len(features) == 1
    assert features[0]["properties"]["name"] == "Queensway"


@respx.mock
def test_iter_streets_raises_rather_than_silently_truncating():
    # A real page shorter than the page size but with numberMatched
    # still ahead of what was actually received - never trusted blindly.
    feature = {
        "type": "Feature",
        "geometry": {"type": "MultiLineString", "coordinates": [[[-5.35, 36.14]]]},
        "properties": {"inspireId": 1, "name": "Queensway"},
    }
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json=_page([feature], matched=500))
    )
    with GibraltarStreetsClient() as gibraltar:
        try:
            list(gibraltar.iter_streets())
            raised = False
        except TruncatedResultError:
            raised = True
    assert raised
