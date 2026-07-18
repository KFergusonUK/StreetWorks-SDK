"""Spain (DGT) roadworks - DATEX II v3, Level C, Spanish-extended profile,
credential-free.

The DGT (Dirección General de Tráfico) National Access Point publishes
national traffic incidents, including roadworks, as open DATEX II - no
authentication required.

**Confirmed live, 2026-07**: a single ``GET`` on the SituationPublication
endpoint (~3.7 MB) returns 656 real situations. The URL versions itself -
the well-known ``datex2_v36.xml`` path 301-redirects to
``datex2_v37.xml``, and the live payload declares
``profileVersion="3.7_1.0"``, not the ``v36`` the filename implies - so
:class:`DGTClient` follows redirects and never assumes a version, matching
what the DGT NAP's own CKAN dataset metadata confirms (dataset
``incidencias-dgt-datex2-v3-7``, format ``DATEX2v3.7``).

**Coverage**: all of Spain *except* Catalonia and the Basque Country, which
run their own regional traffic authorities and publish separately - the
DGT feed states this itself (it's a national, not all-Spain, publication).

**Standard DATEX v3, no bespoke parsing path** - reused through the
existing shared :func:`~streetworks.datex2.parser.iter_situations_full` /
:func:`~streetworks.datex2.parser.iter_roadworks_full`, same as NDW/Iceland/
France. The Spanish national extensions (``cse:``/``sse:``/``lse:``
namespaces, plus a ``ns3:``/``locationExtension`` TPEG-point extension)
sit alongside the standard ``sit:``/``loc:``/``com:`` elements the parser
already reads - the essentials (situation id, record type/xsi:type,
validity, location coordinates, cause) are all standard-namespace, so
nothing extension-only had to be handled; the extensions are preserved
whole in ``.raw`` (this client uses the non-streaming parser - ~3.7 MB is
nowhere near NDW's ~170 MB streaming threshold).

**The real gap Spain surfaced (not an extension issue - a structural
one)**: DGT's feed has **zero** ``MaintenanceWorks``/``ConstructionWorks``
records anywhere in the whole feed (confirmed exhaustively - 656
situations checked). Every other adapter uses one of those two dedicated
xsi:types to mark a roadworks record; Spain instead publishes roadworks as
a generic record type - overwhelmingly ``RoadOrCarriagewayOrLaneManagement``
(373/391 real roadworks records), but also ``SpeedManagement`` (17/391) and
``AbnormalTraffic`` (1/391) - discriminated only by
``cause/causeType=roadMaintenance`` +
``cause/detailedCauseType/roadMaintenanceType=roadworks``. The old
``is_roadworks`` (xsi:type-only) would have silently returned **zero**
roadworks for every single Spanish record. Fixed in
:attr:`~streetworks.datex2.models.SituationRecord.is_roadworks`, additively
- it now also matches on the cause pair when the xsi:type isn't one of the
two dedicated types, confirmed not to change any other adapter's real
fixture (none of them use a ``cause`` element the same way; NDW/France
state ``roadMaintenanceType`` as a flat direct sibling of ``cause``, not
nested inside it). This also meant ``road_maintenance_type`` itself needed
a second read path - Spain nests it three levels down
(``cause/detailedCauseType/roadMaintenanceType``), not as the record's
direct child every other feed uses - fixed in
:func:`~streetworks.datex2.parser._parse_record` as an additive fallback
(direct child tried first, so no other adapter's extraction path changes).

**Location, verified across all 391 real roadworks records**: 100%
coordinate coverage, no location-less records. 377/391 use
``SingleRoadLinearLocation`` (a real ``tpegLinearLocation`` from/to pair,
already handled by the existing TPEG logic France's adapter fixed); 14/391
use plain ``PointLocation``. The road identifier is stated as
``roadInformation/roadName`` (e.g. ``"N-400"``, ``"A-1507"``) - **not**
``roadNumber``, which is absent on all 391 records - so
:func:`~streetworks.datex2.parser._parse_location` gained a
``roadName`` fallback (tried only when ``roadNumber`` is absent, so NDW/
France - which do carry real ``roadNumber`` values - are unaffected).

**``administrative_area`` (province)**: genuinely stated on 100% of real
roadworks records (391/391), nested inside each TPEG endpoint's Spanish
extension (``_tpegNonJunctionPointExtension/extendedTpegNonJunctionPoint/
province`` - the coarser ``autonomousCommunity`` sits right next to it, not
used here to match the finer grain NDW/Digitraffic use for
``administrative_area`` elsewhere). Not on the shared model, so
:func:`provinces` reads it from each record's ``.raw`` XML directly, same
shape of solution as :func:`~streetworks.datex2.bisonfute.dir_regions`.
**Known simplification**: a linear segment's two endpoints occasionally sit
in different provinces (9/391 real records, a genuine
province-boundary-crossing road segment, not a data error) - :func:`provinces`
takes whichever the parser encounters first in document order (the ``to``
endpoint, since DATEX lists it before ``from``) rather than representing
both; documented, not silently dropped.

**Other honest gaps, confirmed against the real feed**: ``source_name``
comes out ``None`` for every record - the ``<source>`` element states only
``sourceIdentification`` (always ``"DGT"``, the operator, not a sub-office)
and never a ``sourceName``, unlike NDW/France. ``validity.status`` was
``"active"`` on all 391 real roadworks records at fetch time (a live
snapshot, not a forward-looking planning feed), so ``date_confidence``
should generally come out ``VERIFIED`` in practice - genuinely observed,
not assumed to always be true of every future fetch. No
``generalPublicComment`` was present on any real roadworks record, so
``traffic_management`` comes out ``None`` throughout.

**Licence and attribution** (confirmed via the DGT NAP's own CKAN dataset
metadata for ``incidencias-dgt-datex2-v3-7``): published under **Creative
Commons Attribution (CC BY)**, terms of use at
https://www.dgt.es/contenido/aviso-legal/ - free reuse, redistribution, and
commercial exploitation permitted with attribution. Cite "Dirección General
de Tráfico (DGT), via the DGT National Access Point (nap.dgt.es)" wherever
Spanish roadworks data from this module is displayed or redistributed.

**Scope**: mainland Spain plus the islands under DGT's remit, minus
Catalonia and the Basque Country (their own regional authorities, separate
future sources, out of scope here).
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Situation, SituationRecord
from .parser import _local
from .parser import iter_roadworks_full as _iter_roadworks_full
from .parser import iter_situations_full as _iter_situations_full

__all__ = ["BASE_URL", "SITUATION_PUBLICATION_PATH", "DGTClient", "provinces"]

BASE_URL = "https://nap.dgt.es"
SITUATION_PUBLICATION_PATH = "datex2/v3/dgt/SituationPublication/datex2_v36.xml"


def _province(record: SituationRecord) -> str | None:
    if record.raw is None:
        return None
    for element in record.raw.iter():
        if _local(element.tag) == "province":
            text = (element.text or "").strip()
            if text:
                return text
    return None


def provinces(situations: list[Situation]) -> dict[str, str]:
    """Map ``situation.id -> province name`` (e.g. ``"Toledo"``) for every
    roadworks situation that states one - pass the result to
    ``streetworks.common.from_datex2(situation, administrative_area=...)``,
    since a ``Situation`` alone doesn't carry it. See module docstring for
    why this reads ``.raw`` directly, and for the province-boundary-crossing
    simplification."""
    result: dict[str, str] = {}
    for situation in situations:
        if not situation.roadworks:
            continue
        province = _province(situation.roadworks[0])
        if province:
            result[situation.id] = province
    return result


class DGTClient:
    """Fetch Spanish national roadworks (excl. Catalonia & the Basque
    Country) from the DGT National Access Point. No credentials required.

    >>> from streetworks.datex2.dgt import DGTClient, provinces
    >>> from streetworks.common import from_datex2
    >>> with DGTClient() as dgt:
    ...     situations = list(dgt.iter_roadworks())
    >>> spanish_provinces = provinces(situations)
    >>> for situation in situations:
    ...     works = from_datex2(
    ...         situation, territory="Spain",
    ...         administrative_area=spanish_provinces.get(situation.id),
    ...     )
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
        """``GET`` the SituationPublication - the raw DATEX II XML response
        body (all current traffic incidents, including roadworks). The URL
        redirects to whatever version DGT currently serves - see module
        docstring."""
        response = self._transport.request(
            "GET", f"{self.base_url}/{SITUATION_PUBLICATION_PATH}"
        )
        return response.content

    def iter_situations(self) -> Iterator[Situation]:
        yield from _iter_situations_full(io.BytesIO(self.get_situations()), provider="DGT/Spain")

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record - see module docstring for why that isn't a
        simple xsi:type check for this source."""
        yield from _iter_roadworks_full(io.BytesIO(self.get_situations()), provider="DGT/Spain")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> DGTClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
