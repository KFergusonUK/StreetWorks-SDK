"""Street Manager authentication and token lifecycle.

Behaviour follows the DfT integration guidance:

* ``POST {work}/authenticate`` returns ``idToken`` (1h), ``accessToken`` (1h),
  ``refreshToken`` (1 day) and ``organisationReference``.
* Do **not** re-authenticate per call - the id token is cached and reused.
* When the id token nears expiry, a new one is obtained via the Party API
  refresh endpoint (``POST {party}/refresh``); if refreshing fails for any
  reason we fall back to a full re-authentication.
* Every resource request carries the id token in the ``token`` header.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import threading
import time
from dataclasses import dataclass
from typing import Any

from .._transport import AsyncTransport, SyncTransport
from ..exceptions import APIError
from .environments import Api, ApiVersion, Environment, base_url

# Refresh the token this many seconds before its actual expiry.
EXPIRY_LEEWAY = 120.0
# If the JWT exp claim can't be read, assume this lifetime (spec says 1 hour).
FALLBACK_LIFETIME = 55 * 60.0


def _jwt_expiry(token: str) -> float | None:
    """Best-effort read of the ``exp`` claim from a JWT (no signature check -
    we only need the expiry hint; the server validates the token properly)."""
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        return float(exp) if exp is not None else None
    except (IndexError, ValueError, binascii.Error, json.JSONDecodeError):
        return None


@dataclass
class TokenSet:
    id_token: str
    access_token: str | None
    refresh_token: str | None
    organisation_reference: str | None
    expires_at: float

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> TokenSet:
        def pick(*keys: str) -> str | None:
            for key in keys:
                if data.get(key) is not None:
                    return data[key]
            return None

        id_token = pick("id_token", "idToken")
        if id_token is None:
            raise KeyError(
                "Authentication response contained no id token "
                f"(keys: {sorted(data)})"
            )
        expires_at = _jwt_expiry(id_token) or (time.time() + FALLBACK_LIFETIME)
        return cls(
            id_token=id_token,
            access_token=pick("access_token", "accessToken"),
            refresh_token=pick("refresh_token", "refreshToken"),
            organisation_reference=pick("organisation_reference", "organisationReference"),
            expires_at=expires_at,
        )

    @property
    def fresh(self) -> bool:
        return time.time() < (self.expires_at - EXPIRY_LEEWAY)


class _TokenManagerBase:
    def __init__(
        self,
        email: str,
        password: str,
        *,
        environment: Environment | str = Environment.SANDBOX,
        version: ApiVersion | str = ApiVersion.V6,
    ) -> None:
        self._email = email
        self._password = password
        self._auth_url = f"{base_url(environment, version, Api.WORK)}/authenticate"
        self._refresh_url = f"{base_url(environment, version, Api.PARTY)}/refresh"
        self._logout_url = f"{base_url(environment, version, Api.PARTY)}/logout"
        self.tokens: TokenSet | None = None

    @property
    def organisation_reference(self) -> str | None:
        return self.tokens.organisation_reference if self.tokens else None

    # Note: the wire format is camelCase (confirmed against SANDBOX). Swagger
    # generators expose snake_case Python attributes, but they map back to
    # these camelCase JSON keys - don't be misled into sending snake_case.
    def _auth_body(self) -> dict[str, str]:
        return {"emailAddress": self._email, "password": self._password}

    def _refresh_body(self) -> dict[str, str]:
        assert self.tokens and self.tokens.refresh_token
        return {"refreshToken": self.tokens.refresh_token}


class SyncTokenManager(_TokenManagerBase):
    """Thread-safe token manager for sync clients."""

    def __init__(self, email: str, password: str, *, transport: SyncTransport, **kwargs: Any):
        super().__init__(email, password, **kwargs)
        self._transport = transport
        self._lock = threading.Lock()

    def token_headers(self) -> dict[str, str]:
        return {"token": self.get_id_token()}

    def get_id_token(self) -> str:
        with self._lock:
            if self.tokens is not None and self.tokens.fresh:
                return self.tokens.id_token
            if self.tokens is not None and self.tokens.refresh_token:
                try:
                    self.tokens = self._refresh()
                    return self.tokens.id_token
                except APIError:
                    pass  # refresh token expired/rejected - fall through to re-auth
            self.tokens = self._authenticate()
            return self.tokens.id_token

    def _authenticate(self) -> TokenSet:
        response = self._transport.request("POST", self._auth_url, json=self._auth_body())
        return TokenSet.from_response(response.json())

    def _refresh(self) -> TokenSet:
        response = self._transport.request("POST", self._refresh_url, json=self._refresh_body())
        return TokenSet.from_response(response.json())

    def logout(self) -> None:
        """Invalidate all tokens for this user via ``POST {party}/logout``."""
        if self.tokens is None or self.tokens.access_token is None:
            return
        self._transport.request(
            "POST",
            self._logout_url,
            json={"accessToken": self.tokens.access_token},
            headers={"token": self.tokens.id_token},
        )
        self.tokens = None


class AsyncTokenManager(_TokenManagerBase):
    """Asyncio-safe token manager for async clients."""

    def __init__(self, email: str, password: str, *, transport: AsyncTransport, **kwargs: Any):
        super().__init__(email, password, **kwargs)
        self._transport = transport
        self._lock = asyncio.Lock()

    async def token_headers(self) -> dict[str, str]:
        return {"token": await self.get_id_token()}

    async def get_id_token(self) -> str:
        async with self._lock:
            if self.tokens is not None and self.tokens.fresh:
                return self.tokens.id_token
            if self.tokens is not None and self.tokens.refresh_token:
                try:
                    self.tokens = await self._refresh()
                    return self.tokens.id_token
                except APIError:
                    pass
            self.tokens = await self._authenticate()
            return self.tokens.id_token

    async def _authenticate(self) -> TokenSet:
        response = await self._transport.request("POST", self._auth_url, json=self._auth_body())
        return TokenSet.from_response(response.json())

    async def _refresh(self) -> TokenSet:
        response = await self._transport.request(
            "POST", self._refresh_url, json=self._refresh_body()
        )
        return TokenSet.from_response(response.json())

    async def logout(self) -> None:
        if self.tokens is None or self.tokens.access_token is None:
            return
        await self._transport.request(
            "POST",
            self._logout_url,
            json={"accessToken": self.tokens.access_token},
            headers={"token": self.tokens.id_token},
        )
        self.tokens = None
