"""OS Open USRN - credential-free GB-wide USRN lookup with geometry.

Ordnance Survey publishes Open USRN (every Unique Street Reference Number in
Great Britain with a geometry) as OS OpenData. The Downloads API needs no API
key for OpenData products:

* ``GET https://api.os.uk/downloads/v1/products/OpenUSRN`` - product metadata
* ``GET .../products/OpenUSRN/downloads`` - the downloadable files
  (``url``, ``fileName``, ``format``, ``size``)

The product ships as a GeoPackage (~300 MB, usually zipped), which is SQLite
underneath - see :mod:`streetworks.openusrn.reader` for querying it with no
extra dependencies.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport, _raise_for_response

__all__ = ["OpenUSRNClient", "AsyncOpenUSRNClient", "PRODUCT_URL", "extract_gpkg"]

PRODUCT_URL = "https://api.os.uk/downloads/v1/products/OpenUSRN"


def extract_gpkg(archive: str | Path, dest_dir: str | Path | None = None) -> Path:
    """Extract the ``.gpkg`` member from a downloaded zip and return its path.
    If ``archive`` is already a ``.gpkg``, it is returned unchanged."""
    archive = Path(archive)
    if archive.suffix.lower() == ".gpkg":
        return archive
    dest_dir = Path(dest_dir) if dest_dir else archive.parent
    with zipfile.ZipFile(archive) as z:
        members = [n for n in z.namelist() if n.lower().endswith(".gpkg")]
        if not members:
            raise ValueError(f"no .gpkg member found in {archive}")
        z.extract(members[0], dest_dir)
    return dest_dir / members[0]


class OpenUSRNClient:
    """Query and download the OS Open USRN product. No credentials required.

    >>> from streetworks.openusrn import OpenUSRNClient
    >>> with OpenUSRNClient() as os_open:
    ...     info = os_open.product_info()
    ...     path = os_open.download("openusrn.zip")   # ~300 MB, streamed
    """

    def __init__(
        self,
        *,
        product_url: str = PRODUCT_URL,
        retry: RetryConfig | None = None,
        timeout: float = 600.0,
        client: httpx.Client | None = None,
    ):
        self.product_url = product_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    def product_info(self) -> Any:
        """Product metadata: name, description, version and data date."""
        return self._transport.request("GET", self.product_url).json()

    def downloads(self, *, file_format: str | None = "GeoPackage") -> list[dict]:
        """The downloadable files for the product, optionally filtered by
        format. Each entry carries ``url``, ``fileName``, ``format`` and
        ``size`` (bytes)."""
        params = {"format": file_format} if file_format else None
        response = self._transport.request(
            "GET", f"{self.product_url}/downloads", params=params
        )
        return response.json()

    def download(
        self, dest: str | Path, *, file_format: str = "GeoPackage"
    ) -> Path:
        """Stream the product file to ``dest`` and return its path.

        The GeoPackage is ~300 MB; it is streamed in chunks, never held in
        memory. The result is typically a zip - use :func:`extract_gpkg` to
        get the ``.gpkg`` out of it.
        """
        entries = self.downloads(file_format=file_format)
        if not entries:
            raise ValueError(f"no {file_format!r} download available for Open USRN")
        entry = entries[0]
        dest = Path(dest)
        with self._client.stream("GET", entry["url"]) as response:
            if response.status_code >= 400:
                response.read()
                _raise_for_response(response)
            with open(dest, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        return dest

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> OpenUSRNClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncOpenUSRNClient:
    """Async twin of :class:`OpenUSRNClient`."""

    def __init__(
        self,
        *,
        product_url: str = PRODUCT_URL,
        timeout: float = 600.0,
        client: httpx.AsyncClient | None = None,
    ):
        self.product_url = product_url.rstrip("/")
        self._client = client or httpx.AsyncClient(
            timeout=timeout, follow_redirects=True
        )

    async def product_info(self) -> Any:
        response = await self._client.get(self.product_url)
        if response.status_code >= 400:
            _raise_for_response(response)
        return response.json()

    async def downloads(self, *, file_format: str | None = "GeoPackage") -> list[dict]:
        params = {"format": file_format} if file_format else None
        response = await self._client.get(f"{self.product_url}/downloads", params=params)
        if response.status_code >= 400:
            _raise_for_response(response)
        return response.json()

    async def download(
        self, dest: str | Path, *, file_format: str = "GeoPackage"
    ) -> Path:
        entries = await self.downloads(file_format=file_format)
        if not entries:
            raise ValueError(f"no {file_format!r} download available for Open USRN")
        dest = Path(dest)
        async with self._client.stream("GET", entries[0]["url"]) as response:
            if response.status_code >= 400:
                await response.aread()
                _raise_for_response(response)
            with open(dest, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        return dest

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncOpenUSRNClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
