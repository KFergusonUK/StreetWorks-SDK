"""Tests for streetworks.arcgis.jersey - wiring only; the pagination
strategy itself is tested generically in test_arcgis_client.py against
the exact real Jersey behaviour that motivated it.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.arcgis.jersey import BASE_URL, ROADWORKS_LAYER, JerseyRoadworksClient


@respx.mock
def test_iter_roadworks_queries_the_real_roadworks_layer():
    respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectIdField": "FID",
                "maxRecordCount": 1000,
                "advancedQueryCapabilities": {"supportsPagination": False},
                "fields": [{"name": "FID"}],
            },
        )
    )
    respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "geometry": None, "properties": {"FID": 1, "PROJID": "P1"}}
                ],
            },
        )
    )
    with JerseyRoadworksClient() as jersey:
        records = list(jersey.iter_roadworks())
    assert records[0]["properties"]["PROJID"] == "P1"


@respx.mock
def test_iter_roadworks_passes_through_a_custom_where_clause():
    route = respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectIdField": "FID",
                "maxRecordCount": 1000,
                "advancedQueryCapabilities": {"supportsPagination": False},
                "fields": [{"name": "FID"}],
            },
        )
    )
    query_route = respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with JerseyRoadworksClient() as jersey:
        list(jersey.iter_roadworks(where="PROJID='P108864-JSC'"))
    assert route.called
    sent_where = query_route.calls[0].request.url.params.get("where")
    assert sent_where == "PROJID='P108864-JSC'"
