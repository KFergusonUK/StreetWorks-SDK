"""IGN Géoplateforme WFS access to BD TOPO's transport theme
(`troncon_de_route`, `voie_nommee`) - this module's only built access
route. See the package docstring for why the bulk GeoPackage download,
though real and identically licensed, has no automated route here.

Confirmed live 2026-07: `CQL_FILTER` (e.g. `insee_commune_gauche='01004'`)
works correctly on this WFS, including for `resultType=hits` counts -
unlike PDOK's WFS for NWB, which was found to silently ignore it (see
:mod:`streetworks.nwb.client`). This server does **not** offer
`outputFormat=application/gpkg` (confirmed live: `GetCapabilities` lists
only GML, GeoJSON, KML and CSV) - the NWB-style "get a GeoPackage straight
from the WFS" trick doesn't apply here, one more reason the bulk route
stays unbuilt rather than faked through a format this server doesn't
support.
"""

from __future__ import annotations

from typing import Any

import httpx

from .._transport import AsyncTransport, RetryConfig, SyncTransport
from .models import Troncon, VoieNommee, troncon_from_feature, voie_nommee_from_feature

__all__ = ["BDTopoClient", "AsyncBDTopoClient", "WFS_BASE_URL"]

WFS_BASE_URL = "https://data.geopf.fr/wfs/ows"

_TRONCON_TYPE = "BDTOPO_V3:troncon_de_route"
_VOIE_NOMMEE_TYPE = "BDTOPO_V3:voie_nommee"


def _base_query(type_name: str) -> dict[str, Any]:
    return {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": type_name,
        "OUTPUTFORMAT": "application/json",
    }


def _hits_query(type_name: str) -> dict[str, Any]:
    return {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": type_name,
        "RESULTTYPE": "hits",
    }


def _parse_number_matched(xml_text: str) -> int:
    marker = 'numberMatched="'
    start = xml_text.index(marker) + len(marker)
    end = xml_text.index('"', start)
    return int(xml_text[start:end])


class BDTopoClient:
    """France's BD TOPO transport theme (IGN) - road segments
    (`troncon_de_route`) and named streets (`voie_nommee`), live via WFS.
    No credentials required.

    >>> from streetworks.bdtopo import BDTopoClient
    >>> with BDTopoClient() as bdtopo:
    ...     segments = bdtopo.query_troncons(cql_filter="insee_commune_gauche='01004'")
    ...     streets = bdtopo.query_voies_nommees(cql_filter="insee_commune='01004'")
    """

    def __init__(
        self,
        *,
        base_url: str = WFS_BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    def query_troncons(
        self, *, cql_filter: str | None = None, count: int | None = None, **params: Any
    ) -> list[Troncon]:
        """Query `troncon_de_route` (road segments), optionally filtered
        with a real `CQL_FILTER` (e.g. an INSEE commune code on either
        side, or a `cleabs`)."""
        query = {**_base_query(_TRONCON_TYPE), **params}
        if cql_filter:
            query["CQL_FILTER"] = cql_filter
        if count is not None:
            query["COUNT"] = count
        response = self._transport.request("GET", self.base_url, params=query)
        return [troncon_from_feature(f) for f in response.json().get("features", [])]

    def query_voies_nommees(
        self, *, cql_filter: str | None = None, count: int | None = None, **params: Any
    ) -> list[VoieNommee]:
        """Query `voie_nommee` (named streets), the two-level spine above
        `troncon_de_route` - see the models module docstring."""
        query = {**_base_query(_VOIE_NOMMEE_TYPE), **params}
        if cql_filter:
            query["CQL_FILTER"] = cql_filter
        if count is not None:
            query["COUNT"] = count
        response = self._transport.request("GET", self.base_url, params=query)
        return [voie_nommee_from_feature(f) for f in response.json().get("features", [])]

    def count_troncons(self, *, cql_filter: str | None = None) -> int:
        """The real match count via `resultType=hits` - confirmed live to
        honour `CQL_FILTER` correctly (unlike PDOK's NWB WFS)."""
        query = _hits_query(_TRONCON_TYPE)
        if cql_filter:
            query["CQL_FILTER"] = cql_filter
        response = self._transport.request("GET", self.base_url, params=query)
        return _parse_number_matched(response.text)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BDTopoClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncBDTopoClient:
    """Async twin of :class:`BDTopoClient`."""

    def __init__(
        self,
        *,
        base_url: str = WFS_BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        self._transport = AsyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    async def query_troncons(
        self, *, cql_filter: str | None = None, count: int | None = None, **params: Any
    ) -> list[Troncon]:
        query = {**_base_query(_TRONCON_TYPE), **params}
        if cql_filter:
            query["CQL_FILTER"] = cql_filter
        if count is not None:
            query["COUNT"] = count
        response = await self._transport.request("GET", self.base_url, params=query)
        return [troncon_from_feature(f) for f in response.json().get("features", [])]

    async def query_voies_nommees(
        self, *, cql_filter: str | None = None, count: int | None = None, **params: Any
    ) -> list[VoieNommee]:
        query = {**_base_query(_VOIE_NOMMEE_TYPE), **params}
        if cql_filter:
            query["CQL_FILTER"] = cql_filter
        if count is not None:
            query["COUNT"] = count
        response = await self._transport.request("GET", self.base_url, params=query)
        return [voie_nommee_from_feature(f) for f in response.json().get("features", [])]

    async def count_troncons(self, *, cql_filter: str | None = None) -> int:
        query = _hits_query(_TRONCON_TYPE)
        if cql_filter:
            query["CQL_FILTER"] = cql_filter
        response = await self._transport.request("GET", self.base_url, params=query)
        return _parse_number_matched(response.text)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncBDTopoClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
