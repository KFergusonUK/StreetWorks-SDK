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
from ..exceptions import APIError
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


# --------------------------------------------------------------------------- #
# WMS (Web Map Service) helpers. The NSG service endpoints serve both WFS and
# WMS; these build standard OGC WMS KVP requests. Version differences handled:
# 1.3.0 uses CRS and I/J and (for geographic CRSs like EPSG:4326) lat/lon axis
# order in BBOX; 1.1.1 uses SRS and X/Y with lon/lat. The default here is
# EPSG:27700 (easting,northing), which is unambiguous in both versions.
# --------------------------------------------------------------------------- #


def _wms_layer_names(layers: Layer | str | Sequence[Layer | str]) -> str:
    """WMS layer names on the NSG services are *unprefixed* (``StreetLines``),
    unlike the WFS feature types (``ms:StreetLines``) - verified against the
    live WMS capabilities. Strip the namespace so the ``Layer`` enum works for
    both services; plain strings (e.g. the WMS-only aggregate ``"Streets"``)
    pass through unchanged."""
    if isinstance(layers, (Layer, str)):
        layers = [layers]
    names = (layer.value if isinstance(layer, Layer) else str(layer) for layer in layers)
    return ",".join(n.removeprefix("ms:") for n in names)


def _wms_bbox(bbox: Sequence[float]) -> str:
    if len(bbox) != 4:
        raise ValueError("bbox must be (minx, miny, maxx, maxy)")
    return ",".join(str(v) for v in bbox)


def _wms_map_params(
    layers: Layer | str | Sequence[Layer | str],
    bbox: Sequence[float],
    *,
    width: int,
    height: int,
    crs: str,
    image_format: str,
    styles: str,
    transparent: bool,
    version: str,
    extra: dict[str, Any],
) -> dict[str, Any]:
    crs_key = "crs" if version.startswith("1.3") else "srs"
    params: dict[str, Any] = {
        "service": "WMS",
        "version": version,
        "request": "GetMap",
        "layers": _wms_layer_names(layers),
        "styles": styles,
        crs_key: crs,
        "bbox": _wms_bbox(bbox),
        "width": width,
        "height": height,
        "format": image_format,
        "transparent": str(transparent).upper(),
    }
    params.update(extra)
    return params


