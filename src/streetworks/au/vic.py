"""Victoria: DTP Planned Disruptions - Road, the second member of the
:mod:`streetworks.au` cluster. Permit-Team-validated, richer-structured
than New South Wales' feed, and - since Phase 2 - confirmed against real
data too.

**Architecture: a separate module from NSW, deliberately not one adapter
per country.** Victoria publishes *two independent APIs* on different
version tracks with different schemas - "Planned Disruptions" (this
module, permit-derived, works-relevant) and "Unplanned Disruptions"
(incident-shaped, backed by a different system - the Road Incident
Database - now on v3, not built here). NSW's "one adapter, parameterised
over layer" pattern doesn't apply here: that pattern relies on every
layer sharing one real schema, confirmed from NSW's own spec; Victoria's
two APIs do not share a schema, so collapsing them would paper over a
real difference, not simplify one. If "unplanned" is ever built, it
belongs in its own module (``streetworks.au.vic_unplanned`` or similar),
not merged into this one.

.. attention::
   **PHASE 2 CONFIRMED (2026-07-30)** - verified against a real
   authenticated pull, by a tester running ``scripts/smoke_test.py`` with
   their own Transport Victoria Open Data Hub subscription key. 500 real
   planned-disruption features returned on the first page alone. This
   confirmed every genuinely-open item from Phase 1 (coordinate order,
   timestamp format, impact-field shapes) and found **one real design
   mistake in this module's own converter** (see "A real design mistake
   this confirmed" below) - not a mistake in the source investigation or
   the OpenAPI spec this time, but in this module's own reasoning about
   what a GeometryCollection's Point/LineString pair represents. No
   longer grouped under the README's Credentials wanted section.

**What's confirmed, live, from the real OpenAPI spec (fetched and parsed
directly this session, 2026-07)**:

- **Base URL and path**, from the spec's own ``servers``/``paths``
  blocks: ``https://api.opendata.transport.vic.gov.au/opendata/roads/disruptions``
  + ``GET /planned/v1/`` with a required ``format`` query parameter
  (``GeoJson`` default, or ``GeoJsonPoint``/``GeoJsonLine``).
- **Rate limit and cache, from the operation's own description text**:
  "10 calls per minute and caching time of 10 minutes," max 1000 records
  per query.
- **Pagination is token-based**: send the previous response's
  ``nextPageDetails.nextPageToken`` back as a ``NextPageToken`` request
  header; loop while ``hasMoreRecords`` is true.
- **The full response schema**, field-by-field from the spec's own
  ``components.schemas`` (not inferred): a GeoJSON-shaped
  ``FeatureCollection`` whose ``geometry`` is itself a
  ``GeometryCollection`` (``{"type", "geometries": [{"type",
  "coordinates"}, ...]}``) for the default ``GeoJson`` format - **not** a
  bare ``Point``/``LineString`` the way NSW's or most DATEX geometry is.
  ``properties`` carries ``id``, ``source`` (``sourceName``/``sourceId``),
  ``status``, ``closedRoadName``, ``startIntersectionRoadName``,
  ``startIntersectionLocality``, ``localGovernmentArea``, ``rmaClass``,
  ``eventType``/``eventSubtype``/``eventDueTo``, ``impact``
  (``direction``/``impactType``/``delay``/``numberLanesImpacted``/
  ``speedLimitOnSite``, **all typed** ``string`` **in the real schema,
  even the numeric-looking ones**), ``duration`` (``start``/``end``,
  both ``string``; ``recurrences[]`` with ``startDay``/``daysDuration``
  (a real ``integer``)/``startTime``/``duration``/``allDay`` (a real
  ``boolean``)), ``description``, ``lastUpdated``. No example values are
  embedded anywhere in the spec.

**A real design mistake this confirmed, in this module's own reasoning,
not the source material**: Phase 1's ``_coordinate`` preferred a
GeometryCollection's LineString over its Point, on the assumption they
were coarse-vs-precise views of the *same* site - the DATEX/WZDx shape.
A real feature disproved this: its LineString spanned **~150km end to
end** (``[144.97, -37.69]`` to ``[146.91, -36.10]``), matching
``srns: "M31,B400"`` - the entire Hume Freeway corridor the disruption
sits on, not a precise extent of it. Its Point, by contrast, sat exactly
at the real disruption site (``closedRoadName: "METROPOLITAN RING
OUT-HUME RAMP"``) within that span. Promoting the LineString to
``Coordinate.points`` would have silently replaced one worksite's
location with an entire highway - :func:`streetworks.common.from_vic_disruptions._coordinate`
now prefers the Point and never reads the LineString at all (see that
module's own docstring). A genuinely useful lesson for reading any future
DTP-style GeometryCollection: don't assume every multi-geometry pairing
means the same thing NSW's/DATEX's coarse-point-plus-precise-line one
does - check what the line actually spans before trusting it.

**A decisive, live-verified correction to the source investigation
brief's own bet - the auth header.** The brief flagged a genuine
docs-vs-docs conflict: the human-facing dataset page names the header
``KeyID``; the OpenAPI spec's own ``securitySchemes`` name
``Ocp-Apim-Subscription-Key`` (header) or ``subscription-key`` (query) -
the standard Azure API Management names - and the brief bet on the APIM
names being correct at the real gateway. **A live probe settles it the
other way.** The gateway's ``WWW-Authenticate`` error message itself
changes depending on which header is sent::

    no key, or Ocp-Apim-Subscription-Key, or ?subscription-key=  ->
      error_description="Failed to find key field: KeyId"
    KeyID: <anything>  ->
      error_description="API Key not authorized: <anything>"

The first message means the gateway never even found a recognised key
field; the second means it found one and rejected the *value*. This
module therefore sends ``KeyID`` (confirmed case-insensitively - ``KeyId``
behaves identically, ordinary HTTP header semantics), not the OpenAPI
spec's own advertised scheme - a real case of a machine-readable spec
being wrong about its own gateway, not just stale prose. A genuinely
useful finding for whoever built the spec, too, worth reporting upstream.
Also notable, not otherwise consequential: the error responses are
SOAP-shaped XML (a Vordel/Axway API Gateway fault, per the
``http://www.vordel.com/soapfaults`` namespace in the body) fronted by
Cloudflare, despite this being an otherwise-REST/JSON API - the third
provider in this SDK (after NSW's Layer7 gateway and Trafikverket's
XML-request/JSON-response envelope) where the gateway's own error shape
doesn't match the API's advertised data format.

**A correction to this module's own design brief**: the brief's proposed
canonical mapping suggested ``administrative_area = localGovernmentArea``.
Checked against :class:`~streetworks.common.Works`'s own documented
semantics (``administrative_area`` is "the sub-national body that *owns*
the data," not a geographic descriptor of where a record sits) - an LGA
is geography, not data ownership, so it doesn't fit that field the way
DTP (the actual publishing authority, confirmed from the spec's own
description: "the DTP is the coordinating road authority... for any
works on, or that may affect, the road network, the DTP must manage the
disruption") does. This module sets ``administrative_area="Department of
Transport and Planning"`` (matching the operator-as-authority rule
already applied to Autobahn GmbH/TfNSW/Via Lietuva) and carries
``localGovernmentArea`` in ``WorksSite.location_description`` instead,
alongside the road-name fields - a geography detail, not a provenance
one. See :mod:`streetworks.common.from_vic_disruptions`.

**``source.sourceName``/``source.sourceId`` map to ``Works.promoter``** -
their presence hints the planned feed may aggregate more than one
upstream source behind "DTP," the same do-not-deduplicate signal this
SDK already treats DGT/Consell de Mallorca's republication and multiple
providers covering one physical location the same way.

**Dates - confirmed live, and genuinely unusual**: ``duration.start``/
``end`` are real ISO-8601 timestamps with **no UTC offset at all**
(e.g. ``"2024-02-01T00:00:00"``, confirmed from a real feature) - not
epoch millis (NSW's own format, which this module's design deliberately
didn't assume Victoria shared), and not offset-aware either.
:func:`streetworks._dt.parse_iso8601` parses these successfully (Python's
``fromisoformat`` accepts naive timestamps), but the resulting
``datetime`` is **timezone-naive** - genuinely ambiguous whether it means
Victorian local time (AEST/AEDT) or UTC, since the source states neither.
Carried through as a naive ``datetime`` rather than guessing a tzinfo to
attach, the same "don't invent what the source doesn't state" discipline
this SDK applies everywhere. ``recurrences[].duration`` is confirmed to
be a real **ISO-8601 duration string** (e.g. ``"PT6H"`` = 6 hours, not
free text as Phase 1 guessed) - not specially parsed/formatted here yet,
still carried through as-is inside ``operating_window``'s joined text.

**Geometry - confirmed live**: real coordinates are GeoJSON-native
``[lon, lat]`` (e.g. ``[145.653193, -36.700197]``, genuine Victorian
territory), exactly as Phase 1 presumed. The default ``format=GeoJson``
``GeometryCollection`` shape is confirmed correct and is the only one
this module parses; ``GeoJsonPoint``/``GeoJsonLine`` remain accepted by
:meth:`VicDisruptionsClient.get_planned_disruptions`'s ``format``
parameter but their response shape is still unconfirmed - see "A real
design mistake this confirmed" above for what the GeometryCollection's
Point/LineString pairing actually turned out to mean.

**Licence**: **Creative Commons Attribution 4.0**, confirmed live via
the dataset resource page - stated directly, satisfying the Open
Definition. Distinct from any document-level restriction, same
NSW-established distinction (not separately re-checked for a Victoria
document footer, since the one PDF that might carry one isn't fetchable
- see above). Attribution to the Department of Transport and Planning is
a genuine requirement wherever this data is displayed or redistributed.

**Credentials**: a subscription key from the `Transport Victoria Open
Data Hub <https://opendata.transport.vic.gov.au/dataset/planned-disruptions-road>`_.
Env var: ``VIC_DISRUPTIONS_API_KEY`` (see ``.env.example``,
``scripts/smoke_test.py``).

**Real field values confirmed, not previously known**: ``impact.delay``
holds real free-text ranges (e.g. ``"0 to 5 min"``), not bare numbers -
confirms Phase 1's choice to never coerce impact fields to a number was
correct, not overcautious. ``rmaClass`` is a real, small coded set
(observed live: ``FW``, ``AO``, ``MU``, ``AH``, ``PR``, and a real
``None`` for ~7% of features) - genuinely a code, not free text, though
this module doesn't have authoritative definitions for what each code
means beyond ``FW`` (Freeway, inferred from context, not stated). ``id``
is a real structured string (e.g. ``"Planned:OneView:IMP-0119747"``), not
a bare UUID - the ``"Planned:"`` prefix suggests the source already
guards against collision with a future "unplanned" adapter's own ids,
though this is inferred from the string shape, not confirmed from
documentation. ``endIntersectionRoadName``/``endIntersectionLocality``
(not named in the OpenAPI spec's own schema, only discovered in a real
response) are genuinely common (92% populated in one real pull) and are
now included in ``WorksSite.location_description`` alongside the fields
Phase 1 already used - see
:mod:`streetworks.common.from_vic_disruptions`.

**What's still open** (not blocking - this module is Phase 2 confirmed,
but these details remain genuinely unverified):

1. The real relationship between a GeometryCollection's Point and
   LineString beyond "don't trust the line" (see above) - is the line
   always the containing route, or does that vary by ``eventType``?
   Only one real feature has been inspected closely enough to say.
2. Full ``rmaClass`` code definitions (``AO``/``MU``/``AH``/``PR`` beyond
   ``FW``) - observed live, not documented anywhere found.
3. The ``GeoJsonPoint``/``GeoJsonLine`` response shapes (this module
   always requests the default ``GeoJson`` collection shape).
4. Whether ``eventType`` ever has real values beyond "Roadworks"/"Special
   event" (2/500 real features in one pull) - a small real minority
   worth knowing about, not filtered out here, the same treatment NSW's
   real ferry-hazard minority gets.
"""

