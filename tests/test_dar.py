"""Tests for streetworks.dar - wiring only. See streetworks.dar.client's
module docstring for the live evidence behind each real behaviour
covered here (pagination, and why DAWA was not used instead)."""

from __future__ import annotations

import httpx
import respx

from streetworks.dar import BASE_URL, STREETS_ENTITY, DarClient


@respx.mock
def test_iter_streets_pages_by_page_number():
    route = respx.get(f"{BASE_URL}/{STREETS_ENTITY}").mock(
        side_effect=[
            httpx.Response(200, json=[{"id_lokalId": f"r{i}"} for i in range(3)]),
            httpx.Response(200, json=[{"id_lokalId": "r3"}]),
        ]
    )
    with DarClient(page_size=3) as dar:
        records = list(dar.iter_streets())
    assert [r["id_lokalId"] for r in records] == ["r0", "r1", "r2", "r3"]
    assert route.calls[0].request.url.params.get("page") == "1"
    assert route.calls[1].request.url.params.get("page") == "2"


@respx.mock
def test_iter_streets_stops_on_a_short_first_page():
    respx.get(f"{BASE_URL}/{STREETS_ENTITY}").mock(
        return_value=httpx.Response(200, json=[{"id_lokalId": "only"}])
    )
    with DarClient(page_size=5000) as dar:
        records = list(dar.iter_streets())
    assert len(records) == 1


@respx.mock
def test_iter_streets_yields_real_shaped_fields():
    respx.get(f"{BASE_URL}/{STREETS_ENTITY}").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id_lokalId": "00008748-e0ee-4cb3-83b7-167455a2efaf",
                    "vejnavn": "Halvdansvej",
                    "vejnavnebeliggenhed_vejnavnelinje": (
                        "MULTILINESTRING((715111.99 6213560.73,715113.38 6213568.14))"
                    ),
                }
            ],
        )
    )
    with DarClient() as dar:
        records = list(dar.iter_streets())
    assert len(records) == 1
    assert records[0]["vejnavn"] == "Halvdansvej"
