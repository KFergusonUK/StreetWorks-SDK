"""Tests for streetworks.arcgis.nrn - wiring only; the pagination
strategy itself is tested generically in test_arcgis_client.py.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.arcgis.nrn import BASE_URL, LAYER_IDS, NrnClient


def _layer_info():
    return {
        "objectIdField": None,
        "maxRecordCount": 2000,
        "advancedQueryCapabilities": {"supportsPagination": True},
        "fields": [{"name": "OBJECTID"}],
    }


def _mock_layer_info(layer_id: int) -> None:
    respx.get(f"{BASE_URL}/{layer_id}").mock(return_value=httpx.Response(200, json=_layer_info()))


@respx.mock
def test_iter_roads_queries_a_real_road_class_province_layer():
    layer = LAYER_IDS["local_roads"]["ON"]
    _mock_layer_info(layer)
    feature = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[-79.39, 43.65], [-79.38, 43.66]]},
        "properties": {"OBJECTID": 1, "l_stname_c": "Wellington Street West"},
    }
    respx.get(f"{BASE_URL}/{layer}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": [feature]})
    )
    with NrnClient() as nrn:
        roads = list(nrn.iter_roads(layer))
    assert roads[0]["properties"]["l_stname_c"] == "Wellington Street West"


@respx.mock
def test_iter_roads_passes_bbox_as_an_envelope_geometry():
    layer = LAYER_IDS["local_roads"]["ON"]
    _mock_layer_info(layer)
    query_route = respx.get(f"{BASE_URL}/{layer}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with NrnClient() as nrn:
        list(nrn.iter_roads(layer, bbox=(-79.40, 43.64, -79.38, 43.66)))
    params = query_route.calls[0].request.url.params
    assert params.get("geometryType") == "esriGeometryEnvelope"
    assert params.get("inSR") == "4326"
    assert params.get("outSR") == "4326"
    assert "-79.4" in params.get("geometry")


def test_layer_ids_cover_every_real_road_class_and_province():
    from streetworks.arcgis.nrn import PROVINCES, ROAD_CLASSES

    assert len(PROVINCES) == 13
    assert len(ROAD_CLASSES) == 5
    for road_class in ROAD_CLASSES:
        assert set(LAYER_IDS[road_class]) == set(PROVINCES)
    # No two (road_class, province) pairs share a layer id - each of the
    # real 65 leaf layers is genuinely distinct (confirmed live).
    all_ids = [lid for province_map in LAYER_IDS.values() for lid in province_map.values()]
    assert len(all_ids) == len(set(all_ids)) == 65
