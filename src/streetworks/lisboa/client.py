"""Lisboa: Condicionamentos de Trânsito - the Câmara Municipal de
Lisboa's (CML) own traffic-conditioning feed, this SDK's first Portugal
provider at any level (the national IMT NAP remains credential-parked;
this sidesteps it entirely via a separate keyless municipal feed).

.. attention::
   **Confirmed live (2026-08-09)** against a real, unauthenticated pull
   (694 real features at time of writing).

**The gating check the source brief itself named, resolved.** The
catalogue record for this dataset (`dados.gov.pt`) states *"Última
atualização: 22 de maio de 2023"* - stale metadata that, taken alone,
would suggest a dead/archived dataset (the Chicago-dead-dataset,
Madrid-moved-portal pattern this project has hit before). But that page
describes the *catalogue entry*, not the data: the real live platform
(``condicionamentos-transito.cm-lisboa.pt``, CML's "nova plataforma de
gestão integrada da mobilidade") is a live Angular SPA with no data of
its own in the page source - its backend, found by reading the app's own
JS bundle (the same technique that found Road Report NT's real backend
earlier in this project), is genuinely current: 453/694 real records
carry a 2026 `pedido` (case reference) id, with real dates as recent as
this investigation.

**Endpoint, found via the app's own bundled JS, not documented
anywhere public.** The Angular app's `environment` config states
``ws: "//lisboa.city-platform.com/percursos/ws/app/public"``; the
component that renders closures appends ``"/traffic/closures/"`` to it.
Confirmed live: a single keyless ``GET`` on
``https://lisboa.city-platform.com/percursos/ws/app/public/traffic/closures/``
returns the full real GeoJSON `FeatureCollection` (no pagination, no
`bbox`/date filtering - the API returns everything every time; the app
itself filters client-side).

**Roadworks filter: `motivo` (free-text reason), evidence-based, not a
clean boolean like Madrid's `es_obras`.** 27 real distinct values exist,
mixing genuine roadworks/construction reasons with unrelated categories
(deliveries, parking reservations, house moves, filming, processions,
demonstrations). This module's own ``_is_roadworks()`` classifies
**473/694 (68%)** as roadworks: anything containing the substring
``"OBRA"`` (Portuguese for "works" -
``"OBRA - FAIXA DE RODAGEM"``, ``"CARGAS E DESCARGAS/OBRAS"``, ``"ACESSO
DE VEÍCULOS À OBRA"``, ...), plus a small explicit set of values that
are clearly construction activity without literally containing that
word (``"BETONAGENS"`` - concrete pouring, ``"REPAVIMENTAÇÕES"`` -
repaving, ``"MONTAGEM DE GRUA"``/``"DESMONTAGEM DE GRUA"`` - crane
erection/dismantling). **Genuinely ambiguous values are excluded, not
guessed either way** - most notably ``"LIGAÇÃO DE RAMAL"`` (utility
branch-line connection, 57 real records - plausibly involves excavation,
but never states "obra" and isn't confirmed construction rather than a
simple hookup) and ``"AUTOGRUA"`` (mobile crane truck, 13 real records -
could be for a house move as easily as a worksite). All 27 real distinct
``motivo`` values and their live counts are enumerated in
``docs/providers/portugal.md``.

**Geometry: real `MultiLineString`, WGS84** - every one of 694 real
features, not `Point`/`LineString` like this SDK's other municipal
sources. 666/694 have exactly one sub-line; up to 7 sub-lines seen on a
few real records. **Only the first sub-line is used** - the same
deliberate simplification :mod:`streetworks.common.from_berlin` already
makes for a `GeometryCollection` with multiple `LineString` entries,
since :class:`~streetworks.common.models.Coordinate` supports one line
per point, not several. CRS: `EPSG:4326`, evidenced from the same app
bundle's own WMS map-layer requests (`SRS=EPSG:4326`) and independently
consistent with the real coordinate ranges (~-9.1 to -9.2°E, ~38.7-38.8°N
- genuine Lisbon values, not a projected PT-TM06/EPSG:3763 easting/
northing pair, which the source brief had flagged as a real possibility
for Portuguese data).

**Dates: `periodos_condicionamentos` is a list, not one window** - a
real, genuine richer shape than Madrid/DriveBC's single start/end:
665/694 real features have exactly one period, but up to 4 real periods
exist on some. Each period states `date_min`/`date_max` (bare dates) and
separate `hour_min`/`hour_max` (daily time-of-day), plus `is_interrupted`
(a real boolean - `True` on 583/727 real periods, meaning "not currently
in effect within its own window," genuinely the majority state, not an
edge case). `from_lisboa` combines the *first* period's start and the
*last* period's end into one `WorksSite` window, the same multi-interval
handling already used for DriveBC; `is_interrupted` stays on `.raw`
rather than forced into a field that doesn't fit it.

**Licence: CC BY 4.0, confirmed live** at `dados.gov.pt`'s catalogue page
for this exact dataset (*"Licença: Creative Commons Attribution 4.0 - CC
BY 4.0"*, publisher "Município de Lisboa") - the same page whose stale
"última atualização" date prompted the freshness check above; the
licence statement itself isn't dated the same way and is treated as
still governing the live data, the same official CML dataset either way.

**No app key required** - every claim above came from a fully
unauthenticated pull; CORS headers on the response are scoped to the
platform's own frontend origin, which restricts browser JavaScript, not
a server-side HTTP client like this one (confirmed - the pull that
produced every number above sent no `Origin` header at all).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["CLOSURES_URL", "LisboaClient"]

JSON = dict[str, Any]

#: Found in the Angular app's own bundled JS (environment.ws +
#: "/traffic/closures/"), not documented anywhere public. Confirmed live
#: 2026-08-09.
CLOSURES_URL = "https://lisboa.city-platform.com/percursos/ws/app/public/traffic/closures/"

#: Real, evidenced `motivo` values that literally contain "OBRA"
#: (Portuguese "works") are treated as roadworks via a substring check,
#: not this set. This set covers real construction-activity values that
#: *don't* contain that substring - see module docstring for the full
#: real value list and what's deliberately excluded as too ambiguous.
_EXTRA_ROADWORKS_MOTIVOS = frozenset(
    {
        "BETONAGENS/CARGAS DESCARGAS",
        "BETONAGENS",
        "REPAVIMENTAÇÕES",
        "MONTAGEM DE GRUA",
        "DESMONTAGEM DE GRUA",
    }
)


def _is_roadworks(motivo: str | None) -> bool:
    if not motivo:
        return False
    return "OBRA" in motivo or motivo in _EXTRA_ROADWORKS_MOTIVOS


class LisboaClient:
    """Fetch Lisboa's (CML) Condicionamentos de Trânsito feed. No
    credentials required.

    >>> from streetworks.lisboa import LisboaClient
    >>> from streetworks.common import from_lisboa
    >>> with LisboaClient() as lisboa:  # doctest: +SKIP
    ...     works = from_lisboa(list(lisboa.iter_roadworks()))
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

    def iter_condicionamentos(self) -> Iterator[JSON]:
        """Every real feature, unfiltered - includes deliveries, parking
        reservations, house moves, filming, processions and
        demonstrations alongside real roadworks. See module docstring."""
        response = self._transport.request("GET", CLOSURES_URL)
        body = response.json()
        yield from body.get("features") or []

    def iter_roadworks(self) -> Iterator[JSON]:
        """Real roadworks features only - see module docstring for the
        evidenced `motivo` classification `_is_roadworks` applies."""
        for record in self.iter_condicionamentos():
            if _is_roadworks(record.get("properties", {}).get("motivo")):
                yield record

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> LisboaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
