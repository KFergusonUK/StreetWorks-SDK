"""Sweden (Trafikverket) roadworks - Trafikverket's own XML-request/
JSON-response API, **not** a DATEX II serialisation.

.. attention::
   **PENDING LIVE VERIFICATION.** This module is built against Trafikverket's
   documented request/response shape (a real, live, credential-free probe -
   see "What's confirmed" below) plus field names cross-referenced across
   several third-party client libraries and a real, publicly-viewable example
   query - not against a real authenticated response. No real Swedish
   ``Situation``/``Deviation`` payload has been seen by this SDK. Better-
   confirmed than :mod:`streetworks.datex2.vegvesen` was at the same stage
   (the endpoint, auth failure shape, object name and schema version are all
   live-verified here, not just documented), but still not production-ready
   until Phase 2 (a real credentialed pull) confirms the field mapping below.

**What's confirmed, live, credential-free (2026-07)**: a deliberately invalid
key against the real endpoint returns a genuine, structured rejection, not a
generic error page:

.. code-block:: text

   POST https://api.trafikinfo.trafikverket.se/v2/data.json
     <REQUEST><LOGIN authenticationkey="test"/>
       <QUERY objecttype="Situation" schemaversion="1.5"/></REQUEST>
   -> HTTP 401
   {"RESPONSE":{"RESULT":[{"ERROR":{"SOURCE":"Security","MESSAGE":"Invalid authentication"}}]}}

This confirms the endpoint, the request envelope shape (XML in, JSON out),
the ``Situation`` object name, and schema version ``1.5`` all live -
independent of any documentation page's own claims.

**Not DATEX II - Trafikverket's own request/response envelope.** A
``POST`` carries a plain XML body (``LOGIN``/``QUERY``/``FILTER``/
``INCLUDE`` elements - not a DATEX ``d2LogicalModel``), and the response is
JSON, not XML: ``{"RESPONSE": {"RESULT": [{"Situation": [...]}]}}``, each
``Situation`` carrying one or more ``Deviation`` objects. This needs its own
small request-builder/parser onto the shared
:class:`~streetworks.datex2.models.Situation`/
:class:`~streetworks.datex2.models.SituationRecord` models - the same shape
of solution as :mod:`streetworks.datex2.digitraffic` (Finland's own
Simple-JSON, not a DATEX serialisation either) - **not** the streaming DATEX
XML parser, which would simply fail to find anything to match here.

**Field names - documented, not verified.** Cross-referenced across
Trafikverket's own API console description, a real published example query
(a public GitHub gist querying ``Deviation.Geometry.SWEREF99TM``/
``Deviation.Header``/``Deviation.IconId``/etc. with a live radius filter),
and independent third-party client libraries (C#, R) that all agree on the
same field set: ``Header``, ``Message``, ``MessageType``, ``MessageCode``,
``IconId``, ``SeverityCode``, ``SeverityText``, ``RoadNumber``,
``StartTime``, ``TemporaryLimit``, ``TrafficRestrictionType``,
``ValidUntilFurtherNotice``, ``WebLink``, ``Geometry.WGS84``,
``Geometry.SWEREF99TM``. Trafikverket's own description of the
``Situation`` object states it covers "events and disruptions such as
traffic messages, road work (vägarbeten), accidents, restrictions" - so
roadworks genuinely are in scope for this object type, not a guess - but
**no confirmed value distinguishes a roadworks ``Deviation`` from any other
kind**. ``MessageType`` is real and documented as free text (one real
published example: ``"Färjor"``/"Ferries", ``MessageTypeValue``
``"TransitInformation"``) alongside the separate, real ``MessageCode``
field - but no real example naming the roadworks value for either was
found. **Deliberately not guessed at**: :func:`parse_situations` preserves
``MessageType`` verbatim as ``SituationRecord.record_type``, which means
:attr:`~streetworks.datex2.models.SituationRecord.is_roadworks` (checking
against ``ROADWORKS_TYPES``, a DATEX vocabulary Trafikverket doesn't share)
will not match real Swedish values - so :meth:`TrafikverketClient.iter_roadworks`
**will return an empty list against real data until Phase 2 confirms the
real discriminator value and this module is updated to recognise it**. Use
:meth:`TrafikverketClient.iter_situations` and inspect ``record_type``
yourself in the meantime - never silently filtered to a guessed value.

**CRS**: ``Geometry.WGS84`` is documented (not verified) as a WKT
``POINT (lon lat)`` string, per Trafikverket's own naming and every
third-party client's handling of it - parsed here, flipped to this SDK's
``(lat, lon)`` convention for ``EPSG:4326`` same as every DATEX adapter.
``Geometry.SWEREF99TM`` (Sweden's own national grid, metre-based) is the
documented alternative/redundant geometry - not requested here, WGS84 is
simpler and sufficient if confirmed correct.

**Credentials**: free, self-service registration at
`data.trafikverket.se <https://data.trafikverket.se/>`_ (the API account
signup, confirmed live/reachable) or via `Trafiklab
<https://www.trafiklab.se/api/other-apis/trafikverket/>`_, which can issue
the same key without a separate Trafikverket account. Issues an **API key**
(not Basic Auth) - see :class:`TrafikverketClient`'s ``api_key``. Env var:
``TRAFIKVERKET_API_KEY`` (see ``.env.example``, ``scripts/smoke_test.py``).

**Licence**: **CC0 1.0 Universal (Public Domain Dedication)** - confirmed
in the NAP survey (``docs/nap-survey.md``) via the registration flow's own
licence link and the catalogue's per-dataset licence facet (43/49 datasets,
including the roadworks one, shown as CC0). The least restricted licence
tier - no attribution required even - but the test fixture here is still
**synthetic**, since no real data has been seen at all (not a licence
question for this one, a "nothing to trim from" one).

**What's still open until Phase 2** (a real credentialed pull):

1. Whether the response JSON nests fields exactly as their dotted
   ``INCLUDE`` paths suggest (``{"Deviation": {"Geometry": {"WGS84": ...}}}``)
   - the standard, documented Trafikverket convention, but unconfirmed
   against a real payload.
2. **The real value(s) of ``MessageType``/``MessageCode`` that mean
   roadworks** - the single most important open item, since nothing here
   can filter to roadworks-only without it (see above).
3. Whether ``Deviation`` carries a genuine unique ``Id`` field (assumed,
   not confirmed - every other Trafikverket object type has one by
   convention, but not verified for ``Situation``/``Deviation`` directly).
4. Real coordinate coverage, and whether ``Geometry.WGS84`` is ever
   absent for a real roadworks-relevant record.
"""

