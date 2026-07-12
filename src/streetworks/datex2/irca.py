"""Iceland (IRCA / Vegagerðin) roadworks - DATEX II v3, snapshotPull, no
credentials required.

The Icelandic Road and Coastal Administration (IRCA, part of Vegagerðin -
the Icelandic Road and Coastal Administration) has published road
conditions and situations as DATEX II v3 since March 2021
(https://datex2.eu/2021/04/14/datex-ii-in-iceland/). This module targets the
"Point Incidents" service (``SituationPublication`` - roadworks and other
point situations), one of five services documented at
https://www.vegagerdin.is/vegagerdin/gagnasafn/vefthjonustur/datexii-2.

**Confirmed live, credential-free, 2026-07** (fresh probes, not a one-off):
a bare SOAP ``pullSnapshotData`` request against
``https://datex.vegagerdin.is/situationpublication3_1/SituationService``
succeeds with **no authentication, no API key, no IP allow-listing** -
unlike Norway/Vegvesen (see :mod:`streetworks.datex2.vegvesen`, which needs
credentials and is pending live verification), Iceland's service is fully
open, so this adapter ships complete, not phased.

**``SOAPAction`` is mandatory**: a request without the correct
``SOAPAction`` header gets a live ``500`` SOAP fault ("No operation found
for specified action") - confirmed by triggering it. The correct value,
read from the live WSDL rather than guessed, is
:data:`~streetworks.datex2._snapshotpull.SOAP_ACTION`. This client shares
that request-construction logic with
:mod:`streetworks.datex2._snapshotpull`, since Norway's server exposes the
identical WSDL operation - see that module's docstring for why Norway's own
client doesn't (yet) use it.

**Parser reuse, verified (not just hypothesised, unlike Norway)**: this
module wires into the existing shared field-extraction logic via
:func:`~streetworks.datex2.parser.iter_situations_full` /
:func:`~streetworks.datex2.parser.iter_roadworks_full` - confirmed against
three independent live fetches (61-62 real situations each) that the SOAP
envelope wrapper is transparent to the parser (it matches on local element
names only) and that field extraction (validity dates, ``PointLocation``
via ``pointByCoordinates``, comments) works correctly. Unlike NDW/Norway,
this uses the ``_full`` (whole-document, non-streaming) variant rather than
:func:`~streetworks.datex2.parser.iter_situations` - Iceland's response is
~250 KB, nowhere near the scale that streaming/clearing exists for, so
there's no reason to give up ``.raw`` fidelity here (see below).

**Field-by-field, verified against real data**:

* ``record_type`` is genuinely ``xsi:type`` (``MaintenanceWorks`` - 25 of 61
  situations on one live fetch, 25 of 62 on another) - a real discriminator,
  not a compromise, unlike Digitraffic's hardcoded value.
* ``Location.points`` is always ``PointLocation``/``pointByCoordinates``
  (WGS84 lat/lon) - checked across every situation on two independent live
  fetches (0 ``LinearLocation``, 0 ``posList``). Some records also carry an
  ``openlrPointLocationReference`` (OpenLR, not Alert-C) - not decoded into
  geometry, consistent with this SDK's standing rule for any location-code
  referencing method, and not currently surfaced on :class:`Location` at
  all (no field for it - OpenLR wasn't anticipated by the shared model,
  and this feed's ``pointCoordinates`` already gives precise geometry
  directly, so nothing is lost by not decoding it).
* ``road_maintenance_type`` is a real, always-``"roadworks"`` value on every
  ``MaintenanceWorks`` record seen (25/25, both fetches) - genuinely stated,
  just low-cardinality in this feed, not a hardcode.
* No ``<source>`` element appears on any record inspected - ``source_name``
  stays ``None`` for every Iceland-derived record.
* **``.raw`` is populated** on both ``Situation`` and ``SituationRecord``
  - the source ``Element`` for each. Unlike NDW/Norway (which stream and
  clear elements to bound memory on huge feeds, so ``.raw`` stays ``None``
  there - see :mod:`streetworks.datex2.models`), Iceland's ~250 KB response
  is small enough to parse fully into memory without that trade-off, via
  :func:`~streetworks.datex2.parser.iter_situations_full`.
* **No administrative_area-equivalent field exists anywhere in this
  feed** - checked exhaustively (every unique element local name across a
  full live fetch): no region/authority/municipality/district/county
  element of any kind. ``publicationCreator`` states only
  ``country=IS``/``nationalIdentifier=IRCA`` - a national identifier, not a
  sub-national one. So ``administrative_area`` is left unset (``None``),
  never inferred, matching this SDK's standing discipline.
* The multilingual-comments bug (empty ``lang="en"`` placeholder listed
  before the real ``lang="is"`` text) that this provider's real data
  originally surfaced is now fixed in the shared parser - see
  :func:`~streetworks.datex2.parser._multilingual`.

``territory``/``administrative_area`` (see
:mod:`streetworks.common.from_datex2`): pass ``territory="Iceland"`` (no
DATEX feed states its own country as a territory name; ``IS`` is available
via ``publicationCreator`` but this adapter doesn't currently surface it as
a distinct field - same documented caller-supplies-it convention as every
other DATEX adapter). No ``administrative_area`` - see above.
``source_grade`` is :attr:`~streetworks.common.SourceGrade.OPERATOR`,
matching every DATEX adapter.

**Licence and attribution** (confirmed live,
https://www.vegagerdin.is/vegagerdin/gagnasafn/vefthjonustur/terms-and-conditions):
IRCA/Vegagerðin's data is published under a licence granting "a perpetual
licence to use the information anywhere you want free of charge",
permitting copying, publishing, distribution, transmission, and commercial
exploitation. Attribution is **mandatory** - the required wording, verbatim
from the licence, is:

    Based on information provided by the Icelandic Road and Coastal
    Administration (IRCA)

Cite this wherever Icelandic roadworks data from this module is displayed
or redistributed.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from ._snapshotpull import pull_snapshot
from .models import Situation
from .parser import iter_roadworks_full as _iter_roadworks_full
from .parser import iter_situations_full as _iter_situations_full

__all__ = ["BASE_URL", "SITUATION_ENDPOINT", "IcelandClient"]

BASE_URL = "https://datex.vegagerdin.is"
SITUATION_ENDPOINT = f"{BASE_URL}/situationpublication3_1/SituationService"


class IcelandClient:
    """Fetch Icelandic roadworks from IRCA/Vegagerðin's DATEX II snapshotPull
    service. No credentials required.

    >>> from streetworks.datex2.irca import IcelandClient
    >>> from streetworks.common import from_datex2
    >>> with IcelandClient() as irca:
    ...     for situation in irca.iter_roadworks():
    ...         works = from_datex2(situation, territory="Iceland")
    """

    def __init__(
        self,
        *,
        endpoint_url: str = SITUATION_ENDPOINT,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_situations(self) -> bytes:
        """POST the ``pullSnapshotData`` SOAP request and return the raw
        DATEX II XML response body."""
        return pull_snapshot(self._transport, self.endpoint_url)

    def iter_situations(self) -> Iterator[Situation]:
        """Parses the whole (small, ~250 KB) response into memory at once,
        not streaming - so ``.raw`` is populated on every ``Situation``/
        ``SituationRecord`` (unlike NDW/Norway's streaming parser)."""
        yield from _iter_situations_full(io.BytesIO(self.get_situations()))

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record (``MaintenanceWorks``/``ConstructionWorks``)."""
        yield from _iter_roadworks_full(io.BytesIO(self.get_situations()))

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> IcelandClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
