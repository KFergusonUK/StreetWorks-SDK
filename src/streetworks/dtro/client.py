"""DfT Digital Traffic Regulation Orders (D-TRO) client.

Verified against the D-TRO API documentation and Postman collections
(July 2026):

* Environments: integration ``https://dtro-integration.dft.gov.uk/v1`` and
  production ``https://dtro.dft.gov.uk/v1`` - isolated services with separate
  application credentials.
* Auth: OAuth 2.0 client credentials via ``POST {base}/oauth-generator`` with
  the client id/secret as HTTP Basic credentials. Access tokens last 30
  minutes; this client caches and renews them automatically.
* Requests carry ``Authorization: Bearer``, plus ``x-app-id`` (your
  application's UUID) and an ``X-Correlation-ID`` (auto-generated per request
  unless supplied).
* Publishing requires an application with the publisher scope; consuming
  works with either scope.
* Payload limits: 10 MB for JSON bodies/files; gzip uploads decompress to a
  maximum of 25 MB.
"""

from __future__ import annotations

import gzip as gzip_module
import uuid
from enum import Enum
from typing import Any

import httpx

from .._oauth import AsyncClientCredentials, SyncClientCredentials
from .._transport import AsyncTransport, RetryConfig, SyncTransport

JSON = dict[str, Any]


class Environment(str, Enum):
    INTEGRATION = "https://dtro-integration.dft.gov.uk/v1"
    PRODUCTION = "https://dtro.dft.gov.uk/v1"

    @property
    def base(self) -> str:
        return self.value


class DTROClient:
    """Synchronous D-TRO client (publisher and/or consumer)."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        app_id: str | None = None,
        environment: Environment | str = Environment.INTEGRATION,
        timeout: float = 60.0,
        retry: RetryConfig | None = None,
    ) -> None:
        self.base = environment.base if isinstance(environment, Environment) else str(
            environment
        ).rstrip("/")
        self.app_id = app_id
        self._transport = SyncTransport(timeout=timeout, retry=retry)
        self._oauth = SyncClientCredentials(
            f"{self.base}/oauth-generator",
            client_id,
            client_secret,
            style="basic",
            transport=self._transport,
        )

    # ------------------------------------------------------------------ #

    def _headers(self) -> dict[str, str]:
        headers = self._oauth.bearer_headers()
        headers["X-Correlation-ID"] = str(uuid.uuid4())
        if self.app_id:
            headers["x-app-id"] = self.app_id
        return headers

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Generic escape hatch for endpoints not wrapped below."""
        url = f"{self.base}/{path.lstrip('/')}"
        return self._transport.request(method, url, header_provider=self._headers, **kwargs)

    # --- consume ---------------------------------------------------------- #

    def get_dtro(self, dtro_id: str) -> JSON:
        """``GET /dtros/{id}`` - retrieve a single D-TRO."""
        return self.request("GET", f"dtros/{dtro_id}").json()

    def get_all_dtros_url(self) -> JSON:
        """``GET /dtros/all`` - returns a signed URL (valid 60 minutes) for a
        CSV of all published D-TROs."""
        return self.request("GET", "dtros/all").json()

    def search_events(self, **criteria: Any) -> JSON:
        """``POST /events`` - search D-TRO create/update/delete events.

        Supported criteria include ``page``, ``pageSize``, ``since``, ``to``,
        ``traCreator``, ``currentTraOwner``, ``troName``, ``regulationType``,
        ``vehicleType``, ``orderReportingPoint``, and ``regulationStart`` /
        ``regulationEnd`` as ``{"operator": ..., "value": ...}`` dicts.
        """
        return self.request("POST", "events", json=criteria).json()

    # --- publish (publisher scope required) -------------------------------- #

    def create_dtro(self, payload: JSON) -> JSON:
        """``POST /dtros/createFromBody`` (payload limit 10 MB)."""
        return self.request("POST", "dtros/createFromBody", json=payload).json()

    def update_dtro(self, dtro_id: str, payload: JSON) -> JSON:
        """``PUT /dtros/updateFromBody/{dtroId}``."""
        return self.request("PUT", f"dtros/updateFromBody/{dtro_id}", json=payload).json()

    def create_dtro_from_file(
        self, content: bytes, *, filename: str = "dtro.json", gzip: bool = False
    ) -> JSON:
        """``POST /dtros/createFromFile`` - upload raw JSON bytes; set
        ``gzip=True`` to compress before upload (large D-TROs; the server
        accepts up to 25 MB decompressed)."""
        if gzip:
            content = gzip_module.compress(content)
            filename = filename if filename.endswith(".gz") else f"{filename}.gz"
        response = self.request(
            "POST", "dtros/createFromFile", files={"file": (filename, content)}
        )
        return response.json()

    def update_dtro_from_file(
        self, dtro_id: str, content: bytes, *, filename: str = "dtro.json", gzip: bool = False
    ) -> JSON:
        """``PUT /dtros/updateFromFile/{dtroId}``."""
        if gzip:
            content = gzip_module.compress(content)
            filename = filename if filename.endswith(".gz") else f"{filename}.gz"
        response = self.request(
            "PUT", f"dtros/updateFromFile/{dtro_id}", files={"file": (filename, content)}
        )
        return response.json()

    def delete_dtro(self, dtro_id: str) -> None:
        """``DELETE /dtros/{dtroId}``."""
        self.request("DELETE", f"dtros/{dtro_id}")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> DTROClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncDTROClient:
    """Asynchronous D-TRO client."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        app_id: str | None = None,
        environment: Environment | str = Environment.INTEGRATION,
        timeout: float = 60.0,
        retry: RetryConfig | None = None,
    ) -> None:
        self.base = environment.base if isinstance(environment, Environment) else str(
            environment
        ).rstrip("/")
        self.app_id = app_id
        self._transport = AsyncTransport(timeout=timeout, retry=retry)
        self._oauth = AsyncClientCredentials(
            f"{self.base}/oauth-generator",
            client_id,
            client_secret,
            style="basic",
            transport=self._transport,
        )

    async def _headers(self) -> dict[str, str]:
        headers = await self._oauth.bearer_headers()
        headers["X-Correlation-ID"] = str(uuid.uuid4())
        if self.app_id:
            headers["x-app-id"] = self.app_id
        return headers

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.base}/{path.lstrip('/')}"
        return await self._transport.request(
            method, url, header_provider=self._headers, **kwargs
        )

    async def get_dtro(self, dtro_id: str) -> JSON:
        return (await self.request("GET", f"dtros/{dtro_id}")).json()

    async def get_all_dtros_url(self) -> JSON:
        return (await self.request("GET", "dtros/all")).json()

    async def search_events(self, **criteria: Any) -> JSON:
        return (await self.request("POST", "events", json=criteria)).json()

    async def create_dtro(self, payload: JSON) -> JSON:
        return (await self.request("POST", "dtros/createFromBody", json=payload)).json()

    async def update_dtro(self, dtro_id: str, payload: JSON) -> JSON:
        return (
            await self.request("PUT", f"dtros/updateFromBody/{dtro_id}", json=payload)
        ).json()

    async def delete_dtro(self, dtro_id: str) -> None:
        await self.request("DELETE", f"dtros/{dtro_id}")

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncDTROClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
