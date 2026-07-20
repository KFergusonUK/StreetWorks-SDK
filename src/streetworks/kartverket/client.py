"""Kartverket's open, credential-free services: the address REST API
(``ws.geonorge.no/adresser``), the SSR place-names REST API
(``ws.geonorge.no/stedsnavn``), and Atom-feed-discovered bulk CSV
downloads (see :mod:`streetworks.kartverket.atom`).

**Both REST APIs are confirmed live, open data, no registration** - the
address API's own Geonorge metadata states ``AccessConstraints: "Åpne
data"`` (open data) under Creative Commons BY 4.0; the SSR search
service's states ``"No conditions apply to access and use"``. Neither
needs the agreement one data.norge.no catalogue entry mentions - that
entry (confirmed live: ``"MatrikkelAPI"``, a completely different,
**SOAP**-based service under ``AccessConstraints: "Norge digitalt
begrenset"`` [restricted], requiring "avtale med Kartverket") is a
different product this module does not wrap. Out of scope, not built -
same treatment as NVDB Vegnett (see the models module docstring).

**The irony worth recording**: Norway's *roadworks* adapter
(:mod:`streetworks.datex2.vegvesen`) is this SDK's one unverified
provider, blocked on Statens vegvesen credentials. Norway's *gazetteer*
(this module, a different agency - Kartverket) is wide open and needs no
registration at all. Same country, opposite access story, two different
public bodies.

**Capacity, per Kartverket's own documentation**: the address API
supports 10 concurrent requests at ~98% availability - be a good citizen,
reuse ``_transport.py``'s retry/backoff rather than parallelising hard.
The SSR search service caps results at 5000 hits / 500 per page.

**Bulk CSV is real and is the canonical bulk route here** - unlike Spain,
this is not GML-only: Kartverket publishes ``CSV``, ``FGDB``, ``GML``,
``PostGIS`` and ``SOSI`` side by side for the same dataset (confirmed live
via the Geonorge catalogue), so CSV was picked deliberately, the same
standard-library-only discipline as every other bulk provider in this SDK.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

from .._transport import AsyncTransport, RetryConfig, SyncTransport, _raise_for_response
from .atom import FEED_URL, BulkEntry, parse_feed
from .models import Address, PlaceName, address_from_json, place_from_navn, place_from_sted
from .reader import iter_addresses

__all__ = ["KartverketClient", "AsyncKartverketClient", "ADDRESS_BASE_URL", "SSR_BASE_URL"]

ADDRESS_BASE_URL = "https://ws.geonorge.no/adresser/v1"
SSR_BASE_URL = "https://ws.geonorge.no/stedsnavn/v1"


def _addresses_from_response(data: dict) -> list[Address]:
    return [address_from_json(a) for a in data.get("adresser", [])]


def _places_from_sted_response(data: dict) -> list[PlaceName]:
    return [place_from_sted(n) for n in data.get("navn", [])]


def _places_from_navn_response(data: dict) -> list[PlaceName]:
    return [place_from_navn(n) for n in data.get("navn", [])]


class KartverketClient:
    """Norway's national address register and official place names
    (Kartverket) - credential-free, no registration.

    >>> from streetworks.kartverket import KartverketClient
    >>> with KartverketClient() as kv:
    ...     hits = kv.search(sok="Karl Johans gate 1")
    ...     places = kv.search_places(sok="Karasjok")   # 3 official names
    ...     entries = kv.discover_bulk_downloads()
    """

    def __init__(
        self,
        *,
        address_base_url: str = ADDRESS_BASE_URL,
        ssr_base_url: str = SSR_BASE_URL,
        feed_url: str = FEED_URL,
        retry: RetryConfig | None = None,
        timeout: float = 300.0,
        client: httpx.Client | None = None,
    ):
        self.address_base_url = address_base_url.rstrip("/")
        self.ssr_base_url = ssr_base_url.rstrip("/")
        self.feed_url = feed_url
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    # --- address REST API --------------------------------------------------- #

    def search(self, **params: Any) -> list[Address]:
        """Free-text or field-scoped address search (``/sok``) - e.g.
        ``sok="Karl Johans gate 1"``, or ``adressenavn=...,
        kommunenummer=...``. Wildcard (``*``) supported in ``sok``."""
        response = self._transport.request("GET", f"{self.address_base_url}/sok", params=params)
        return _addresses_from_response(response.json())

    def search_nearby(
        self, lat: float, lon: float, *, radius: float | None = None, **params: Any
    ) -> list[Address]:
        """Point-proximity address search (``/punktsok``) - WGS84/EPSG:4258
        ``lat``/``lon``, matching the address API's own CRS."""
        query: dict[str, Any] = {"lat": lat, "lon": lon, **params}
        if radius is not None:
            query["radius"] = radius
        response = self._transport.request(
            "GET", f"{self.address_base_url}/punktsok", params=query
        )
        return _addresses_from_response(response.json())

    # --- SSR (stedsnavn) place-names API ------------------------------------ #

    def search_places(self, **params: Any) -> list[PlaceName]:
        """Search places by name/area/object type (``/sted``) - one result
        per real place, with every one of its official name forms."""
        response = self._transport.request("GET", f"{self.ssr_base_url}/sted", params=params)
        return _places_from_sted_response(response.json())

    def search_names(self, **params: Any) -> list[PlaceName]:
        """Search individual name forms (``/navn``) - one result per real
        name (language-filterable via ``sprak=...``), normalised to the
        same :class:`~streetworks.kartverket.models.PlaceName` shape as
        :meth:`search_places` - see the models module docstring."""
        response = self._transport.request("GET", f"{self.ssr_base_url}/navn", params=params)
        return _places_from_navn_response(response.json())

    def nearby_places(
        self, nord: float, ost: float, *, koordsys: int = 4258, radius: float, **params: Any
    ) -> list[PlaceName]:
        """Point-proximity place search (``/punkt``). ``koordsys`` accepts
        either ``4258`` (lat/lon) or ``25833`` (UTM33) - confirmed live -
        default matches the address API's own CRS."""
        query: dict[str, Any] = {
            "nord": nord,
            "ost": ost,
            "koordsys": koordsys,
            "radius": radius,
            **params,
        }
        response = self._transport.request("GET", f"{self.ssr_base_url}/punkt", params=query)
        return _places_from_sted_response(response.json())

    def object_types(self) -> list[dict[str, str]]:
        """The legal SSR object types (``/navneobjekttyper``) - 291 real
        types confirmed live, spanning natural features, settlements, and
        genuine address/road types (``Adressenavn``, ``Vegstrekning``,
        ``Vegkryss``, ...)."""
        response = self._transport.request("GET", f"{self.ssr_base_url}/navneobjekttyper")
        result: list[dict[str, str]] = response.json()
        return result

    def languages(self) -> list[dict[str, str]]:
        """The legal SSR language codes (``/sprak``) - includes Norwegian,
        Northern/Southern/Skolt Sámi, Kven, and neighbouring-country
        languages, confirmed live."""
        response = self._transport.request("GET", f"{self.ssr_base_url}/sprak")
        result: list[dict[str, str]] = response.json()
        return result

    # --- bulk files (Atom feed discovery + streamed download) -------------- #

    def discover_bulk_downloads(self) -> list[BulkEntry]:
        """Parse the Matrikkelen-Adresse Atom feed - every real CSV
        download currently offered, never a hardcoded URL."""
        response = self._transport.request("GET", self.feed_url)
        return parse_feed(response.content)

    def download_bulk(self, entry: BulkEntry | str, dest: str | Path) -> Path:
        """Stream one bulk CSV zip (from :meth:`discover_bulk_downloads`,
        or its ``url`` directly) to ``dest``."""
        url = entry.url if isinstance(entry, BulkEntry) else entry
        dest = Path(dest)
        with self._client.stream("GET", url) as response:
            if response.status_code >= 400:
                response.read()
                _raise_for_response(response)
            with open(dest, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        return dest

    # --- reading (thin wrapper over streetworks.kartverket.reader) --------- #

    @staticmethod
    def iter_addresses(source, **kwargs) -> Iterator[Address]:
        return iter_addresses(source, **kwargs)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> KartverketClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncKartverketClient:
    """Async twin of :class:`KartverketClient`; bulk-file reading is
    synchronous streaming either way."""

    def __init__(
        self,
        *,
        address_base_url: str = ADDRESS_BASE_URL,
        ssr_base_url: str = SSR_BASE_URL,
        feed_url: str = FEED_URL,
        retry: RetryConfig | None = None,
        timeout: float = 300.0,
        client: httpx.AsyncClient | None = None,
    ):
        self.address_base_url = address_base_url.rstrip("/")
        self.ssr_base_url = ssr_base_url.rstrip("/")
        self.feed_url = feed_url
        self._client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        self._transport = AsyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    async def search(self, **params: Any) -> list[Address]:
        response = await self._transport.request(
            "GET", f"{self.address_base_url}/sok", params=params
        )
        return _addresses_from_response(response.json())

    async def search_nearby(
        self, lat: float, lon: float, *, radius: float | None = None, **params: Any
    ) -> list[Address]:
        query: dict[str, Any] = {"lat": lat, "lon": lon, **params}
        if radius is not None:
            query["radius"] = radius
        response = await self._transport.request(
            "GET", f"{self.address_base_url}/punktsok", params=query
        )
        return _addresses_from_response(response.json())

    async def search_places(self, **params: Any) -> list[PlaceName]:
        response = await self._transport.request(
            "GET", f"{self.ssr_base_url}/sted", params=params
        )
        return _places_from_sted_response(response.json())

    async def search_names(self, **params: Any) -> list[PlaceName]:
        response = await self._transport.request(
            "GET", f"{self.ssr_base_url}/navn", params=params
        )
        return _places_from_navn_response(response.json())

    async def nearby_places(
        self, nord: float, ost: float, *, koordsys: int = 4258, radius: float, **params: Any
    ) -> list[PlaceName]:
        query: dict[str, Any] = {
            "nord": nord,
            "ost": ost,
            "koordsys": koordsys,
            "radius": radius,
            **params,
        }
        response = await self._transport.request(
            "GET", f"{self.ssr_base_url}/punkt", params=query
        )
        return _places_from_sted_response(response.json())

    async def object_types(self) -> list[dict[str, str]]:
        response = await self._transport.request("GET", f"{self.ssr_base_url}/navneobjekttyper")
        result: list[dict[str, str]] = response.json()
        return result

    async def languages(self) -> list[dict[str, str]]:
        response = await self._transport.request("GET", f"{self.ssr_base_url}/sprak")
        result: list[dict[str, str]] = response.json()
        return result

    async def discover_bulk_downloads(self) -> list[BulkEntry]:
        response = await self._transport.request("GET", self.feed_url)
        return parse_feed(response.content)

    async def download_bulk(self, entry: BulkEntry | str, dest: str | Path) -> Path:
        url = entry.url if isinstance(entry, BulkEntry) else entry
        dest = Path(dest)
        async with self._client.stream("GET", url) as response:
            if response.status_code >= 400:
                await response.aread()
                _raise_for_response(response)
            with open(dest, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        return dest

    iter_addresses = staticmethod(iter_addresses)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncKartverketClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
