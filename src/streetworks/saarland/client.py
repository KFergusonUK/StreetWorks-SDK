"""Saarland: Landesbetrieb für Straßenbau (LfS) roadworks feed - a real,
live, keyless GeoJSON feed, continuing this SDK's German state roadworks
fan-out (:mod:`streetworks.ogc.germany` - Hamburg, Brandenburg, Saxony,
Baden-Württemberg, Schleswig-Holstein, Rheinland-Pfalz) with a state
whose own real data isn't published through a WFS at all.

**Found by reading the real public map app's own bundled JS - the same
technique that found Lisboa's Condicionamentos endpoint.**
``baustellen.saarland`` is LfS's own real Leaflet-based public map
(confirmed live, no login, no key); its ``js/map.js`` states two real
relative data paths, ``data/baustellen/roadworks_line_geojson.geojson``
(used here - richer real ``MultiLineString`` geometry, not collapsed to
a point) and ``data/baustellen/roadworks_point_geojson.geojson`` (the
same 38 real records, ``Point`` geometry only - not consumed, since the
line layer is a strict superset).

**38 real features at investigation time (2026-08-20) - genuinely
smaller than this SDK's other German states**, consistent with
Saarland's own small size (Germany's smallest area state bar the
city-states). Real road-class prefixes found in the free-text
``description`` field span ``L`` (Landesstraße) and ``B``
(Bundesstraße) only - no ``K``/``A`` seen live, plausibly because LfS's
own remit doesn't cover Kreisstraßen/Autobahnen, not confirmed from
documentation.

**``roadname`` is a real field, genuinely blank on some records (14/38
at investigation time) - not a data-quality gap.** Where blank, the
real route number is still stated inside ``description`` (e.g. ``"L 116
..."``) as free text; per this SDK's "never extract structured data
from free text" discipline (the same call Hamburg's own ``titel`` field
gets), this is left as free text on ``.raw`` rather than parsed out.

**Dates have no explicit UTC offset - ``"2022-11-28T00:00"``/
``"2026-12-31T23:59:59"``, genuinely naive** (unlike Baden-Württemberg's
own real ``+02:00``-suffixed dates on the same shared cluster) -
represented as midnight/stated-time Europe/Berlin via :mod:`zoneinfo`,
the same convention every date-only state in this cluster already uses.

**Licence: genuinely unconfirmed, not "none exists" - three real
sources checked, none confirm.** No entry found on GOVdata for this
exact feed; the GDI-DE metadata catalogue search API returned a real
``403`` (not routed around); ``saarland.de``'s own general pages
returned a real ``403`` too (a site-wide WAF, not this dataset
specifically - confirmed by the same block on unrelated saarland.de
pages). The same honest tier Autobahn GmbH's own licence sits at in
this SDK - confirm your own reuse rights before redistributing data
pulled through this module further downstream.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "ROADWORKS_URL", "SaarlandClient"]

JSON = dict[str, Any]

#: LfS's own real public map app - confirmed live, no key required. See
#: module docstring for how this was found.
BASE_URL = "https://baustellen.saarland"

#: The real line-geometry roadworks feed - richer than the sibling
#: point-only feed (same 38 records), see module docstring.
ROADWORKS_URL = f"{BASE_URL}/data/baustellen/roadworks_line_geojson.geojson"


class SaarlandClient:
    """Fetch Saarland's real LfS roadworks feed. No credentials required.

    >>> from streetworks.saarland import SaarlandClient
    >>> from streetworks.common import from_saarland
    >>> with SaarlandClient() as saarland:  # doctest: +SKIP
    ...     works = from_saarland(list(saarland.iter_roadworks()))
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
        """Every real feature (GeoJSON ``Feature`` dicts) - no filtering
        needed, every record on this feed is genuinely a roadworks
        closure/restriction."""
        response = self._transport.request("GET", ROADWORKS_URL)
        yield from response.json().get("features") or []

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> SaarlandClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
