"""Tests for streetworks.arcgis.client.ArcGISFeatureClient - the generic
protocol layer. Provider-specific behaviour (Jersey, TIGERweb) is tested in
their own test files; this file is about the pagination/truncation
strategy itself, built from real Jersey (broken resultOffset) and real
TIGERweb (working resultOffset) behaviour confirmed live this session.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from streetworks.arcgis import ArcGISFeatureClient
from streetworks.exceptions import TruncatedResultError

BASE = "https://example.test/arcgis/rest/services/Example/FeatureServer"


def _layer_info(*, oid_field, max_record_count, supports_pagination):
    return {
        "objectIdField": oid_field,
        "maxRecordCount": max_record_count,
        "advancedQueryCapabilities": {"supportsPagination": supports_pagination},
        "fields": [{"name": "FID"}] if oid_field else [],
    }


def _feature_collection(ids, oid_field="FID"):
    features = [
        {"type": "Feature", "geometry": None, "properties": {oid_field: i}} for i in ids
    ]
    return {"type": "FeatureCollection", "features": features}


@respx.mock
def test_query_prefers_geojson_and_returns_it_unchanged():
    info = _layer_info(oid_field="FID", max_record_count=1000, supports_pagination=True)
    respx.get(f"{BASE}/0").mock(return_value=httpx.Response(200, json=info))
    respx.get(f"{BASE}/0/query").mock(
        return_value=httpx.Response(200, json=_feature_collection([1, 2]))
    )
    with ArcGISFeatureClient() as arcgis:
        result = arcgis.query(BASE, 0)
    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 2


@respx.mock
def test_query_falls_back_to_esri_json_when_geojson_not_honoured():
    def responder(request):
        if request.url.params.get("f") == "geojson":
            # A server that ignores f=geojson and returns Esri JSON anyway.
            return httpx.Response(200, json={"objectIdFieldName": "FID", "features": [
                {"attributes": {"FID": 1}, "geometry": {"paths": [[[1.0, 2.0], [3.0, 4.0]]]}}
            ]})
        return httpx.Response(200, json={"features": [
            {"attributes": {"FID": 1}, "geometry": {"paths": [[[1.0, 2.0], [3.0, 4.0]]]}}
        ]})

    respx.get(f"{BASE}/0/query").mock(side_effect=responder)
    with ArcGISFeatureClient() as arcgis:
        result = arcgis.query(BASE, 0)
    assert result["type"] == "FeatureCollection"
    feature = result["features"][0]
    assert feature["geometry"] == {"type": "LineString", "coordinates": [[1.0, 2.0], [3.0, 4.0]]}
    assert feature["properties"] == {"FID": 1}


@respx.mock
def test_count_uses_return_count_only():
    respx.get(f"{BASE}/0/query").mock(return_value=httpx.Response(200, json={"count": 22105}))
    with ArcGISFeatureClient() as arcgis:
        assert arcgis.count(BASE, 0) == 22105


@respx.mock
def test_iter_features_pages_via_offset_when_it_genuinely_works():
    # TIGERweb-shaped: supportsPagination=true, and offset genuinely advances.
    info = _layer_info(oid_field="OBJECTID", max_record_count=2, supports_pagination=True)
    respx.get(f"{BASE}/0").mock(return_value=httpx.Response(200, json=info))

    def responder(request):
        offset = int(request.url.params.get("resultOffset", "0"))
        all_ids = [1, 2, 3]
        page = all_ids[offset : offset + 2]
        return httpx.Response(200, json=_feature_collection(page, oid_field="OBJECTID"))

    respx.get(f"{BASE}/0/query").mock(side_effect=responder)
    with ArcGISFeatureClient() as arcgis:
        features = list(arcgis.iter_features(BASE, 0))
    assert [f["properties"]["OBJECTID"] for f in features] == [1, 2, 3]


@respx.mock
def test_iter_features_falls_back_to_oid_range_when_offset_is_silently_broken():
    # Jersey-shaped: supportsPagination=false, and it's genuinely true -
    # resultOffset always returns the same first page regardless of value.
    respx.get(f"{BASE}/0").mock(
        return_value=httpx.Response(
            200, json=_layer_info(oid_field="FID", max_record_count=2, supports_pagination=False)
        )
    )

    def responder(request):
        where = request.url.params.get("where", "1=1")
        if "FID >" in where:
            threshold = int(where.split("FID >")[1].split(")")[0])
            all_ids = [1, 2, 3, 4, 5]
            page = [i for i in all_ids if i > threshold][:2]
            return httpx.Response(200, json=_feature_collection(page))
        # Any resultOffset value - always the same first page (the real bug).
        return httpx.Response(200, json=_feature_collection([1, 2]))

    respx.get(f"{BASE}/0/query").mock(side_effect=responder)
    with ArcGISFeatureClient() as arcgis:
        features = list(arcgis.iter_features(BASE, 0))
    ids = [f["properties"]["FID"] for f in features]
    assert ids == [1, 2, 3, 4, 5]
    assert len(ids) == len(set(ids))  # no duplicates despite the broken offset path


@respx.mock
def test_iter_features_short_first_page_needs_no_further_paging():
    info = _layer_info(oid_field="FID", max_record_count=1000, supports_pagination=True)
    respx.get(f"{BASE}/0").mock(return_value=httpx.Response(200, json=info))
    respx.get(f"{BASE}/0/query").mock(
        return_value=httpx.Response(200, json=_feature_collection([1, 2]))
    )
    with ArcGISFeatureClient() as arcgis:
        features = list(arcgis.iter_features(BASE, 0))
    assert len(features) == 2


@respx.mock
def test_iter_features_raises_truncated_result_error_rather_than_silently_truncating():
    # The exact case the design brief calls out: a layer returning exactly
    # maxRecordCount rows, with no working pagination and no objectIdField
    # to fall back on - must not be treated as complete.
    respx.get(f"{BASE}/0").mock(
        return_value=httpx.Response(
            200, json=_layer_info(oid_field=None, max_record_count=2, supports_pagination=False)
        )
    )
    # Always returns exactly 2 features (== maxRecordCount), regardless of
    # resultOffset - indistinguishable, without an oid field, from "there
    # are more records we can't reach."
    respx.get(f"{BASE}/0/query").mock(
        return_value=httpx.Response(200, json=_feature_collection([1, 2], oid_field="X"))
    )
    with ArcGISFeatureClient() as arcgis:
        with pytest.raises(TruncatedResultError, match="cannot be safely retrieved"):
            list(arcgis.iter_features(BASE, 0))
