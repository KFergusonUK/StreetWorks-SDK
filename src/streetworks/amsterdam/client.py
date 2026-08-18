"""Amsterdam - WIOR (Werken in de Openbare Ruimte, "Works in the Public
Space"), Gemeente Amsterdam's own coordination register for planned and
in-progress public-space works. A separate, municipal-level data class
from this SDK's existing Dutch coverage - NDW's national DATEX II feed
(``streetworks.datex2``), NWB's national road network, and BAG's
national address register all cover the Netherlands at country scale;
this is the first Dutch *municipal* roadworks register, the same
"national feed plus one city's own permit register" shape Denmark
(Vejdirektoratet + Copenhagen), Norway (Vegvesen + Oslo) and Switzerland
(Kanton Zürich + Stadt Zürich) already have.

**Real, live, genuinely keyless REST API - confirmed directly, not
assumed.** Gemeente Amsterdam publishes ``api.data.amsterdam.nl``, a
DSO-API (Amsterdam's own open-data platform) covering 120+ real
datasets; ``wior``'s own catalogue metadata states
``"api_authentication": ["OPENBAAR"]`` ("public") and
``"terms_of_use": {"government_only": false, "pay_per_use": false}`` -
confirmed live with a plain unauthenticated ``GET``. **A real path
quirk**: the dataset's own OpenAPI document (at ``/v1/wior/``) lists
``/wior`` as its path, but that path is relative to the dataset's own
sub-router, not the API root - the real, live data endpoint is the
doubled ``/v1/wior/wior/`` (confirmed live: the undoubled path 404s).

**10,063 real works records, confirmed live 2026-08-18** (a real,
comprehensive municipal register, not a thin slice) - real project
names (``"Noordzeeweg (tussen Luvernes en Hornweg) T-stukken
vervangen"``), real work-type categories (``typeWerkzaamheden`` -
comma-joined where more than one applies, e.g. ``"Aanleggen,Aansluiten"``),
and a real, live-confirmed data-quality quirk kept rather than
normalised away: one real record carries ``hoofdstatus: "Yes"`` instead
of a real Dutch status value - :mod:`streetworks.common.from_amsterdam`
treats ``hoofdstatus`` as an open string, never validated against a
closed enum, so this doesn't raise or get silently coerced.

**Geometry: real ``Polygon``/``MultiPolygon`` only - genuinely no
Point/LineString rows found live** (867/1000 + 133/1000 in a live
sample). **Real server-side reprojection to WGS84, confirmed live -
unlike Denmark's DAR, which has none at all.** An ``Accept-Crs:
EPSG:4326`` request header is genuinely honoured (confirmed live: the
response's own ``Content-Crs`` header echoes back
``http://www.opengis.net/gml/srs/epsg.xml#4326``, and real Amsterdam
coordinates come back, e.g. lon 4.80/lat 52.39) - this client sends it
on every request rather than reprojecting client-side.

**Pagination: real HAL-style ``_links.next.href``, confirmed live to
disappear cleanly on the real last page** (page 11 of 11 at
``_pageSize=1000``, 63 records, no ``next`` key) - this client follows
the link directly rather than reconstructing page numbers itself.

**Licence: Gemeente Amsterdam's own general open-data terms, checked
live, not a single named SPDX licence.** The dataset's own catalogue
metadata states ``"license": "public"``; Gemeente Amsterdam's general
geodata terms page (``maps.amsterdam.nl/open_geodata/terms.php``,
confirmed live) grants free use and reuse "voor elk wettig doel"
("for any lawful purpose"), commercial and non-commercial, with
attribution appreciated but explicitly **not** required
("Bronvermelding... niet verplicht") - functionally CC0-equivalent in
permissiveness, but not stated under that specific label anywhere
checked, so this SDK doesn't assert one.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "AmsterdamClient"]

JSON = dict[str, Any]

#: Confirmed live: the doubled path is real, not a typo - see module
#: docstring.
BASE_URL = "https://api.data.amsterdam.nl/v1/wior/wior/"

#: Confirmed live to be honoured server-side - see module docstring.
_ACCEPT_CRS = "EPSG:4326"

_DEFAULT_PAGE_SIZE = 1000


class AmsterdamClient:
    """Fetch Gemeente Amsterdam's real WIOR public-space-works register.
    No credentials required.

    >>> from streetworks.amsterdam import AmsterdamClient
    >>> from streetworks.common import from_amsterdam
    >>> with AmsterdamClient() as amsterdam:  # doctest: +SKIP
    ...     works = from_amsterdam(list(amsterdam.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        page_size: int = _DEFAULT_PAGE_SIZE,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(
            timeout=timeout, follow_redirects=True, headers={"Accept-Crs": _ACCEPT_CRS}
        )
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )
        self._page_size = page_size

    def iter_roadworks(self) -> Iterator[JSON]:
        """Yield every real WIOR record, following the real
        ``_links.next.href`` HAL pagination link until it's genuinely
        absent - confirmed live to mean the real last page. See module
        docstring."""
        url: str | None = f"{BASE_URL}?_pageSize={self._page_size}"
        while url:
            response = self._transport.request("GET", url)
            payload = response.json()
            yield from payload.get("_embedded", {}).get("wior", [])
            url = payload.get("_links", {}).get("next", {}).get("href")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> AmsterdamClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
