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

        Four fields are **required** by the API: ``page``, ``pageSize``,
        ``since`` and ``to`` (the last two are ISO 8601 date-times). Optional
        criteria include ``traCreator``, ``currentTraOwner``, ``troName``,
        ``regulationType``, ``vehicleType``, ``orderReportingPoint``,
        ``modifiedFrom`` / ``modifiedTo``, ``deletedFrom`` / ``deletedTo``, and
        ``regulationStart`` / ``regulationEnd``.

        Example::

            dtro.search_events(page=1, pageSize=50,
                               since="2025-01-01T00:00:00",
                               to="2025-03-01T00:00:00")
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

    @property
    def token_info(self) -> JSON | None:
        """Metadata from the most recent token response, if any - includes
        ``scope``, ``api_product_list`` and ``organization_name``, which reveal
        which environment and access level you authenticated into. ``None``
        until the first authenticated call."""
        return self._oauth.last_token_response

    # --- provisions (publisher scope; require the App-Id header) ------------ #

    def _app_id_header(self) -> dict[str, str]:
        if not self.app_id:
            raise ValueError(
                "app_id is required for provisions endpoints "
                "(they send it as the 'App-Id' header, distinct from x-app-id)"
            )
        return {"App-Id": self.app_id}

    def create_provisions(self, provisions: list[JSON], *, dtro_id: str | None = None) -> Any:
        """``POST /provisions/createFromBody`` - body is a JSON array of
        provision objects. Requires ``app_id`` (sent as the ``App-Id`` header)."""
        params = {"dtroId": dtro_id} if dtro_id else None
        return self.request(
            "POST",
            "provisions/createFromBody",
            json=provisions,
            params=params,
            headers=self._app_id_header(),
        ).json()

    def update_provision(self, provision_id: str, provision: JSON) -> Any:
        """``PUT /provisions/{provisionId}``. Requires ``app_id``."""
        return self.request(
            "PUT", f"provisions/{provision_id}", json=provision, headers=self._app_id_header()
        ).json()

    def delete_provision(self, provision_id: str) -> None:
        """``DELETE /provisions/{provisionId}``. Requires ``app_id``."""
        self.request("DELETE", f"provisions/{provision_id}", headers=self._app_id_header())

    # --- schemas & search (consume) ---------------------------------------- #

    def schema_versions(self) -> Any:
        """``GET /schemas/versions`` - list available D-TRO schema versions."""
        return self.request("GET", "schemas/versions").json()

    def schemas(self) -> Any:
        """``GET /schemas`` - list schemas."""
        return self.request("GET", "schemas").json()

    def get_schema(self, version: str) -> Any:
        """``GET /schemas/{version}`` - fetch a specific schema version."""
        return self.request("GET", f"schemas/{version}").json()

    def search(self, query: JSON) -> Any:
        """``POST /search`` - search published D-TROs (a ``DtroSearch`` body)."""
        return self.request("POST", "search", json=query).json()

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

    def _app_id_header(self) -> dict[str, str]:
        if not self.app_id:
            raise ValueError(
                "app_id is required for provisions endpoints "
                "(they send it as the 'App-Id' header, distinct from x-app-id)"
            )
        return {"App-Id": self.app_id}

    async def create_provisions(
        self, provisions: list[JSON], *, dtro_id: str | None = None
    ) -> Any:
        params = {"dtroId": dtro_id} if dtro_id else None
        return (
            await self.request(
                "POST",
                "provisions/createFromBody",
                json=provisions,
                params=params,
                headers=self._app_id_header(),
            )
        ).json()

    async def update_provision(self, provision_id: str, provision: JSON) -> Any:
        return (
            await self.request(
                "PUT",
                f"provisions/{provision_id}",
                json=provision,
                headers=self._app_id_header(),
            )
        ).json()

    async def delete_provision(self, provision_id: str) -> None:
        await self.request(
            "DELETE", f"provisions/{provision_id}", headers=self._app_id_header()
        )

    async def schema_versions(self) -> Any:
        return (await self.request("GET", "schemas/versions")).json()

    async def get_schema(self, version: str) -> Any:
        return (await self.request("GET", f"schemas/{version}")).json()

    async def search(self, query: JSON) -> Any:
        return (await self.request("POST", "search", json=query)).json()

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncDTROClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
