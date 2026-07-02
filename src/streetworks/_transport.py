"""Shared HTTP transport for all provider modules.

One retry/backoff/error-mapping implementation, exposed as a sync and an async
class over the same logic, so every API client in the SDK behaves consistently:

* retries on 429 and transient 5xx (502/503/504), honouring ``Retry-After``
* exponential backoff with jitter (per Street Manager integration guidance)
* raises the mapped :mod:`streetworks.exceptions` type on failure
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

from .exceptions import (
    APIError,
    RateLimitError,
    TransportError,
    error_for_status,
)

HeaderProvider = Callable[[], Mapping[str, str]]
AsyncHeaderProvider = Callable[[], Awaitable[Mapping[str, str]]]

DEFAULT_TIMEOUT = 30.0
_RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})


@dataclass(frozen=True)
class RetryConfig:
    """Retry behaviour for a transport."""

    max_attempts: int = 4
    backoff_factor: float = 0.5
    max_backoff: float = 30.0
    retry_statuses: frozenset[int] = field(default_factory=lambda: _RETRYABLE_STATUSES)

    def delay(self, attempt: int, retry_after: float | None = None) -> float:
        """Seconds to sleep before retry number ``attempt`` (1-indexed)."""
        if retry_after is not None:
            return min(retry_after, self.max_backoff)
        exp = self.backoff_factor * (2 ** (attempt - 1))
        return min(exp, self.max_backoff) * (0.5 + random.random() / 2)


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None  # HTTP-date form; let backoff handle it


def _raise_for_response(response: httpx.Response) -> None:
    if response.is_success:
        return
    try:
        body: Any = response.json()
        message = body.get("message") if isinstance(body, dict) else None
    except ValueError:
        body = response.text
        message = None
    message = message or f"HTTP {response.status_code} from {response.request.url}"
    exc_type = error_for_status(response.status_code)
    kwargs: dict[str, Any] = {
        "status_code": response.status_code,
        "body": body,
        "request_url": str(response.request.url),
    }
    if exc_type is RateLimitError:
        kwargs["retry_after"] = _retry_after_seconds(response)
    raise exc_type(message, **kwargs)


class SyncTransport:
    """Thin wrapper over ``httpx.Client`` adding retries and error mapping."""

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        retry: RetryConfig | None = None,
        auth: httpx.Auth | None = None,
        headers: Mapping[str, str] | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.retry = retry or RetryConfig()
        self._client = client or httpx.Client(timeout=timeout, auth=auth, headers=headers)

    def request(
        self,
        method: str,
        url: str,
        *,
        header_provider: HeaderProvider | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(1, self.retry.max_attempts + 1):
            headers = dict(kwargs.pop("headers", None) or {})
            if header_provider is not None:
                headers.update(header_provider())
            try:
                response = self._client.request(method, url, headers=headers, **kwargs)
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt == self.retry.max_attempts:
                    raise TransportError(f"{method} {url} failed: {exc}") from exc
                time.sleep(self.retry.delay(attempt))
                continue
            retryable = response.status_code in self.retry.retry_statuses
            if retryable and attempt < self.retry.max_attempts:
                time.sleep(self.retry.delay(attempt, _retry_after_seconds(response)))
                continue
            _raise_for_response(response)
            return response
        raise TransportError(f"{method} {url} failed after retries") from last_exc

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SyncTransport:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncTransport:
    """Thin wrapper over ``httpx.AsyncClient`` adding retries and error mapping."""

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        retry: RetryConfig | None = None,
        auth: httpx.Auth | None = None,
        headers: Mapping[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.retry = retry or RetryConfig()
        self._client = client or httpx.AsyncClient(timeout=timeout, auth=auth, headers=headers)

    async def request(
        self,
        method: str,
        url: str,
        *,
        header_provider: AsyncHeaderProvider | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(1, self.retry.max_attempts + 1):
            headers = dict(kwargs.pop("headers", None) or {})
            if header_provider is not None:
                headers.update(await header_provider())
            try:
                response = await self._client.request(method, url, headers=headers, **kwargs)
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt == self.retry.max_attempts:
                    raise TransportError(f"{method} {url} failed: {exc}") from exc
                await asyncio.sleep(self.retry.delay(attempt))
                continue
            retryable = response.status_code in self.retry.retry_statuses
            if retryable and attempt < self.retry.max_attempts:
                await asyncio.sleep(self.retry.delay(attempt, _retry_after_seconds(response)))
                continue
            _raise_for_response(response)
            return response
        raise TransportError(f"{method} {url} failed after retries") from last_exc

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncTransport:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()


__all__ = [
    "APIError",
    "AsyncTransport",
    "RetryConfig",
    "SyncTransport",
]