from __future__ import annotations

import re
import warnings
from datetime import datetime
from typing import Any

import httpx

from .._dt import parse_iso8601 as _dt
from .._transport import RetryConfig, SyncTransport
from .models import Location, Situation, SituationRecord

__all__ = ["BASE_URL", "DATA_PATH", "SCHEMA_VERSION", "TrafikverketClient", "parse_situations"]

warnings.warn(
    "streetworks.datex2.trafikverket is a Credentials-wanted scaffold: built "
    "to Trafikverket's confirmed-live API shape (see module docstring), not "
    "yet verified against a real authenticated response. Have a Trafikverket "
    "API key? Running the smoke test and reporting back one real trimmed "
    "record would confirm this adapter - see the 'help wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues for exactly "
    "what's needed.",
    UserWarning,
    stacklevel=2,
)

JSON = dict[str, Any]

BASE_URL = "https://api.trafikinfo.trafikverket.se"
DATA_PATH = "v2/data.json"

#: Confirmed live via the invalid-key probe in the module docstring.
SCHEMA_VERSION = "1.5"

#: Documented (not verified against a real response) - see module docstring.
_INCLUDE_FIELDS = (
    "Deviation.Id",
    "Deviation.Header",
    "Deviation.Message",
    "Deviation.MessageType",
    "Deviation.MessageCode",
    "Deviation.IconId",
    "Deviation.SeverityCode",
    "Deviation.SeverityText",
    "Deviation.RoadNumber",
    "Deviation.StartTime",
    "Deviation.EndTime",
    "Deviation.TemporaryLimit",
    "Deviation.TrafficRestrictionType",
    "Deviation.ValidUntilFurtherNotice",
    "Deviation.WebLink",
    "Deviation.Geometry.WGS84",
    "Deviation.ModifiedTime",
)

_WKT_POINT = re.compile(r"^POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)$", re.IGNORECASE)


def _escape_xml_attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def build_request(api_key: str) -> str:
    """The real, confirmed request envelope (see module docstring) -
    exposed as its own function so a caller (or a future test against real
    credentials) can inspect or replay the exact body sent."""
    includes = "".join(f"<INCLUDE>{name}</INCLUDE>" for name in _INCLUDE_FIELDS)
    key = _escape_xml_attr(api_key)
    return (
        f'<REQUEST><LOGIN authenticationkey="{key}"/>'
        f'<QUERY objecttype="Situation" schemaversion="{SCHEMA_VERSION}">'
        f"{includes}</QUERY></REQUEST>"
    )


