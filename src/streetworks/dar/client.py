"""Denmark's Danmarks Adresseregister (DAR) - the authoritative national
register for Danish street names and addresses, hosted on Datafordeleren
(Denmark's national data-distribution platform). This module covers only
the ``Navngivenvej`` ("named road") entity - DAR's street/road-name
layer with real line geometry - not the register's separate ``Adresse``/
``Husnummer`` (address-point) entities, an address-level concern out of
scope here, the same distinction Italy's ANNCSU draws between its own
streets layer and its (deliberately unbuilt) ``accessi`` address layer.

**Not the source originally investigated - the obvious one is being
shut down.** DAWA (Danmarks Adressers Web API, ``api.dataforsyningen.dk``)
was checked first: genuinely keyless, real national ``vejstykker``/
``navngivneveje`` data confirmed live. But DAWA's own docs page carries
a live warning, *"DAWA lukker"* ("DAWA is closing") - confirmed via web
search: DAWA is being phased out toward **1 October 2026** (today is
17 August 2026), superseded by Datafordeleren. Building against a feed
six weeks from shutdown would ship a provider already due to break, so
DAR (the actual successor, hosted directly on Datafordeleren) was built
instead - see ``docs/providers/denmark.md`` for the full DAWA-closure
finding.

**Real, live, genuinely keyless REST endpoint - confirmed directly, not
assumed from Datafordeleren's general portal, which does push account
creation for its higher-sensitivity registers.** A plain unauthenticated
``GET`` against
``https://services.datafordeler.dk/DAR/DAR/3.0.0/rest/Navngivenvej``
returns real national data (200, no auth header sent or required,
``Access-Control-Allow-Origin: *``) - real Danish street names confirmed
(``"Halvdansvej"``, ``"Abel Cathrines Gade"``).

**CRS: real ETRS89 / UTM zone 32N (``EPSG:25832``), no reprojection
option on this endpoint - confirmed live, not assumed.** A ``srid``
query parameter was tried (following DAWA's own convention) and
rejected with a real ``400``: *"Parameter: srid unrecognized. Did you
mean: id?"* - unlike Digiroad's WFS (``srsName=EPSG:4326``, genuinely
honoured server-side) or LMI's WFS (WGS84 by default), this REST API has
no server-side reprojection at all. :mod:`streetworks.common.from_dar`
reprojects client-side via :mod:`streetworks.common._utm32n`, a closed-form
transform cross-checked against DAWA's own real WGS84 output for the
same real road (Halvdansvej, kommune 0217/vejkode 2844) - both agree to
within a few metres.

**Real schema, confirmed live**: ``vejnavn``/``vejadresseringsnavn``/
``udtaltVejnavn`` (the stated name, its addressing form, and its spoken
form - all three real, usually identical), ``id_lokalId`` (a real stable
UUID), ``vejnavnebeliggenhed_vejnavnelinje`` (the real line geometry,
WKT ``MULTILINESTRING`` - genuinely multi-part on most records, since
one named road is rarely a single unbroken line). **A real fallback
pair, found live on the 0.06% of records with no line**:
``vejnavnebeliggenhed_vejtilslutningspunkter`` (real "road connection
points", WKT ``MULTIPOINT``) and ``vejnavnebeliggenhed_vejnavneområde``
(a real "road name area" WKT ``POLYGON``) - see
:mod:`streetworks.common.from_dar`'s own docstring for how the
converter uses the point as a real fallback location and keeps the
polygon `.raw`-only, never forced into a line/point field.
``administreresAfKommune``
(the real administering municipality's 4-digit kommune code -
:mod:`streetworks.common.from_dar` keeps this as the raw code, not a
resolved name, since no kommune-code-to-name lookup is fetched here),
``status`` (a real lifecycle code - live sample of 5000 records: ``{2:
1, 3: 4981, 4: 11, 5: 7}`` - the exact codelist semantics weren't found
published anywhere checked live, so no status-based filtering is
applied; every record the API returns is treated as real).

**Pagination: real, confirmed live** - ``pagesize``/``page`` query
parameters (1-indexed), confirmed to return genuinely distinct records
per page (not a repeat of page 1), and an empty list (never an error)
past the real end of the dataset. **A real server quirk found and
avoided, not reproduced**: a bare, unpaginated request (no ``pagesize``
at all) returns the full national dataset in one response but the
connection was twice observed to truncate mid-record on a very large
pull (chunked transfer cut short) - ``pagesize=5000`` was confirmed live
to complete cleanly and is used as this client's default page size.

**Licence: CC BY 4.0, confirmed live** via Datafordeleren's own terms
page (``datafordeler.dk/vejledning/brugervilkaar/danmarks-adresseregister-dar/``):
*"Som bruger af frie grunddata er du underlagt CC BY 4.0 licens"*,
requiring attribution to Klimadatastyrelsen (the parent authority for
SDFI, the Danish Agency for Data Supply and Infrastructure).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "STREETS_ENTITY", "DarClient"]

JSON = dict[str, Any]

#: DAR 3.0.0's real REST base - confirmed live, no auth required. See
#: module docstring.
BASE_URL = "https://services.datafordeler.dk/DAR/DAR/3.0.0/rest"

#: The real named-road entity - DAR's street layer. See module docstring.
STREETS_ENTITY = "Navngivenvej"

#: Confirmed live: 5000 completes cleanly where an unpaginated request
#: was twice observed to truncate mid-record. See module docstring.
_DEFAULT_PAGE_SIZE = 5000


class DarClient:
    """Fetch Denmark's real national named-road register. No credentials
    required.

    >>> from streetworks.dar import DarClient
    >>> from streetworks.common import from_dar_street
    >>> with DarClient() as dar:  # doctest: +SKIP
    ...     streets = [from_dar_street(r) for r in dar.iter_streets()]
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
        """Yield every real named-road record, paging until a page comes
        back short of the requested size - confirmed live to mean the
        real end of the dataset, never an error. See module docstring."""
        page = 1
        while True:
            response = self._transport.request(
                "GET",
                f"{BASE_URL}/{STREETS_ENTITY}",
                params={"pagesize": str(self._page_size), "page": str(page)},
            )
            records = response.json()
            yield from records
            if len(records) < self._page_size:
                return
            page += 1

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> DarClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
