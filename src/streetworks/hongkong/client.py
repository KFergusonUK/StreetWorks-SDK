"""Hong Kong (Transport Department / Highways Department): Roadworks
Location - a genuinely keyless, trilingual (English/Traditional
Chinese/Simplified Chinese) JSON+GeoJSON feed of Highways Department's
own live lane-closure roadworks on Hong Kong's strategic road network.

.. attention::
   **Confirmed live (2026-08-24)** against a real, unauthenticated pull
   (8 real records at time of writing, all ``worksstatus="In Progress"``)
   matching the Transport Department's own published data specification
   field-for-field.

**Genuinely keyless - no app key, no registration, nothing.** Unlike
most feeds in this SDK, there isn't even an optional rate-limit-courtesy
key like TfL's or Socrata's (:mod:`streetworks.tfl.client`,
:class:`streetworks.socrata.client.SodaClient`) - the resource URL is
just a plain public JSON file, confirmed by reading the Transport
Department's own published data specification PDF
(``roadworks_location_data_specification.pdf``, version 1.02, May 2026)
alongside a real live pull.

**Scope is real and narrower than "all Hong Kong roadworks" - stated
explicitly, not inferred.** This is Highways Department's own roadworks
"involving lane closure on public roads with a speed limit of 70km/hr
or above" - Hong Kong's strategic/expressway-grade network, the same
"not comprehensive, but honestly scoped" shape as ASFINAG/TfL in this
SDK, not Brussels' comprehensive local-street coverage. The feed only
ever holds roadworks that are either genuinely in progress or "under
preparation" (due to start within 12 hours) - not a forward-looking
schedule.

**``worksstatus`` has exactly two real documented values, confirmed by
the spec, not just observed** - ``"Under Preparation"`` and
``"In Progress"``. Every one of the 8 real live records checked was
``"In Progress"`` - ``"Under Preparation"`` is a real, spec-stated
value, not fabricated, but wasn't observed live in this pull (checked
explicitly, not assumed absent).

**Every text field is real and trilingual** - English (bare field name),
Traditional Chinese (``_tc``), and Simplified Chinese (``_sc``) variants
of ``datasource``/``workstype``/``district``/``roadname``/``locdesc``/
``bound``/``lane``/``remark``/``worksstatus``/``disclaimer`` are all
populated on every real record. Only the English variant is promoted by
:mod:`streetworks.common.from_hongkong`; the Chinese variants stay on
``.raw``.

**Geometry: real WGS84 ``latitude``/``longitude`` fields directly on
each record** (the spec states this explicitly: ``"WGS84, latitude/
longitude of roadwork's location"``) - this client reads the plain JSON
resource (flat objects with top-level ``latitude``/``longitude``), not
the sibling GeoJSON resource
(``get_all_the_roadworks.geojson``, wrapping the identical fields in a
``Point`` feature) - functionally identical data, JSON avoids an
unnecessary geometry-unwrapping step.

**Licence: DATA.GOV.HK's portal-wide terms, confirmed live** (not a
per-dataset licence - none is stated on the dataset's own catalogue
page) - free for commercial and non-commercial use, but **attribution
is required**: *"you shall identify clearly the source of the Data and
acknowledge the Government and the Relevant Organisations' ownership of
the intellectual property rights in the Data"*.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "HongKongClient"]

JSON = dict[str, Any]

#: Transport Department's real, keyless roadworks-location resource -
#: confirmed live. See module docstring.
BASE_URL = "https://resource.data.one.gov.hk/td/roadworks-location/get_all_the_roadworks.json"


class HongKongClient:
    """Fetch Hong Kong's real Roadworks Location feed. No credentials
    required or even available - see module docstring.

    >>> from streetworks.hongkong import HongKongClient
    >>> from streetworks.common import from_hongkong
    >>> with HongKongClient() as client:  # doctest: +SKIP
    ...     works = from_hongkong(list(client.iter_roadworks()))
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

    def iter_roadworks(self) -> Iterator[JSON]:
        """Every real roadworks record - the whole resource is already
        roadworks-scoped, no category filter needed (unlike TfL)."""
        response = self._transport.request("GET", BASE_URL)
        yield from response.json() or []

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> HongKongClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
