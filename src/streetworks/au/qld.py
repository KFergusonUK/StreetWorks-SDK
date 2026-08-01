"""Queensland: QLDTraffic Events (TMR) - the fourth :mod:`streetworks.au`
member, and the first with **no credential wait at all**: a public,
globally-shared API key is published directly in TMR's own API
specification, intended for exactly this use.

**Architecture: one adapter, parameterised over `event_type` - the NSW
pattern, not Victoria's.** A single endpoint (``GET /v2/events``) returns
every current event (Hazard/Crash/Congestion/Roadworks/Special event/
Flooding) mixed together in one ``FeatureCollection`` - unlike NSW's
per-layer files, there is no server-side type filter at all (the spec
lists no query parameters beyond ``apikey``), so
:meth:`QldTrafficClient.iter_events` filters client-side on the real
``event_type`` field. :meth:`~QldTrafficClient.iter_roadworks` is the
``event_type == "Roadworks"`` convenience default; every other type stays
reachable via :meth:`iter_events` for a routing/multi-hazard consumer.
**No pagination** - confirmed live (2026-08-01): a single real pull
returned all 458 current events (2.2 MB) in one response, matching the
spec's own silence on any paging mechanism.

.. attention::
   **Investigated 2026-07-30, confirmed live 2026-08-01** against a real,
   credential-free pull (458 real events, 244 real ``Roadworks``). Two of
   the source API specification's own documented claims turned out to be
   wrong when checked against real data - see "Two real doc-vs-reality
   mismatches" below - and the real geometry/authority shape is
   substantially richer than the source investigation brief anticipated.
   Not a Credentials-wanted scaffold at any point - built and shipped
   live-verified in one pass, the same shape as WA.

**The public API key is meant to be used exactly like this - not a
credential leak.** TMR's own specification (v1.10, section 2.1.1.1) publishes it
directly, in plaintext, captioned "A public API key ... is available for
developers who do not wish to register and receive their own key,"
globally rate-limited to 100 requests/minute *shared across every
anonymous consumer of the API worldwide* - confirmed live: this key was
returned a real ``429``/``LimitExceededException`` on a first attempt
(2026-07-30), before any request from this session had exhausted it,
settling by itself with no action taken. A caller making frequent/
production calls should register their own key by emailing
``QLDTraffic@tmr.qld.gov.au`` (organisation name, contact person, email,
application name) rather than compete for the shared quota - see
:data:`PUBLIC_API_KEY`.

**Two real doc-vs-reality mismatches, found by checking, not assumed from
the spec text:**

1. **The spec claims (section 4.1-4.2) that ``geometry.type`` is always**
   ``"GeometryCollection"``. A real pull found this false: only 10/458
   (2.2%) real features are actually ``GeometryCollection`` - the other
   448/458 (97.8%) are a bare top-level ``MultiLineString`` (313) or
   ``MultiPoint`` (135), with no collection wrapper at all.
   :func:`streetworks.common.from_au_qld_qldtraffic._geometries` handles
   all three real top-level shapes, not just the documented one.
2. **The spec's own ``source_name`` enum table (section 4.3.1) lists exactly
   three values**: ``EPS``, ``Guardian``, ``tfNSW`` (lower-case ``t``).
   Real data shows **five**: the same three (real casing **``TfNSW``**,
   capital ``T`` - a second, minor mismatch) plus two genuinely
   undocumented values, ``Asignit`` and ``MBRC`` - both real republishing
   platforms/direct feeds from Queensland local government authorities
   (Ipswich City Council via Asignit; City of Moreton Bay direct via
   ``MBRC``), not interstate at all. Never assume this enum is closed;
   :func:`~streetworks.common.from_au_qld_qldtraffic.from_au_qld_qldtraffic`
   doesn't validate against it, it just carries the real value through.

**``area_alert`` - confirmed live exactly as documented, for the one real
case seen.** When ``properties.area_alert`` is ``true`` (1/458 real
events, a "Special event," not a roadworks record, but the mechanism is
generic across every ``event_type``), ``geometry.type`` genuinely is
``GeometryCollection`` and the **last** entry in ``geometries`` genuinely
is the alert polygon, confirmed against the one real example (a
``Point``+``Polygon`` pair). Excluded before any works geometry is built -
see :mod:`streetworks.common.from_au_qld_qldtraffic`.

**CRS: real coordinates are ``EPSG:7844`` (GDA2020), not WGS84- confirmed
live on every single feature (458/458), stated as a genuine embedded
``crs`` member on the geometry object itself** (``{"type": "name",
"properties": {"name": "EPSG:7844"}}``) - never assumed, never silently
relabelled ``EPSG:4326`` the way the source investigation brief's "WGS84"
framing would have. GDA2020 and WGS84 are numerically close (Australia's
tectonic plate has drifted ~1.5 m from the ITRF frame WGS84 was last
realised against) but are not the same CRS by definition - this SDK's
standing CRS policy states what the source states, never what's "close
enough."

**Roadworks geometry - a real, substantial deviation from the source
brief's Victoria-derived assumption, not a mechanical implementation of
it.** The brief expected "Point = precise site, LineString = impact
extent - prefer the Point, drop the LineString" (Victoria's own real
lesson). Checked against 244 real ``Roadworks`` events, this doesn't
transfer: **216/244 (88.5%) have *no* Point at all - only a
``MultiLineString``.** Dropping every LineString the way Victoria's
converter does would leave the large majority of real Queensland
roadworks with no geometry whatsoever, not a safe/lossless simplification
the way it was for Victoria (which always had a real Point standing in).
A real span check across all 216 (crude great-circle bounding-box
distance, not a geodesic) found the true picture is **mixed, not
uniformly one or the other**: median ~1.07 km and 62% under 2 km
(genuinely worksite-scale - e.g. a real 42 m span,
"Fitzroy Developmental Road (Springton Creek Bridge)"), but a real ~9%
tail runs 20-133 km (genuinely Victoria-style corridor extent - e.g. a
real 133.5 km span on Flinders Highway). Given the source's own field is
named and documented as *"a set of geometries indicating the affected
roads"* (never claiming precision), this module's converter carries the
LineString(s) through honestly as exactly that - the real, stated
affected-road extent, via ``Coordinate.points``/``parts`` - rather than
either fabricating a false "precise site" claim or discarding real,
often-precise data outright. See
:mod:`streetworks.common.from_au_qld_qldtraffic`'s own docstring for the
precise rule and the honesty trade-off this makes explicit rather than
hiding. 26/244 (10.7%) are ``MultiPoint``-only (almost always exactly one
point); only 2/244 (0.8%) genuinely mix a Point with a LineString the way
Victoria's shape always does.

**``event_subtype`` is one flat enum shared across every ``event_type``,
confirmed live, not partitioned per type the way the spec's own
3-part-hierarchy framing might suggest.** Real evidence: the one real
``"Emergency roadworks"``-subtyped event in the pull has
``event_type == "Hazard"``, not ``"Roadworks"`` - a caller filtering
strictly on ``event_type == "Roadworks"`` would never see it. All 244 real
``event_type == "Roadworks"`` records in this pull are subtype
``"Planned roadworks"`` (244/244) - a real "emergency roadworks" record
classified *as* ``Roadworks`` has not been observed live, so
``DateConfidence`` grading doesn't special-case it (see the converter).

**``source.provided_by`` is the real, rich per-record authority field -
richer than the source brief's "interstate republication" framing
anticipated, and confirmed 100% populated (0/244 real Roadworks records
null).** 17 distinct real values across one pull: the plurality is
"Department of Transport and Main Roads" (202/244, ~83%), but real,
named, non-TMR values include a private tollway operator ("Transurban",
8 records) and 15 different Queensland local government/disaster-
management authorities (e.g. "Brisbane City Council", "Ipswich City
Council", "Somerset Regional Council", "Fraser Coast Regional Council") -
this is genuinely richer than a QLD-vs-NSW split, and
:func:`~streetworks.common.from_au_qld_qldtraffic.from_au_qld_qldtraffic`
uses it directly as ``administrative_area`` per record, rather than one
hardcoded operator name the way NSW/Victoria do - see that module's own
docstring. The interstate (``TfNSW``) republication the brief flagged is
real and confirmed live, but in this pull it only ever appears as
``event_type == "Hazard"`` (61/61 real ``TfNSW``-sourced records), never
as ``Roadworks`` (0/244) - worth re-checking on a future pull, since this
could change, but it doesn't currently collide with
:meth:`~QldTrafficClient.iter_roadworks`'s default output.

**Dates**: ``duration.start``/``end`` are tz-aware ISO 8601 with a real
``+10:00`` offset (AEST; Queensland has no daylight saving, unlike NSW/
Victoria) - confirmed live, and always populated for real ``Roadworks``
records (0/244 null either field), cleaner than NSW's/Victoria's own
partial population. Parsed via the existing
:func:`streetworks._dt.parse_iso8601`, which already tolerates
non-standard fractional-second precision - no new date-parsing code
needed here.

**Licence: CC BY 4.0 AU**, stated directly in the API specification
(section 2.1) - *"Use of the data must be in accordance with the Creative
Commons Attribution 4.0 Australia (CC BY 4.0 AU) license."* The real
top-level ``rights.owner`` field defers attribution per-record to
whichever entity actually provided it (*"Department of Transport and Main
Roads, Transport for NSW, or the respective Local Government
Authority"*) - confirmed live to match exactly what ``source.provided_by``
states per record, so attribution should chain through that field, not a
single blanket TMR credit.

**Credentials**: none required (see "public API key" above). Env var
``QLD_QLDTRAFFIC_API_KEY`` is optional - only needed for a caller who has
registered their own private key instead of the shared public one; falls
back to :data:`PUBLIC_API_KEY` when unset (see ``.env.example``,
``scripts/smoke_test.py``).

**What's still open** (not blocking - this module is confirmed live, but
these details remain genuinely unverified):

1. Whether ``TfNSW``-sourced records ever appear as ``event_type ==
   "Roadworks"`` on a different pull - not observed in this one (see
   above), but the republication mechanism is real, so it's plausible on
   a future pull.
2. ``event_priority``'s highest real value, ``"Red Alert"``, was not
   observed live (244 real Roadworks records topped out at "High") -
   documented as a real possible value, not confirmed reachable for
   roadworks specifically.
3. The real, undocumented ``image`` field (a plain URL string, 2/244 real
   records) and ``recurrences[].event_id`` (present on every real
   recurrence checked, absent from the spec's own field table) are
   carried through on ``.raw`` but not otherwise modelled.
"""

