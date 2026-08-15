"""Transport for London (TfL): Road Disruption - the accessible
complement to Street Manager's own register-grade, all-borough
`opendata` feed. This SDK's first standalone London roadworks
coverage, alongside the separate England-wide Street Manager permit
register - do not dedupe (a works on a TLRN red route can genuinely
appear in both: Street Manager as the permit, TfL as the live
operational disruption).

.. attention::
   **Confirmed live (2026-08-15)** against a real, unauthenticated pull
   (118 real disruption rows, 116 real ``Works`` rows, at time of
   writing).

**Genuinely keyless - confirmed live, better than the source brief's
own "register for a free key" assumption.**
``GET https://api.tfl.gov.uk/Road/all/Disruption`` returns full real
data with no ``app_key`` at all. TfL's own free 500-requests-a-minute
key plan remains real and available, but purely as an optional
rate-limit courtesy - the same "app token is optional, never required"
role this SDK's own :class:`~streetworks.socrata.client.SodaClient`
already documents for Socrata's ``X-App-Token``.

**``category == "Works"`` is a real, clean filter - confirmed by
reading the excluded records, not just trusting the label.** 116/118
real live records; the other 2 (``Hazards``/Fire, ``Network delays``/
Heavy traffic) were checked directly and are genuinely not roadworks.
:meth:`TflClient.iter_roadworks` applies this filter;
:meth:`TflClient.iter_disruptions` returns everything raw.

**Geometry is real GeoJSON with an explicit stated CRS** - every
record's ``geography`` field states
``"crs": {"type": "name", "properties": {"name": "EPSG:4326"}}``
explicitly, genuine WGS84. Only ``Point`` geometry was seen across the
full 116-record live ``Works`` pull; a ``roadDisruptionLines`` field
exists in the schema but was empty on every real record checked - not
handled in the converter, since this SDK doesn't write geometry code
for a shape it has never actually observed.

**A real nuance to the "TLRN, not all-London" scope claim, found not
just assumed.** ``corridorIds`` (a plausible road-number identifier,
e.g. ``["a10"]``) is **inconsistently populated - only 51/116 (44%) of
real ``Works`` records carry one, including just 11/21 of the core
"TfL works" subcategory itself.** Not a reliable TLRN-membership signal
or join key - see :mod:`streetworks.common.from_tfl` for why it stays
on ``.raw`` only.

**``status`` was ``"Active"`` on all 116 live real ``Works`` records -
checked explicitly, not assumed constant.** This endpoint only returns
currently-active disruptions, a genuinely different epistemic class
from a permit application's scheduled dates.

**Licence: confirmed directly from TfL's own terms page**
(``tfl.gov.uk/corporate/terms-and-conditions/transport-data-service``)
- based on OGL v2.0 with TfL-specific amendments, requiring **three**
real attribution statements: *"Powered by TfL Open Data"*, *"Contains
OS data © Crown copyright and database rights 2016"*, and *"Geomni UK
Map data © and database rights [2019]"*.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "TflClient"]

JSON = dict[str, Any]

#: TfL's Unified API - confirmed live keyless. See module docstring.
BASE_URL = "https://api.tfl.gov.uk/Road/all/Disruption"


class TflClient:
    """Fetch Transport for London's real Road Disruption feed. No
    credentials required - ``app_key`` is an optional rate-limit
    courtesy, the same role Socrata's ``X-App-Token`` plays for
    :class:`~streetworks.socrata.client.SodaClient`.

    >>> from streetworks.tfl import TflClient
    >>> from streetworks.common import from_tfl
    >>> with TflClient() as tfl:  # doctest: +SKIP
    ...     works = from_tfl(list(tfl.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        app_key: str | None = None,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._app_key = app_key
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_disruptions(self) -> Iterator[JSON]:
        """Every real disruption - raw, unfiltered, includes non-works
        categories (Hazards, Network delays). See module docstring."""
        params = {"app_key": self._app_key} if self._app_key else None
        response = self._transport.request("GET", BASE_URL, params=params)
        yield from response.json() or []

    def iter_roadworks(self) -> Iterator[JSON]:
        """Real ``category == "Works"`` disruptions only - see module
        docstring for the live-confirmed filter."""
        for record in self.iter_disruptions():
            if record.get("category") == "Works":
                yield record

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> TflClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