from __future__ import annotations

from typing import Any, Literal

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "VicDisruptionsClient", "parse_features"]

JSON = dict[str, Any]
Format = Literal["GeoJson", "GeoJsonPoint", "GeoJsonLine"]

BASE_URL = "https://api.opendata.transport.vic.gov.au/opendata/roads/disruptions"
_PLANNED_PATH = "planned/v1/"

#: A defensive cap on pagination loops in iter_planned_disruptions() - a
#: malformed/looping hasMoreRecords response shouldn't hang a caller
#: forever. 1000 records/page per the spec; this allows up to 1,000,000
#: records before giving up, far beyond any plausible real total.
_MAX_PAGES = 1000


def parse_features(payload: JSON) -> list[JSON]:
    """Parse a real ``FeatureCollection`` response into a list of feature
    dicts, unchanged from the source shape - unlike NSW's
    ``_clean_properties``, real Victorian features checked so far don't
    show the same empty-string/null-placeholder pollution, so nothing is
    coerced/cleaned here."""
    features = payload.get("features") or []
    return [f for f in features if isinstance(f, dict)]


class VicDisruptionsClient:
    """Fetch Victorian planned road disruptions from DTP's Planned
    Disruptions - Road API. **Phase 2 confirmed - see module docstring.**

    Requires a Transport Victoria Open Data Hub subscription key (see
    module docstring).

    >>> from streetworks.au.vic import VicDisruptionsClient
    >>> with VicDisruptionsClient(api_key=api_key) as vic:  # doctest: +SKIP
    ...     for feature in vic.iter_planned_disruptions():
    ...         print(feature["id"], feature["properties"].get("eventType"))
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

    def get_planned_disruptions(
        self, *, format: Format = "GeoJson", next_page_token: str | None = None
    ) -> JSON:
        """``GET planned/v1/?format=<format>`` - one page (up to 1000
        records per the spec). Pass ``next_page_token`` (a previous
        response's ``nextPageDetails.nextPageToken``) to continue, or use
        :meth:`iter_planned_disruptions` to page through automatically."""
        headers = {"KeyID": self.api_key}
        if next_page_token:
            headers["NextPageToken"] = next_page_token
        response = self._transport.request(
            "GET",
            f"{self.base_url}/{_PLANNED_PATH}",
            params={"format": format},
            headers=headers,
        )
        return response.json()

    def iter_planned_disruptions(self, *, format: Format = "GeoJson") -> list[JSON]:
        """Every planned-disruption feature, paging automatically via
        ``nextPageDetails`` until ``hasMoreRecords`` is false (or
        :data:`_MAX_PAGES` is hit, as a defensive guard - see module
        constant). Already planned-disruptions-only by construction."""
        features: list[JSON] = []
        token: str | None = None
        for _ in range(_MAX_PAGES):
            payload = self.get_planned_disruptions(format=format, next_page_token=token)
            features.extend(parse_features(payload))
            next_page = payload.get("nextPageDetails") or {}
            if not next_page.get("hasMoreRecords"):
                break
            token = next_page.get("nextPageToken")
            if not token:
                break
        return features

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> VicDisruptionsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
