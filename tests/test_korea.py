"""Tests for streetworks.korea. **Pending live verification** - see the
module docstring in ``streetworks.korea.client``. No real authenticated
data.go.kr response has ever been seen, and even the real pull URL is
unconfirmed - the fixture (``korea_construction_status.json``) is entirely
synthetic, built around the standard data.go.kr response envelope, with
inferred (not confirmed) field key names.
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.korea import KoreaClient

TEST_URL = "https://example-not-real.data.go.kr/openapi/ConstructionStatus"

ITEMS_PAGE = json.loads(
    (Path(__file__).parent / "fixtures" / "korea_construction_status.json").read_text()
)


def test_client_requires_base_url():
    with pytest.raises(ValueError):
        KoreaClient(base_url="", service_key="test-key")


def test_client_requires_service_key():
    with pytest.raises(ValueError):
        KoreaClient(base_url=TEST_URL, service_key="")


@respx.mock
def test_iter_items_reads_the_standard_envelope_and_sends_service_key():
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, json=ITEMS_PAGE))
    with KoreaClient(base_url=TEST_URL, service_key="test-key") as client:
        items = list(client.iter_items())
    assert len(items) == 2
    assert items[0]["routeNm"] == "경부고속도로"
    request = respx.calls.last.request
    assert request.url.params["serviceKey"] == "test-key"
    assert request.url.params["numOfRows"] == "100"
    assert request.url.params["pageNo"] == "1"


@respx.mock
def test_iter_items_paginates_until_a_short_page():
    full_page = {
        "response": {
            "body": {
                "items": {"item": [{"routeNm": f"route-{i}"} for i in range(100)]},
                "numOfRows": 100,
                "pageNo": 1,
                "totalCount": 101,
            }
        }
    }
    last_page = {
        "response": {
            "body": {
                "items": {"item": [{"routeNm": "route-100"}]},
                "numOfRows": 100,
                "pageNo": 2,
                "totalCount": 101,
            }
        }
    }
    route = respx.get(TEST_URL)
    route.side_effect = [
        httpx.Response(200, json=full_page),
        httpx.Response(200, json=last_page),
    ]
    with KoreaClient(base_url=TEST_URL, service_key="test-key") as client:
        items = list(client.iter_items())
    assert len(items) == 101
    assert route.calls.call_count == 2


@respx.mock
def test_iter_items_yields_nothing_on_an_unrecognised_shape():
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, json={"unexpected": "shape"}))
    with KoreaClient(base_url=TEST_URL, service_key="test-key") as client:
        items = list(client.iter_items())
    assert items == []


@respx.mock
def test_iter_items_handles_a_single_item_not_wrapped_in_a_list():
    payload = {
        "response": {
            "body": {
                "items": {"item": {"routeNm": "solo-route"}},
                "numOfRows": 100,
                "pageNo": 1,
                "totalCount": 1,
            }
        }
    }
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, json=payload))
    with KoreaClient(base_url=TEST_URL, service_key="test-key") as client:
        items = list(client.iter_items())
    assert items == [{"routeNm": "solo-route"}]
