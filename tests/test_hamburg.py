"""Tests for streetworks.hamburg - wiring only. See
streetworks.hamburg.client's own module docstring for the live evidence
behind each real behaviour covered here (the real OGC API Features
"next" link, and why Berlin was checked first and genuinely blocked)."""

from __future__ import annotations

import httpx
import respx

from streetworks.hamburg import BASE_URL, HamburgStreetsClient


@respx.mock
def test_iter_streets_follows_the_real_next_link():
    route = respx.get(BASE_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "features": [{"id": "1", "properties": {"strname": "A"}}],
                    "links": [{"rel": "next", "href": f"{BASE_URL}?f=json&limit=1&offset=1"}],
                },
            ),
            httpx.Response(
                200,
                json={"features": [{"id": "2", "properties": {"strname": "B"}}], "links": []},
            ),
        ]
    )
    with HamburgStreetsClient(page_size=1) as hamburg:
        features = list(hamburg.iter_streets())
    assert [f["id"] for f in features] == ["1", "2"]
    assert route.call_count == 2


@respx.mock
def test_iter_streets_stops_when_no_next_link():
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200, json={"features": [{"id": "1", "properties": {"strname": "A"}}], "links": []}
        )
    )
    with HamburgStreetsClient() as hamburg:
        features = list(hamburg.iter_streets())
    assert len(features) == 1


@respx.mock
def test_iter_streets_yields_real_shaped_fields():
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "features": [
                    {
                        "id": "00002",
                        "geometry": {"type": "Point", "coordinates": [10.099, 53.487]},
                        "properties": {"strname": "Wasserpark Dove-Elbe"},
                    }
                ],
                "links": [],
            },
        )
    )
    with HamburgStreetsClient() as hamburg:
        features = list(hamburg.iter_streets())
    assert features[0]["properties"]["strname"] == "Wasserpark Dove-Elbe"
