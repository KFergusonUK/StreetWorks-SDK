"""Tests for streetworks.lmi - wiring only, including the real GeoServer
quirk this module works around (application/json-only output). See
streetworks.lmi.client's module docstring for the live evidence behind
each.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.exceptions import TruncatedResultError
from streetworks.lmi import BASE_URL, STREETS_TYPE_NAME, LmiStreetsClient


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
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=_page([], matched=0)))
    with LmiStreetsClient() as lmi:
        list(lmi.iter_streets())
    params = route.calls[0].request.url.params
    assert params.get("OUTPUTFORMAT") == "application/json"
    assert params.get("SRSNAME") == "EPSG:4326"
    assert params.get("TYPENAMES") == STREETS_TYPE_NAME


@respx.mock
def test_iter_streets_yields_real_features_in_one_page():
    feature = {
        "type": "Feature",
        "geometry": {"type": "MultiLineString", "coordinates": [[[-21.9, 64.1], [-21.8, 64.2]]]},
        "properties": {"objectid": 1, "nafnfitju": "Laugavegur"},
    }
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=_page([feature], matched=1)))
    with LmiStreetsClient() as lmi:
        features = list(lmi.iter_streets())
    assert len(features) == 1
    assert features[0]["properties"]["nafnfitju"] == "Laugavegur"


@respx.mock
def test_iter_streets_raises_rather_than_silently_truncating():
    feature = {
        "type": "Feature",
        "geometry": {"type": "MultiLineString", "coordinates": [[[-21.9, 64.1]]]},
        "properties": {"objectid": 1, "nafnfitju": "Laugavegur"},
    }
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=_page([feature], matched=500)))
    with LmiStreetsClient() as lmi:
        try:
            list(lmi.iter_streets())
            raised = False
        except TruncatedResultError:
            raised = True
    assert raised
