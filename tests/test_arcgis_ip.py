"""Tests for streetworks.arcgis.ip - wiring only; the pagination strategy
itself is tested generically in test_arcgis_client.py.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.arcgis.ip import BASE_URL, CONDICIONAMENTOS_LAYER, IPRoadworksClient

_LAYER_META = {
    "objectIdField": "objectid",
    "maxRecordCount": 1000,
    "advancedQueryCapabilities": {"supportsPagination": True},
    "fields": [{"name": "objectid"}],
}


@respx.mock
def test_iter_roadworks_filters_to_the_real_tipo_values_server_side():
    respx.get(f"{BASE_URL}/{CONDICIONAMENTOS_LAYER}").mock(
        return_value=httpx.Response(200, json=_LAYER_META)
    )
    query_route = respx.get(f"{BASE_URL}/{CONDICIONAMENTOS_LAYER}/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [-8.6, 41.1]},
                        "properties": {"objectid": 1, "tipo": "MaintenanceWorks"},
                    }
                ],
            },
        )
    )
    with IPRoadworksClient() as ip:
        records = list(ip.iter_roadworks())
    assert records[0]["properties"]["tipo"] == "MaintenanceWorks"
    sent_where = query_route.calls[0].request.url.params.get("where")
    assert sent_where == "tipo IN ('MaintenanceWorks','ConstructionWorks')"


@respx.mock
def test_iter_condicionamentos_defaults_to_unfiltered():
    respx.get(f"{BASE_URL}/{CONDICIONAMENTOS_LAYER}").mock(
        return_value=httpx.Response(200, json=_LAYER_META)
    )
    query_route = respx.get(f"{BASE_URL}/{CONDICIONAMENTOS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with IPRoadworksClient() as ip:
        list(ip.iter_condicionamentos())
    assert query_route.calls[0].request.url.params.get("where") == "1=1"
