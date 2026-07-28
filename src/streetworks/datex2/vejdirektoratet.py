"""Denmark (Vejdirektoratet / Dataudveksleren) roadworks - genuine DATEX II
3.2, credential-gated at the data-pull layer only.

.. attention::
   **PENDING LIVE VERIFICATION.** This module is built against
   Vejdirektoratet's own protocol documentation (the "Fælles TRACÉ
   Protokolbeskrivelse," a detailed technical spec - see "What's confirmed"
   below) and a real, live, credential-free fetch of the open metadata
   catalogue - not against a real authenticated data pull. No real Danish
   ``trafikmeldinger`` response has been seen. Better-confirmed than
   :mod:`streetworks.datex2.vegvesen` was at the same stage (the schema
   version, record types, and enumerated work-type values are all confirmed
   from Vejdirektoratet's own spec document, not inferred), but still not
   production-ready until Phase 2 (a real credentialed pull) confirms the
   parser-reuse hypothesis below.

**What's confirmed, from Vejdirektoratet's own protocol spec**: real DATEX
II v3.2 ``sit:SituationRecord`` types, explicitly enumerated (not a bare
presence check) - ``sit:ConstructionWorks`` and ``sit:MaintenanceWorks``
(both roll up to a ``Roadworks`` class in the spec's own class diagram),
with real ``constructionWorkType`` (``constructionWork``,
``demolitionWork``, ``roadImprovementOrUpgrading``, ``roadWideningWork``)
and ``roadMaintenanceType`` (``clearanceWork``, ``installationWork``,
``maintenanceWork``, ``overheadWorks``, ``repairWork``, ``resurfacingWork``,
``roadsideWork``, ``roadworks``, ``saltingInProgress``,
``snowploughsInUse``, ``treeAndVegetationCuttingWork``) values listed. This
is genuine, standard DATEX II vocabulary - :data:`~streetworks.datex2.models.ROADWORKS_TYPES`
and :attr:`~streetworks.datex2.models.SituationRecord.is_roadworks` apply
unchanged, no Denmark-specific discriminator logic needed (unlike Sweden -
see :mod:`streetworks.datex2.trafikverket`).

**Two parallel transports**, both documented in their own protocol PDFs:
AMQP push (each ``sit:Situation`` sent individually on creation/update,
DATEX XML carried in an AMQP ``Bare Message``'s ``application-data``
field) and REST pull (``HTTP GET``, response body a ``trafikmeldinger``
list of DATEX II XML strings). **This module targets REST pull only** - no
AMQP client exists in this SDK, and a national roadworks polling use case
fits REST better than a persistent AMQP subscription.

**Parser reuse hypothesis** (not yet confirmed against real Danish data):
genuine DATEX II XML, so this module wires straight into the existing
shared :func:`~streetworks.datex2.parser.iter_situations` /
:func:`~streetworks.datex2.parser.iter_roadworks` - the same functions
NDW/vegvesen use - rather than writing a new parse path. Unconfirmed
whether the REST response's ``trafikmeldinger`` wrapper (a list of DATEX
XML *strings*, per the protocol doc, not one bare XML document) needs
unwrapping/concatenation before the shared parser can consume it - see
:meth:`VejdirektoratetClient.iter_situations`, which handles the
documented "list of XML string" shape by parsing each entry separately;
whether real responses actually nest this way is exactly a Phase 2 item.

**No hardcoded data URL.** Unlike every other DATEX adapter in this SDK,
Vejdirektoratet issues the actual per-dataset REST pull address **during
registration**, not as a single public constant (confirmed: the protocol
doc and the catalogue both stop at "configured in DU [Dataudveksleren]
when the dataset is set up" - no public data endpoint exists to probe).
:class:`VejdirektoratetClient` therefore takes ``base_url`` as a required
constructor argument, not a module default - see ``VEJDIREKTORATET_URL``
in ``.env.example``.

**Auth**: HTTP Basic, confirmed directly from the protocol doc's own
words: *"En request skal bruge HTTP Basic Authentication for at godkendes
og må kun sendes over HTTPS... username og password konfigureres i DU ved
opsætning af datasæt"* ("A request must use HTTP Basic Authentication to
be authorised and may only be sent over HTTPS... username and password
are configured in DU when the dataset is set up.") - both the scheme and
the fact that credentials are per-dataset, not global, are stated
verbatim, not inferred.

**The open catalogue is genuinely open** - confirmed live (2026-07):
``GET https://businessservice.dataudveksler.app.vd.dk/api/Metadata?format=dcat``
returns all 196 registered datasets, DCAT/RDF-XML, no credential. The
specific roadworks dataset ("OOV2 Trafikmeldinger", id 222) is present and
tagged ``mobilitydcatap:mobilityTheme`` = ``road-work-information`` /
``short-term-road-works`` / ``long-term-road-works``, with
``mobilitydcatap:mobilityDataStandard`` = ``datex-II`` and
``dct:license`` = ``CC_BY_4_0`` (this dataset's own coded licence field -
other datasets in the same catalogue carry different licences, e.g.
``CC_BYNC_4_0``, so this was confirmed per-dataset, not assumed from the
catalogue in general). This confirms the roadworks dataset's existence,
theme, standard, and licence live - only the actual data pull remains
credential-gated.

**Credentials**: registration via `Dataudveksleren
<https://du-portal-ui.dataudveksler.app.vd.dk/>`_ (confirmed live, both
``du.vd.dk``/``nap.vd.dk`` redirect here). Registration issues **HTTP
Basic Auth username/password, configured per dataset**, plus the actual
REST pull URL for that dataset (see "No hardcoded data URL" above). Env
vars: ``VEJDIREKTORATET_URL``/``VEJDIREKTORATET_USERNAME``/
``VEJDIREKTORATET_PASSWORD`` (see ``.env.example``, ``scripts/smoke_test.py``).

**Licence**: **CC BY 4.0**, confirmed live and per-dataset (see above) -
attribute Vejdirektoratet (the Danish Road Directorate) per CC BY's
requirement wherever this data is displayed or redistributed.

**``territory``/``administrative_area``**: pass ``territory="Denmark"`` to
:func:`~streetworks.common.from_datex2` (no DATEX feed states its own
country, same documented convention as every other DATEX adapter).
``administrative_area`` has no confirmed source field yet - unconfirmed
until Phase 2 sees a real record.

**What's still open until Phase 2** (a real credentialed pull):

1. Whether ``trafikmeldinger`` really is a list of independent DATEX XML
   strings (per the protocol doc) or a single wrapping document - shapes
   whether :meth:`VejdirektoratetClient.iter_situations`'s per-entry
   parsing is correct as written.
2. Whether the REST response is DATEX II 3.2 unchanged, or a Vejdirektoratet
   profile of it with fields the shared parser doesn't expect (unconfirmed
   either way - the protocol doc describes the *transport*, not a full
   XSD diff against vanilla 3.2).
3. Real coordinate/location-referencing coverage - the protocol doc
   doesn't state which referencing method(s) real records use.
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

__all__ = ["VejdirektoratetClient"]

warnings.warn(
    "streetworks.datex2.vejdirektoratet is a Credentials-wanted scaffold: "
    "built to Vejdirektoratet's confirmed DATEX II 3.2 schema (see module "
    "docstring), not yet verified against a real authenticated response. "
    "Have Dataudveksleren credentials for a roadworks dataset? Running the "
    "smoke test and reporting back one real trimmed record would confirm "
    "this adapter - see the 'help wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues for exactly "
    "what's needed.",
    UserWarning,
    stacklevel=2,
)

_TRAFIKMELDINGER_PATH = "trafikmeldinger"


class VejdirektoratetClient:
    """Fetch Danish roadworks from Vejdirektoratet's Dataudveksleren REST
    pull. **Pending live verification - see module docstring.**

    Requires ``base_url`` (the per-dataset pull address issued at
    registration - there is no public default, see module docstring) and
    HTTP Basic ``username``/``password``.

    >>> from streetworks.datex2.vejdirektoratet import VejdirektoratetClient
    >>> from streetworks.common import from_datex2
    >>> with VejdirektoratetClient(  # doctest: +SKIP
    ...     base_url=base_url, username=username, password=password,
    ... ) as vejdirektoratet:
    ...     for situation in vejdirektoratet.iter_roadworks():
    ...         works = from_datex2(situation, territory="Denmark")
    """

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url:
            raise ValueError(
                "base_url is required - Vejdirektoratet issues the real pull "
                "address at registration, see module docstring"
            )
        if not username or not password:
            raise ValueError("username and password are required (HTTP Basic)")
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            auth=httpx.BasicAuth(username, password),
        )
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_trafikmeldinger(self) -> list[bytes]:
        """``GET`` the configured endpoint - the documented
        ``trafikmeldinger`` shape is a list of DATEX II XML strings (not
        one wrapping document, per the protocol doc - see module
        docstring, item 1). Returns each entry's raw bytes, undecoded."""
        response = self._transport.request("GET", f"{self.base_url}/{_TRAFIKMELDINGER_PATH}")
        payload = response.json()
        entries = payload if isinstance(payload, list) else payload.get("trafikmeldinger") or []
        return [entry.encode("utf-8") if isinstance(entry, str) else entry for entry in entries]

    def iter_situations(self) -> Iterator[Situation]:
        for xml_bytes in self.get_trafikmeldinger():
            yield from _iter_situations(io.BytesIO(xml_bytes), provider="Vejdirektoratet/Denmark")

    def iter_roadworks(self) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least
        one roadworks record (``MaintenanceWorks``/``ConstructionWorks``)."""
        for xml_bytes in self.get_trafikmeldinger():
            yield from _iter_roadworks(io.BytesIO(xml_bytes), provider="Vejdirektoratet/Denmark")

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> VejdirektoratetClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
