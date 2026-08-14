"""Austria (ASFINAG) roadworks - genuine DATEX II, credential-gated at the
data-pull layer only, the same shape as
:mod:`streetworks.datex2.vejdirektoratet`.

.. attention::
   **PENDING LIVE VERIFICATION.** This module is built against ASFINAG's
   own official dataset page on Austria's National Access Point
   (``mobilitaetsdaten.gv.at``) - not against a real authenticated data
   pull. No real Austrian ``Situation``/``SituationRecord`` response has
   been seen. **Less confirmed than Vejdirektoratet at the same stage**:
   Vejdirektoratet's protocol spec states its auth scheme (HTTP Basic)
   verbatim; no equivalent statement was found anywhere public for
   ASFINAG - checked the dataset page, its licence page, and the
   registration portal's own JS bundle, no mention of "API key"/"Token"/
   "Schlüssel" anywhere. The auth *mechanism*, not just the credential
   value, is genuinely unknown until someone registers.

**What's confirmed, from ASFINAG's own official dataset page** (*"Verkehrs­
meldungen zu geplanten Ereignissen (ASFINAG)"*,
``mobilitaetsdaten.gv.at/daten/verkehrsmeldungen-zu-geplanten-ereignissen-asfinag``,
checked live 2026-08-14): the dataset covers real event types
``Baustellen`` (roadworks), ``Instandhaltungsarbeiten`` (maintenance),
``Sanierungen`` (renovations), and pre-planned events (e.g. a triathlon)
on the ASFINAG motorway/expressway network - stated explicitly as
**DATEX II Situations with SituationRecords**
(*"Die Ereignis-Daten werden in diesem Datenprofil als DATEX II
Situations mit SituationRecords abgebildet"*), with real
"Geschwindigkeitstrichter" (speed funnels) and lane-guidance detail. Real
technical metadata stated on the page: format XML, interface HTTP/HTTPS,
update rate 1 minute, transfer mode pull. A sample filename is named
(``en_asfinag_plannedevents_v4_0_reduced.xml``) but not downloadable
without registration - the ``v4_0`` in that name is **not confirmed** to
mean DATEX II schema version 4 (no such public DATEX II version exists);
it more likely refers to ASFINAG's own dataset/profile versioning, left
unconfirmed rather than assumed either way.

**The investigation brief's own "check the open RSS first" question -
resolved, negatively, not just left open.** A real, genuinely keyless
public RSS/ATOM feed exists on the same NAP
(``mobilitaetsdaten.gv.at/en/daten/public-rss-feed-unplanned-and-safety-related-traffic-events-asfinag``)
- but its own page states explicitly *"This feed provides unplanned and
safety-related traffic events"*, filed under the NAP's own "Road events
and conditions" category, not "Road work information" (the roadworks
dataset's own category). **Confirmed live that this keyless route does
not carry roadworks** - there is no keyless shortcut for Austria,
unlike Italy's CCISS. Both DATEX-format and RSS-format routes exist on
this NAP; only the DATEX one covers ``Baustellen``.

**No hardcoded data URL, and no confirmed auth scheme - genuinely more
open than Vejdirektoratet.** The dataset page states access requires
registration via ASFINAG's own portal (``contentportal.asfinag.at``, a
real Angular SPA with "Anmelden"/"Registrieren" - Log in/Register -
links), but neither that page nor its licence terms nor its JS bundle
(read directly, the same technique that found Roma's/Lisboa's/Oslo's
real backends - here it found nothing, since the real API host is either
same-origin-relative and auth-gated, or genuinely not present in this
bundle) state the real pull URL or the credential mechanism. An older,
separately-documented API host (``services2.asfinag.at/web/trafficdata``,
found via web search, described in third-party mentions as offering "a
simply parameterized URL" per ``DATA_ITEM``) is **unreachable from this
build environment** (connection failure, not a slow response) - possibly
decommissioned in favour of the newer Content Portal, possibly a
regional/network access restriction; not resolved either way.
:class:`AsfinagClient` therefore takes ``base_url`` as a required
constructor argument (no module default) and, rather than guess a header
name or auth scheme, accepts a pre-configured ``httpx.Client`` (the same
``client=`` parameter every module in this SDK already exposes) so a
real registered user can wire in whatever auth their real credentials
turn out to need, once Phase 2 confirms it.

**Parser reuse hypothesis** (not yet confirmed against real Austrian
data): genuine DATEX II, so this module wires straight into the existing
shared :func:`~streetworks.datex2.parser.iter_situations` /
:func:`~streetworks.datex2.parser.iter_roadworks` - the same functions
NDW/Vegvesen/Vejdirektoratet use - rather than a new parse path, the same
call already made for Vejdirektoratet. Unconfirmed whether ASFINAG's
real response wraps a bare DATEX ``d2LogicalModel`` document directly or
some other envelope (a JSON wrapper, a list of strings, etc., the same
kind of thing Vejdirektoratet's own protocol doc had to spell out) -
:meth:`AsfinagClient.iter_situations` assumes a bare XML document body,
the simplest real-world shape, but this is a genuine Phase 2 unknown.

**Licence: CC-BY-4.0, confirmed live, with real supplementary
conditions beyond plain CC-BY - not glossed over.** Confirmed directly
from ASFINAG's own licence page
(``contentportal.asfinag.at/assets/licenses/cc-by-40-asf/de/cc-by-40-asf.html``):
the base licence is Creative Commons Attribution 4.0 International,
unmodified, but registration requires accepting real supplementary
conditions - you must disclose your own downstream services/products
built on this data back to ASFINAG (*"Bekanntgabe der Dienste"*), and
ASFINAG reserves the right to publicly reference your own trademark/name
when describing that it supplies you data (*"Nennung durch uns"*). A
real, genuine obligation beyond the bare CC-BY-4.0 grant, the same kind
of nuance already documented for Paris's ODbL share-alike clause.

**Credentials**: registration via `ASFINAG Content Portal
<https://contentportal.asfinag.at/>`_ (confirmed live and reachable);
the dataset page states *"Lizenz mit kostenloser Nutzung"* (free-use
licence), consistent with a self-service flow, but this hasn't been
walked through - whether it's genuinely self-service or requires manual
approval is itself unconfirmed. Env var placeholder:
``ASFINAG_BASE_URL`` (see ``.env.example``).

**``territory``/``administrative_area``**: pass ``territory="Austria"``
to :func:`~streetworks.common.from_datex2` (no DATEX feed states its own
country, same documented convention as every other DATEX adapter);
``administrative_area="ASFINAG"`` is reasonable (ASFINAG is Austria's
sole motorway/expressway operator, the same "operator IS the authority"
case Madrid/National Highways already use) but unconfirmed against a
real record's own fields.

**What's still open until Phase 2** (a real credentialed pull):

1. The real pull URL and auth mechanism - genuinely unknown, see above.
2. Whether the response body is a bare DATEX XML document or wrapped in
   some envelope.
3. Whether real Austrian data uses the standard DATEX
   ``ConstructionWorks``/``MaintenanceWorks`` roadworks vocabulary
   :data:`~streetworks.datex2.models.ROADWORKS_TYPES` already recognises,
   or needs its own discriminator the way Trafikverket's ``MessageType``
   did.
4. Real coordinate/location-referencing coverage and CRS - the dataset
   page states only the network scope (Austrian motorways/expressways),
   not a referencing method or CRS.
"""

