"""Generic OGC geodata fetch client - WFS, OGC API Features, or a direct
GeoJSON download.

Deliberately not roadworks-specific: this client only knows how to get
GeoJSON out of an OGC-flavoured endpoint. What the features *mean* is
entirely the caller's business - see :mod:`streetworks.ogc.germany` for
the roadworks case. Kept this generic on purpose so a future gazetteer
source (also commonly published as German-state WFS) can reuse it rather
than needing its own fetch layer.

**GeoJSON-primary, no GML parsing.** :meth:`OGCFeaturesClient.get_wfs_features`
always requests ``application/geo+json`` - if a server doesn't offer that
output format (confirmed live for Mecklenburg-Vorpommern's WFS: GML-only,
explicitly rejects ``application/geo+json`` with an ``InvalidParameterValue``
exception), that source is out of scope for this client, not something to
work around with a GML parser.

**Not the same client as DataVIA's.** `streetworks.datavia` is a shipped,
credentialed, live-verified provider for a different service entirely;
this client is unauthenticated GeoJSON fetching over WFS/OGC API Features.
They share almost nothing but the letters WFS - deliberately not
generalised together, see the module's originating design notes.
"""

from __future__ import annotations

from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["OGCFeaturesClient"]

JSON = dict[str, Any]


class OGCFeaturesClient:
    """Fetch GeoJSON from an OGC WFS, OGC API Features, or direct-download
    endpoint. No credentials - every source this client is built for is
    open geodata.

    >>> from streetworks.ogc import OGCFeaturesClient
    >>> with OGCFeaturesClient() as ogc:
    ...     payload = ogc.get_wfs_features(
    ...         "https://geodienste.hamburg.de/hh_wfs_baustellen",
    ...         type_name="de.hh.up:baustelle",
    ...     )
    ...     print(len(payload["features"]))
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

    def get(self, url: str, params: dict[str, str] | None = None) -> JSON:
        """``GET url`` (with optional query params) and return the parsed
        JSON body - a GeoJSON ``FeatureCollection`` for a WFS/OGC API
        Features response, or whatever JSON document a direct-download URL
        serves."""
        response = self._transport.request("GET", url, params=params)
        return response.json()

    def get_wfs_features(
        self,
        base_url: str,
        *,
        type_name: str,
        version: str = "2.0.0",
        output_format: str = "application/geo+json",
        srs_name: str = "EPSG:4326",
        extra_params: dict[str, str] | None = None,
    ) -> JSON:
        """Issue a WFS ``GetFeature`` request and return the parsed GeoJSON
        ``FeatureCollection``. Always requests GeoJSON explicitly (never
        the server's default output format, which is commonly GML) and
        always requests ``srs_name`` explicitly (never the server's
        default CRS, commonly a UTM zone, not WGS84) - see module
        docstring for why both defaults can't be trusted."""
        params = {
            "SERVICE": "WFS",
            "VERSION": version,
            "REQUEST": "GetFeature",
            "TYPENAMES": type_name,
            "OUTPUTFORMAT": output_format,
            "SRSNAME": srs_name,
        }
        if extra_params:
            params.update(extra_params)
        return self.get(base_url, params)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> OGCFeaturesClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
