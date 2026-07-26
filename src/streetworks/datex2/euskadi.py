"""Basque Country (Euskadi, Dirección de Tráfico del Gobierno Vasco)
roadworks - DATEX II **v1.0**, credential-free.

The *second* of DGT's two documented exclusions (DGT explicitly omits
Catalonia and the Basque Country - Catalonia's own gap is filled by
:mod:`streetworks.sct`; this fills the other). Published on Spain's
national NAP (``nap.dgt.es``, dataset ``incidencias-dt-gv``) by the Basque
Government's own traffic directorate, at a real, live endpoint.

**Licence: the publisher states "No licence - No contract" - literally,
not "unconfirmed."** This is a real, explicit statement, not an absence
of information - checked directly on the NAP's own dataset page. Absence
of a licence means no permission has been granted (copyright is automatic
and default-restrictive; a licence is what *adds* permissions), so this
is genuinely more restrictive than Autobahn GmbH's "couldn't find the
terms" case, not less - the distinction matters and is kept explicit
everywhere this adapter is documented. Practical position, same outcome
as Autobahn, different reasoning: calling a public government endpoint is
not a use of the data, so the client is built freely; but committing real
Basque records into this MIT-licensed, openly-redistributed repository
would be redistribution, which nothing here permits - so the test fixture
is **synthetic** (real confirmed shape, invented content), never real
data. This is Spanish public-sector information, and Spain's own
transposition of the EU PSI/open-data directive creates a general
presumption that public-sector information is reusable unless stated
otherwise - so it is *probably* reusable in practice - but "probably,
under PSI law" is not "the publisher granted a licence," and only the
honest version belongs in this SDK's docs. Confirm your own rights before
relying on this commercially; an email to the Basque open-data team would
resolve this properly (a follow-up, not a blocker, same as the pending
Autobahn/Consell de Mallorca licence emails).

**DATEX II v1.0 - the oldest schema version in this SDK** (every other
adapter targets v2.x or v3.x). Confirmed live: the shared parser
(:func:`~streetworks.datex2.parser.iter_situations_full`) reads it with no
code changes needed for the roadworks classification itself
(``MaintenanceWorks``/``ConstructionWorks`` - both already in
``ROADWORKS_TYPES``) - 96/119 real situations carry at least one
roadworks record in one live pull (78 ``MaintenanceWorks`` + 23
``ConstructionWorks``). But a genuine v1.0-specific field-fidelity issue
**was** found and fixed, additively, in the shared parser:

**Real parser fix: ``tpeglinearLocation`` (lower-case), not
``tpegLinearLocation``.** Confirmed live by direct byte search of the raw
feed: 74/74 real TPEG linear-location records use the lower-case v1.0
spelling; zero use the v2/v3 PascalCase one. Before this fix, the shared
parser's two-point ``from``/``to`` extraction never matched it, silently
falling through to the generic single-point fallback - a real line
degraded into just one point, not a documented convention. Fixed as a
second, fallback lookup in
:func:`~streetworks.datex2.parser._parse_location` (v2/v3 spelling tried
first, so no other adapter's behaviour changes - confirmed via a live
before/after regression across France, Spain, Belgium, Luxembourg and
Bulgaria: identical roadworks counts and 2+-point-location counts,
zero drift). After the fix: of 101 real roadworks records, 36 have a real
2+-point line, 6 have a single point, and 59 have **no coordinates at
all** - genuinely partial coordinate coverage (42/101, ~42%), not the
100% seen on every other Spanish/DATEX adapter in this SDK. The remaining
59 state their location purely via Alert-C codes
(``alertCLocationName``/``specificLocation``, not decoded, same policy as
elsewhere) and "reference points" (a road number plus a distance in
metres along it - captured as ``road_number``, the distance itself is not
on the shared model and stays in ``.raw``).

**Other real fields checked, one genuine gap left undecided, deliberately
not "fixed"**: ``impact/delays/delaysType`` (real values seen:
``"longDelays"``) sits under a different path than the shared model's
``impact_delay_band`` field (which reads ``delayBand`` directly) - so
``impact_delay_band`` comes out ``None`` for every real Euskadi record
checked (0/101). Not wired in: ``delayBand`` is itself unpopulated on
*every* other DATEX adapter checked in this SDK too (France: 0/158,
Spain: 0/378) - there's no cross-provider precedent for what values
belong there, so mapping a differently-named v1.0 field into it would be
a guess about equivalence, not a confirmed one. Reported here, not
silently dropped, but not merged into the shared model either. No
``generalPublicComment``/free-text comment exists on any real record
checked (0/119) - an honest gap, same shape as Belgium's.

**``administrativeArea`` - a real per-record province field, nested
three levels deep (``referencePointLinear``/``referencePoint``/
``administrativeArea``/``value``), not on the shared model** - the same
shape of gap DGT's own ``provinces()`` helper exists for. Real values
confirmed live across all three Basque provinces (``GIPUZKOA``,
``BIZKAIA``/``Bizkaia``, ``ARABA``/``Alava`` - genuinely inconsistent
casing across records, not normalised here, kept as stated) plus a real
literal placeholder, ``"Desconocida"`` (Spanish "unknown", 48/124 records
checked) - treated as unstated, not a real area name, by
:func:`provinces` below.

**CRS: WGS84, confirmed live from real point values** (e.g. lat ~43.19-
43.29, lon ~-2.17 to -2.43 - correct for the Basque Country; genuinely
projected-CRS values would read six figures, not two). No reprojection
question - the simplest CRS story alongside Bulgaria/Lithuania's siblings
so far, once the point is actually captured (see the parser fix above).

**Network scope: ``multi_authority_interurban``**, the same shape as
DGT's and SCT's own real data - real road numbers span the state network
(``N-634``, ``AP-1``, ``AP-8``, ``AP-68``) and the three Diputación Foral
networks (``GI-``/Gipuzkoa, ``BI-``/Bizkaia, and Araba's own, though no
real Araba-prefixed road number was seen in the pull checked), never
municipal streets.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Situation, SituationRecord
from .parser import iter_roadworks_full as _iter_roadworks_full
from .parser import iter_situations_full as _iter_situations_full

__all__ = ["BASE_URL", "SITUATION_PATH", "EuskadiClient", "provinces"]

BASE_URL = "https://infocar.dgt.es"
SITUATION_PATH = "datex2/dt-gv/SituationPublication/all/content.xml"

#: A real, literal placeholder value ("unknown" in Spanish) seen on many
#: real records - not a real province name, see module docstring.
_UNKNOWN_PROVINCE = "desconocida"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _province(record: SituationRecord) -> str | None:
    if record.raw is None:
        return None
    for element in record.raw.iter():
        if _local(element.tag) == "administrativeArea":
            for child in element:
                if _local(child.tag) == "value" and child.text:
                    text = child.text.strip()
                    if text and text.lower() != _UNKNOWN_PROVINCE:
                        return text
    return None


def provinces(situations: list[Situation]) -> dict[str, str]:
    """Map ``situation.id -> province name`` (e.g. ``"GIPUZKOA"``) for
    every roadworks situation that states a real one - pass the result to
    ``streetworks.common.from_datex2(situation, administrative_area=...)``,
    the same pattern as :func:`streetworks.datex2.dgt.provinces`. Casing
    is kept exactly as stated (confirmed live to be genuinely
    inconsistent - see module docstring), not normalised. The real literal
    ``"Desconocida"`` ("unknown") placeholder is treated as unstated, not
    a real area name."""
    result: dict[str, str] = {}
    for situation in situations:
        if not situation.roadworks:
            continue
        province = _province(situation.roadworks[0])
        if province:
            result[situation.id] = province
    return result


class EuskadiClient:
    """Fetch the Basque Country's national roadworks (Dirección de
    Tráfico del Gobierno Vasco, via Spain's national NAP). No credentials
    required.

    >>> from streetworks.datex2.euskadi import EuskadiClient, provinces
    >>> from streetworks.common import from_datex2
    >>> with EuskadiClient() as euskadi:
    ...     situations = list(euskadi.iter_roadworks())
    >>> basque_provinces = provinces(situations)
    >>> for situation in situations:
    ...     works = from_datex2(
    ...         situation, territory="Spain",
    ...         administrative_area=basque_provinces.get(situation.id),
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
        """``GET content.xml`` - the raw DATEX II v1.0 SituationPublication
        response body (all current Basque road situations)."""
        response = self._transport.request("GET", f"{self.base_url}/{SITUATION_PATH}")
        return response.content

    def iter_situations(self) -> Iterator[Situation]:
        yield from _iter_situations_full(io.BytesIO(self.get_situations()), provider="Euskadi")

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record (``MaintenanceWorks``/``ConstructionWorks`` -
        see module docstring)."""
        yield from _iter_roadworks_full(io.BytesIO(self.get_situations()), provider="Euskadi")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> EuskadiClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
