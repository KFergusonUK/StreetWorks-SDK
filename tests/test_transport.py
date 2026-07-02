import httpx
import pytest
import respx

from streetworks._transport import RetryConfig, SyncTransport
from streetworks.exceptions import (
    AccountLockedError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
)

FAST_RETRY = RetryConfig(max_attempts=3, backoff_factor=0.0, max_backoff=0.0)


@respx.mock
def test_retries_on_429_then_succeeds():
    route = respx.get("https://example.test/thing").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    with SyncTransport(retry=FAST_RETRY) as transport:
        response = transport.request("GET", "https://example.test/thing")
    assert response.json() == {"ok": True}
    assert route.call_count == 2


@respx.mock
def test_rate_limit_error_after_exhausting_retries():
    respx.get("https://example.test/thing").mock(return_value=httpx.Response(429))
    with SyncTransport(retry=FAST_RETRY) as transport:
        with pytest.raises(RateLimitError):
            transport.request("GET", "https://example.test/thing")


@respx.mock
@pytest.mark.parametrize(
    ("status", "exc"),
    [
        (401, AuthenticationError),
        (404, NotFoundError),
        (423, AccountLockedError),
        (500, ServerError),
    ],
)
def test_error_mapping(status, exc):
    respx.get("https://example.test/thing").mock(
        return_value=httpx.Response(status, json={"message": "boom"})
    )
    with SyncTransport(retry=RetryConfig(max_attempts=1)) as transport:
        with pytest.raises(exc) as excinfo:
            transport.request("GET", "https://example.test/thing")
    assert excinfo.value.status_code == status
    assert "boom" in str(excinfo.value)


@respx.mock
def test_header_provider_applied_per_attempt():
    seen = []

    def record(request):
        seen.append(request.headers.get("token"))
        return httpx.Response(200, json={})

    respx.get("https://example.test/thing").mock(side_effect=record)
    with SyncTransport(retry=FAST_RETRY) as transport:
        transport.request(
            "GET", "https://example.test/thing", header_provider=lambda: {"token": "abc"}
        )
    assert seen == ["abc"]
