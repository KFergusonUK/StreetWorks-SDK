"""Flanders (Belgium) - the Straatnamenregister ("Street Names
Register"), part of Digitaal Vlaanderen's Basisregisters Vlaanderen
(Flemish Base Registries) suite. This SDK's first Belgian streets/
gazetteer coverage - a sibling to the existing Belgian roadworks
provider (Verkeerscentrum Vlaanderen, ``streetworks.datex2.belgium``),
which is itself already Flanders-only, not all-Belgium (Wallonia
publishes its own separate feed, not wrapped by this SDK; Brussels
wasn't checked) - the same regional scope carries over here.

**Not the layer first checked - a road-segment WFS with embedded names
was tried first, a dedicated name register was found instead.**
Informatie Vlaanderen's own "Wegenregister" WFS
(``geo.api.vlaanderen.be/Wegenregister/wfs``, confirmed live, keyless)
carries a real ``Wegsegment`` layer with real line geometry, but street
identity there is a genuinely different, richer shape than this SDK's
own single-name ``Street`` model cleanly supports: each segment states
**two** independent street-name references, ``linkerstraatnaam``/
``rechterstraatnaam`` (left/right side of the road can genuinely differ
- a real Belgian addressing convention), and both are frequently blank
(footpaths/cycleways with no adjacent named street) - closer to NWB's
own "street is an aggregation of segments" shape than a queryable named
entity. The Basisregisters Vlaanderen REST API's own
``Straatnaam`` resource, found separately, publishes street identity
directly as its own real entity instead.

**Real, live, keyless REST/JSON-LD API - confirmed live, not assumed
from the WFS above.** A plain unauthenticated ``GET`` against
``api.basisregisters.vlaanderen.be/v2/straatnamen`` returns real
national data - roughly 99,600 real street names, confirmed live by
bisecting the ``offset`` parameter (the list response states no total
count field directly).

**No geometry on this resource - the same pure name-registry shape
ANNCSU (Italy)/BEV (Austria) already established, not a gap in this
build.** Real coordinates would need a separate join back to the
Wegenregister WFS above (via a real, stated ``linkerstraatnaamObjectId``/
``rechterstraatnaamObjectId`` cross-reference) - not attempted here, the
same "streets built, richer join left for later" call this SDK already
made for ANNCSU's own ``accessi`` sibling.

**No municipality context in the list response either - a real,
confirmed API quirk, not an oversight in this client.** The
documentation-suggested filter parameter, ``gemeenteniscode``, is
silently ignored (confirmed live: three requests - two different real
codes and no filter at all - return byte-identical first pages); an
undocumented ``gemeentenaam=<name>`` text filter genuinely does work
(confirmed live: distinctly different, correctly-scoped results for
"Antwerpen"), but using it to resolve every street's municipality would
mean a real ~300-municipality fan-out this client doesn't attempt -
``administrative_area`` is therefore left unresolved (``None``) by
:mod:`streetworks.common.from_vlaanderen`, the same honest gap Denmark's
DAR leaves for its own raw kommune code.

**Pagination: real, confirmed live** - `offset`/`limit` parameters, with
a real ``volgende`` ("next") field carrying the next page's full URL,
confirmed live to be absent on the genuine last page.

**No credentials.** Licence: Flanders' standard government open-data
terms, the "Modellicentie Gratis Hergebruik" (Model Licence for Free
Reuse - confirmed live and reachable at
``data.vlaanderen.be/doc/licentie/modellicentie-gratis-hergebruik/v1.0``,
though its own clause text is behind a JS-rendered page this module
couldn't extract directly) - the default licence for Flemish government
open data (confirmed via web search, not this specific API's own
per-dataset licence field), free reuse for any purpose with attribution
as the only stated condition.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "VlaanderenStreetsClient"]

JSON = dict[str, Any]

#: The real, live, keyless national (Flanders-only) bulk-listing route.
#: See module docstring.
BASE_URL = "https://api.basisregisters.vlaanderen.be/v2/straatnamen"

_DEFAULT_PAGE_SIZE = 500


class VlaanderenStreetsClient:
    """Fetch Flanders' real Straatnamenregister (street-name register).
    No credentials required.

    >>> from streetworks.vlaanderen import VlaanderenStreetsClient
    >>> from streetworks.common import from_vlaanderen_street
    >>> with VlaanderenStreetsClient() as vlaanderen:  # doctest: +SKIP
    ...     streets = [from_vlaanderen_street(r) for r in vlaanderen.iter_streets()]
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
        """Yield every real Flemish street name, following the real
        ``volgende`` pagination link until it's genuinely absent -
        confirmed live to mean the real last page. See module
        docstring."""
        url: str | None = f"{BASE_URL}?offset=0&limit={self._page_size}"
        while url:
            response = self._transport.request("GET", url)
            payload = response.json()
            yield from payload.get("straatnamen", [])
            url = payload.get("volgende")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> VlaanderenStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
