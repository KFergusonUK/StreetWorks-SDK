"""Germany (Hamburg) - the Zentraler AdressService Hamburg ("GAGES",
Gazetteer Gesamt), a joint address/street gazetteer run by the
Statistisches Amt für Hamburg und Schleswig-Holstein (StA-Nord, the
statistical office) and the Landesbetrieb Geoinformation und Vermessung
(LGV, Hamburg's state geoinformation/surveying agency). This SDK's
first German state-level streets/gazetteer coverage - the federal
BKG source and the address layer were both found too coarse or gated
(see `docs/germany-streets-investigation.md`), so this module checks
one of the states already touched for roadworks instead, the same
per-state fallback shape that investigation left open.

**Not the source first tried - Berlin was checked first and genuinely
blocked, not ruled out.** Berlin's own GDI WFS host
(``gdi.berlin.de``, serving every Berlin state geodata WFS - addresses,
street network, everything) is confirmed live to be down for
maintenance across every real path tried (a generic German
"Wartungsarbeiten" page, no ETA stated) - a real, reportable
connectivity failure, not routed around. Hamburg was checked instead.

**Real, live, keyless OGC API Features - confirmed live, not assumed
from the old (shut-down) FIS-Broker-era WFS this dataset's own catalogue
page still lists as an archived snapshot.** Hamburg's own catalogue
entry (`suche.transparenz.hamburg.de`) links to a real, current OGC API
Features landing page which resolves to
``qs-api.hamburg.de/datasets/v1/gages_vereinfacht`` - confirmed live,
two real collections: ``hauskoordinaten`` (house coordinates) and
``strassen`` (streets, this module's own subject). 9,639 real Hamburg
street records, confirmed live, 100% carrying a real name.

**Real Point geometry, genuinely reprojected server-side to WGS84 by
default - confirmed live, not assumed.** This service's own storage CRS
is `EPSG:25832` (UTM32N), but a plain request with no CRS parameter
already returns real WGS84 coordinates (`CRS84`, confirmed against real
Hamburg geography, e.g. `[10.22, 53.49]`) - the collection's own
metadata explicitly lists `CRS84`/`EPSG:4326`/`EPSG:25832`/`EPSG:3857`
as real supported alternatives.

**Pagination: real, standard OGC API Features `links` with `rel:
"next"`, confirmed live** - followed directly rather than reconstructing
offsets, the same "follow the real link until it's genuinely absent"
discipline this SDK already applies to Amsterdam's WIOR and Flanders'
Straatnamenregister.

**`administrative_area` is a per-provider constant, `"Hamburg"`** - the
real per-feature `geographicidentifier` field states a finer real
Ortsteil (district) code (e.g. `"(OT 0603)"`) inline in one composite
string, but no separate Ortsteil-code-to-name lookup collection exists
on this API - kept `.raw`-only rather than parsed into a fabricated
field, the same "don't force a coarse win where no cheap resolution
exists" call this SDK made for Denmark's DAR kommune code.

**No credentials.** Licence: **Datenlizenz Deutschland - Namensnennung -
2.0** (Germany's own standard open-data attribution licence),
confirmed live from this dataset's own CKAN metadata on
`suche.transparenz.hamburg.de`.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "HamburgStreetsClient"]

JSON = dict[str, Any]

#: The real, live, keyless OGC API Features route - see module
#: docstring for why gdi.berlin.de (Berlin) was checked first and
#: genuinely blocked instead.
BASE_URL = "https://qs-api.hamburg.de/datasets/v1/gages_vereinfacht/collections/strassen/items"

_DEFAULT_PAGE_SIZE = 1000


class HamburgStreetsClient:
    """Fetch Hamburg's real street gazetteer (Zentraler AdressService
    Hamburg / GAGES). No credentials required.

    >>> from streetworks.hamburg import HamburgStreetsClient
    >>> from streetworks.common import from_hamburg_street
    >>> with HamburgStreetsClient() as hamburg:  # doctest: +SKIP
    ...     streets = [from_hamburg_street(f) for f in hamburg.iter_streets()]
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        page_size: int = _DEFAULT_PAGE_SIZE,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )
        self._page_size = page_size

    def iter_streets(self) -> Iterator[JSON]:
        """Yield every real Hamburg street (GeoJSON ``Feature`` dicts),
        following the real OGC API Features ``rel: "next"`` link until
        it's genuinely absent - confirmed live to mean the real last
        page. See module docstring."""
        url: str | None = f"{BASE_URL}?f=json&limit={self._page_size}"
        while url:
            payload = self._transport.request("GET", url).json()
            yield from payload.get("features", [])
            url = next(
                (link["href"] for link in payload.get("links", []) if link.get("rel") == "next"),
                None,
            )

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> HamburgStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
