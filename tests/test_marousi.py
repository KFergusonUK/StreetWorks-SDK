"""Tests for streetworks.marousi - wiring only, including the real
GeoServer quirk this module works around (application/json-only
output). See streetworks.marousi.client's module docstring for the
live evidence behind each.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.marousi import BASE_URL, STREETS_TYPE_NAME, MarousiStreetsClient


@respx.mock
def test_iter_streets_requests_plain_json_not_geo_json():
    route = respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with MarousiStreetsClient() as marousi:
        list(marousi.iter_streets())
    params = route.calls[0].request.url.params
    assert params.get("OUTPUTFORMAT") == "application/json"
    assert params.get("SRSNAME") == "EPSG:4326"
    assert params.get("TYPENAMES") == STREETS_TYPE_NAME


@respx.mock
def test_iter_streets_yields_real_features():
    feature = {
        "type": "Feature",
        "geometry": {"type": "MultiPolygon", "coordinates": [[[[23.78, 38.02]]]]},
        "properties": {"id": 6, "onoma_is": "ΑΓΑΜΕΜΝΟΝΟΣ"},
    }
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200, json={"type": "FeatureCollection", "features": [feature]}
        )
    )
    with MarousiStreetsClient() as marousi:
        features = list(marousi.iter_streets())
    assert len(features) == 1
    assert features[0]["properties"]["onoma_is"] == "ΑΓΑΜΕΜΝΟΝΟΣ"
