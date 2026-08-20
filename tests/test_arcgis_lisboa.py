"""Tests for streetworks.arcgis.lisboa - wiring only; the pagination
strategy itself is tested generically in test_arcgis_client.py.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.arcgis.lisboa import BASE_URL, STREETS_LAYER, LisboaStreetsClient


@respx.mock
def test_iter_streets_defaults_to_no_where_filter():
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
    with LisboaStreetsClient() as lisboa:
        list(lisboa.iter_streets())
    sent_where = query_route.calls[0].request.url.params.get("where")
    assert sent_where == "1=1"


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
    with LisboaStreetsClient() as lisboa:
        list(lisboa.iter_streets(where="DESIGNACAO='Avenida da Liberdade'"))
    sent_where = query_route.calls[0].request.url.params.get("where")
    assert sent_where == "DESIGNACAO='Avenida da Liberdade'"


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
                        "properties": {"OBJECTID": 1, "DESIGNACAO": "Avenida da Liberdade"},
                    }
                ],
            },
        )
    )
    with LisboaStreetsClient() as lisboa:
        records = list(lisboa.iter_streets())
    assert records[0]["properties"]["DESIGNACAO"] == "Avenida da Liberdade"
