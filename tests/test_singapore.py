"""Tests for streetworks.singapore. **Pending live verification** - see the
module docstring in ``streetworks.singapore.client``. No real authenticated
LTA DataMall response has ever been seen; the three fixtures
(``singapore_road_works.json``, ``singapore_road_openings.json``,
``singapore_traffic_incidents.json``) are synthetic, built from LTA's own
documented sample values and enum, not fetched from any real endpoint.
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.singapore import BASE_URL, SingaporeClient

ROAD_WORKS = json.loads(
    (Path(__file__).parent / "fixtures" / "singapore_road_works.json").read_text()
)
ROAD_OPENINGS = json.loads(
    (Path(__file__).parent / "fixtures" / "singapore_road_openings.json").read_text()
)
TRAFFIC_INCIDENTS = json.loads(
    (Path(__file__).parent / "fixtures" / "singapore_traffic_incidents.json").read_text()
)


def test_client_requires_account_key():
    with pytest.raises(ValueError):
        SingaporeClient(account_key="")


@respx.mock
def test_iter_road_works_tags_kind_and_sends_account_key_header():
    respx.get(f"{BASE_URL}/RoadWorks").mock(return_value=httpx.Response(200, json=ROAD_WORKS))
    with SingaporeClient(account_key="test-key") as client:
        records = list(client.iter_road_works())
    assert len(records) == 1
    assert records[0]["kind"] == "road_works"
    assert records[0]["EventID"] == "RMAPP-201512-0217"
    request = respx.calls.last.request
    assert request.headers["AccountKey"] == "test-key"


@respx.mock
def test_iter_road_openings_tags_kind():
    respx.get(f"{BASE_URL}/RoadOpenings").mock(
        return_value=httpx.Response(200, json=ROAD_OPENINGS)
    )
    with SingaporeClient(account_key="test-key") as client:
        records = list(client.iter_road_openings())
    assert len(records) == 1
    assert records[0]["kind"] == "road_openings"


@respx.mock
def test_iter_traffic_incidents_yields_every_type_unfiltered():
    respx.get(f"{BASE_URL}/TrafficIncidents").mock(
        return_value=httpx.Response(200, json=TRAFFIC_INCIDENTS)
    )
    with SingaporeClient(account_key="test-key") as client:
        records = list(client.iter_traffic_incidents())
    assert len(records) == 2
    assert {r["Type"] for r in records} == {"Vehicle breakdown", "Roadwork"}


@respx.mock
def test_iter_roadworks_combines_all_three_sources_filtering_incidents():
    respx.get(f"{BASE_URL}/RoadWorks").mock(return_value=httpx.Response(200, json=ROAD_WORKS))
    respx.get(f"{BASE_URL}/RoadOpenings").mock(
        return_value=httpx.Response(200, json=ROAD_OPENINGS)
    )
    respx.get(f"{BASE_URL}/TrafficIncidents").mock(
        return_value=httpx.Response(200, json=TRAFFIC_INCIDENTS)
    )
    with SingaporeClient(account_key="test-key") as client:
        records = list(client.iter_roadworks())
    # 1 real RoadWorks + 1 real RoadOpenings + 1 real Roadwork-type
    # incident - the Vehicle breakdown incident is excluded.
    assert len(records) == 3
    kinds = [r["kind"] for r in records]
    assert kinds == ["road_works", "road_openings", "incident"]


@respx.mock
def test_pagination_follows_skip_until_a_short_page():
    full_page = {"value": [{"EventID": f"E-{i}"} for i in range(500)]}
    last_page = {"value": [{"EventID": "E-500"}]}
    route = respx.get(f"{BASE_URL}/RoadWorks")
    route.side_effect = [
        httpx.Response(200, json=full_page),
        httpx.Response(200, json=last_page),
    ]
    with SingaporeClient(account_key="test-key") as client:
        records = list(client.iter_road_works())
    assert len(records) == 501
    assert route.calls.call_count == 2
    second_request = route.calls[1].request
    assert second_request.url.params["$skip"] == "500"