from __future__ import annotations

import io
import warnings
from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Situation
from .parser import iter_roadworks as _iter_roadworks
from .parser import iter_situations as _iter_situations

__all__ = ["AsfinagClient"]

warnings.warn(
    "streetworks.datex2.austria is a Credentials-wanted scaffold: built to "
    "ASFINAG's own confirmed dataset description (see module docstring), "
    "not yet verified against a real authenticated response - and less "
    "confirmed than Vejdirektoratet at the same stage, since even the auth "
    "mechanism (not just the credential value) is unknown. Have ASFINAG "
    "Content Portal access for the 'Verkehrsmeldungen zu geplanten "
    "Ereignissen' dataset? Running the smoke test and reporting back one "
    "real trimmed record, the real pull URL shape, and the auth mechanism "
    "used would be the single most useful contribution - see the 'help "
    "wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues for exactly "
    "what's needed.",
    UserWarning,
    stacklevel=2,
)


class AsfinagClient:
    """Fetch Austrian roadworks from ASFINAG's Content Portal DATEX II
    pull. **Pending live verification - see module docstring, especially
    the real pull URL / auth mechanism being genuinely unconfirmed.**

    Requires ``base_url`` (the real per-dataset pull address issued at
    registration - there is no public default, see module docstring).
    Auth is deliberately not hardcoded - pass a pre-configured
    ``client=httpx.Client(...)`` with whatever ``auth=``/``headers=``
    your real registered credentials turn out to need.

    >>> from streetworks.datex2.austria import AsfinagClient
    >>> from streetworks.common import from_datex2
    >>> with AsfinagClient(base_url=base_url) as asfinag:  # doctest: +SKIP
    ...     for situation in asfinag.iter_roadworks():
    ...         works = from_datex2(situation, territory="Austria")
    """

    def __init__(
        self,
        *,
        base_url: str,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url:
            raise ValueError(
                "base_url is required - ASFINAG issues the real pull address "
                "at registration, see module docstring"
            )
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_situations_xml(self) -> bytes:
        """``GET`` the configured endpoint - assumes a bare DATEX XML
        document body, the simplest real-world shape; see module
        docstring for why this is a Phase 2 unknown, not a confirmed
        fact."""
        response = self._transport.request("GET", self.base_url)
        return response.content

    def iter_situations(self) -> Iterator[Situation]:
        xml_bytes = self.get_situations_xml()
        yield from _iter_situations(io.BytesIO(xml_bytes), provider="ASFINAG/Austria")

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at
        least one roadworks record."""
        xml_bytes = self.get_situations_xml()
        yield from _iter_roadworks(io.BytesIO(xml_bytes), provider="ASFINAG/Austria")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> AsfinagClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
