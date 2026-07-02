"""Geoplace DataVIA client (National Street Gazetteer over OGC WFS/WMS).

Verified against the DataVIA documentation (July 2026):

* Basic-auth service:
  ``https://www.datavia.geoplace.co.uk/api/OgcService/basic/nsg-services-basic``
* OAuth2/OIDC service (client credentials for server-to-server):
  ``https://www.datavia.geoplace.co.uk/api/OgcService/oidc/nsg-services-oidc``
  with token endpoint ``https://www.datavia.geoplace.co.uk/connect/token``
* POST (recommended): WFS 1.1.0 ``GetFeature`` XML bodies with ``ogc:Filter``
* GET: WFS 2.0.0 KVP with ``startIndex``/``count`` paging
* Output formats: GEOJSON, OGRGML, SHAPEZIP, CSV, SPATIALITEZIP

Note the ``www.`` prefix is significant - Geoplace documents the service URLs
with it, and some clients (e.g. ArcGIS Online trusted servers) require an
exact match.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from enum import Enum
from typing import Any

import httpx

from .._oauth import AsyncClientCredentials, SyncClientCredentials
from .._transport import AsyncTransport, RetryConfig, SyncTransport
from . import filters

HOST = "https://www.datavia.geoplace.co.uk"
BASIC_SERVICE_URL = f"{HOST}/api/OgcService/basic/nsg-services-basic"
OIDC_SERVICE_URL = f"{HOST}/api/OgcService/oidc/nsg-services-oidc"
TOKEN_URL = f"{HOST}/connect/token"


class Layer(str, Enum):
    """DataVIA WFS layers (typeNames). ASD layers come in three geometry
    flavours - query all three for full coverage of part-road records."""

    STREET_LINES = "ms:StreetLines"
    ESU_STREETS = "ms:ESUStreets"
    ESU_ONE_WAY_EXEMPTIONS = "ms:ESUOneWayExemptions"
    INTEREST_LINES = "ms:StreetInterestLines"
    INTEREST_POINTS = "ms:StreetInterestPoints"
    INTEREST_POLYGONS = "ms:StreetInterestPolygons"
    CONSTRUCTION_LINES = "ms:StreetConstructionLines"
    CONSTRUCTION_POINTS = "ms:StreetConstructionPoints"
    CONSTRUCTION_POLYGONS = "ms:StreetConstructionPolygons"
    SPECIAL_DESIGNATION_LINES = "ms:StreetSpecialDesignationLines"
    SPECIAL_DESIGNATION_POINTS = "ms:StreetSpecialDesignationPoints"
    SPECIAL_DESIGNATION_POLYGONS = "ms:StreetSpecialDesignationPolygons"


class OutputFormat(str, Enum):
    GEOJSON = "geojson"
    OGRGML = "OGRGML"
    SHAPEZIP = "SHAPEZIP"
    CSV = "CSV"
    SPATIALITEZIP = "SPATIALITEZIP"


def _type_name(layer: Layer | str) -> str:
    if isinstance(layer, Layer):
        return layer.value
    name = str(layer)
    return name if ":" in name else f"ms:{name}"


class _DataViaBase:
    def _build_get_params(
        self,
        layer: Layer | str,
        *,
        srs: str,
        start_index: int | None,
        count: int | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "request": "GetFeature",
            "service": "WFS",
            "version": "2.0.0",
            "typenames": _type_name(layer),
            "srsName": srs,
        }
        if start_index is not None:
            params["startIndex"] = start_index
        if count is not None:
            params["count"] = count
        return params


class DataViaClient(_DataViaBase):
    """Synchronous DataVIA client.

    Two ways to authenticate:

    * Basic (username/password) - ``DataViaClient(username=..., password=...)``
    * OAuth2 client credentials  - ``DataViaClient(client_id=..., client_secret=...)``

    The right service URL is selected automatically for each method.
    """

    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        service_url: str | None = None,
        timeout: float = 120.0,
        retry: RetryConfig | None = None,
    ) -> None:
        basic = username is not None and password is not None
        oidc = client_id is not None and client_secret is not None
        if basic == oidc:
            raise ValueError(
                "Provide either username+password (Basic) or "
                "client_id+client_secret (OAuth2), not both/neither"
            )
        self._oauth: SyncClientCredentials | None = None
        if basic:
            self.service_url = service_url or BASIC_SERVICE_URL
            self._transport = SyncTransport(
                timeout=timeout, retry=retry, auth=httpx.BasicAuth(username, password)
            )
        else:
            self.service_url = service_url or OIDC_SERVICE_URL
            self._transport = SyncTransport(timeout=timeout, retry=retry)
            self._oauth = SyncClientCredentials(
                TOKEN_URL,
                client_id,  # type: ignore[arg-type]
                client_secret,  # type: ignore[arg-type]
                style="body",
                transport=self._transport,
            )

    def _headers(self) -> dict[str, str]:
        return self._oauth.bearer_headers() if self._oauth else {}

    # ------------------------------------------------------------------ #

    def get_capabilities(self) -> str:
        """WFS ``GetCapabilities`` - lists layers your account can access."""
        response = self._transport.request(
            "GET",
            self.service_url,
            params={"service": "WFS", "version": "2.0.0", "request": "GetCapabilities"},
            header_provider=self._headers,
        )
        return response.text

    def get_features(
        self,
        layer: Layer | str,
        *,
        filter_fragment: str | None = None,
        srs: str = "EPSG:4326",
        output_format: OutputFormat | str = OutputFormat.GEOJSON,
        start_index: int | None = None,
        count: int | None = None,
    ) -> Any:
        """WFS ``GetFeature`` via POST (recommended by Geoplace).

        ``filter_fragment`` is any combination from
        :mod:`streetworks.datavia.filters`, e.g.::

            from streetworks.datavia import filters as f
            client.get_features(Layer.SPECIAL_DESIGNATION_LINES,
                                filter_fragment=f.and_(
                                    f.intersects_polygon(ring),
                                    f.property_equals("special_designation_code", 2)))

        Returns parsed GeoJSON (dict) for the geojson format, raw bytes for
        binary formats (SHAPEZIP, SPATIALITEZIP), text otherwise.
        """
        fmt = output_format.value if isinstance(output_format, OutputFormat) else output_format
        body = filters.getfeature_xml(
            _type_name(layer),
            filter_fragment=filter_fragment,
            srs=srs,
            output_format=fmt,
            start_index=start_index,
            count=count,
        )
        response = self._transport.request(
            "POST",
            self.service_url,
            content=body.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
            header_provider=self._headers,
        )
        return _decode(response, fmt)

    def get_features_kvp(
        self,
        layer: Layer | str,
        *,
        srs: str = "EPSG:27700",
        start_index: int | None = 0,
        count: int | None = 500,
    ) -> Any:
        """WFS ``GetFeature`` via GET KVP - handy for unfiltered bulk paging."""
        response = self._transport.request(
            "GET",
            self.service_url,
            params=self._build_get_params(
                layer, srs=srs, start_index=start_index, count=count
            ),
            header_provider=self._headers,
        )
        return _decode(response, "geojson")

    def iter_features(
        self,
        layer: Layer | str,
        *,
        filter_fragment: str | None = None,
        srs: str = "EPSG:4326",
        page_size: int = 500,
        max_features: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield GeoJSON features one by one, paging transparently."""
        start = 0
        yielded = 0
        while True:
            page = self.get_features(
                layer,
                filter_fragment=filter_fragment,
                srs=srs,
                start_index=start,
                count=page_size,
            )
            features = page.get("features", []) if isinstance(page, dict) else []
            for feature in features:
                yield feature
                yielded += 1
                if max_features is not None and yielded >= max_features:
                    return
            if len(features) < page_size:
                return
            start += page_size

    # --- conveniences ---------------------------------------------------- #

    def street_by_usrn(self, usrn: int | str, *, srs: str = "EPSG:4326") -> Any:
        """Street line record(s) for a single USRN."""
        return self.get_features(
            Layer.STREET_LINES, filter_fragment=filters.usrn_equals(usrn), srs=srs
        )

    def streets_near_point(
        self, x: float, y: float, distance_m: float, *, srs: str = "EPSG:4326"
    ) -> Any:
        """Streets within ``distance_m`` metres of a point (x=lon/easting)."""
        return self.get_features(
            Layer.STREET_LINES,
            filter_fragment=filters.dwithin_point(x, y, distance_m),
            srs=srs,
        )

    def streets_in_polygon(
        self, ring: Sequence[filters.Coordinate], *, srs: str = "EPSG:4326"
    ) -> Any:
        """Streets intersecting a polygon (ring of (x, y) pairs)."""
        return self.get_features(
            Layer.STREET_LINES, filter_fragment=filters.intersects_polygon(ring), srs=srs
        )

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> DataViaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def _decode(response: httpx.Response, output_format: str) -> Any:
    fmt = output_format.lower()
    if fmt == "geojson":
        return response.json()
    if fmt in ("shapezip", "spatialitezip"):
        return response.content
    return response.text


