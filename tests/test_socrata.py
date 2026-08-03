"""Tests for the generic Socrata (SODA) client - the shared transport
factored out of streetworks.wzdx.registry when streetworks.nycdot needed
the identical shape. See streetworks.socrata.client's own module
docstring.
"""

from __future__ import annotations

import httpx
import respx

from streetworks.socrata import SodaClient

DATASET_URL = "https://example.test/resource/abcd-1234.json"


@respx.mock
def test_iter_records_stops_on_a_short_final_page():
    """A page shorter than page_size is the standard "no more rows"
    signal - a single request, not a follow-up empty-page check."""
    route = respx.get(DATASET_URL).mock(
        return_value=httpx.Response(200, json=[{"id": i} for i in range(2)])
    )
    with SodaClient() as soda:
        rows = list(soda.iter_records(DATASET_URL, page_size=3))
    assert len(rows) == 2
    assert route.call_count == 1
    assert route.calls[0].request.url.params.get("$limit") == "3"
    assert route.calls[0].request.url.params.get("$offset") == "0"


@respx.mock
def test_iter_records_pages_via_limit_offset():
    route = respx.get(DATASET_URL).mock(
        side_effect=[
            httpx.Response(200, json=[{"id": i} for i in range(3)]),
            httpx.Response(200, json=[{"id": i} for i in range(3, 5)]),
        ]
    )
    with SodaClient() as soda:
        rows = list(soda.iter_records(DATASET_URL, page_size=3))
    assert len(rows) == 5
    assert route.calls[0].request.url.params.get("$offset") == "0"
    assert route.calls[1].request.url.params.get("$offset") == "3"


@respx.mock
def test_iter_records_passes_where_select_order():
    route = respx.get(DATASET_URL).mock(return_value=httpx.Response(200, json=[]))
    with SodaClient() as soda:
        list(
            soda.iter_records(
                DATASET_URL, where="state='new york'", select="state", order="state"
            )
        )
    params = route.calls[0].request.url.params
    assert params.get("$where") == "state='new york'"
    assert params.get("$select") == "state"
    assert params.get("$order") == "state"


@respx.mock
def test_app_token_sent_as_header_when_provided():
    route = respx.get(DATASET_URL).mock(return_value=httpx.Response(200, json=[]))
    with SodaClient(app_token="my-real-token") as soda:
        list(soda.iter_records(DATASET_URL))
    assert route.calls[0].request.headers.get("X-App-Token") == "my-real-token"


@respx.mock
def test_no_app_token_by_default():
    route = respx.get(DATASET_URL).mock(return_value=httpx.Response(200, json=[]))
    with SodaClient() as soda:
        list(soda.iter_records(DATASET_URL))
    assert "X-App-Token" not in route.calls[0].request.headers