def _check_wms_image(response: httpx.Response) -> bytes:
    """A WMS server reports errors as XML with HTTP 200; detect that when an
    image was requested and raise with the ServiceException text."""
    content = response.content
    content_type = response.headers.get("content-type", "")
    if "xml" in content_type or content[:5].lstrip()[:1] == b"<":
        text = content.decode("utf-8", "replace")
        raise APIError(
            f"WMS returned a service exception instead of an image: {text[:500]}",
            status_code=response.status_code,
            body=text,
            request_url=str(response.request.url),
        )
    return content


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

    # --- WMS (rendered map images) ----------------------------------------- #

    def wms_capabilities(self, *, version: str = "1.3.0") -> str:
        """WMS ``GetCapabilities`` - the map layers, styles, and formats."""
        response = self._transport.request(
            "GET",
            self.service_url,
            params={"service": "WMS", "version": version, "request": "GetCapabilities"},
            header_provider=self._headers,
        )
        return response.text

    def get_map(
        self,
        layers: Layer | str | Sequence[Layer | str],
        bbox: Sequence[float],
        *,
        width: int = 768,
        height: int = 768,
        crs: str = "EPSG:27700",
        image_format: str = "image/png",
        styles: str = "",
        transparent: bool = True,
        version: str = "1.3.0",
        **extra: Any,
    ) -> bytes:
        """WMS ``GetMap`` - a rendered map image of NSG layers as bytes.

        ``bbox`` is ``(minx, miny, maxx, maxy)`` in ``crs`` units - with the
        default British National Grid that's eastings/northings. (If you use
        ``EPSG:4326`` with WMS 1.3.0, the axis order is latitude,longitude -
        a classic WMS trap; sticking to 27700 avoids it.) Multiple layers
        render bottom-to-top in the order given. The WMS also offers
        aggregate layers not in the ``Layer`` enum - ``"Streets"`` renders the
        full composite street map::

            png = dv.get_map(
                [Layer.STREET_LINES],
                (424000, 533800, 426000, 535200),   # Spennymoor, County Durham
            )
            Path("durham.png").write_bytes(png)
        """
        response = self._transport.request(
            "GET",
            self.service_url,
            params=_wms_map_params(
                layers,
                bbox,
                width=width,
                height=height,
                crs=crs,
                image_format=image_format,
                styles=styles,
                transparent=transparent,
                version=version,
                extra=extra,
            ),
            header_provider=self._headers,
        )
        return _check_wms_image(response)

    def get_feature_info(
        self,
        layers: Layer | str | Sequence[Layer | str],
        bbox: Sequence[float],
        i: int,
        j: int,
        *,
        width: int = 768,
        height: int = 768,
        crs: str = "EPSG:27700",
        info_format: str = "application/json",
        feature_count: int = 10,
        version: str = "1.3.0",
        **extra: Any,
    ) -> Any:
        """WMS ``GetFeatureInfo`` - "what's at this pixel?" for a GetMap.

        ``i``/``j`` are pixel coordinates within the ``width`` x ``height``
        image (WMS 1.1.1 calls them ``x``/``y``; both handled). Returns parsed
        JSON when ``info_format`` is JSON, else the response text.
        """
        params = _wms_map_params(
            layers,
            bbox,
            width=width,
            height=height,
            crs=crs,
            image_format="image/png",
            styles="",
            transparent=True,
            version=version,
            extra={},
        )
        params["request"] = "GetFeatureInfo"
        params["query_layers"] = params["layers"]
        params["info_format"] = info_format
        params["feature_count"] = feature_count
        if version.startswith("1.3"):
            params["i"], params["j"] = i, j
        else:
            params["x"], params["y"] = i, j
        params.pop("format")
        params.pop("transparent")
        params.update(extra)
        response = self._transport.request(
            "GET", self.service_url, params=params, header_provider=self._headers
        )
        if "json" in info_format:
            return response.json()
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
            params=self._build_get_params(layer, srs=srs, start_index=start_index, count=count),
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

    async def wms_capabilities(self, *, version: str = "1.3.0") -> str:
        response = await self._transport.request(
            "GET",
            self.service_url,
            params={"service": "WMS", "version": version, "request": "GetCapabilities"},
            header_provider=self._headers,
        )
        return response.text

    async def get_map(
        self,
        layers: Layer | str | Sequence[Layer | str],
        bbox: Sequence[float],
        *,
        width: int = 768,
        height: int = 768,
        crs: str = "EPSG:27700",
        image_format: str = "image/png",
        styles: str = "",
        transparent: bool = True,
        version: str = "1.3.0",
        **extra: Any,
    ) -> bytes:
        """WMS ``GetMap`` (see the sync client for full docs)."""
        response = await self._transport.request(
            "GET",
            self.service_url,
            params=_wms_map_params(
                layers,
                bbox,
                width=width,
                height=height,
                crs=crs,
                image_format=image_format,
                styles=styles,
                transparent=transparent,
                version=version,
                extra=extra,
            ),
            header_provider=self._headers,
        )
        return _check_wms_image(response)

    async def get_feature_info(
        self,
        layers: Layer | str | Sequence[Layer | str],
        bbox: Sequence[float],
        i: int,
        j: int,
        *,
        width: int = 768,
        height: int = 768,
        crs: str = "EPSG:27700",
        info_format: str = "application/json",
        feature_count: int = 10,
        version: str = "1.3.0",
        **extra: Any,
    ) -> Any:
        params = _wms_map_params(
            layers,
            bbox,
            width=width,
            height=height,
            crs=crs,
            image_format="image/png",
            styles="",
            transparent=True,
            version=version,
            extra={},
        )
        params["request"] = "GetFeatureInfo"
        params["query_layers"] = params["layers"]
        params["info_format"] = info_format
        params["feature_count"] = feature_count
        if version.startswith("1.3"):
            params["i"], params["j"] = i, j
        else:
            params["x"], params["y"] = i, j
        params.pop("format")
        params.pop("transparent")
        params.update(extra)
        response = await self._transport.request(
            "GET", self.service_url, params=params, header_provider=self._headers
        )
        if "json" in info_format:
            return response.json()
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
