"""Statens vegvesen's NVDB REST API - `/vegnett` (road network topology)
and `/vegobjekter` (road objects, including `Adresse`, type 538 - the
naming/addressing layer, see :mod:`streetworks.nvdb.models`).

**No credentials required for reads - confirmed live, and confirmed in
NVDB's own API guidelines** ("Det er ikke nødvendig å registrere en
bruker for å bruke APIet til å lese data fra NVDB" - "It is not
necessary to register a user to use the API to read data from NVDB",
`nvdb-vegdata/apidokumentasjon` on GitHub, the real source behind
`api.vegdata.no`). The only real requirement, confirmed live (a bare
request without it returns HTTP 400, ``"X-Client må være satt..."`` -
"X-Client must be set...") is the `X-Client` header, a client-identifying
string, not an API key - `X-Kontaktperson` (a contact email) is
documented as recommended, not enforced. **This is the striking asymmetry
the design brief asked about**: Statens vegvesen's own DATEX roadworks
feed (:mod:`streetworks.datex2.vegvesen`) is this SDK's one
credential-blocked, unverified provider; this, from the same agency, is
wide open.

**Licence: NLOD 1.0 (Norsk lisens for offentlige data), not Elveg's CC BY
4.0** - confirmed from the NVDB API's own documentation
(`retningslinjer.md`), not assumed from Kartverket's Elveg distribution
metadata, per the design brief's own instruction. Same underlying road
network, two different publishers, two different licences.

Both endpoints paginate with a real cursor (`metadata.neste.start`/
`.href`) and accept a `kommune` (municipality) filter, confirmed live at
real scale (1,000+ results per page) - REST is this module's only
access route; the CSV export service (`nvdb-eksport`) was evaluated and
not built, since the REST API already does the job cleanly (per the
design brief's "don't build two routes for the same job").
"""

from __future__ import annotations

from typing import Any

import httpx

from .._transport import AsyncTransport, RetryConfig, SyncTransport
from .models import (
    VegAdresse,
    Veglenkesekvens,
    vegadresse_from_response,
    veglenkesekvens_from_response,
)

__all__ = [
    "ADRESSE_TYPE_ID",
    "VEGNETT_BASE_URL",
    "VEGOBJEKTER_BASE_URL",
    "AsyncNVDBClient",
    "NVDBClient",
]

VEGNETT_BASE_URL = "https://nvdbapiles.atlas.vegvesen.no/vegnett/api/v4"
VEGOBJEKTER_BASE_URL = "https://nvdbapiles.atlas.vegvesen.no/vegobjekter/api/v4"

#: The "Adresse" road-object type - see the models module docstring.
ADRESSE_TYPE_ID = 538

_DEFAULT_CLIENT_HEADER = "streetworks-sdk"


class NVDBClient:
    """Norway's national road network (NVDB) - road link topology and
    addressing, live via REST. No credentials required, just a
    self-identifying `X-Client` header (see the module docstring).

    >>> from streetworks.nvdb import NVDBClient
    >>> with NVDBClient(client_name="my-app") as nvdb:
    ...     sequences = nvdb.veglenkesekvenser(kommune=4201)
    ...     addresses = nvdb.adresser(kommune=4201)
    ...     print(addresses[0].adressenavn, addresses[0].veglenkesekvens_ids)
    """

    def __init__(
        self,
        *,
        client_name: str = _DEFAULT_CLIENT_HEADER,
        contact: str | None = None,
        vegnett_base_url: str = VEGNETT_BASE_URL,
        vegobjekter_base_url: str = VEGOBJEKTER_BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ):
        self.vegnett_base_url = vegnett_base_url.rstrip("/")
        self.vegobjekter_base_url = vegobjekter_base_url.rstrip("/")
        headers = {"X-Client": client_name}
        if contact:
            headers["X-Kontaktperson"] = contact
        self._client = client or httpx.Client(
            timeout=timeout, follow_redirects=True, headers=headers
        )
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    def veglenkesekvenser(
        self, *, kommune: int | None = None, count: int | None = None, **params: Any
    ) -> list[Veglenkesekvens]:
        """Fetch road link sequences, optionally filtered to one
        municipality. `count` maps to the API's own `antall` (page size)
        parameter - one page, not auto-paginated; use the raw response's
        `metadata.neste` to continue (see the module docstring)."""
        query = dict(params)
        if kommune is not None:
            query["kommune"] = kommune
        if count is not None:
            query["antall"] = count
        response = self._transport.request(
            "GET", f"{self.vegnett_base_url}/veglenkesekvenser", params=query
        )
        return [veglenkesekvens_from_response(o) for o in response.json().get("objekter", [])]

    def adresser(
        self, *, kommune: int | None = None, count: int | None = None, **params: Any
    ) -> list[VegAdresse]:
        """Fetch `Adresse` road objects (type 538) - the naming/addressing
        layer, see :mod:`streetworks.nvdb.models`. Always requests
        `inkluder=alle` so list results carry full attributes inline,
        confirmed live to avoid an N+1 fetch-by-id per address."""
        query = {"inkluder": "alle", **params}
        if kommune is not None:
            query["kommune"] = kommune
        if count is not None:
            query["antall"] = count
        response = self._transport.request(
            "GET", f"{self.vegobjekter_base_url}/vegobjekter/{ADRESSE_TYPE_ID}", params=query
        )
        return [vegadresse_from_response(o) for o in response.json().get("objekter", [])]

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> NVDBClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncNVDBClient:
    """Async twin of :class:`NVDBClient`."""

    def __init__(
        self,
        *,
        client_name: str = _DEFAULT_CLIENT_HEADER,
        contact: str | None = None,
        vegnett_base_url: str = VEGNETT_BASE_URL,
        vegobjekter_base_url: str = VEGOBJEKTER_BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ):
        self.vegnett_base_url = vegnett_base_url.rstrip("/")
        self.vegobjekter_base_url = vegobjekter_base_url.rstrip("/")
        headers = {"X-Client": client_name}
        if contact:
            headers["X-Kontaktperson"] = contact
        self._client = client or httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, headers=headers
        )
        self._transport = AsyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    async def veglenkesekvenser(
        self, *, kommune: int | None = None, count: int | None = None, **params: Any
    ) -> list[Veglenkesekvens]:
        query = dict(params)
        if kommune is not None:
            query["kommune"] = kommune
        if count is not None:
            query["antall"] = count
        response = await self._transport.request(
            "GET", f"{self.vegnett_base_url}/veglenkesekvenser", params=query
        )
        return [veglenkesekvens_from_response(o) for o in response.json().get("objekter", [])]

    async def adresser(
        self, *, kommune: int | None = None, count: int | None = None, **params: Any
    ) -> list[VegAdresse]:
        query = {"inkluder": "alle", **params}
        if kommune is not None:
            query["kommune"] = kommune
        if count is not None:
            query["antall"] = count
        response = await self._transport.request(
            "GET", f"{self.vegobjekter_base_url}/vegobjekter/{ADRESSE_TYPE_ID}", params=query
        )
        return [vegadresse_from_response(o) for o in response.json().get("objekter", [])]

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncNVDBClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
