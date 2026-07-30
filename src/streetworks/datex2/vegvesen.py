"""Norway (Statens vegvesen) roadworks - DATEX II v3, over the snapshotPull
SOAP/REST interface.

.. attention::
   **PHASE 2 CONFIRMED (2026-07-30). The mixed-CRS geometry finding below
   is now resolved, not just documented.** Verified against a real
   authenticated pull, by a tester running ``scripts/smoke_test.py`` with
   real HTTP Basic credentials: 844 real Norwegian roadworks situations,
   real ``MaintenanceWorks`` records, real Norwegian-language comments,
   real road numbers (e.g. ``E18``). The parser-reuse hypothesis holds -
   the shared streaming parser handles the real response with zero code
   changes. **Real coordinates are genuinely mixed CRS within the same
   feed** - roughly 76% UTM zone 33N (``EPSG:25833``, confirmed via a real
   ``srsName="25833"`` attribute), roughly 24% genuine WGS84 - but every
   point now carries an honest, individually-resolved CRS: use
   :func:`streetworks.common.from_vegvesen.from_vegvesen` (not
   :func:`~streetworks.common.from_datex2.from_datex2` directly), which
   resolves each record's declared ``srsName`` plus its own coordinate
   value range via
   :func:`~streetworks.common._crs.resolve_coordinate_crs` - see "The
   mixed-CRS finding: resolved" below and :mod:`streetworks.common._crs`
   for the resolution rule (axis order decided by magnitude, never
   declared/positional order; no silent reprojection anywhere).

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

**Auth**: HTTP Basic (``username``/``password``) confirmed correct against
real issued credentials - the endpoint also accepted a bare probe's
``WWW-Authenticate: Bearer`` challenge, so ``token`` is still accepted as
an alternative (mutually exclusive with Basic, same pattern as
:class:`~streetworks.datavia.DataViaClient`), but only Basic has actually
been exercised against real data.

**Parser reuse hypothesis - confirmed correct.** This module wires
straight into the existing shared
:func:`~streetworks.datex2.parser.iter_situations` /
:func:`~streetworks.datex2.parser.iter_roadworks` - the same functions
NDW uses - rather than a new parse path, since real Norwegian data really
is standard DATEX II ``SituationPublication``. Real Phase 1 groundwork
(a real Iceland IRCA response proving the plumbing on a
structurally-identical document, still the source of
``tests/fixtures/vegvesen_getsituation_sample.xml``) turned out to
predict Norway's own shape correctly: zero code changes were needed to
parse the real Norwegian pull.

**Confirmed live**: genuine DATEX II **v3** (``modelBaseVersion="3"``,
real namespaces matching NDW/Iceland's own) - settling the "v3.1 vs
data.norge.no's v2.0 catalogue claim" discrepancy in v3's favour. The
real REST-path response wrapper is a **bare** ``<messageContainer>``, not
a SOAP envelope (the Iceland fixture's own SOAP wrapper was a red
herring for this specific path - the shared parser tolerates either,
since it matches on local element names regardless of wrapper, but
Norway's own real shape is simpler). ``publicationCreator/
nationalIdentifier`` is real ``"NPRA"``; each situation's own ``source/
sourceName`` is too. Real comments are genuinely Norwegian-language
(e.g. ``"Vegarbeid, to påvirkede kjørefelt."`` - "Roadwork, two affected
lanes"), and real road numbers are populated (e.g. ``E18``). A previously
undocumented real location-referencing wrapper, ``LocationGroupByList``,
appears throughout - the shared parser handles it transparently (it
searches for ``pointCoordinates`` anywhere in the subtree, regardless of
wrapper), so this needed no code change either.

**The mixed-CRS finding: resolved.** Checked directly against 844 real
roadworks records in one live pull: ``location.point`` values split
roughly 76% in UTM-range (large values like ``(263598.322,
6640985.828)``) and roughly 24% in genuine WGS84 range. A real
``srsName="25833"`` attribute confirms the UTM values are ETRS89/UTM zone
33N (``EPSG:25833``); a separate real situation's ``pointCoordinates``
carried plain WGS84 latitude/longitude with no ``srsName`` override at
all. **This is not the Belgium/Lithuania shape** (a single provider-wide
CRS override via ``from_datex2(crs=...)``) - no single ``crs=`` value is
correct for the whole feed, since it genuinely varies per record.

A follow-up diagnostic pass (a raw regex scan of a real pull, independent
of this SDK's own parser) pinned the mechanism precisely: of 2,636 real
coordinate elements, all 2,133 ``gmlLineString``-sourced ones carry
``srsName="25833"`` with zero exceptions, and all 503
``pointCoordinates``-sourced ones sit in genuine WGS84 range with zero
``srsName`` ever present - two clean, non-overlapping encodings, not a
mislabelling problem. :attr:`~streetworks.datex2.models.Location.srs_name`
now captures this declaration (:mod:`streetworks.datex2.parser`), and
:func:`~streetworks.common._crs.resolve_coordinate_crs` resolves each
record's real CRS from that declaration plus its own coordinate value
range (UTM northing/easting vs. WGS84 lat/lon bands specific to Norway),
deciding axis order by magnitude rather than trusting declared/positional
order (confirmed live: the ``posList`` path states raw
easting-then-northing, the opposite convention from
``pointCoordinates``'s explicit lat-then-lon). Use
:func:`streetworks.common.from_vegvesen.from_vegvesen`, which pre-supplies
this candidate list - calling ``from_datex2()`` directly still works but
falls back to a single ``crs=`` guess, the old, wrong behaviour, since it
doesn't know Norway's candidates unless you pass ``crs_candidates=``
yourself. Resolution status (declared/inferred/corrected) is deliberately
not stored on ``Coordinate`` - it's real, useful information, but kept as
telemetry only (logs, this module's ``scope_note``, ``smoke_test.py``
output), never on the canonical model; see :mod:`streetworks.common._crs`
for why.

A second, independent bug surfaced while fixing this: 8/842 real
roadworks records in one pull had **both** a precise ``gmlLineString``
line and a redundant ``pointCoordinates`` convenience point in the same
location group - the old parser concatenated them into one ``points``
tuple, silently mixing UTM and WGS84 values as if they were adjacent line
vertices. Fixed in :mod:`streetworks.datex2.parser`: the two are now
mutually exclusive, the line winning when both are present (see
:class:`~streetworks.datex2.models.Location`'s own docstring).

**Location handling**: ``pointCoordinates`` (for ``PointLocation``) or the
first vertex of a ``gmlLineString``/``posList`` (for ``LinearLocation`` -
confirmed live on a real bridge-works record with no ``pointCoordinates``
at all) is read for geometry, via the already-shared
:func:`~streetworks.datex2.parser._parse_location` - confirmed live to
extract a value for every one of 844 real roadworks records (0 missing
points), though see the CRS finding above for what that value actually
means - both extraction paths are equally subject to it. Alert-C location
references are deliberately
**not** decoded into geometry anywhere in this SDK; only the
human-readable name is preserved, in ``Location.alert_c_location`` - the
existing, shared behaviour, not something added for Norway. **NVDB
external references are real and confirmed present**
(``externalReferencingSystem`` values ``NVDB;SOURCEDATE`` and
``NVDB;POINT;ROADWAY``, e.g. a real ``externalLocationCode``
``"885428;0.999781861373312;BOTH"``), but still not resolved into
geometry - the shared parser doesn't read ``externalReferencing`` at
all, and the real field shape (a composite string, semicolon-delimited)
isn't confidently decoded here yet. :data:`NVDB_BASE_URL` remains
recorded as a starting point for that future work, not because
resolution code exists.

**``.raw``**: because this hypothesis reuses the streaming XML parser
unchanged, :attr:`~streetworks.datex2.models.Situation.raw` /
:attr:`~streetworks.datex2.models.SituationRecord.raw` stay ``None`` for
Norway too - the same documented memory-bounding trade-off NDW already
has (see :mod:`streetworks.datex2.models`). **Confirmed warranted, not
just theoretical**: a real full snapshot pull is ~24 MB - the same order
of magnitude as NDW's own feed, not a small single-credential response -
so the streaming trade-off is a real, justified choice here too, not
overcautious.

**``territory``/``administrative_area``**: pass ``territory="Norway"`` to
:func:`~streetworks.common.from_datex2` (no DATEX feed states its own
country, same documented convention as every other DATEX adapter).
``administrative_area`` **still has no confirmed regional-subdivision
field** - real ``source/sourceName`` is populated (``"NPRA"``,
confirmed live), but that's the same national operator every situation
carries, not a per-record region the way Finland's ``province`` is, so
promoting it would misrepresent a national value as a regional one. Left
``None`` still. ``source_grade`` is
:attr:`~streetworks.common.SourceGrade.OPERATOR`, matching every DATEX
adapter.

**Attribution**: data from this service is published under the `Norwegian
Licence for Open Government Data (NLOD)
<https://data.norge.no/nlod/en/2.0>`_ - cite "Norwegian Public Roads
Administration (Statens vegvesen)" per NLOD's attribution requirement
wherever Norwegian roadworks data from this module is displayed or
redistributed.

**Credentials**: free; request access to the "Road traffic information"
publication (nationwide - roadworks, closures, accidents, weather events)
at
`vegvesen.no/en/fag/technology/open-data/a-selection-of-open-data/what-is-datex/get-access
<https://www.vegvesen.no/en/fag/technology/open-data/a-selection-of-open-data/what-is-datex/get-access/>`_.
Registration issues a **username and password** (HTTP Basic) - confirmed
correct, see "Auth" above; ``token``/Bearer remains available but
untested. Env vars: ``VEGVESEN_USERNAME``/``VEGVESEN_PASSWORD`` or
``VEGVESEN_TOKEN`` (see ``.env.example``, ``scripts/smoke_test.py``).

**The version discrepancy is resolved: v3, not v2.0.** This module
targeted v3.1 (confirmed live at ``BASE_URL``); data.norge.no's own
service catalogue still describes Statens vegvesen's DATEX offering as
v2.0 with legacy services running in parallel, but the real credentialed
pull's own ``modelBaseVersion="3"`` attribute settles which one real
issued credentials actually land on.

**What's still open** (not blocking - this module is Phase 2 confirmed,
but these remain genuinely unresolved):

1. Resolving real NVDB ``externalReferencing`` values (confirmed present,
   see above) into usable geometry or a linear reference - the composite
   string shape (e.g. ``"885428;0.999781861373312;BOTH"``) is observed,
   not confidently decoded.
2. Bearer/token auth remains untested - only Basic has been exercised
   against real issued credentials.
3. The roadworks *profile* details - exactly which optional DATEX
   elements Norway populates beyond what's listed above - checked only
   incidentally, not exhaustively, across the 844 real records seen.

The mixed-CRS geometry problem that used to top this list is **fixed**,
not open - see "The mixed-CRS finding: resolved" above.

A separate item surfaced while building this module's original fixture
has since been **fixed**, not just noted: the Iceland sample's
``generalPublicComment`` lists an *empty* ``lang="en"`` value before the
real ``lang="is"`` text, and the shared parser's
:func:`~streetworks.datex2.parser._multilingual` used to take the *first*
``value`` regardless of language or emptiness, so ``comments`` came back
empty for both fixture records despite real Icelandic text being
present. That was a genuine bug affecting every DATEX provider with this
value ordering, not a Norway-specific quirk - fixed in
:func:`~streetworks.datex2.parser._multilingual` (skips empty entries,
takes the first non-empty one) alongside shipping
:mod:`streetworks.datex2.irca` (Iceland), which is what surfaced it.
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
    service. **Phase 2 confirmed - see module docstring, including the now-
    resolved mixed-CRS geometry finding.**

    Requires credentials (HTTP Basic - confirmed correct; or Bearer,
    untested). Provide exactly one of
    ``username``+``password`` or ``token``.

    >>> from streetworks.datex2.vegvesen import VegvesenClient
    >>> from streetworks.common import from_vegvesen
    >>> with VegvesenClient(token=token) as vegvesen:  # doctest: +SKIP
    ...     for situation in vegvesen.iter_roadworks():
    ...         works = from_vegvesen(situation)
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
        yield from _iter_situations(io.BytesIO(self.get_situations()), provider="Vegvesen/Norway")

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record (``MaintenanceWorks``/``ConstructionWorks``)."""
        yield from _iter_roadworks(io.BytesIO(self.get_situations()), provider="Vegvesen/Norway")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> VegvesenClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