class AsyncDataViaClient(_DataViaBase):
    """Asynchronous DataVIA client (same interface as :class:`DataViaClient`)."""

    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        service_url: str | None = None,
        timeout: float = 120.0,
        retry: RetryConfig | None = None,
    ) -> None:
        basic = username is not None and password is not None
        oidc = client_id is not None and client_secret is not None
        if basic == oidc:
            raise ValueError(
                "Provide either username+password (Basic) or "
                "client_id+client_secret (OAuth2), not both/neither"
            )
        self._oauth: AsyncClientCredentials | None = None
        if basic:
            self.service_url = service_url or BASIC_SERVICE_URL
            self._transport = AsyncTransport(
                timeout=timeout, retry=retry, auth=httpx.BasicAuth(username, password)
            )
        else:
            self.service_url = service_url or OIDC_SERVICE_URL
            self._transport = AsyncTransport(timeout=timeout, retry=retry)
            self._oauth = AsyncClientCredentials(
                TOKEN_URL,
                client_id,  # type: ignore[arg-type]
                client_secret,  # type: ignore[arg-type]
                style="body",
                transport=self._transport,
            )

    async def _headers(self) -> dict[str, str]:
        return await self._oauth.bearer_headers() if self._oauth else {}

    async def get_capabilities(self) -> str:
        response = await self._transport.request(
            "GET",
            self.service_url,
            params={"service": "WFS", "version": "2.0.0", "request": "GetCapabilities"},
            header_provider=self._headers,
        )
        return response.text

    async def get_features(
        self,
        layer: Layer | str,
        *,
        filter_fragment: str | None = None,
        srs: str = "EPSG:4326",
        output_format: OutputFormat | str = OutputFormat.GEOJSON,
        start_index: int | None = None,
        count: int | None = None,
    ) -> Any:
        fmt = output_format.value if isinstance(output_format, OutputFormat) else output_format
        body = filters.getfeature_xml(
            _type_name(layer),
            filter_fragment=filter_fragment,
            srs=srs,
            output_format=fmt,
            start_index=start_index,
            count=count,
        )
        response = await self._transport.request(
            "POST",
            self.service_url,
            content=body.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
            header_provider=self._headers,
        )
        return _decode(response, fmt)

    async def street_by_usrn(self, usrn: int | str, *, srs: str = "EPSG:4326") -> Any:
        return await self.get_features(
            Layer.STREET_LINES, filter_fragment=filters.usrn_equals(usrn), srs=srs
        )

    async def streets_near_point(
        self, x: float, y: float, distance_m: float, *, srs: str = "EPSG:4326"
    ) -> Any:
        return await self.get_features(
            Layer.STREET_LINES,
            filter_fragment=filters.dwithin_point(x, y, distance_m),
            srs=srs,
        )

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncDataViaClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
