"""Generic OpenDataSoft Explore API v2.1 client - the French/EU near-
equivalent of Socrata (see :mod:`streetworks.socrata`), and the platform
several French département-level roadworks feeds independently turned
out to be published on.

**Extracted now, not from day one - the same sequence that produced
:class:`~streetworks.socrata.SodaClient`.** :mod:`streetworks.paris`
(Chantiers à Paris) was this SDK's first OpenDataSoft consumer, built
deliberately bespoke - its own module docstring explains why: "bespoke
first, extracted only when a second OpenDataSoft-backed provider needs
the identical shape." That threshold is now real, not hypothetical:
Sarthe, Loire-Atlantique and Hauts-de-Seine's own real département
roadworks feeds all independently turned out to be genuine, live
``/api/explore/v2.1/catalog/datasets/{dataset}/records`` deployments -
confirmed live to share byte-for-byte the same pagination shape
(``results``/``total_count``, ``limit``/``offset``) and even the same
real field-naming convention for geometry (``geo_shape``/
``geo_point_2d``) Paris's own dataset uses. Paris's own
:class:`~streetworks.paris.ParisClient` is left exactly as it was - not
retrofitted onto this client, since it already works and retrofitting it
carries real regression risk for no functional gain. Only the new
département consumers use this module.

**No credentials required for any real deployment checked so far** -
ODS app keys, where they exist at all, only raise rate limits, the same
optional-courtesy role Socrata's own ``X-App-Token`` plays - see
:mod:`streetworks.paris`'s own module docstring for that precedent.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["OpenDataSoftClient"]

JSON = dict[str, Any]

#: A safety net against a malformed/looping server response, not
#: evidence any real deployment's own limit/offset pagination is
#: unreliable - the same role streetworks.paris.ParisClient's own
#: _MAX_PAGES plays.
_MAX_PAGES = 10_000


class OpenDataSoftClient:
    """Fetch records from any real OpenDataSoft Explore API v2.1
    ``.../records`` endpoint. No credentials required for any real
    deployment checked so far.

    >>> from streetworks.opendatasoft import OpenDataSoftClient
    >>> URL = "https://data.sarthe.fr/api/explore/v2.1/catalog/datasets/227200029_chantiers_routiers/records"
    >>> with OpenDataSoftClient() as ods:  # doctest: +SKIP
    ...     records = list(ods.iter_records(URL))
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_records(
        self, records_url: str, *, where: str | None = None, page_size: int = 100
    ) -> Iterator[JSON]:
        """Yield every real record from ``records_url`` (a full
        ``.../records`` endpoint URL), paging via ``limit``/``offset``
        until a page comes back shorter than ``page_size`` or ``offset``
        reaches the server's own ``total_count``. ``where`` is a real
        ODSQL filter expression, passed straight through."""
        offset = 0
        for _ in range(_MAX_PAGES):
            params: dict[str, str] = {"limit": str(page_size), "offset": str(offset)}
            if where:
                params["where"] = where
            response = self._transport.request("GET", records_url, params=params)
            body = response.json()
            results = body.get("results") or []
            yield from results
            offset += len(results)
            if len(results) < page_size or offset >= body.get("total_count", offset):
                return

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> OpenDataSoftClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
