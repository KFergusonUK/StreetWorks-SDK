"""Norway (Statens vegvesen) roadworks - DATEX II v3, over the snapshotPull
SOAP/REST interface.

.. attention::
   **PENDING LIVE VERIFICATION.** Everything in this module is built against
   Statens vegvesen's own WSDL/service catalogue (probed live, credential-
   free) plus a real, live, *non-Norwegian* DATEX snapshotPull response used
   to validate the parser-reuse hypothesis - see "What's verified" and
   "What's still open" below. No Norwegian ``GetSituation`` response has
   been seen. Registration for API access is submitted; this client is not
   confirmed correct against real Norwegian data and should not be treated
   as production-ready until Phase 2 (a live credentialed pull) confirms it.

**Endpoint** (probed live, 2026-07): Statens vegvesen runs a DATEX II v3.1
snapshotPull server at ``datex-server-get-v3-1.atlas.vegvesen.no``, exposing
roadworks as the ``GetSituation`` operation, both as SOAP
(``pullSnapshotData``, WSDL confirmed at ``GetSituation?wsdl``, namespace
``http://datex2.eu/wsdl/snapshotPull/2020``) and as a REST-style companion
path, ``GetSituation/pullsnapshotdata`` - this client uses the latter (a
plain ``GET``, no SOAP envelope to construct). The unauthenticated service
catalogue at ``/datexapi/`` lists this and eleven other ``GetXxx`` operations
(VMS, CCTV, weather, travel time) - only ``GetSituation`` is roadworks-
relevant.

**Auth**: confirmed live via a direct probe of the REST path - a bare
request gets ``401 Unauthorized`` with *both* ``WWW-Authenticate: Basic
realm="Access to datex2/prod-1"`` and ``WWW-Authenticate: Bearer
realm="Access to datex2/prod-1"`` challenge headers, so this client accepts
either ``username``/``password`` (HTTP Basic) or ``token`` (Bearer) -
mutually exclusive, same pattern as
:class:`~streetworks.datavia.DataViaClient`. No credentials were available
to confirm which scheme Statens vegvesen's actual issued credentials use -
that's Phase 2 (also possibly stated in whatever registration confirmation
arrives with the credentials).

**Parser reuse hypothesis** (the brief's primary hypothesis, not yet
confirmed against real Norwegian data): this module wires straight into the
existing shared :func:`~streetworks.datex2.parser.iter_situations` /
:func:`~streetworks.datex2.parser.iter_roadworks` - the same functions NDW
uses - rather than writing a new parse path, since the WSDL confirms this is
standard DATEX II ``SituationPublication`` (not a bespoke JSON schema like
National Highways or Digitraffic). **Partially validated already**: no real
Norwegian sample was obtainable (Statens vegvesen's own reference repo,
``vegvesen/datex-client``, is archived since 2021 and only demonstrates
weather-station data; the official DATEX-II-EU ``UF2024-Hands-On-Journey``
training repo confirms the SOAP envelope/``snapshotPull`` wrapper shape but
only with a placeholder ``PublicEvent`` example, no real roadworks record).
That same training repo's Python client pointed at a **live, unauthenticated
DATEX II v3 snapshotPull server run by Iceland's road authority (IRCA)** -
the identical ``snapshotPull``/``SituationPublication`` v3 interface, same
WSDL namespace, same reference tooling lineage, but genuinely a different
country's implementation, not Norway's. Fetching it returned a real,
populated response (62 situations, real ``MaintenanceWorks`` records, real
validity dates, real ``PointLocation`` geometry via
``pointByCoordinates``/``latitude``+``longitude`` - the identical shape
NDW's own fixture uses). The trimmed fixture in this repo
(``tests/fixtures/vegvesen_getsituation_sample.xml``) is **two real
situations from that Iceland response**, wrapped in the real SOAP envelope
it actually arrived in (``s:Envelope``/``s:Body``/``pullSnapshotDataOutput``/
``payload``) - used here to confirm ``iter_situations`` parses a genuine
SOAP-wrapped snapshotPull document unchanged (it matches purely on local
element names, so the SOAP envelope, ``pullSnapshotDataOutput`` wrapper, and
even the unfamiliar root elements are all transparently ignored - confirmed
by running this exact fixture through the parser with zero code changes).
**This shows the plumbing works on a structurally-identical document, not
that Norway's own feed matches Iceland's** - Norway could still differ in
DATEX version, in which optional fields it populates, or in using a location
referencing method Iceland's sample didn't exercise (see below).

**Location handling** (per the brief): only ``pointCoordinates`` (WGS84,
``EPSG:4326``) is read for geometry, via the already-shared
:func:`~streetworks.datex2.parser._parse_location` - no code changes needed,
it already does this for NDW/the Iceland fixture. Alert-C location
references are deliberately **not** decoded into geometry anywhere in this
SDK; only the human-readable name is preserved, in
``Location.alert_c_location`` - this is the existing, shared behaviour, not
something added for Norway. NVDB (the Norwegian road database) linear
references are a *different*, Norway-specific location-referencing method
that the shared parser has no knowledge of, and no real Norwegian record has
been seen to learn its actual field shape - see "What's still open" below;
:data:`NVDB_BASE_URL` is recorded here (confirmed live, credential-free,
2026-07) as a starting point for Phase 2, not because any resolution code
exists yet. Writing a resolver against a guessed field shape would mean
fabricating a mapping this SDK's whole design discipline exists to avoid.

**``.raw``**: because this hypothesis reuses the streaming XML parser
unchanged, :attr:`~streetworks.datex2.models.Situation.raw` /
:attr:`~streetworks.datex2.models.SituationRecord.raw` stay ``None`` for
Norway too - the same documented memory-bounding trade-off NDW already has
(see :mod:`streetworks.datex2.models`). Whether that trade-off is actually
warranted for Norway - a single credentialed snapshot pull, not NDW's
~170 MB national open-data dump - is unconfirmed until Phase 2 shows the
real response size; if it turns out to be small, a non-streaming parse path
that preserves ``.raw`` may be worth adding then.

**``territory``/``administrative_area``**: pass ``territory="Norway"`` to
:func:`~streetworks.common.from_datex2` (no DATEX feed states its own
country, same documented convention as every other DATEX adapter).
``administrative_area`` has **no confirmed source field yet** - unlike
Finland's ``province`` or NDW's ``source_name``, no real Norwegian record has
been inspected to know whether one exists, so it defaults to ``None``
(``from_datex2``'s own default, since ``source_name`` isn't confirmed to be
an authority name here either) until Phase 2 confirms a genuinely-stated
region field. ``source_grade`` is
:attr:`~streetworks.common.SourceGrade.OPERATOR`, matching every DATEX
adapter.

**Attribution**: data from this service is published under the `Norwegian
Licence for Open Government Data (NLOD)
<https://data.norge.no/nlod/en/2.0>`_ - cite "Norwegian Public Roads
Administration (Statens vegvesen)" per NLOD's attribution requirement
wherever Norwegian roadworks data from this module is displayed or
redistributed.

**What's still open until Phase 2** (a real credentialed pull):

1. The exact DATEX version actually served (WSDL says v3.1; the roadworks
   *profile* details - which optional elements Norway populates - are
   unconfirmed).
2. Whether the existing shared parser handles a real Norwegian response
   unchanged, or needs adjustment (e.g. for an NVDB-specific location
   extension the Iceland fixture didn't exercise).
3. What location referencing method real Norwegian roadworks records
   actually carry - ``pointCoordinates``, NVDB linear refs, Alert-C, or a
   mix - the brief anticipates NVDB refs are common, but this is unconfirmed.

A fourth item surfaced while building this fixture and has since been
**fixed**, not just noted: the Iceland sample's ``generalPublicComment``
lists an *empty* ``lang="en"`` value before the real ``lang="is"`` text, and
the shared parser's :func:`~streetworks.datex2.parser._multilingual` used to
take the *first* ``value`` regardless of language or emptiness, so
``comments`` came back empty for both fixture records despite real Icelandic
text being present. That was a genuine bug affecting every DATEX provider
with this value ordering, not a Norway-specific quirk - fixed in
:func:`~streetworks.datex2.parser._multilingual` (skips empty entries, takes
the first non-empty one) alongside shipping
:mod:`streetworks.datex2.irca` (Iceland), which is what surfaced it. This
fixture's comments are now correctly populated - see
``tests/test_vegvesen.py``.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Situation
from .parser import iter_roadworks as _iter_roadworks
from .parser import iter_situations as _iter_situations

__all__ = ["BASE_URL", "NVDB_BASE_URL", "VegvesenClient"]

BASE_URL = "https://datex-server-get-v3-1.atlas.vegvesen.no"
_SITUATION_PATH = "datexapi/GetSituation/pullsnapshotdata"

#: NVDB API Les (the Norwegian road database's read API) - confirmed live,
#: credential-free (200 OK on a real query, 2026-07). Recorded for Phase 2's
#: lazy/optional linear-reference resolution once a real Norwegian
#: situationRecord shows what field actually carries an NVDB reference; no
#: resolution code exists yet - see module docstring.
NVDB_BASE_URL = "https://nvdbapiles.atlas.vegvesen.no"


class VegvesenClient:
    """Fetch Norwegian roadworks from Statens vegvesen's DATEX II snapshotPull
    service. **Pending live verification - see module docstring.**

    Requires credentials (HTTP Basic or Bearer - whichever Statens vegvesen
    issues; unconfirmed until Phase 2). Provide exactly one of
    ``username``+``password`` or ``token``.

    >>> from streetworks.datex2.vegvesen import VegvesenClient
    >>> from streetworks.common import from_datex2
    >>> with VegvesenClient(token=token) as vegvesen:  # doctest: +SKIP
    ...     for situation in vegvesen.iter_roadworks():
    ...         works = from_datex2(situation, territory="Norway")
    """

    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        basic = username is not None and password is not None
        bearer = token is not None
        if basic == bearer:
            raise ValueError(
                "Provide either username+password (HTTP Basic) or token "
                "(Bearer), not both/neither"
            )
        self.base_url = base_url.rstrip("/")
        auth = httpx.BasicAuth(username, password) if basic else None
        headers = {"Authorization": f"Bearer {token}"} if bearer else None
        client = client or httpx.Client(
            timeout=timeout, follow_redirects=True, auth=auth, headers=headers
        )
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_situations(self) -> bytes:
        """``GET GetSituation/pullsnapshotdata`` - the raw DATEX II XML
        response body. Response wrapper shape (bare ``messageContainer`` vs.
        a SOAP envelope) is unconfirmed for this REST-style path until
        Phase 2 - :meth:`iter_situations` handles either, since the shared
        parser matches on local element names regardless of wrapper (see
        module docstring)."""
        response = self._transport.request("GET", f"{self.base_url}/{_SITUATION_PATH}")
        return response.content

    def iter_situations(self) -> Iterator[Situation]:
        yield from _iter_situations(io.BytesIO(self.get_situations()))

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record (``MaintenanceWorks``/``ConstructionWorks``)."""
        yield from _iter_roadworks(io.BytesIO(self.get_situations()))

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> VegvesenClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
