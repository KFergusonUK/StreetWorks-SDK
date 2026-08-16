"""Tests for streetworks.arcgis.guernsey - wiring only; the pagination
strategy itself is tested generically in test_arcgis_client.py.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.arcgis.guernsey import BASE_URL, STREETS_LAYER, GuernseyStreetsClient


@respx.mock
def test_iter_streets_defaults_to_the_real_road_not_blank_filter():
    respx.get(f"{BASE_URL}/{STREETS_LAYER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectIdField": None,
                "maxRecordCount": 2000,
                "advancedQueryCapabilities": {"supportsPagination": True},
                "fields": [{"name": "OBJECTID"}],
            },
        )
    )
    query_route = respx.get(f"{BASE_URL}/{STREETS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with GuernseyStreetsClient() as guernsey:
        list(guernsey.iter_streets())
    sent_where = query_route.calls[0].request.url.params.get("where")
    assert sent_where == "ROAD<>' '"


@respx.mock
def test_iter_streets_passes_through_a_custom_where_clause():
    respx.get(f"{BASE_URL}/{STREETS_LAYER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectIdField": None,
                "maxRecordCount": 2000,
                "advancedQueryCapabilities": {"supportsPagination": True},
                "fields": [{"name": "OBJECTID"}],
            },
        )
    )
    query_route = respx.get(f"{BASE_URL}/{STREETS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with GuernseyStreetsClient() as guernsey:
        list(guernsey.iter_streets(where="1=1"))
    sent_where = query_route.calls[0].request.url.params.get("where")
    assert sent_where == "1=1"


@respx.mock
def test_iter_streets_yields_real_features():
    respx.get(f"{BASE_URL}/{STREETS_LAYER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectIdField": None,
                "maxRecordCount": 2000,
                "advancedQueryCapabilities": {"supportsPagination": True},
                "fields": [{"name": "OBJECTID"}],
            },
        )
    )
    respx.get(f"{BASE_URL}/{STREETS_LAYER}/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": None,
                        "properties": {"OBJECTID": 1, "ROAD": "CANDIE ROAD"},
                    }
                ],
            },
        )
    )
    with GuernseyStreetsClient() as guernsey:
        records = list(guernsey.iter_streets())
    assert records[0]["properties"]["ROAD"] == "CANDIE ROAD"
