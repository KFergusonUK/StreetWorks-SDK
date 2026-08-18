"""Tests for streetworks.amsterdam - wiring only. See
streetworks.amsterdam.client's module docstring for the live evidence
behind each real behaviour covered here (the doubled real path, the
Accept-Crs header, and HAL-style pagination)."""

from __future__ import annotations

import httpx
import respx

from streetworks.amsterdam import BASE_URL, AmsterdamClient


@respx.mock
def test_iter_roadworks_sends_accept_crs_header():
    route = respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200, json={"_embedded": {"wior": [{"wiorNummer": "W1"}]}, "_links": {}}
        )
    )
    with AmsterdamClient() as amsterdam:
        list(amsterdam.iter_roadworks())
    assert route.calls[0].request.headers["Accept-Crs"] == "EPSG:4326"


@respx.mock
def test_iter_roadworks_follows_hal_next_link():
    route = respx.get(BASE_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "_embedded": {"wior": [{"wiorNummer": "W1"}, {"wiorNummer": "W2"}]},
                    "_links": {"next": {"href": f"{BASE_URL}?_pageSize=2&page=2"}},
                },
            ),
            httpx.Response(
                200, json={"_embedded": {"wior": [{"wiorNummer": "W3"}]}, "_links": {}}
            ),
        ]
    )
    with AmsterdamClient(page_size=2) as amsterdam:
        records = list(amsterdam.iter_roadworks())
    assert [r["wiorNummer"] for r in records] == ["W1", "W2", "W3"]
    assert route.call_count == 2


@respx.mock
def test_iter_roadworks_yields_real_shaped_fields():
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "_embedded": {
                    "wior": [
                        {
                            "wiorNummer": "W22013761",
                            "projectnaam": "Noordzeeweg T-stukken vervangen",
                            "hoofdstatus": "Uitvoering",
                        }
                    ]
                },
                "_links": {},
            },
        )
    )
    with AmsterdamClient() as amsterdam:
        records = list(amsterdam.iter_roadworks())
    assert len(records) == 1
    assert records[0]["hoofdstatus"] == "Uitvoering"
