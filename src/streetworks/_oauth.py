"""Shared OAuth 2.0 client-credentials support.

Several UK street works services authenticate with the client credentials
grant (D-TRO, Geoplace DataVIA's OIDC option). The token endpoints differ in
where they expect the credentials:

* ``basic`` - client id/secret as HTTP Basic auth, grant type in the body
  (D-TRO style)
* ``body``  - client id/secret and grant type all in the form body
  (DataVIA style)

Tokens are cached and refreshed shortly before expiry (``expires_in`` from
the token response, with a safe fallback).
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Literal

from ._transport import AsyncTransport, SyncTransport

# Refresh this many seconds before the token actually expires.
EXPIRY_LEEWAY = 60.0
# If the token response has no expires_in, assume this lifetime.
FALLBACK_LIFETIME = 25 * 60.0

CredentialStyle = Literal["basic", "body"]


class _ClientCredentialsBase:
    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        *,
        style: CredentialStyle = "basic",
        scope: str | None = None,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._style = style
        self._scope = scope
        self._access_token: str | None = None
        self._expires_at: float = 0.0
        self.last_token_response: dict[str, Any] | None = None

    @property
    def _fresh(self) -> bool:
        return self._access_token is not None and time.time() < (self._expires_at - EXPIRY_LEEWAY)

    def _request_kwargs(self) -> dict[str, Any]:
        data: dict[str, str] = {"grant_type": "client_credentials"}
        if self._scope:
            data["scope"] = self._scope
        kwargs: dict[str, Any] = {"data": data}
        if self._style == "basic":
            kwargs["auth"] = (self._client_id, self._client_secret)
        else:
            data["client_id"] = self._client_id
            data["client_secret"] = self._client_secret
        return kwargs

    def _store(self, payload: dict[str, Any]) -> str:
        self.last_token_response = payload
        self._access_token = payload["access_token"]
        lifetime = float(payload.get("expires_in") or FALLBACK_LIFETIME)
        self._expires_at = time.time() + lifetime
        return self._access_token


class SyncClientCredentials(_ClientCredentialsBase):
    """Thread-safe client-credentials token manager."""

    def __init__(self, *args: Any, transport: SyncTransport, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._transport = transport
        self._lock = threading.Lock()

    def get_access_token(self) -> str:
        with self._lock:
            if self._fresh:
                assert self._access_token is not None
                return self._access_token
            response = self._transport.request("POST", self._token_url, **self._request_kwargs())
            return self._store(response.json())

    def bearer_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.get_access_token()}"}


class AsyncClientCredentials(_ClientCredentialsBase):
    """Asyncio-safe client-credentials token manager."""

    def __init__(self, *args: Any, transport: AsyncTransport, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._transport = transport
        self._lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        async with self._lock:
            if self._fresh:
                assert self._access_token is not None
                return self._access_token
            response = await self._transport.request(
                "POST", self._token_url, **self._request_kwargs()
            )
            return self._store(response.json())

    async def bearer_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {await self.get_access_token()}"}
