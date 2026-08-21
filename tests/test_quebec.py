"""Tests for streetworks.quebec - wiring only. Converter behaviour is
tested in test_common_quebec.py against the same real fixture.
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.quebec import BASE_URL, TYPE_NAME, QuebecClient

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "quebec_travaux_routiers.json").read_text(
        encoding="utf-8"
    )
)


@respx.mock
def test_iter_roadworks_yields_real_features():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    with QuebecClient() as quebec:
        features = list(quebec.iter_roadworks())
    assert len(features) == 7
    assert features[0]["properties"]["identifiantChantier"] == "250648"


@respx.mock
def test_iter_roadworks_requests_the_real_type_name_and_crs():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    with QuebecClient() as quebec:
        list(quebec.iter_roadworks())
    params = dict(httpx.QueryParams(route.calls.last.request.url.query))
    assert params["TYPENAMES"] == TYPE_NAME
    assert params["SRSNAME"] == "EPSG:4326"
