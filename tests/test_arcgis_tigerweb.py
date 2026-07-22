"""Tests for streetworks.arcgis.tigerweb - wiring only; the pagination
strategy itself is tested generically in test_arcgis_client.py.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.arcgis.tigerweb import BASE_URL, LOCAL_ROADS_LAYER, TIGERwebClient


def _layer_info():
    return {
        "objectIdField": "OBJECTID",
        "maxRecordCount": 100000,
        "advancedQueryCapabilities": {"supportsPagination": True},
        "fields": [{"name": "OBJECTID"}],
    }


def _mock_layer_info(layer_id: int) -> None:
    respx.get(f"{BASE_URL}/{layer_id}").mock(return_value=httpx.Response(200, json=_layer_info()))


@respx.mock
def test_iter_roads_queries_the_local_roads_layer_by_default():
    _mock_layer_info(LOCAL_ROADS_LAYER)
    feature = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[-77.03, 38.89], [-77.02, 38.90]]},
        "properties": {"OBJECTID": 1, "NAME": "D St NW", "MTFCC": "S1400"},
    }
    respx.get(f"{BASE_URL}/{LOCAL_ROADS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": [feature]})
    )
    with TIGERwebClient() as tiger:
        roads = list(tiger.iter_roads())
    assert roads[0]["properties"]["NAME"] == "D St NW"


@respx.mock
def test_iter_roads_passes_bbox_as_an_envelope_geometry():
    _mock_layer_info(LOCAL_ROADS_LAYER)
    query_route = respx.get(f"{BASE_URL}/{LOCAL_ROADS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with TIGERwebClient() as tiger:
        list(tiger.iter_roads(bbox=(-77.05, 38.89, -77.03, 38.91)))
    params = query_route.calls[0].request.url.params
    assert params.get("geometryType") == "esriGeometryEnvelope"
    assert params.get("inSR") == "4326"
    assert params.get("outSR") == "4326"
    assert "-77.05" in params.get("geometry")


@respx.mock
def test_iter_roads_accepts_an_explicit_layer_id():
    from streetworks.arcgis.tigerweb import PRIMARY_ROADS_LAYER

    _mock_layer_info(PRIMARY_ROADS_LAYER)
    query_route = respx.get(f"{BASE_URL}/{PRIMARY_ROADS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with TIGERwebClient() as tiger:
        list(tiger.iter_roads(PRIMARY_ROADS_LAYER))
    assert query_route.called
