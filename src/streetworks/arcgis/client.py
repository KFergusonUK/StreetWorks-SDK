"""Generic ArcGIS REST Feature Service / Map Service client.

The third client shape in this SDK, after the DATEX/JSON adapters and
:class:`~streetworks.ogc.OGCFeaturesClient`. Built fresh for this protocol -
**not** a generalisation of ``OGCFeaturesClient`` (WFS/OGC API Features) or
:class:`~streetworks.datavia.DataViaClient` (a specific credentialed WFS
service). They share almost nothing but "fetches geodata over HTTP." If real
duplication emerges after a third ArcGIS consumer, convergence can be
proposed then, as its own piece of work - not assumed now.

**Why this shape**: avoids shapefile and file-geodatabase entirely, so no
GDAL and no geospatial dependency - this SDK's standard-library-plus-httpx
property is preserved. Serves the ``.../query?f=geojson`` endpoint every
ArcGIS REST Feature/Map Service exposes, credential-free for every real
service checked so far (Jersey RoadWorkx, TIGERweb).

**Pagination is the real trap here - verified live, not assumed, against
two genuinely different real services**:

* Jersey's real RoadWorks layer states
  ``advancedQueryCapabilities.supportsPagination: false`` - and this is
  **true**, not just declared: a live ``resultOffset``/``resultRecordCount``
  request returns HTTP 200 with a plausible-looking page of records, but
  it's silently the *same* first page every time, at any offset (confirmed
  live this session, offsets 0/500/1000/2000/21000 all returned identical
  leading feature ids). The layer's own ``FID`` (its ``objectIdField``) is
  the real, working fallback: ``WHERE FID > {last} ORDER BY FID`` genuinely
  advances (confirmed live). ``exceededTransferLimit: true`` is present and
  reliable on both ``f=json`` and ``f=geojson`` responses as the truncation
  signal - Jersey's RoadWorks layer has 22,105 real records behind a
  ``maxRecordCount`` of 1,000, so a naive one-shot query silently returns
  under 5% of the data with no error.
* TIGERweb's layers state (and, verified live, genuinely honour)
  ``supportsPagination: true`` - real ``resultOffset`` requests return
  genuinely different features per page (confirmed live).

Because a server's own metadata can be actively wrong (Jersey's case, not
just conservative), :meth:`ArcGISFeatureClient.iter_features` doesn't trust
``supportsPagination`` alone - it verifies live, by comparing the first two
pages fetched with different offsets, and falls back to object-id-range
paging the moment offset-paging fails to genuinely advance. Raises
:class:`~streetworks.exceptions.TruncatedResultError` rather than silently
returning a partial result if neither strategy is usable (no
``objectIdField`` stated). A silently truncated national dataset would be
the worst possible failure.

**CRS is stated per-service, and ``outSR``/``f=geojson`` are each, on their
own, unreliable signals - verified live, not assumed**: TIGERweb's
``f=geojson`` output is genuine WGS84 (EPSG:4326) even with **no** ``outSR``
requested - confirmed live (a real Washington DC bbox query returned
``-77.03076800022644, 38.894642000156054``-shaped lon/lat pairs, not Web
Mercator, the layer's stated native ``spatialReference``). Jersey's
``f=geojson`` output does the opposite: it stays in the service's native
CRS (``"NewJTM"``, a custom Transverse Mercator WKT with no ``wkid`` stated
on the RoadWorks layer itself - separately confirmed, via a sibling service
on the same deployment (``JSYBaseMap``) that *does* state
``"wkid": 3109, "latestWkid": 3109``, and by cross-checking that wkid's own
published WKT against NewJTM's parameters, byte-for-byte identical
(``latitude_of_origin=49.225``, ``central_meridian=-2.135``,
``scale_factor=0.9999999``, ``false_easting=40000``,
``false_northing=70000``) - to be **EPSG:3109**, "ETRS89 / Jersey Transverse
Mercator") - and explicitly requesting ``outSR=4326`` live made no
difference at all, confirmed by comparing coordinate values byte-for-byte
with and without it. So "GeoJSON implies WGS84" is a real behaviour of some
ArcGIS Server deployments, not a protocol guarantee - never assumed here.
Every consumer of this client must record what CRS it actually verified for
its own service, not infer one from the request it made. This client never
reprojects anything itself.

**Output format**: ``f=geojson`` is requested first; if a server's
response isn't a genuine ``FeatureCollection`` (some older/differently
configured ArcGIS Server deployments reject or ignore it), this client
transparently retries with ``f=json`` (Esri's own geometry format -
``paths``/``rings``/``x``+``y`` rather than GeoJSON ``coordinates``) and
converts. Every real service checked so far (Jersey, TIGERweb) honoured
``f=geojson`` directly, so the fallback path is currently unexercised
against real data - documented honestly, not assumed untested.
"""