from __future__ import annotations

from typing import Any, Literal

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "PUBLIC_API_KEY", "EVENT_TYPES", "QldTrafficClient"]

JSON = dict[str, Any]

EventType = Literal[
    "Hazard", "Crash", "Congestion", "Roadworks", "Special event", "Flooding"
]

BASE_URL = "https://api.qldtraffic.qld.gov.au/v2"
_EVENTS_PATH = "events"

#: The real, globally-shared public API key, published in plaintext by
#: TMR's own API specification (v1.10, section 2.1.1.1) for exactly this use -
#: not a credential leak. Rate-limited to 100 requests/minute, shared
#: across every anonymous consumer worldwide - see module docstring.
PUBLIC_API_KEY = "3e83add325cbb69ac4d8e5bf433d770b"

#: Every real event_type value, confirmed from the API specification's
#: own field table (section 4.3) - "Roadworks" is this module's default via
#: iter_roadworks(); the rest are opt-in via iter_events(event_types=...).
EVENT_TYPES: tuple[EventType, ...] = (
    "Hazard",
    "Crash",
    "Congestion",
    "Roadworks",
    "Special event",
    "Flooding",
)


class QldTrafficClient:
    """Fetch Queensland road events from QLDTraffic's ``/v2/events`` feed.
    No credential wait - the public API key works out of the box (see
    module docstring); pass ``api_key`` to use a registered private key
    instead.

    >>> from streetworks.au.qld import QldTrafficClient
    >>> from streetworks.common import from_au_qld_qldtraffic
    >>> with QldTrafficClient() as qld:  # doctest: +SKIP
    ...     works_list = from_au_qld_qldtraffic(qld.iter_roadworks())
    """

    def __init__(
        self,
        *,
        api_key: str = PUBLIC_API_KEY,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_events(self) -> JSON:
        """``GET /v2/events?apikey=...`` - every current event, all types
        mixed, as one real ``FeatureCollection`` (confirmed live: no
        pagination, no server-side type filter - see module docstring).
        Returns the parsed JSON response."""
        response = self._transport.request(
            "GET",
            f"{self.base_url}/{_EVENTS_PATH}",
            params={"apikey": self.api_key},
        )
        return response.json()

    def iter_events(self, *, event_types: tuple[str, ...] | None = None) -> list[JSON]:
        """Every current event, optionally filtered client-side to
        ``event_types`` (the real ``properties.event_type`` value) - there
        is no server-side filter to delegate to, see module docstring.
        ``event_types=None`` (the default) returns every real type
        unfiltered."""
        payload = self.get_events()
        features = payload.get("features") or []
        if event_types is None:
            return [f for f in features if isinstance(f, dict)]
        return [
            f
            for f in features
            if isinstance(f, dict) and f.get("properties", {}).get("event_type") in event_types
        ]

    def iter_roadworks(self) -> list[JSON]:
        """``event_type == "Roadworks"`` convenience wrapper over
        :meth:`iter_events` - this module's best-confirmed slice (244 real
        events, one live pull, 2026-08-01)."""
        return self.iter_events(event_types=("Roadworks",))

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> QldTrafficClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
