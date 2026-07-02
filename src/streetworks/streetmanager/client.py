"""Typed sync and async clients for the DfT Street Manager APIs.

Design notes
------------
* One client object exposes all nine API services as resource groups:
  ``client.work``, ``client.reporting``, ``client.lookup``, ``client.geojson``,
  ``client.party``, ``client.export``, ``client.event``, ``client.sampling``,
  ``client.worklist``.
* Frequently used endpoints (confirmed against the V6 specification) have
  typed convenience methods. Everything else is reachable via the generic
  ``get/post/put/delete`` methods on each group, so the SDK never blocks you
  from calling an endpoint we haven't wrapped yet.
* Authentication, token caching/refresh, retries and 429 handling are
  automatic. Tokens are shared across all resource groups of a client.

Example
-------
>>> from streetworks.streetmanager import StreetManagerClient, Environment
>>> with StreetManagerClient("api-user@example.com", "secret",
...                          environment=Environment.SANDBOX) as sm:
...     work = sm.work.get_work("WRN123")
...     submitted = sm.reporting.permits(status="submitted")
"""

from __future__ import annotations

from typing import Any

import httpx

from .._transport import AsyncTransport, RetryConfig, SyncTransport
from .auth import AsyncTokenManager, SyncTokenManager
from .environments import Api, ApiVersion, Environment, base_url

JSON = dict[str, Any]


# --------------------------------------------------------------------------- #
# Sync client
# --------------------------------------------------------------------------- #


class _SyncGroup:
    """Generic access to one API service (e.g. ``/v6/work``)."""

    api: Api

    def __init__(self, client: StreetManagerClient) -> None:
        self._c = client
        self.base = base_url(client.environment, client.version, self.api)

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.base}/{path.lstrip('/')}"
        return self._c._transport.request(
            method, url, header_provider=self._c._auth.token_headers, **kwargs
        )

    def get(self, path: str, *, params: JSON | None = None, **kw: Any) -> Any:
        return self.request("GET", path, params=params, **kw).json()

    def post(self, path: str, *, json: Any = None, **kw: Any) -> Any:
        return _maybe_json(self.request("POST", path, json=json, **kw))

    def put(self, path: str, *, json: Any = None, **kw: Any) -> Any:
        return _maybe_json(self.request("PUT", path, json=json, **kw))

    def delete(self, path: str, **kw: Any) -> Any:
        return _maybe_json(self.request("DELETE", path, **kw))


def _maybe_json(response: httpx.Response) -> Any:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text


class WorkAPI(_SyncGroup):
    """Work API - submit and progress works, permits, inspections, FPNs..."""

    api = Api.WORK

    # --- works & permits ---------------------------------------------------
    def get_work(self, work_reference_number: str) -> JSON:
        return self.get(f"works/{work_reference_number}")

    def create_work(self, payload: JSON) -> JSON:
        """``POST /works`` - creates a work and its initial permit application."""
        return self.post("works", json=payload)

    def get_permit(self, work_reference_number: str, permit_reference_number: str) -> JSON:
        return self.get(f"works/{work_reference_number}/permits/{permit_reference_number}")

    def assess_permit(
        self, work_reference_number: str, permit_reference_number: str, payload: JSON
    ) -> Any:
        """``PUT .../permits/{prn}/status`` - HA assessment (grant/refuse/etc.)."""
        return self.put(
            f"works/{work_reference_number}/permits/{permit_reference_number}/status",
            json=payload,
        )

    def start_work(self, work_reference_number: str, payload: JSON) -> Any:
        return self.put(f"works/{work_reference_number}/start", json=payload)

    def stop_work(self, work_reference_number: str, payload: JSON) -> Any:
        return self.put(f"works/{work_reference_number}/stop", json=payload)

    # --- alterations -------------------------------------------------------
    def create_alteration(
        self, work_reference_number: str, permit_reference_number: str, payload: JSON
    ) -> JSON:
        return self.post(
            f"works/{work_reference_number}/permits/{permit_reference_number}/alterations",
            json=payload,
        )

    def assess_alteration(
        self,
        work_reference_number: str,
        permit_reference_number: str,
        alteration_reference_number: str,
        payload: JSON,
    ) -> Any:
        return self.put(
            f"works/{work_reference_number}/permits/{permit_reference_number}"
            f"/alterations/{alteration_reference_number}/status",
            json=payload,
        )

    # --- comments, inspections, sites --------------------------------------
    def add_comment(self, work_reference_number: str, payload: JSON) -> JSON:
        return self.post(f"works/{work_reference_number}/comments", json=payload)

    def create_inspection(self, work_reference_number: str, payload: JSON) -> JSON:
        return self.post(f"works/{work_reference_number}/inspections", json=payload)

    def create_site(self, work_reference_number: str, payload: JSON) -> JSON:
        return self.post(f"works/{work_reference_number}/sites", json=payload)

    def create_reinstatement(
        self, work_reference_number: str, site_number: int | str, payload: JSON
    ) -> JSON:
        return self.post(
            f"works/{work_reference_number}/sites/{site_number}/reinstatements", json=payload
        )

    # --- files --------------------------------------------------------------
    def upload_file(self, filename: str, content: bytes, swa_code: str | None = None) -> JSON:
        """``POST /files`` (multipart). Returns ``{"file_id": ...}``."""
        params = {"swaCode": swa_code} if swa_code else None
        response = self.request(
            "POST", "files", files={"file": (filename, content)}, params=params
        )
        return response.json()


