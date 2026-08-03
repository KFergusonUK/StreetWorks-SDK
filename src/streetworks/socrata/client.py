"""Generic Socrata SODA client - the shared transport this SDK's Socrata
providers build on, the same role :class:`~streetworks.arcgis.client.ArcGISFeatureClient`
plays for ArcGIS REST or :class:`~streetworks.ogc.client.OGCFeaturesClient`
plays for OGC WFS. First factored out from :mod:`streetworks.wzdx.registry`
(a Socrata *metadata* read, `69qe-yiui`) when :mod:`streetworks.nycdot`
(a Socrata *data* read, `tqtj-sjs8`, 3.8M+ real rows) needed the identical
GET-with-query-params-and-paginate shape.

**Pagination is `$limit`/`$offset`** - SODA's own documented, reliable
mechanism (no equivalent to ArcGIS's real, confirmed-broken
`resultOffset` on some services - see :mod:`streetworks.arcgis.client`'s
own module docstring for that contrast). :meth:`SodaClient.iter_records`
stops as soon as a page comes back shorter than ``page_size`` - the
standard "last page" signal - with a defensive ``_MAX_PAGES`` cap purely
against a malformed/looping server response, not because offset paging
itself is in doubt here.

**App token is optional, never required** - every Socrata dataset this
SDK reads is publicly queryable without one; a token (`X-App-Token`
header) only raises the anonymous rate limit. Pass one via ``app_token``
if you have it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["SodaClient"]

JSON = dict[str, Any]

#: A safety net against a malformed/looping server response, not evidence
#: SODA's own $limit/$offset pagination is unreliable - see module
#: docstring.
_MAX_PAGES = 10_000


class SodaClient:
    """Fetch rows from any Socrata (SODA) dataset - metadata or data,
    both the identical `resource/{id}.json` shape. No credentials
    required; ``app_token`` is an optional rate-limit courtesy.

    >>> from streetworks.socrata import SodaClient
    >>> with SodaClient() as soda:  # doctest: +SKIP
    ...     rows = list(soda.iter_records(
    ...         "https://data.cityofnewyork.us/resource/tqtj-sjs8.json",
    ...         where="permitseriesshortdesc='STREET OPENING PERMIT'",
    ...     ))
    """

    def __init__(
        self,
        *,
        app_token: str | None = None,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        headers = {"X-App-Token": app_token} if app_token else None
        owned_client = client or httpx.Client(
            timeout=timeout, follow_redirects=True, headers=headers
        )
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_records(
        self,
        dataset_url: str,
        *,
        where: str | None = None,
        select: str | None = None,
        order: str | None = None,
        page_size: int = 1000,
    ) -> Iterator[JSON]:
        """Yield every real row matching ``where`` (SoQL - a plain SQL-ish
        clause, e.g. ``"state='new york'"``), paging via ``$limit``/
        ``$offset`` until a page comes back shorter than ``page_size``."""
        offset = 0
        for _ in range(_MAX_PAGES):
            params: dict[str, str] = {"$limit": str(page_size), "$offset": str(offset)}
            if where:
                params["$where"] = where
            if select:
                params["$select"] = select
            if order:
                params["$order"] = order
            response = self._transport.request("GET", dataset_url, params=params)
            rows = response.json()
            yield from rows
            if len(rows) < page_size:
                return
            offset += page_size

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> SodaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
