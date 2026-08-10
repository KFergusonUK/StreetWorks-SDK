"""Copenhagen: "Gravetilladelser" (excavation permits) - Københavns
Kommune's own street-excavation permit register, this SDK's first Nordic
roadworks coverage.

.. attention::
   **Confirmed live (2026-08-10)** against a real, unauthenticated pull
   (2240 real feature rows at time of writing).

**Not the source or format the investigation brief guessed - checked live
before building.** The brief named "vejarbejde" (roadworks) as the likely
dataset title and assumed an ArcGIS Hub/OGC Features backend. Checked
directly on ``opendata.dk`` (the shared Danish municipal open-data
platform, CKAN/Datopian-backed): the real, live dataset is titled
**"Gravetilladelser"** ("excavation permits" - "overview of digging
permits granted on public roads or private shared roads in the
Municipality of Copenhagen", per the dataset's own live metadata), not
"vejarbejde". Its real backend is a **WFS 1.0.0 GetFeature endpoint**,
not ArcGIS/OGC API Features:
``https://wfs-kbhkort.kk.dk/k101/ows``, layer ``k101:gravetilladelser_aktiv_aabne``
("aktiv_aabne" = "active, open" - this WFS layer is already server-side
filtered to current permits, confirmed live: every one of 2240 real rows
carries the literal ``sagstype="Gravetilladelser"``, so no client-side
type filter is needed here).

**No credentials required** - every claim above came from a fully
unauthenticated GetFeature request with ``SRSNAME=EPSG:4326`` explicit
in the query string, and the response's own embedded ``crs`` block
confirms ``urn:ogc:def:crs:EPSG::4326`` was honoured. Raw coordinates are
standard GeoJSON ``[lon, lat]`` (confirmed against a real Copenhagen
point, ``[12.578, 55.640]``) - :func:`streetworks.common.from_copenhagen`
applies this SDK's usual swap to ``(lat, lon)``.

**A real, load-bearing geometry finding the brief never anticipated: this
layer mixes Point, LineString and Polygon geometry, and the same real
permit is recorded once per geometry shape it has, not once per permit.**
Grouping the raw 2240 rows by ``sagsnr`` (the real case/permit number)
gives 1241 distinct real permits; every multi-row permit has *identical*
non-geometry properties across its rows (confirmed against all 832 real
multi-row cases) - so a repeated ``sagsnr`` means "the same permit, once
per geometry representation" (e.g. one ``Point`` marker plus one
``Polygon`` extent for the same real excavation), not several distinct
worksites the way Jersey's ``PROJID``/NYC DOT's ``applicationtrackingid``
group real, separate sites under one project. Confirmed live: **zero**
of the 1241 real permits are Polygon-only - every one has a ``LineString``
or ``Point`` alternative - so :func:`streetworks.common.from_copenhagen`
dedupes by ``sagsnr`` and never needs to handle a polygon ring at all.

A secondary, pre-converted-to-point layer exists
(``k101:gravetilladelser_aktiv_aabne_conv_pkt``) but is confirmed live to
cover only 691 of the 1241 real permits (56%) - not used here, since it
would silently drop real permits the primary layer has.

**Licence confirmed live via the dataset's own CKAN metadata**:
Creative Commons Attribution 4.0 (CC-BY-4.0), with an explicit
``license_url``.

Real schema (12 fields, confirmed 100% populated across all 2240 rows,
zero nulls): ``ogc_fid``, ``lokation`` (free-text address), ``sagsnr``
(the real case number), ``projekt_start``/``projekt_slut`` (dates, real
format ``DD-MM-YY``, e.g. ``"04-07-26"`` - not ISO-8601), ``tidspunkt_fra``/
``tidspunkt_til`` (daily permitted working hours, e.g. ``"07:00"``/
``"18:00"``), ``kategori`` (the real works-type: Fibernet, EL,
Asfaltarbejder, Brolægningsarbejder, Fjernvarme, Vejafvanding, ...),
``gravetype`` (which street element is affected - Kørebane=carriageway,
Fortov=sidewalk, Cykelsti=bike path, P-Areal=parking area),
``bygherre`` (the commissioning client), ``entreprenoer`` (the
contractor), ``sagstype`` (always the literal ``"Gravetilladelser"``).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["GRAVETILLADELSER_URL", "CopenhagenClient"]

JSON = dict[str, Any]

#: Found via opendata.dk's own CKAN metadata for the "Gravetilladelser"
#: dataset (``admin.opendata.dk/api/3/action/package_show?id=gravetilladelser``),
#: not the ArcGIS/OGC Features source the investigation brief assumed.
#: Confirmed live 2026-08-10.
WFS_BASE_URL = "https://wfs-kbhkort.kk.dk/k101/ows"

#: The real, server-side-filtered "active, open" layer - see module
#: docstring for why no client-side status filter is needed on top of it.
_LAYER = "k101:gravetilladelser_aktiv_aabne"

_WFS_PARAMS = {
    "service": "WFS",
    "version": "1.0.0",
    "request": "GetFeature",
    "typeName": _LAYER,
    "outputFormat": "json",
    "SRSNAME": "EPSG:4326",
}

#: The full GetFeature URL with its query string, exposed for callers/tests
#: that want the exact real request this client makes.
GRAVETILLADELSER_URL = str(httpx.URL(WFS_BASE_URL, params=_WFS_PARAMS))


class CopenhagenClient:
    """Fetch Københavns Kommune's Gravetilladelser (excavation permits)
    WFS layer. No credentials required.

    >>> from streetworks.copenhagen import CopenhagenClient
    >>> from streetworks.common import from_copenhagen
    >>> with CopenhagenClient() as copenhagen:  # doctest: +SKIP
    ...     works = from_copenhagen(list(copenhagen.iter_roadworks()))
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
        """Every real feature row from the active/open Gravetilladelser
        layer, raw and unfiltered/undeduped - the same permit appears once
        per geometry shape it has (see module docstring). Deduping by
        ``sagsnr`` and picking one geometry per permit is
        :func:`streetworks.common.from_copenhagen`'s job, not this
        client's - it hands back exactly what the WFS service states."""
        response = self._transport.request("GET", WFS_BASE_URL, params=_WFS_PARAMS)
        payload = response.json()
        yield from payload.get("features") or []

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> CopenhagenClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