class ReportingAPI(_SyncGroup):
    """Reporting API - filterable, paged lists; the primary bulk-read API."""

    api = Api.REPORTING

    def permits(self, **params: Any) -> JSON:
        """``GET /permits`` e.g. ``permits(status="submitted")``."""
        return self.get("permits", params=params)

    def inspections(self, **params: Any) -> JSON:
        return self.get("inspections", params=params)

    def fixed_penalty_notices(self, **params: Any) -> JSON:
        return self.get("fixed-penalty-notices", params=params)

    def reinstatements(self, **params: Any) -> JSON:
        return self.get("reinstatements", params=params)

    def alterations(self, **params: Any) -> JSON:
        return self.get("alterations", params=params)


class LookupAPI(_SyncGroup):
    """Street Lookup API - NSG/ASD queries by USRN or location."""

    api = Api.LOOKUP

    def streets(self, **params: Any) -> Any:
        """``GET /nsg/streets`` - query NSG street data (e.g. by coordinates)."""
        return self.get("nsg/streets", params=params)

    def street_by_usrn(self, usrn: int | str) -> Any:
        """``GET /nsg/streets/{usrn}``."""
        return self.get(f"nsg/streets/{usrn}")


class GeoJsonAPI(_SyncGroup):
    """GeoJSON API - spatial works/activity data (BNG / EPSG:27700)."""

    api = Api.GEOJSON

    def works(self, **params: Any) -> JSON:
        """``GET /works`` - works within a bounding box, as GeoJSON."""
        return self.get("works", params=params)

    def activities(self, **params: Any) -> JSON:
        return self.get("activities", params=params)


class PartyAPI(_SyncGroup):
    """Party API - users, organisations, workstreams, token lifecycle."""

    api = Api.PARTY

    def user(self, email: str) -> JSON:
        return self.get(f"users/{email}")

    def organisation(self, organisation_reference: str) -> JSON:
        return self.get(f"organisations/{organisation_reference}")

    def workstreams(self, organisation_reference: str) -> Any:
        return self.get(f"organisations/{organisation_reference}/workstreams")


class ExportAPI(_SyncGroup):
    """Data Export API - request CSV extracts and download them."""

    api = Api.EXPORT

    def request_csv(self, resource: str, payload: JSON | None = None) -> JSON:
        """``POST /{resource}/csv`` e.g. ``request_csv("permits", {...})``."""
        return self.post(f"{resource}/csv", json=payload or {})

    def get_csv(self, csv_id: int | str) -> bytes:
        """``GET /csv/{csvId}`` - returns the raw CSV bytes."""
        return self.request("GET", f"csv/{csv_id}").content


class EventAPI(_SyncGroup):
    """Event API - ``/works/updates`` polling for reconciliation."""

    api = Api.EVENT

    def works_updates(self, **params: Any) -> Any:
        return self.get("works/updates", params=params)


class SamplingAPI(_SyncGroup):
    api = Api.SAMPLING


class WorklistAPI(_SyncGroup):
    api = Api.WORKLIST


class StreetManagerClient:
    """Synchronous client for all Street Manager APIs."""

    def __init__(
        self,
        email: str,
        password: str,
        *,
        environment: Environment | str = Environment.SANDBOX,
        version: ApiVersion | str = ApiVersion.V6,
        timeout: float = 30.0,
        retry: RetryConfig | None = None,
        transport: SyncTransport | None = None,
    ) -> None:
        self.environment = environment
        self.version = version
        self._transport = transport or SyncTransport(timeout=timeout, retry=retry)
        self._auth = SyncTokenManager(
            email, password, transport=self._transport, environment=environment, version=version
        )
        self.work = WorkAPI(self)
        self.reporting = ReportingAPI(self)
        self.lookup = LookupAPI(self)
        self.geojson = GeoJsonAPI(self)
        self.party = PartyAPI(self)
        self.export = ExportAPI(self)
        self.event = EventAPI(self)
        self.sampling = SamplingAPI(self)
        self.worklist = WorklistAPI(self)

    @property
    def organisation_reference(self) -> str | None:
        """SWA code / organisation reference of the authenticated user."""
        return self._auth.organisation_reference

    def authenticate(self) -> str | None:
        """Eagerly acquire an ID token, verifying credentials and connectivity.

        Returns the organisation reference on success. Raises
        :class:`~streetworks.exceptions.AuthenticationError` for bad
        credentials, ``AccountLockedError`` (423), ``OrganisationSuspendedError``
        (412), or a transport error if the service is unreachable. Useful as a
        fail-fast check at start-up or in a connectivity smoke test.
        """
        self._auth.get_id_token()
        return self.organisation_reference

    def logout(self) -> None:
        self._auth.logout()

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> StreetManagerClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