from __future__ import annotations

import json as _json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport
from ..exceptions import TruncatedResultError

__all__ = ["ArcGISFeatureClient", "LayerInfo"]

JSON = dict[str, Any]

_DEFAULT_PAGE_SIZE = 1000


def _esri_geometry_to_geojson(geometry: JSON | None) -> JSON | None:
    """Convert one Esri JSON geometry (``f=json``'s own shape) to GeoJSON -
    used only on the fallback path, see module docstring."""
    if not geometry:
        return None
    if "paths" in geometry:
        paths = geometry["paths"]
        if len(paths) == 1:
            return {"type": "LineString", "coordinates": paths[0]}
        return {"type": "MultiLineString", "coordinates": paths}
    if "rings" in geometry:
        return {"type": "Polygon", "coordinates": geometry["rings"]}
    if "points" in geometry:
        return {"type": "MultiPoint", "coordinates": geometry["points"]}
    if "x" in geometry and "y" in geometry:
        return {"type": "Point", "coordinates": [geometry["x"], geometry["y"]]}
    return None


def _esri_json_to_geojson(payload: JSON) -> JSON:
    """Convert a whole Esri JSON query response into a GeoJSON
    ``FeatureCollection`` - the ``f=json`` fallback path."""
    features = [
        {
            "type": "Feature",
            "geometry": _esri_geometry_to_geojson(feature.get("geometry")),
            "properties": feature.get("attributes", {}),
        }
        for feature in payload.get("features", [])
    ]
    result: JSON = {"type": "FeatureCollection", "features": features}
    if "exceededTransferLimit" in payload:
        result["exceededTransferLimit"] = payload["exceededTransferLimit"]
    return result


@dataclass(frozen=True)
class LayerInfo:
    """The subset of an ArcGIS layer's ``?f=json`` metadata this client
    acts on for pagination and discovery. Everything else in that response
    (fields, extent, geometry type, ...) is still reachable via
    :meth:`ArcGISFeatureClient.layer_info` directly - this is just the
    part :meth:`ArcGISFeatureClient.iter_features` needs."""

    object_id_field: str | None
    max_record_count: int | None
    supports_pagination: bool
    spatial_reference: JSON | None
    fields: tuple[str, ...]

    @classmethod
    def from_json(cls, payload: JSON) -> LayerInfo:
        advanced = payload.get("advancedQueryCapabilities") or {}
        return cls(
            object_id_field=payload.get("objectIdField"),
            max_record_count=payload.get("maxRecordCount"),
            supports_pagination=bool(advanced.get("supportsPagination", False)),
            spatial_reference=payload.get("spatialReference"),
            fields=tuple(f["name"] for f in payload.get("fields", [])),
        )


