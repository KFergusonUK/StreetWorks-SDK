"""Victoria: DTP Planned Disruptions - Road, the second member of the
:mod:`streetworks.au` cluster. Permit-Team-validated, richer-structured
than New South Wales' feed, but with **no real sample seen anywhere** -
weaker fixture provenance than NSW despite the schema itself being
better-typed.

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
   **PENDING LIVE VERIFICATION - more speculative than NSW.** Built from
   the real, machine-readable OpenAPI 3.0.1 spec (fetched and parsed
   directly, not just summarised - see "What's confirmed" below) plus a
   live, credential-free probe of the real endpoint. Unlike NSW, **no
   real payload has ever been seen anywhere** - the spec's own Swagger UI
   cannot render a preview (its own description says so, due to response
   size), and the linked technical documentation PDF is not publicly
   fetchable (confirmed this session - the blob storage account returns
   ``PublicAccessNotPermitted``, not a broken link). So while the schema
   itself is better-typed than NSW's, the actual data shapes - coordinate
   order, timestamp format, and whether the ``string``-typed "numeric"
   impact fields (``delay``/``numberLanesImpacted``/``speedLimitOnSite``)
   contain bare numbers or free text - are all genuinely unconfirmed. The
   test fixture is therefore **synthetic** (structurally correct per the
   real schema, invented values), unlike NSW's real transcribed sample.

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

**Dates are genuinely unresolved** - ``duration.start``/``end`` are typed
``string`` with no confirmed format anywhere (ISO-8601 vs epoch millis
vs something else). NSW's feed happened to use epoch millis; nothing
here confirms Victoria does too, and guessing wrong would silently
produce wrong dates rather than an honest gap. This module tries
:func:`streetworks._dt.parse_iso8601` (the SDK's existing tolerant
ISO-8601 parser) and falls back to ``None``, never epoch-millis division,
if that fails - the safer wrong-format failure mode, since a genuine
ISO string run through an epoch-millis parser would produce a wildly
implausible date that's easy to notice, while the reverse could produce
a plausible-looking wrong date.

**Geometry**: only the default ``format=GeoJson`` (``GeometryCollection``)
shape is parsed here, since it's the only one the schema documents in
detail; ``GeoJsonPoint``/``GeoJsonLine`` are accepted by
:meth:`VicDisruptionsClient.get_planned_disruptions`'s ``format``
parameter but their exact response shape (a bare geometry object,
presumably, but unconfirmed) isn't specially handled - the parser reads
defensively and won't crash on either shape, but only the collection
form has been checked against the real spec. Coordinate order is
presumed GeoJSON-native ``[lon, lat]`` (Victoria sits ~145°E/37°S, so a
real value should read like ``[145.x, -37.x]``) - **not independently
confirmed**, since no real coordinate has been seen.

**Licence**: **Creative Commons Attribution 4.0**, confirmed live via
the dataset resource page - stated directly, satisfying the Open
Definition. Distinct from any document-level restriction, same
NSW-established distinction (not separately re-checked for a Victoria
document footer, since the one PDF that might carry one isn't fetchable
- see above). Attribution to the Department of Transport and Planning is
a genuine requirement wherever this data is displayed or redistributed.

**Credentials**: a subscription key from the `Transport Victoria Open
Data Hub <https://opendata.transport.vic.gov.au/dataset/planned-disruptions-road>`_
(per the source investigation brief - not independently re-registered
this session). Env var: ``VIC_DISRUPTIONS_API_KEY`` (see
``.env.example``, ``scripts/smoke_test.py``).

**What's still open until Phase 2** (a real credentialed pull):

1. Real coordinate order/values (presumed ``[lon, lat]``, unconfirmed).
2. The real ``duration.start``/``end`` timestamp format.
3. Whether the ``string``-typed impact fields (``delay``/
   ``numberLanesImpacted``/``speedLimitOnSite``) hold bare numbers, units
   attached ("15 min"), or free text - carried through as plain strings
   here, never coerced to a number that might silently misparse a shape
   never seen.
4. Whether ``localGovernmentArea`` is a controlled code/enum (as the
   source investigation brief assumed) or free text (as the schema alone
   states - just ``"string"``, no enum given).
5. The ``GeoJsonPoint``/``GeoJsonLine`` response shapes.
6. Whether real ``id`` values could ever collide with a future
   "unplanned" adapter's own ids, the way NSW's do across layers -
   unknown, since unplanned isn't built here to compare against.
"""

from __future__ import annotations

import warnings
from typing import Any, Literal

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "VicDisruptionsClient", "parse_features"]

warnings.warn(
    "streetworks.au.vic is a Credentials-wanted scaffold: built to DTP's "
    "documented API shape (see module docstring), not yet verified against "
    "a real authenticated response - and unlike NSW, no real sample has "
    "ever been seen for this one, so the schema types are more speculative "
    "too. Have a Transport Victoria Open Data Hub key? Running the smoke "
    "test and reporting back one real trimmed record would confirm this "
    "adapter - see the 'help wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues for exactly "
    "what's needed.",
    UserWarning,
    stacklevel=2,
)

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
    dicts, unchanged from the source shape - see module docstring for why
    nothing is coerced/cleaned here the way NSW's ``_clean_properties``
    is: no real response has been seen to confirm what cleaning, if any,
    is warranted."""
    features = payload.get("features") or []
    return [f for f in features if isinstance(f, dict)]


class VicDisruptionsClient:
    """Fetch Victorian planned road disruptions from DTP's Planned
    Disruptions - Road API. **Pending live verification - see module
    docstring**, more speculative than NSW's adapter (no real sample seen
    anywhere for this one).

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
