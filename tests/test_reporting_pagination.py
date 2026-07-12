"""Tests for Reporting API offset-based auto-pagination."""

import httpx
import respx

from streetworks.streetmanager import AsyncStreetManagerClient, StreetManagerClient
from streetworks.streetmanager.environments import Environment

SANDBOX = "https://api.sandbox.manage-roadworks.service.gov.uk"
SANDBOX_REPORTING = f"{SANDBOX}/v6/reporting"


def mock_auth() -> None:
    respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        return_value=httpx.Response(
            200, json={"idToken": "tok", "refreshToken": "ref", "organisationReference": 1}
        )
    )


def _page(rows: list[dict], has_next: bool) -> httpx.Response:
    # The live API uses snake_case here (live-verified), unlike e.g. the
    # camelCase auth endpoint - Street Manager mixes conventions.
    return httpx.Response(
        200, json={"pagination": {"total_rows": 5, "has_next_page": has_next}, "rows": rows}
    )


@respx.mock
def test_iter_permits_walks_all_pages():
    mock_auth()
    route = respx.get(f"{SANDBOX_REPORTING}/permits").mock(
        side_effect=[
            _page([{"id": 1}, {"id": 2}], has_next=True),
            _page([{"id": 3}, {"id": 4}], has_next=True),
            _page([{"id": 5}], has_next=False),
        ]
    )
    with StreetManagerClient("e@x.com", "pw", environment=Environment.SANDBOX) as sm:
        ids = [row["id"] for row in sm.reporting.iter_permits(status="submitted")]

    assert ids == [1, 2, 3, 4, 5]
    # offset advances by rows received: 0, 2, 4
    offsets = [r.request.url.params.get("offset") for r in route.calls]
    assert offsets == ["0", "2", "4"]
    # the filter is preserved on every page
    assert all(r.request.url.params.get("status") == "submitted" for r in route.calls)


@respx.mock
def test_iter_stops_on_empty_rows_even_if_has_next_claims_more():
    """Defensive: a malformed response must not cause an infinite loop."""
    mock_auth()
    respx.get(f"{SANDBOX_REPORTING}/inspections").mock(side_effect=[_page([], has_next=True)])
    with StreetManagerClient("e@x.com", "pw", environment=Environment.SANDBOX) as sm:
        assert list(sm.reporting.iter_inspections()) == []


@respx.mock
def test_iter_respects_caller_starting_offset():
    mock_auth()
    route = respx.get(f"{SANDBOX_REPORTING}/permits").mock(
        side_effect=[_page([{"id": 9}], has_next=False)]
    )
    with StreetManagerClient("e@x.com", "pw", environment=Environment.SANDBOX) as sm:
        rows = list(sm.reporting.iter_permits(offset=100))
    assert [r["id"] for r in rows] == [9]
    assert route.calls[0].request.url.params.get("offset") == "100"


@respx.mock
async def test_async_iter_permits_walks_all_pages():
    mock_auth()
    respx.get(f"{SANDBOX_REPORTING}/permits").mock(
        side_effect=[
            _page([{"id": 1}], has_next=True),
            _page([{"id": 2}], has_next=False),
        ]
    )
    async with AsyncStreetManagerClient("e@x.com", "pw", environment=Environment.SANDBOX) as sm:
        ids = [row["id"] async for row in sm.reporting.iter_permits()]
    assert ids == [1, 2]


@respx.mock
def test_iter_tolerates_camelcase_pagination_key():
    """Defensive: the swagger reference implies camelCase; accept it too."""
    mock_auth()
    respx.get(f"{SANDBOX_REPORTING}/permits").mock(
        side_effect=[
            httpx.Response(
                200,
                json={"pagination": {"hasNextPage": True}, "rows": [{"id": 1}]},
            ),
            httpx.Response(
                200,
                json={"pagination": {"hasNextPage": False}, "rows": [{"id": 2}]},
            ),
        ]
    )
    with StreetManagerClient("e@x.com", "pw", environment=Environment.SANDBOX) as sm:
        assert [r["id"] for r in sm.reporting.iter_permits()] == [1, 2]