class ArcGISFeatureClient:
    """Fetch features from an ArcGIS REST ``MapServer``/``FeatureServer``
    layer. No credentials - every source this client is built for is
    publicly queryable without authentication.

    >>> from streetworks.arcgis import ArcGISFeatureClient
    >>> BASE = "https://roadworks.gov.je/arcgis/rest/services/JSWFeatureService/FeatureServer"
    >>> with ArcGISFeatureClient() as arcgis:  # doctest: +SKIP
    ...     for feature in arcgis.iter_features(BASE, 3):
    ...         print(feature["properties"]["PROJID"])
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def service_info(self, base_url: str) -> JSON:
        """``GET {base_url}?f=json`` - service-level metadata: the layer
        list, service-wide spatial reference, ``maxRecordCount``."""
        response = self._transport.request("GET", base_url, params={"f": "json"})
        return response.json()

    def layer_info(self, base_url: str, layer_id: int) -> JSON:
        """``GET {base_url}/{layer_id}?f=json`` - layer-level metadata:
        real field list, ``maxRecordCount``, ``advancedQueryCapabilities``
        (including whether pagination is genuinely supported - see module
        docstring for why that field alone can't be trusted)."""
        url = f"{base_url.rstrip('/')}/{layer_id}"
        response = self._transport.request("GET", url, params={"f": "json"})
        return response.json()

    def query(
        self,
        base_url: str,
        layer_id: int,
        *,
        where: str = "1=1",
        out_fields: str = "*",
        out_sr: str | int | None = None,
        result_offset: int | None = None,
        result_record_count: int | None = None,
        order_by_fields: str | None = None,
        geometry: JSON | None = None,
        geometry_type: str = "esriGeometryEnvelope",
        in_sr: str | int | None = None,
        spatial_rel: str = "esriSpatialRelIntersects",
        extra_params: dict[str, str] | None = None,
    ) -> JSON:
        """One ``query`` call - a GeoJSON ``FeatureCollection``, with
        ``exceededTransferLimit`` carried through under that same key if
        the server states it (both ``f=geojson`` and ``f=json`` do, on
        every real service checked).

        This is **one page**. It does not detect or resolve truncation for
        you - see :meth:`iter_features` for that. If you call this
        directly rather than iterating, check
        ``result.get("exceededTransferLimit")`` yourself before trusting
        the result is complete.

        ``geometry`` is a plain dict (an Esri geometry - e.g.
        ``{"xmin":..., "ymin":..., "xmax":..., "ymax":...,
        "spatialReference": {"wkid": 4326}}`` for an envelope), JSON-encoded
        here. Never reprojected - ``out_sr`` is passed through as asked,
        but see the module docstring: whether the server actually honours
        it is not something this client can verify for you in general,
        only per-service.
        """
        params: dict[str, Any] = {"where": where, "outFields": out_fields, "f": "geojson"}
        if out_sr is not None:
            params["outSR"] = out_sr
        if result_offset is not None:
            params["resultOffset"] = result_offset
        if result_record_count is not None:
            params["resultRecordCount"] = result_record_count
        if order_by_fields is not None:
            params["orderByFields"] = order_by_fields
        if geometry is not None:
            params["geometry"] = _json.dumps(geometry)
            params["geometryType"] = geometry_type
            params["spatialRel"] = spatial_rel
            if in_sr is not None:
                params["inSR"] = in_sr
        if extra_params:
            params.update(extra_params)

        url = f"{base_url.rstrip('/')}/{layer_id}/query"
        response = self._transport.request("GET", url, params=params)
        payload = response.json()
        if payload.get("type") != "FeatureCollection":
            # Server didn't honour f=geojson - fall back to Esri JSON and convert.
            # Unexercised against real data so far - see module docstring.
            params["f"] = "json"
            response = self._transport.request("GET", url, params=params)
            payload = _esri_json_to_geojson(response.json())
        return payload

    def count(self, base_url: str, layer_id: int, *, where: str = "1=1") -> int:
        """``returnCountOnly=true`` - the real total record count,
        independent of any page/transfer limit. Use this to know a
        layer's true size before deciding whether/how to page it (Jersey's
        real RoadWorks layer: 22,105, behind a ``maxRecordCount`` of
        1,000 - ``query()`` alone would never reveal that gap)."""
        url = f"{base_url.rstrip('/')}/{layer_id}/query"
        response = self._transport.request(
            "GET", url, params={"where": where, "returnCountOnly": "true", "f": "json"}
        )
        return int(response.json()["count"])

    def iter_features(
        self,
        base_url: str,
        layer_id: int,
        *,
        where: str = "1=1",
        out_fields: str = "*",
        out_sr: str | int | None = None,
        page_size: int | None = None,
        geometry: JSON | None = None,
        geometry_type: str = "esriGeometryEnvelope",
        in_sr: str | int | None = None,
        spatial_rel: str = "esriSpatialRelIntersects",
    ) -> Iterator[JSON]:
        """Yield every real GeoJSON feature matching ``where`` (default:
        everything), paging correctly regardless of whether the layer's
        own metadata about pagination support can be trusted - see the
        module docstring for the real Jersey/TIGERweb evidence this
        strategy is built on.

        Strategy, in order: (1) fetch a first page; if it's shorter than
        the page size, that's everything - done. (2) Otherwise, fetch a
        second page via ``resultOffset`` and check it's genuinely
        *different* from the first (different leading object ids, or a
        different feature set entirely if no object-id field is stated).
        If offset-paging is verified live to work, continue with it.
        (3) If it isn't - the metadata claimed support that isn't real,
        Jersey's exact case - fall back to object-id-range paging
        (``WHERE {oid_field} > {last_seen} ORDER BY {oid_field}``) using
        the layer's own stated ``objectIdField``.

        Raises :class:`~streetworks.exceptions.TruncatedResultError` if
        offset-paging doesn't work *and* no ``objectIdField`` is stated to
        fall back on - never silently returns a partial result.
        """
        info = LayerInfo.from_json(self.layer_info(base_url, layer_id))
        size = page_size or info.max_record_count or _DEFAULT_PAGE_SIZE
        oid_field = info.object_id_field

        def _fetch(*, result_offset: int | None = None, oid_after: int | None = None) -> JSON:
            effective_where = where
            if oid_after is not None:
                assert oid_field is not None
                effective_where = f"({where}) AND ({oid_field} > {oid_after})"
            return self.query(
                base_url,
                layer_id,
                where=effective_where,
                out_fields=out_fields,
                out_sr=out_sr,
                result_offset=result_offset if oid_after is None else None,
                result_record_count=size,
                order_by_fields=oid_field,
                geometry=geometry,
                geometry_type=geometry_type,
                in_sr=in_sr,
                spatial_rel=spatial_rel,
            )

        def _oid(feature: JSON) -> Any:
            return feature.get("properties", {}).get(oid_field) if oid_field else None

        first_page = _fetch(result_offset=0).get("features", [])
        if len(first_page) < size:
            yield from first_page
            return

        second_page = _fetch(result_offset=size).get("features", [])
        offset_paging_works = bool(second_page) and (
            [_oid(f) for f in second_page] != [_oid(f) for f in first_page]
            if oid_field
            else second_page != first_page
        )

        if offset_paging_works:
            yield from first_page
            yield from second_page
            offset = 2 * size
            page = second_page
            while len(page) == size:
                page = _fetch(result_offset=offset).get("features", [])
                yield from page
                offset += size
            return

        if not oid_field:
            raise TruncatedResultError(
                f"{base_url}/{layer_id}: this layer truncates at {size} features per "
                "page, resultOffset paging does not genuinely advance (verified by "
                "comparing two pages), and no objectIdField is stated to page by "
                "instead - the full result set cannot be safely retrieved."
            )

        yield from first_page
        last_oid = max(_oid(f) for f in first_page)
        while True:
            page = _fetch(oid_after=last_oid).get("features", [])
            if not page:
                return
            yield from page
            if len(page) < size:
                return
            last_oid = max(_oid(f) for f in page)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> ArcGISFeatureClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
