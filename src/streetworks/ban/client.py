"""BAN's geocoding API - credential-free search/reverse over ~25M French
addresses, plus streaming downloads of the bulk files (see
:mod:`streetworks.ban.reader`).

**The documented endpoint has moved, and the move is now final.** The BAN's
"API Adresse" transferred from DINUM to IGN's Géoplateforme; the old
``api-adresse.data.gouv.fr`` sends ``Deprecation``/``Sunset`` headers dated
2026-01-31 (already past, confirmed live 2026-07) and a
``x-api-new-host: https://data.geopf.fr/geocodage/`` header on every
response - it still proxies real, correct results today, but is not this
adapter's base URL. This client targets the documented replacement:

    https://data.geopf.fr/geocodage

confirmed live 2026-07 with real ``search``/``reverse`` requests (design
brief note to the contrary - "returned HTTP 400 to several parameter
forms" - did not reproduce here; a plain ``q=``/``lon=``&``lat=`` request
succeeds, so whatever failed was request construction, not the service).

Rate limits, per IGN's own documentation: 50 calls/second/IP for this
unitary API; bulk CSV geocoding (not implemented here - see
:mod:`streetworks.ban.reader` for the bulk *file* route instead, which is
the closer analogue to the other gazetteers in this SDK) is one concurrent
call per IP.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import httpx

from .._transport import AsyncTransport, RetryConfig, SyncTransport, _raise_for_response
from .models import BANAddress, address_from_api_feature
from .reader import bulk_url, iter_addresses, iter_addresses_csv

__all__ = ["BANClient", "AsyncBANClient", "GEOCODING_BASE_URL"]

GEOCODING_BASE_URL = "https://data.geopf.fr/geocodage"


def _addresses_from_response(data: dict) -> list[BANAddress]:
    return [address_from_api_feature(f) for f in data.get("features", [])]


class BANClient:
    """France's Base Adresse Nationale (BAN) - the national address base,
    ~25M addresses, no credentials required.

    >>> from streetworks.ban import BANClient
    >>> with BANClient() as ban:
    ...     hits = ban.search("8 rue des halles paris")
    ...     here = ban.reverse(2.347222, 48.859393)
    ...     path = ban.download_departement("75", "dept75.csv.gz")  # bulk file
    """

    def __init__(
        self,
        *,
        base_url: str = GEOCODING_BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    def search(
        self,
        q: str,
        *,
        limit: int = 5,
        citycode: str | None = None,
        postcode: str | None = None,
        type: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
    ) -> list[BANAddress]:
        """Search for an address/street/locality by free text. ``type``
        narrows to ``"housenumber"``, ``"street"``, ``"locality"`` or
        ``"municipality"`` (all confirmed live). ``lat``/``lon`` bias
        ranking towards a point without limiting results to it."""
        params: dict[str, str | int | float] = {"q": q, "limit": limit}
        if citycode:
            params["citycode"] = citycode
        if postcode:
            params["postcode"] = postcode
        if type:
            params["type"] = type
        if lat is not None:
            params["lat"] = lat
        if lon is not None:
            params["lon"] = lon
        response = self._transport.request("GET", f"{self.base_url}/search", params=params)
        return _addresses_from_response(response.json())

    def reverse(
        self, lon: float, lat: float, *, limit: int = 1, type: str | None = None
    ) -> list[BANAddress]:
        """Reverse-geocode a WGS84 point to the nearest address(es)."""
        params: dict[str, str | int | float] = {"lon": lon, "lat": lat, "limit": limit}
        if type:
            params["type"] = type
        response = self._transport.request("GET", f"{self.base_url}/reverse", params=params)
        return _addresses_from_response(response.json())

    # --- bulk files (streamed, never buffered whole - see reader.py) ------ #

    def download_departement(
        self, dept: str, dest: str | Path, *, format: str = "csv-bal"
    ) -> Path:
        """Stream one département's bulk address file to ``dest``."""
        return self._download(bulk_url(dept, format=format), dest)

    def download_national(self, dest: str | Path, *, format: str = "csv-bal") -> Path:
        """Stream the national bulk address file to ``dest`` - ~900 MB-1.4 GB
        gzipped, confirmed live 2026-07. Prefer :meth:`download_departement`
        unless national coverage is genuinely needed."""
        return self._download(bulk_url("france", format=format), dest)

    def _download(self, url: str, dest: str | Path) -> Path:
        dest = Path(dest)
        with self._client.stream("GET", url) as response:
            if response.status_code >= 400:
                response.read()
                _raise_for_response(response)
            with open(dest, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        return dest

    # --- reading (thin wrappers over streetworks.ban.reader) -------------- #

    @staticmethod
    def iter_addresses(source, **kwargs) -> Iterator[BANAddress]:
        return iter_addresses(source, **kwargs)

    @staticmethod
    def iter_addresses_csv(source, **kwargs) -> Iterator[BANAddress]:
        return iter_addresses_csv(source, **kwargs)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BANClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncBANClient:
    """Async twin of :class:`BANClient`; bulk-file reading is synchronous
    streaming either way (see :mod:`streetworks.ban.reader`)."""

    def __init__(
        self,
        *,
        base_url: str = GEOCODING_BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        self._transport = AsyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    async def search(
        self,
        q: str,
        *,
        limit: int = 5,
        citycode: str | None = None,
        postcode: str | None = None,
        type: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
    ) -> list[BANAddress]:
        params: dict[str, str | int | float] = {"q": q, "limit": limit}
        if citycode:
            params["citycode"] = citycode
        if postcode:
            params["postcode"] = postcode
        if type:
            params["type"] = type
        if lat is not None:
            params["lat"] = lat
        if lon is not None:
            params["lon"] = lon
        response = await self._transport.request("GET", f"{self.base_url}/search", params=params)
        return _addresses_from_response(response.json())

    async def reverse(
        self, lon: float, lat: float, *, limit: int = 1, type: str | None = None
    ) -> list[BANAddress]:
        params: dict[str, str | int | float] = {"lon": lon, "lat": lat, "limit": limit}
        if type:
            params["type"] = type
        response = await self._transport.request("GET", f"{self.base_url}/reverse", params=params)
        return _addresses_from_response(response.json())

    async def download_departement(
        self, dept: str, dest: str | Path, *, format: str = "csv-bal"
    ) -> Path:
        return await self._download(bulk_url(dept, format=format), dest)

    async def download_national(self, dest: str | Path, *, format: str = "csv-bal") -> Path:
        return await self._download(bulk_url("france", format=format), dest)

    async def _download(self, url: str, dest: str | Path) -> Path:
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
    iter_addresses_csv = staticmethod(iter_addresses_csv)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncBANClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
