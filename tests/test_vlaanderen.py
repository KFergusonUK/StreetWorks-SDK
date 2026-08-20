"""Tests for streetworks.vlaanderen - wiring only. See
streetworks.vlaanderen.client's own module docstring for the live
evidence behind each real behaviour covered here (the real "volgende"
pagination link, and why the Wegenregister WFS wasn't used instead)."""

from __future__ import annotations

import httpx
import respx

from streetworks.vlaanderen import BASE_URL, VlaanderenStreetsClient


@respx.mock
def test_iter_streets_follows_the_real_volgende_link():
    route = respx.get(BASE_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "straatnamen": [{"identificator": {"objectId": "1"}}],
                    "volgende": f"{BASE_URL}?offset=1&limit=1",
                },
            ),
            httpx.Response(200, json={"straatnamen": [{"identificator": {"objectId": "2"}}]}),
        ]
    )
    with VlaanderenStreetsClient(page_size=1) as vlaanderen:
        records = list(vlaanderen.iter_streets())
    assert [r["identificator"]["objectId"] for r in records] == ["1", "2"]
    assert route.call_count == 2


@respx.mock
def test_iter_streets_stops_when_volgende_is_absent():
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200, json={"straatnamen": [{"identificator": {"objectId": "1"}}]}
        )
    )
    with VlaanderenStreetsClient() as vlaanderen:
        records = list(vlaanderen.iter_streets())
    assert len(records) == 1


@respx.mock
def test_iter_streets_yields_real_shaped_fields():
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "straatnamen": [
                    {
                        "identificator": {"objectId": "1"},
                        "straatnaam": {
                            "geografischeNaam": {"spelling": "Acacialaan", "taal": "nl"}
                        },
                        "straatnaamStatus": "inGebruik",
                    }
                ]
            },
        )
    )
    with VlaanderenStreetsClient() as vlaanderen:
        records = list(vlaanderen.iter_streets())
    assert records[0]["straatnaam"]["geografischeNaam"]["spelling"] == "Acacialaan"
