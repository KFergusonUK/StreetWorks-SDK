"""NWB access: the credential-free WFS (live queries, GeoJSON) and the
two-hop Atom feed (bulk GeoPackage discovery + streamed download) - see
:mod:`streetworks.nwb.atom` for why the feed takes two requests, unlike
every other Atom feed in this SDK.

**WFS paging is real, correcting the design brief's own warning** - see
:mod:`streetworks.nwb.models` for the full live-verified explanation
(an unencoded ``+`` in ``outputFormat`` decodes server-side as a space,
producing an invalid-parameter rejection that looks like a hang/ignored
``count`` if retried blindly). :meth:`NWBClient.query` builds the request
through httpx's own ``params=`` dict, which percent-encodes correctly, so
this client was never at risk of reproducing it - documented anyway so
nobody re-diagnoses the same non-bug.

**WFS queries go to Rijkswaterstaat directly, not PDOK - a deliberate,
live-verified split, not an inconsistency.** Both hosts serve the
identical *unfiltered* dataset (same real wegvak, same every field,
checked against both for `wvk_id` 314551046) - but confirmed live,
PDOK's WFS (``service.pdok.nl/rws/nwbwegen``) **silently ignores
``CQL_FILTER`` entirely**: a request filtered to one real municipality
(`gme_naam='Harlingen'`) returned wegvakken from 280 different
municipalities unfiltered, both for actual features and for
``resultType=hits`` counts. `geo.rijkswaterstaat.nl`'s own WFS filters
correctly on the identical query (confirmed: exactly the 1 requested
municipality, 1,886 real matching features). Since server-side filtering
is the entire point of a live query route - the alternative is
downloading the ~1 GB bulk file to filter client-side - `NWBClient.query`
targets Rijkswaterstaat directly. The **bulk GeoPackage download stays on
PDOK's Atom feed** (see :mod:`streetworks.nwb.atom`), which is unaffected
(a static file, not a filtered query) and matches this SDK's existing
convention for other Dutch open data (:mod:`streetworks.bag`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .._transport import AsyncTransport, RetryConfig, SyncTransport, _raise_for_response
from .atom import INDEX_FEED_URL, DownloadEntry, parse_dataset_feed, parse_index_feed
from .models import Wegvak, wegvak_from_feature

__all__ = ["NWBClient", "AsyncNWBClient", "WFS_BASE_URL"]

#: Rijkswaterstaat direct, not PDOK - see the module docstring: PDOK's WFS
#: proxy silently ignores CQL_FILTER, confirmed live.
WFS_BASE_URL = "https://geo.rijkswaterstaat.nl/services/ogc/gdr/nwb_wegen/ows"

_GEOPACKAGE_MEDIA_TYPE = "application/geopackage+sqlite3"


def _wegvakken_from_response(data: dict) -> list[Wegvak]:
    return [wegvak_from_feature(f) for f in data.get("features", [])]


class NWBClient:
    """The Dutch national road network (NWB) - live WFS queries plus
    discovery + streamed download of the bulk GeoPackage. No credentials
    required.

    >>> from streetworks.nwb import NWBClient
    >>> with NWBClient() as nwb:
    ...     segments = nwb.query(cql_filter="gme_naam='Harlingen'")
    ...     path = nwb.download_geopackage("nwb_wegen.gpkg")  # ~1 GB, streamed
    """

    def __init__(
        self,
        *,
        wfs_base_url: str = WFS_BASE_URL,
        index_feed_url: str = INDEX_FEED_URL,
        retry: RetryConfig | None = None,
        timeout: float = 300.0,
        client: httpx.Client | None = None,
    ):
        self.wfs_base_url = wfs_base_url.rstrip("/")
        self.index_feed_url = index_feed_url
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    # --- WFS (live) --------------------------------------------------------- #

    def query(
        self,
        *,
        cql_filter: str | None = None,
        count: int | None = None,
        type_name: str = "wegvakken",
        **params: Any,
    ) -> list[Wegvak]:
        """Query one WFS feature type (``wegvakken`` by default) with a
        real GeoServer ``CQL_FILTER`` (e.g. ``"gme_naam='Harlingen'"``) -
        confirmed live, not a WFS standard but a genuine, working
        GeoServer extension this service supports."""
        query: dict[str, Any] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": type_name,
            "outputFormat": "application/json",
            **params,
        }
        if cql_filter:
            query["CQL_FILTER"] = cql_filter
        if count is not None:
            query["count"] = count
        response = self._transport.request("GET", self.wfs_base_url, params=query)
        return _wegvakken_from_response(response.json())

    def count(self, *, cql_filter: str | None = None, type_name: str = "wegvakken") -> int:
        """The real match count via ``resultType=hits`` - no features
        transferred, confirmed live to be fast even for the full national
        ~1.64M-row `wegvakken` layer."""
        query: dict[str, Any] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": type_name,
            "resultType": "hits",
        }
        if cql_filter:
            query["CQL_FILTER"] = cql_filter
        response = self._transport.request("GET", self.wfs_base_url, params=query)
        text = response.text
        marker = 'numberMatched="'
        start = text.index(marker) + len(marker)
        end = text.index('"', start)
        return int(text[start:end])

    # --- bulk file (two-hop Atom feed discovery + streamed download) ------- #

    def discover_download(self) -> DownloadEntry:
        """Follow both feed hops (see the module docstring) and return
        the current real GeoPackage download entry - never a hardcoded
        URL."""
        index_response = self._transport.request("GET", self.index_feed_url)
        datasets = parse_index_feed(index_response.content)
        for dataset in datasets:
            dataset_response = self._transport.request("GET", dataset.feed_url)
            for entry in parse_dataset_feed(dataset_response.content):
                if entry.media_type == _GEOPACKAGE_MEDIA_TYPE:
                    return entry
        raise ValueError(
            f"no {_GEOPACKAGE_MEDIA_TYPE!r} entry found via {self.index_feed_url} - "
            "PDOK may have changed the feed's shape"
        )

    def download_geopackage(self, dest: str | Path) -> Path:
        """Stream the current national GeoPackage (~1 GB, confirmed live
        2026-07) to ``dest`` - its real URL is resolved from the Atom
        feed on every call, not cached across releases."""
        entry = self.discover_download()
        return self._download(entry.url, dest)

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

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> NWBClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncNWBClient:
    """Async twin of :class:`NWBClient`; bulk-file reading is synchronous
    streaming either way (see :mod:`streetworks.nwb.reader`)."""

    def __init__(
        self,
        *,
        wfs_base_url: str = WFS_BASE_URL,
        index_feed_url: str = INDEX_FEED_URL,
        retry: RetryConfig | None = None,
        timeout: float = 300.0,
        client: httpx.AsyncClient | None = None,
    ):
        self.wfs_base_url = wfs_base_url.rstrip("/")
        self.index_feed_url = index_feed_url
        self._client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        self._transport = AsyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    async def query(
        self,
        *,
        cql_filter: str | None = None,
        count: int | None = None,
        type_name: str = "wegvakken",
        **params: Any,
    ) -> list[Wegvak]:
        query: dict[str, Any] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": type_name,
            "outputFormat": "application/json",
            **params,
        }
        if cql_filter:
            query["CQL_FILTER"] = cql_filter
        if count is not None:
            query["count"] = count
        response = await self._transport.request("GET", self.wfs_base_url, params=query)
        return _wegvakken_from_response(response.json())

    async def count(
        self, *, cql_filter: str | None = None, type_name: str = "wegvakken"
    ) -> int:
        query: dict[str, Any] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": type_name,
            "resultType": "hits",
        }
        if cql_filter:
            query["CQL_FILTER"] = cql_filter
        response = await self._transport.request("GET", self.wfs_base_url, params=query)
        text = response.text
        marker = 'numberMatched="'
        start = text.index(marker) + len(marker)
        end = text.index('"', start)
        return int(text[start:end])

    async def discover_download(self) -> DownloadEntry:
        index_response = await self._transport.request("GET", self.index_feed_url)
        datasets = parse_index_feed(index_response.content)
        for dataset in datasets:
            dataset_response = await self._transport.request("GET", dataset.feed_url)
            for entry in parse_dataset_feed(dataset_response.content):
                if entry.media_type == _GEOPACKAGE_MEDIA_TYPE:
                    return entry
        raise ValueError(
            f"no {_GEOPACKAGE_MEDIA_TYPE!r} entry found via {self.index_feed_url} - "
            "PDOK may have changed the feed's shape"
        )

    async def download_geopackage(self, dest: str | Path) -> Path:
        entry = await self.discover_download()
        return await self._download(entry.url, dest)

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

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncNWBClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
