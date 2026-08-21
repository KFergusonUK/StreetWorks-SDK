"""Tests for streetworks.arcgis.dc - wiring only; the pagination strategy
itself is tested generically in test_arcgis_client.py.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.arcgis.dc import BASE_URL, CONSTRUCTION_PERMIT_LAYER, DCConstructionPermitsClient


@respx.mock
def test_iter_roadworks_queries_the_real_construction_permit_layer():
    respx.get(f"{BASE_URL}/{CONSTRUCTION_PERMIT_LAYER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectIdField": None,
                "maxRecordCount": 1000,
                "advancedQueryCapabilities": {"supportsPagination": True},
                "fields": [{"name": "OBJECTID"}],
            },
        )
    )
    respx.get(f"{BASE_URL}/{CONSTRUCTION_PERMIT_LAYER}/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": None,
                        "properties": {"OBJECTID": 1, "PERMITNUMBER": "PA1"},
                    }
                ],
            },
        )
    )
    with DCConstructionPermitsClient() as dc:
        records = list(dc.iter_roadworks())
    assert records[0]["properties"]["PERMITNUMBER"] == "PA1"


@respx.mock
def test_iter_roadworks_passes_through_a_custom_where_clause():
    respx.get(f"{BASE_URL}/{CONSTRUCTION_PERMIT_LAYER}").mock(
        return_value=httpx.Response(
            200,
            json={
                "objectIdField": None,
                "maxRecordCount": 1000,
                "advancedQueryCapabilities": {"supportsPagination": True},
                "fields": [{"name": "OBJECTID"}],
            },
        )
    )
    query_route = respx.get(f"{BASE_URL}/{CONSTRUCTION_PERMIT_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with DCConstructionPermitsClient() as dc:
        list(dc.iter_roadworks(where="STATUS='Issued'"))
    sent_where = query_route.calls[0].request.url.params.get("where")
    assert sent_where == "STATUS='Issued'"
