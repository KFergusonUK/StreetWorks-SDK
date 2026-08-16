"""Tests for streetworks.arcgis.monaghan - wiring only; the pagination
strategy itself is tested generically in test_arcgis_client.py.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.arcgis.monaghan import BASE_URLS, ROADS_LAYER, MonaghanRoadsClient


def _mock_layer_info(base_url: str) -> None:
    respx.get(f"{base_url}/{ROADS_LAYER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectIdField": "OBJECTID",
                "maxRecordCount": 1000,
                "advancedQueryCapabilities": {"supportsPagination": True},
                "fields": [{"name": "OBJECTID"}],
            },
        )
    )


@respx.mock
def test_iter_roads_queries_the_real_local_service_by_default():
    _mock_layer_info(BASE_URLS["local"])
    respx.get(f"{BASE_URLS['local']}/{ROADS_LAYER}/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": None,
                        "properties": {"OBJECTID": 1, "Road_Name": "L-31011-0"},
                    }
                ],
            },
        )
    )
    with MonaghanRoadsClient() as monaghan:
        roads = list(monaghan.iter_roads())
    assert roads[0]["properties"]["Road_Name"] == "L-31011-0"


@respx.mock
def test_iter_roads_accepts_each_real_road_class():
    for road_class in ("national", "regional", "local"):
        _mock_layer_info(BASE_URLS[road_class])
        query_route = respx.get(f"{BASE_URLS[road_class]}/{ROADS_LAYER}/query").mock(
            return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
        )
        with MonaghanRoadsClient() as monaghan:
            list(monaghan.iter_roads(road_class))
        assert query_route.called
