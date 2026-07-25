"""Luxembourg (Ponts et Chaussées) roadworks - DATEX II v2.3, credential-free.

The Administration des Ponts et Chaussées (Luxembourg's national road
authority) publishes current roadworks on the national road network as
open DATEX II v2.3, via CITA (Centre d'Intervention et de Technologie
Avancée) - no registration, no API key.

**Confirmed live, 2026-07**: a single ``GET`` on ``chantierActuelDatex.xml``
(~570 KB) returns around 110 real situations, ~160 real ``MaintenanceWorks``
records - zero ``ConstructionWorks``. Standard DATEX II v2.3, the same
version France uses, parsed through the same shared
:func:`~streetworks.datex2.parser.iter_situations_full` /
:func:`~streetworks.datex2.parser.iter_roadworks_full` every other DATEX
adapter uses - no bespoke parse path needed, and none was forced by the
real data (unlike Belgium, checked alongside this one - see
:mod:`streetworks.datex2.belgium`).

**Discriminator: clean, single dedicated type.** Every real roadworks
record checked (161/161 in one live pull) uses the dedicated
``MaintenanceWorks`` xsi:type; ``ConstructionWorks`` never appears.
:attr:`~streetworks.datex2.models.SituationRecord.is_roadworks` already
covers this with no changes needed - confirmed against the real feed, not
assumed from the type's presence in ``ROADWORKS_TYPES``.

**Location, verified across all 161 real roadworks records**: 100%
coordinate coverage, genuine WGS84 (values ~49.6-49.8 latitude, ~6.0-6.3
longitude - correct for Luxembourg; no ``srsName`` override anywhere in
the feed, unlike Belgium). Every record is a real 2-point
``SingleRoadLinearLocation`` (a from/to line, not a bare point). Neither
``roadNumber`` nor an Alert-C location name is stated on any record
checked - the feed identifies roadworks by coordinates only, not by a
named/numbered road.

**Other honest gaps, confirmed against the real feed**: every single
record's ``generalPublicComment`` is the identical literal placeholder
text ``"Titre:Nouvelle tape"`` (French, "Title: New stage" with what looks
like a source-side encoding/template artefact truncating "étape") -
present on 161/161 records, but genuinely non-informative; don't expect
``traffic_management`` to carry a real per-site description for this
source. ``validity.status`` is always the literal
``"definedByValidityTimeSpec"``, never ``"active"``/``"planned"``/
``"suspended"`` - so :func:`~streetworks.common.from_datex2`'s
``date_confidence`` will come out ``UNKNOWN`` for every Luxembourg site,
even though ``proposed_start``/``proposed_end`` themselves are real,
varied, genuinely-stated dates (past, current, and future works all
present in one real pull) - the status field just doesn't map to this
SDK's verified/estimated vocabulary, not that the dates are untrustworthy.
``source_name`` is always the literal ``"PCH"`` (Ponts et Chaussées's own
initials) - real and consistent, so it's a meaningful default for
``administrative_area`` without needing an override (see
:mod:`streetworks.common.from_datex2`'s own docstring).

**Licence** (confirmed live via data.public.lu's own dataset API record,
dataset "PCH : Les chantiers actuels"): **CC0** (``cc-zero`` -
Public Domain Dedication) - the cleanest, least restricted licence found
across every DATEX adapter in this SDK so far: no attribution
requirement, no share-alike, no non-commercial restriction. Real trimmed
fixture data is used here without the caveats Belgium's adapter needed.

**Scope**: the national road network only, as published by Ponts et
Chaussées - Luxembourg being a single small country with one national
road authority, there's no regional-fragmentation question the way there
is for Belgium/Germany/Spain.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Situation
from .parser import iter_roadworks_full as _iter_roadworks_full
from .parser import iter_situations_full as _iter_situations_full

__all__ = ["BASE_URL", "DATEX_PATH", "LuxembourgClient"]

BASE_URL = "https://www.cita.lu"
DATEX_PATH = "info_trafic/datex/chantierActuelDatex.xml"


class LuxembourgClient:
    """Fetch Luxembourg's national roadworks from Ponts et Chaussées (via
    CITA). No credentials required.

    >>> from streetworks.datex2.luxembourg import LuxembourgClient
    >>> from streetworks.common import from_datex2
    >>> with LuxembourgClient() as lu:
    ...     situations = list(lu.iter_roadworks())
    >>> for situation in situations:
    ...     works = from_datex2(situation, territory="Luxembourg")
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_situations(self) -> bytes:
        """``GET chantierActuelDatex.xml`` - the raw DATEX II XML response
        body (all current roadworks on the national road network)."""
        response = self._transport.request("GET", f"{self.base_url}/{DATEX_PATH}")
        return response.content

    def iter_situations(self) -> Iterator[Situation]:
        yield from _iter_situations_full(
            io.BytesIO(self.get_situations()), provider="Luxembourg"
        )

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record (``MaintenanceWorks`` - see module docstring)."""
        yield from _iter_roadworks_full(io.BytesIO(self.get_situations()), provider="Luxembourg")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> LuxembourgClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
