"""Dortmund (NRW) - the City of Dortmund's own roadworks register, over
its real ``open-data.dortmund.de`` OpenDataSoft portal. This SDK's first
German *municipal* roadworks provider - a genuinely different tier from
the state-level cluster in :mod:`streetworks.ogc.germany`, opened up
because NRW's own *state*-level roadworks route stays gated (Mobilithek/
DATEX, already parked - see that module's docstring), but this one real
city's own feed isn't.

**Found via GOVdata, not assumed from NRW's own state-level gating.**
NRW's real roadworks data flows through Mobilithek almost everywhere
checked (Cologne, Aachen - both confirmed live to trace only to
Mobilithek marketplace "offer" URLs, no independent open republish
found for either) - Dortmund is a genuine exception, its own real
OpenDataSoft portal (the same platform family as
:mod:`streetworks.paris`'s "Chantiers à Paris", the French/EU near-
equivalent of Socrata) publishing two real, live, keyless datasets
directly, harvested onto Open.NRW/GOVdata but genuinely served from
Dortmund's own infrastructure.

**Two real datasets, not one - "tagesaktuell" (currently active) and
"geplant" (planned), the same real/live-vs-scheduled split this SDK's
own DriveBC/other multi-window sources already carry as separate
concepts.** 134 real ``tagesaktuell`` records and 38 real ``geplant``
records at investigation time (2026-08-20), identical real schema on
both. :meth:`DortmundClient.iter_roadworks` fetches and yields both.

**A real per-record identifier exists - but only via the older,
nested ``/api/v2/catalog/...`` endpoint, not the newer flat
``/api/explore/v2.1/...`` Explore API :mod:`streetworks.paris` uses.**
Checked live: the v2.1 Explore API's own flattened records (matching
Paris's shape) carry no id field at all, the same real gap the plain
``exports/geojson`` shortcut has - only the v2 endpoint's
``record.id`` (a real, stable per-record hash, e.g.
``"e67a4fdab485cfafad87af19e1ad20645de48926"``) survives. This module
uses the v2 endpoint specifically for that reason, not for consistency
with Paris's own choice.

**Real, specific fields - not placeholders.** ``auftraggeber`` (a real
promoter - e.g. ``"EB70 - Stadtentwässerung"`` (the city's own
sewage/drainage utility), ``"Dortmunder Netz"`` (the local gas/
electricity network operator), ``"Stadt Dortmund"``), ``stadtbezirk``
(a real Dortmund city district, e.g. ``"Hörde"``, ``"Huckarde"``),
``art_der_baumassnahme`` (rich free text combining street, works type,
and restriction in one field, e.g. ``"Stiegenweg 12 - Kanalreparatur //
Vollsperrung"`` - no clean separate street field exists, the same
honest gap NYC/Chicago/Paris's own permit registers already carry).
``einschrankung`` is a real field, confirmed live to be ``null`` on
every real record at investigation time - genuinely unpopulated, not
checked further.

**Geometry is already WGS84 - no reprojection needed.**
``geografische_koordinate`` states ``{"lon": ..., "lat": ...}`` degrees
directly (confirmed live, real Dortmund coordinates ~7.3-7.6°E,
~51.4-51.6°N).

**Licence: Datenlizenz Deutschland - Zero - Version 2.0 (dl-zero-de/2.0),
confirmed** directly from GOVdata's own harvested metadata for this
exact dataset - a real, named, effectively public-domain licence (no
attribution even required, unlike the more common by-2.0 variant).

**No credentials required** - every read in this investigation
succeeded unauthenticated.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["TAGESAKTUELL_URL", "GEPLANT_URL", "DortmundClient"]

JSON = dict[str, Any]

_BASE = "https://open-data.dortmund.de/api/v2/catalog/datasets"

#: Currently-active real roadworks - confirmed live, no key required.
TAGESAKTUELL_URL = f"{_BASE}/fb66-baustellen-tagesaktuell/records"

#: Planned real roadworks - same real schema, confirmed live.
GEPLANT_URL = f"{_BASE}/fb66-baustellen-geplant/records"

#: A safety net against a malformed/looping server response - the same
#: role streetworks.paris.ParisClient's own _MAX_PAGES plays.
_MAX_PAGES = 10_000


class DortmundClient:
    """Fetch Dortmund's real roadworks records. No credentials required.

    >>> from streetworks.dortmund import DortmundClient
    >>> from streetworks.common import from_dortmund
    >>> with DortmundClient() as dortmund:  # doctest: +SKIP
    ...     works = from_dortmund(list(dortmund.iter_roadworks()))
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

    def _iter_records(self, url: str, *, page_size: int = 100) -> Iterator[JSON]:
        offset = 0
        for _ in range(_MAX_PAGES):
            params = {"limit": str(page_size), "offset": str(offset)}
            response = self._transport.request("GET", url, params=params)
            body = response.json()
            wrapped = body.get("records") or []
            # Each entry is {"links": [...], "record": {"id": ..., "fields": {...}}} -
            # only the real payload (the "record" key) is yielded here.
            records = [item["record"] for item in wrapped if "record" in item]
            yield from records
            offset += len(wrapped)
            if len(wrapped) < page_size or offset >= body.get("total_count", offset):
                return

    def iter_tagesaktuell(self) -> Iterator[JSON]:
        """Every real currently-active roadworks record."""
        yield from self._iter_records(TAGESAKTUELL_URL)

    def iter_geplant(self) -> Iterator[JSON]:
        """Every real planned roadworks record."""
        yield from self._iter_records(GEPLANT_URL)

    def iter_roadworks(self) -> Iterator[JSON]:
        """Every real roadworks record, both datasets combined - see
        module docstring for why there are two."""
        yield from self.iter_tagesaktuell()
        yield from self.iter_geplant()

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> DortmundClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
