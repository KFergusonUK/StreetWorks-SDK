"""Stockholm (Trafikkontoret) - a Credentials-wanted scaffold, one phase
earlier than :mod:`streetworks.datex2.trafikverket`.

.. attention::
   **PHASE 0 SCAFFOLD - genuinely blocked on real access, less confirmed
   than any other Credentials-wanted provider in this SDK.** Every real
   data-fetching surface tested (WFS ``GetCapabilities``, WMS
   ``GetCapabilities``) returns a genuine HTTP 401 before any dataset
   name, layer, or field is ever revealed - unlike South Australia (whose
   layer *definition* is public) or Trafikverket (whose object type and
   field names are confirmed via public documentation and third-party
   client libraries), **no real schema of any kind has been seen for
   Stockholm.** This module exposes only what's confirmed to exist and
   be reachable - fetching ``GetCapabilities`` itself, once a real key is
   available - not a guessed roadworks query, since there is nothing
   real to build one against yet.

**Resolves `nordic-capitals-investigation.md`'s "Rome-risk" flag - by
confirming it, not disproving it.** The brief flagged Stockholm's city
open-data portal as maybe publishing road network/rules rather than
actual works, and key-gated. Checked live:

- `dataportalen.stockholm.se` (Stockholm's open-data catalogue, a real
  GeoNetwork CSW instance, confirmed live) has a **non-functional
  full-text search** - a nonsense search term (``AnyText=xyzzyqqq``)
  returns the identical 311 records as no filter at all, the same
  "unfiltered" trap this SDK found on Street Manager's Reporting API
  earlier this session. No dataset could be located by keyword search.
- **Trafikkontoret's actual geodata service
  (`openstreetgs.stockholm.se`) requires a real API key for every real
  surface tested - confirmed live, not assumed:** `WFS GetCapabilities`
  and `WMS GetCapabilities` (metadata only, no data) both return a
  genuine structured `HTTP 401` (``text/plain``, body: *"You must
  provide a valid key to consume this API."*) - even listing what
  layers exist requires registration first.
- A real, promising-sounding lead - "a map that coordinates roadworks to
  minimise regional traffic impact" - traces back to the **Regionala
  Trafikgruppen** (Trafikverket, Region Stockholm, Nacka/Sundbyberg/
  Solna, Trafik Stockholm), surfaced via `trafiken.nu`. That's the
  already credential-parked **national** Trafikverket system this SDK
  has (:mod:`streetworks.datex2.trafikverket`), not a separate Stockholm
  city dataset - so even this lead doesn't add new disjoint coverage.
- Trafikkontoret's own getting-started guide's one real worked example
  query is for motorcycle parking places (`pmotorcykel`), reinforcing
  rather than resolving the brief's Rome-risk concern - the one
  concretely-documented dataset is parking, not roadworks.

**Whether a roadworks (`vägarbete`) dataset exists on this platform at
all is genuinely unresolved** - not confirmed present (like Helsinki's
`Kaivuilmoitus_alue`) and not confirmed absent either (like Greece's real
NAP, checked and found to carry none). It stays an open question until
someone with a real key runs :meth:`StockholmClient.get_wfs_capabilities`
and reports back the real layer list.

**Auth mechanism: partially evidenced, not fully confirmed.** The one
real documented example on Trafikkontoret's own getting-started guide (a
working Parking-API query URL) uses ``apiKey=<key>`` as a query
parameter - :class:`StockholmClient` uses the same parameter name on the
WFS endpoint, since it's the only real evidence available, but this is
**not confirmed** to be correct for WFS/OGC API specifically (a fake key
value returns the identical generic error regardless of parameter name
tried, so a wrong parameter name is indistinguishable from a wrong key
value without a real credential to test against). If a real key still
returns 401 through this client, trying the key as an
``Ocp-Apim-Subscription-Key`` header (a common gateway convention,
unconfirmed here) is the next thing to check - see the response headers'
own ``server: Microsoft-IIS/10.0`` / ``x-powered-by: ASP.NET`` (real,
observed), which rules out some gateway styles but not others.

**Credentials**: an API key - registration path found via the site's own
navigation (`"Begär API-nyckel"`, "Request API key") but the exact page
returned a 404 on the one URL guessed; contact `api.it.tk@stockholm.se`
(stated on the getting-started guide as the technical/access contact) or
navigate the portal's own menu from
`https://openstreetgs.stockholm.se/home/` to find the current
self-service (or request) flow.

**Licence**: unconfirmed - not checked, since no dataset has been reached
to check a licence against.
"""

from __future__ import annotations

import warnings
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "StockholmClient"]

warnings.warn(
    "streetworks.stockholm is a Phase 0 Credentials-wanted scaffold: every "
    "real data-fetching surface tested (WFS/WMS GetCapabilities) requires an "
    "API key just to reveal what layers exist, so no schema has been "
    "confirmed - see the module docstring. Have Trafikkontoret API access? "
    "Running StockholmClient.get_wfs_capabilities() and reporting back the "
    "real layer list (does a roadworks/vägarbete layer exist at all?) would "
    "be the single most useful thing - see the 'help wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues for exactly "
    "what's needed.",
    UserWarning,
    stacklevel=2,
)

JSON = dict[str, Any]

#: Confirmed live to exist and require a key (real 401, real body) - see
#: module docstring. No confirmed layer/collection name exists yet.
BASE_URL = "https://openstreetgs.stockholm.se/geoservice/api/wfs"

#: The one real, documented query-parameter name for this platform's key
#: (from Trafikkontoret's own getting-started guide, confirmed for the
#: Parking API specifically) - used here on WFS too, unconfirmed. See
#: module docstring.
_API_KEY_PARAM = "apiKey"


class StockholmClient:
    """Reach Stockholm's Trafikkontoret geodata WFS. **Phase 0 scaffold -
    see module docstring.** Requires a real API key this SDK doesn't
    have; :meth:`get_wfs_capabilities` is the one real, confirmed,
    non-guessed call this client can make - it reveals the real layer
    list once a key works, which is the prerequisite for writing any
    roadworks query at all.

    >>> from streetworks.stockholm import StockholmClient
    >>> with StockholmClient(api_key=api_key) as stockholm:  # doctest: +SKIP
    ...     capabilities_xml = stockholm.get_wfs_capabilities()
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def get_wfs_capabilities(self) -> str:
        """``GetCapabilities`` against the real, confirmed WFS endpoint -
        the raw XML response body. Not a roadworks query: this is the
        prerequisite discovery step, since no real layer/typeName is
        confirmed to exist yet - see module docstring. A 401 here with a
        real key means :data:`_API_KEY_PARAM` is the wrong parameter
        name/placement, not that the key itself is wrong."""
        response = self._transport.request(
            "GET",
            self.base_url,
            params={
                "service": "WFS",
                "request": "GetCapabilities",
                _API_KEY_PARAM: self.api_key,
            },
        )
        return response.text

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> StockholmClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