def _parse_point(wgs84: str | None) -> tuple[float, float] | None:
    """``"POINT (lon lat)"`` -> ``(lat, lon)`` - documented format, see
    module docstring; never assumed present."""
    if not wgs84:
        return None
    match = _WKT_POINT.match(wgs84.strip())
    if not match:
        return None
    lon, lat = float(match.group(1)), float(match.group(2))
    return (lat, lon)


def _parse_deviation(deviation: JSON) -> SituationRecord:
    geometry = deviation.get("Geometry") or {}
    point = _parse_point(geometry.get("WGS84"))
    road_number = deviation.get("RoadNumber")
    return SituationRecord(
        id=str(deviation.get("Id") or ""),
        # Preserved verbatim, not mapped to DATEX vocabulary - see module
        # docstring for why is_roadworks will not match real Swedish values
        # yet.
        record_type=deviation.get("MessageType") or "",
        source_name=deviation.get("Header"),
        comments=(deviation["Message"],) if deviation.get("Message") else (),
        location=Location(
            points=(point,) if point else (),
            road_number=str(road_number) if road_number is not None else None,
        ),
        validity=_parse_validity(deviation),
        impact_delay_band=deviation.get("SeverityText") or deviation.get("SeverityCode"),
        raw=deviation,
    )


def _parse_validity(deviation: JSON) -> Any:
    from .models import Validity

    start = _dt(deviation.get("StartTime"))
    end = _dt(deviation.get("EndTime"))
    return Validity(overall_start=start, overall_end=end)


def _parse_situation(raw_situation: JSON) -> Situation:
    deviations = raw_situation.get("Deviation") or []
    records = [_parse_deviation(d) for d in deviations]
    version_time: datetime | None = None
    if deviations:
        version_time = _dt(deviations[0].get("ModifiedTime"))
    return Situation(
        id=str(raw_situation.get("Id") or ""),
        version_time=version_time,
        records=records,
        raw=raw_situation,
    )


def parse_situations(payload: JSON) -> list[Situation]:
    """Parse a real ``{"RESPONSE": {"RESULT": [{"Situation": [...]}]}}``
    response body into :class:`~streetworks.datex2.models.Situation`
    objects - documented shape, not verified against a real payload, see
    module docstring."""
    results = ((payload.get("RESPONSE") or {}).get("RESULT")) or []
    situations: list[JSON] = []
    for result in results:
        situations.extend(result.get("Situation") or [])
    return [_parse_situation(s) for s in situations]


class TrafikverketClient:
    """Fetch Swedish roadworks-relevant deviations from Trafikverket's own
    Situation/Deviation API. **Pending live verification - see module
    docstring**, especially the roadworks-discriminator caveat on
    :meth:`iter_roadworks`.

    Requires an API key (free self-service registration - see module
    docstring).

    >>> from streetworks.datex2.trafikverket import TrafikverketClient
    >>> from streetworks.common import from_datex2
    >>> with TrafikverketClient(api_key=api_key) as trafikverket:  # doctest: +SKIP
    ...     for situation in trafikverket.iter_situations():
    ...         works = from_datex2(situation, territory="Sweden")
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_situations(self) -> JSON:
        """``POST v2/data.json`` with the real, confirmed request envelope
        (see :func:`build_request`) - the parsed JSON response body."""
        response = self._transport.request(
            "POST",
            f"{self.base_url}/{DATA_PATH}",
            content=build_request(self.api_key),
            headers={"Content-Type": "text/xml"},
        )
        return response.json()

    def iter_situations(self) -> list[Situation]:
        """Every ``Situation`` the query returns - **not filtered to
        roadworks** (see :meth:`iter_roadworks` and the module docstring
        for why that filter isn't safe to apply yet). Inspect
        ``record_type`` (Trafikverket's own ``MessageType`` field,
        verbatim) yourself."""
        return parse_situations(self.get_situations())

    def iter_roadworks(self) -> list[Situation]:
        """Like :meth:`iter_situations`, filtered to
        :attr:`~streetworks.datex2.models.Situation.roadworks` being
        non-empty. **Will return an empty list against real data until
        Phase 2 confirms the real ``MessageType``/``MessageCode`` value
        Trafikverket uses for roadworks** - see module docstring. Kept for
        interface consistency with every other DATEX adapter in this SDK,
        not because it's known to work yet."""
        return [s for s in self.iter_situations() if s.roadworks]

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> TrafikverketClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