# --------------------------------------------------------------------------- #
# Async client
# --------------------------------------------------------------------------- #


class _AsyncGroup:
    api: Api

    def __init__(self, client: AsyncStreetManagerClient) -> None:
        self._c = client
        self.base = base_url(client.environment, client.version, self.api)

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.base}/{path.lstrip('/')}"
        return await self._c._transport.request(
            method, url, header_provider=self._c._auth.token_headers, **kwargs
        )

    async def get(self, path: str, *, params: JSON | None = None, **kw: Any) -> Any:
        return (await self.request("GET", path, params=params, **kw)).json()

    async def post(self, path: str, *, json: Any = None, **kw: Any) -> Any:
        return _maybe_json(await self.request("POST", path, json=json, **kw))

    async def put(self, path: str, *, json: Any = None, **kw: Any) -> Any:
        return _maybe_json(await self.request("PUT", path, json=json, **kw))

    async def delete(self, path: str, **kw: Any) -> Any:
        return _maybe_json(await self.request("DELETE", path, **kw))


class AsyncWorkAPI(_AsyncGroup):
    api = Api.WORK

    async def get_work(self, work_reference_number: str) -> JSON:
        return await self.get(f"works/{work_reference_number}")

    async def create_work(self, payload: JSON) -> JSON:
        return await self.post("works", json=payload)

    async def get_permit(self, work_reference_number: str, permit_reference_number: str) -> JSON:
        return await self.get(f"works/{work_reference_number}/permits/{permit_reference_number}")

    async def assess_permit(
        self, work_reference_number: str, permit_reference_number: str, payload: JSON
    ) -> Any:
        return await self.put(
            f"works/{work_reference_number}/permits/{permit_reference_number}/status",
            json=payload,
        )


class AsyncReportingAPI(_AsyncGroup):
    api = Api.REPORTING

    async def permits(self, **params: Any) -> JSON:
        return await self.get("permits", params=params)

    async def inspections(self, **params: Any) -> JSON:
        return await self.get("inspections", params=params)

    async def fixed_penalty_notices(self, **params: Any) -> JSON:
        return await self.get("fixed-penalty-notices", params=params)

    async def reinstatements(self, **params: Any) -> JSON:
        return await self.get("reinstatements", params=params)

    async def alterations(self, **params: Any) -> JSON:
        return await self.get("alterations", params=params)


class AsyncLookupAPI(_AsyncGroup):
    api = Api.LOOKUP


class AsyncGeoJsonAPI(_AsyncGroup):
    api = Api.GEOJSON


class AsyncPartyAPI(_AsyncGroup):
    api = Api.PARTY


class AsyncExportAPI(_AsyncGroup):
    api = Api.EXPORT


class AsyncEventAPI(_AsyncGroup):
    api = Api.EVENT

    async def works_updates(self, **params: Any) -> Any:
        return await self.get("works/updates", params=params)


class AsyncSamplingAPI(_AsyncGroup):
    api = Api.SAMPLING


class AsyncWorklistAPI(_AsyncGroup):
    api = Api.WORKLIST


class AsyncStreetManagerClient:
    """Asynchronous client for all Street Manager APIs."""

    def __init__(
        self,
        email: str,
        password: str,
        *,
        environment: Environment | str = Environment.SANDBOX,
        version: ApiVersion | str = ApiVersion.V6,
        timeout: float = 30.0,
        retry: RetryConfig | None = None,
        transport: AsyncTransport | None = None,
    ) -> None:
        self.environment = environment
        self.version = version
        self._transport = transport or AsyncTransport(timeout=timeout, retry=retry)
        self._auth = AsyncTokenManager(
            email, password, transport=self._transport, environment=environment, version=version
        )
        self.work = AsyncWorkAPI(self)
        self.reporting = AsyncReportingAPI(self)
        self.lookup = AsyncLookupAPI(self)
        self.geojson = AsyncGeoJsonAPI(self)
        self.party = AsyncPartyAPI(self)
        self.export = AsyncExportAPI(self)
        self.event = AsyncEventAPI(self)
        self.sampling = AsyncSamplingAPI(self)
        self.worklist = AsyncWorklistAPI(self)

    @property
    def organisation_reference(self) -> str | None:
        return self._auth.organisation_reference

    async def authenticate(self) -> str | None:
        """Eagerly acquire an ID token, verifying credentials and connectivity.
        Returns the organisation reference on success."""
        await self._auth.get_id_token()
        return self.organisation_reference

    async def logout(self) -> None:
        await self._auth.logout()

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncStreetManagerClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
