"""Milan: Avvisi di manomissione ("road-tampering/excavation notices") -
this SDK's second Italy municipal provider, after Roma.

.. attention::
   **Confirmed live (2026-08-14)** against a real, unauthenticated pull
   (139 real feature rows at time of writing).

**Resolves the "populous cities" pivot's own open question - the exact
dataset, not just the ecosystem.** Rome fell off-board (capital-projects
tracker only, no roadworks) and the investigation brief asked whether
Milan redeems Italy municipally. It confirmed the *ecosystem* - the
Lombardy Socrata portal (``dati.lombardia.it``) hosts real "Cantieri
stradali attivi" for Cremona/Pavia/Rho/Concesio - but not a Milan-
specific dataset. Checked live: **no Milan/Città-Metropolitana-Milano
dataset exists on the Lombardy portal at all** (searched "cantieri",
"cantieri stradali", "milano cantieri" - nothing). Milan's *own* CKAN
portal (``dati.comune.milano.it``) has none named "cantieri" either -
but searching "scavo" (excavation) surfaces **``ds925_avvisi-di-
manomissione``**, the real Italian legal term for a road-excavation
notice, not the term the brief guessed. Maintained by **Comune di
Milano - Direzione Mobilità e Trasporti**, updated **daily** (confirmed:
``metadata_modified`` was the same day as this investigation), CC-BY,
with a direct GeoJSON download - no API/WFS, no key.

**Single-purpose dataset - no roadworks-vs-other filter needed**, unlike
Lisboa's free-text ``motivo`` mix or Paris's three categories: every
real row is an excavation notice. ``iter_roadworks`` returns
everything unfiltered.

**A real, confirmed quirk: the download URL is filename-agnostic.** The
CKAN resource's own stated ``url`` embeds a generation timestamp in the
filename (the file is regenerated daily), but CKAN resolves purely by
the resource UUID in the path - a request substituting an arbitrary
filename returned identical live content (139 features, same data) as
the real timestamped URL. :data:`MANOMISSIONE_URL` uses a stable,
non-timestamped filename deliberately - it will keep serving each day's
fresh file without ever going stale, not a link that needs re-resolving.

**Geometry: real ``Point``, native WGS84 - not the brief's guessed
Monte Mario/ETRF2000 projected CRS.** Every feature states
``"crs": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}`` and separately
carries explicit ``LONG_X_4326``/``LAT_Y_4326`` properties confirming
it - genuine WGS84 degrees, same as Lisboa/Paris/Copenhagen, no
reprojection needed (unlike Oslo/Helsinki's real projected sources).

**``Tipo di utility/attività`` is a utility-operator excavation
register**, the Milan equivalent of Paris's "Opérateurs de réseau"
category - real values seen live: ``Acqua Potabile``/``Acqua potabile``
(water, inconsistent capitalisation in the source itself), ``Elettricità``
(electricity), ``Gas``, ``Fognatura`` (sewage), ``Teleriscaldamento``
(district heating). Stated honestly as utility-excavation-scoped, not
"every Milan roadworks project" - the city's own separate road-
maintenance programme, if published anywhere, is a different dataset,
not checked here.

**138 of 139 real rows have a planned end date current or in the
future** - this "final" download is already close to active-scoped, not
a full historical archive (one real outlier, a 2021 record, is kept
as-is rather than silently dropped - see
:mod:`streetworks.common.from_milano`).

**Licence: Creative Commons Attribution (CC-BY), confirmed live** via
the dataset's own CKAN metadata (``license_id: "cc-by"``).

**No credentials required** - every claim above came from a fully
unauthenticated GET request.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["MANOMISSIONE_URL", "MilanoClient"]

JSON = dict[str, Any]

#: A stable, filename-agnostic download URL for the real CKAN resource
#: behind "Avvisi di manomissione" - confirmed live that CKAN resolves
#: by the resource UUID in the path, ignoring the filename, so this
#: keeps serving each day's freshly regenerated file. See module
#: docstring.
MANOMISSIONE_URL = (
    "https://dati.comune.milano.it/dataset/"
    "a71f2103-1b01-4568-b98a-8cf047e68db8/resource/"
    "e3d5c87c-cb26-49e0-8102-2c90ee03598c/download/avvisi_manomissione.geojson"
)


class MilanoClient:
    """Fetch Milan's real "Avvisi di manomissione" (road-excavation
    notices). No credentials required.

    >>> from streetworks.milano import MilanoClient
    >>> from streetworks.common import from_milano
    >>> with MilanoClient() as milano:  # doctest: +SKIP
    ...     works = from_milano(list(milano.iter_roadworks()))
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
        """Every real excavation-notice feature - raw, unfiltered. This
        dataset is already single-purpose, see module docstring."""
        response = self._transport.request("GET", MANOMISSIONE_URL)
        body = response.json()
        yield from body.get("features") or []

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> MilanoClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
