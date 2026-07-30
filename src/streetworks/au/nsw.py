"""New South Wales: TfNSW Live Traffic Hazards - roadworks and major
events, two of six hazard types (Incident/Fire/Flood/Alpine/MajorEvent/
Roadwork) published in one shared GeoJSON API. This SDK's first
Australian provider.

**Architecture: one adapter, parameterised over layer - not one adapter
per layer.** All six hazard types (plus the differently-shaped
``regional-lga-*`` composites) share the identical ``FeatureCollection``/
``Feature`` schema, confirmed directly from the guide's own schema
tables, and differ only in ``layerName`` and the endpoint filename. A
separate module per layer would be several near-duplicate parsers over
one real schema. This module covers the two **planned** (works-relevant)
layers - ``roadwork`` and ``majorevent`` - via :meth:`NswLiveTrafficClient.get_features`/
:meth:`~NswLiveTrafficClient.iter_features`, plus the ``roadwork``-only
:meth:`~NswLiveTrafficClient.get_roadworks`/:meth:`~NswLiveTrafficClient.iter_roadworks`
convenience pair (unchanged from this module's first version) and the
equivalent ``majorevent``-only
:meth:`~NswLiveTrafficClient.get_major_events`/:meth:`~NswLiveTrafficClient.iter_major_events`.
The four **unplanned** layers (``incident``/``fire``/``flood``/``alpine``)
and the ``regional-lga-*`` composites are deliberately **not** built here -
out of scope for a works SDK, per the source investigation brief - though
adding one is a small, mechanical extension of :data:`LAYERS` if ever
needed, not a design change.

.. attention::
   **PHASE 2 CONFIRMED (2026-07-30)** - verified against a real
   authenticated pull, by a tester running ``scripts/smoke_test.py`` with
   a real TfNSW API Gateway key. Both ``roadwork`` (363 real features) and
   ``majorevent`` (19 real features) returned genuine live data. This
   found and fixed **one real bug** (see "A real bug this confirmed"
   below) and confirmed almost everything else this module's Phase 1
   design guessed at. No longer grouped under the README's Credentials
   wanted section.

**A real bug this confirmed, now fixed**: the endpoint paths are
``roadwork/open``/``roadwork/closed``/``roadwork/all`` (and
``majorevent/open``/etc.) - **not** ``roadwork-open.json``-style. Phase 1
read the Developer Guide's own Table 1 literally and followed *that* over
the source investigation brief's paraphrase, reasoning the primary
document was more authoritative - a live pull with a real key proved this
backwards: ``roadwork-open.json`` returns a genuine ``404`` even with a
valid key (not just an auth failure), while ``roadwork/open`` returns
``200`` with real data. The guide's own documented file-naming convention
does not match what the live gateway actually routes - a real, humbling
lesson that reading a primary source directly still doesn't beat a live
probe. The investigation brief's original guess was right all along.

**Auth confirmed correct on the first real attempt**: ``Authorization:
apikey <key>`` - this module's Phase 1 default guess (based on other
TfNSW Open Data APIs' documented convention, since the Developer Guide
itself never states the header format) worked against the real gateway
with no changes needed.

**Not DATEX II - TfNSW's own hazards GeoJSON schema**, shared across all
six hazard types. Confirmed directly from the guide's own schema tables
and now from real data: a ``FeatureCollection`` with ``rights``/
``layerName``/``lastPublished``/``features``, each ``Feature`` a standard
``{type, id, geometry, properties}`` shape. **A correction to Phase 1's
own reading of the schema table**: real ``layerName`` values are
``"Roadwork-Open"``/``"MajorEvent-Open"`` (with the file's own open/
closed/all suffix), not the bare ``"RoadWork"``/``"MajorEvent"`` the
schema table's enumeration implied. Since these files are already
filtered by layer by TfNSW (unlike Sweden's own broader ``Situation``
feed - see :mod:`streetworks.datex2.trafikverket`), no in-record
discriminator is needed to tell roadwork/major-event features apart from
other hazard *types* - the same shape of confidence Digitraffic's
endpoint has (see :mod:`streetworks.datex2.digitraffic`). **But real data
shows the ``roadwork`` layer is not perfectly pure**: 5/363 real features
in one live pull were ``mainCategory: "FERRY OUT OF SERVICE"``
(``CategoryIcon: "Hazard"``, not ``"Roadworks"``) - ferry-service
disruptions, not roadworks, sitting in the roadwork-only endpoint.
Genuinely rare (~1.4%) and not filtered out by this module (matching
Digitraffic's own precedent of not second-guessing what an endpoint's own
name promises) - callers wanting strict purity can filter on
``properties["CategoryIcon"] == "Roadworks"`` themselves.

**``id`` is unique only within a layer, confirmed from the guide's own
property table** ("Uniquely identifies this hazard from all other
hazards in the same layer") - a real roadwork ``82681`` and a real
major-event ``82681`` are not guaranteed distinct. Every parsed feature
carries ``layerName`` alongside ``id`` (see :func:`parse_features`), and
:func:`streetworks.common.from_nsw_livetraffic.from_nsw_livetraffic`
builds ``Works.reference`` as the composite ``f"{layer}:{id}"`` - never
the bare ``id`` alone, once a caller might mix layers. **Also confirmed
live**: real ``id`` values are sometimes JSON floats (e.g. ``281450.0``,
43/363 in one pull), not always ints - normalised to ``int`` before
building the composite reference so it never renders a spurious ``.0``.

**A second, real ``layerName`` footgun, caught before shipping rather
than after**: the raw ``layerName`` a real response states is not
status-independent - confirmed live (2026-07-30) that ``roadwork/open``
returns ``layerName: "Roadwork-Open"``, ``roadwork/closed`` returns
``"Roadwork-Closed"``, and ``roadwork/all`` returns bare ``"Roadwork"``
(``majorevent/*`` mirrors this exactly) - three different strings for
the *same* layer, varying only by which status endpoint happened to be
queried, not by what the hazard is. Building the composite reference
from the raw value would give the same real-world hazard a different
``Works.reference`` depending on whether a caller fetched it via
``status="open"`` or ``status="all"`` - silently breaking any
deduplication or tracking that relies on the reference being stable.
:func:`parse_features` therefore also computes a normalised ``layer``
field (:func:`_normalize_layer` strips a real, confirmed ``-Open``/
``-Closed`` suffix, case-insensitively) and the composite reference is
built from *that*, not the raw ``layerName`` - which stays available
verbatim for anything that wants the literal server value.

**Auth**: ``Authorization: apikey <key>`` - confirmed correct against the
real gateway (see above). Override via ``header_format`` remains
available (e.g. ``header_format="Bearer {key}"``) in case a different
account/key type ever needs a different scheme, but the default is now
known-good, not a guess.

**Geometry**: real coordinates are GeoJSON-native ``[lon, lat]``
(confirmed from real data throughout, e.g. ``[151.1737592, -33.8717729]``
for a real Sydney feature). Carried through in that native order, never
flipped to DATEX's ``(lat, lon)`` convention - stated explicitly, per
this SDK's standing CRS/axis-order policy. **``geometry.type`` casing is
inconsistent across hazard types** (the guide's own roadwork/incident
examples use ``"Point"``; its fire example and schema table use
``"POINT"``) - matched case-insensitively here, not on exact string.
**A hazard's point geometry is a centroid, not its true extent** - the
affected road linework is separately encoded in ``encodedPolylines``
(Google's Encoded Polyline Algorithm Format, decoded by a small local
decoder in :mod:`streetworks.common.from_nsw_livetraffic` - no new
dependency) when present; still not seen populated in any real record
checked (363 roadwork + 19 majorevent, one live pull) - the decoder
remains unverified against real polyline data, see "What's still open".
**A real, cautionary lesson from Victoria applies here even though it
hasn't been checked directly for NSW**: this module's design assumed
``encodedPolylines`` is a more-*precise* view of the *same* worksite the
Point marks - the DATEX/WZDx shape. A real Victorian feature disproved
that exact assumption for a structurally similar Point-plus-line pairing
(its companion LineString turned out to span an entire ~150km highway
corridor - the traffic-impact extent, not the site - see
:mod:`streetworks.au.vic`'s own module docstring). Until a real NSW
``encodedPolylines`` value has actually been decoded and checked against
its own Point, **do not assume it's worksite linework rather than a
broader affected-corridor/diversion extent** - the same trap, unverified
here rather than fixed, since there's nothing real to check yet.

**Semantic sentinels, confirmed from the guide's own field descriptions,
not just its general "disregard empty/null" warning, and now from real
data too**: ``expectedDelay`` of ``0`` *or* ``-1`` means "no delay
information available", not zero delay (guide's own wording, quoted in
:func:`_none_if_sentinel`'s docstring) - real data confirms ``-1`` is the
overwhelmingly common real value. Coerced to ``None`` before any field
mapping, so a genuine "no data" ``0``/``-1`` is never mistaken for a real
value.

**A real, previously-unflagged footgun, confirmed to recur across real
records, not a one-off**: ``subCategoryA`` holds the **literal string**
``"null"`` (four characters) on some real records, not the JSON value
``null`` - and a real project name (e.g. "Bridge work") on others, so it
genuinely is a populated, meaningful field, not a placeholder-only one.
:func:`_clean_properties` (the guide's own documented "disregard empty/
null properties" rule) deliberately does **not** treat the string as
empty - only real ``None``/``""``/whitespace-only/``[]`` are stripped.

**No gazetteer join key exists anywhere in this feed** - confirmed
against real data throughout: ``roads[]`` is free text only
(``mainStreet``, ``crossStreet``, ``secondLocation``, ``locationQualifier``,
``suburb``, ``region``), no identifier of any kind. Weaker than NWB's
``bag_orl`` gap (which at least carries an id) - there is nothing to join
on here at all. ``WorksSite.location_description`` is built by joining
the free-text fields; no ``street_ref``/``location_usrn`` is populated.

**Dates**: ``start``/``end`` are epoch-millis UTC, but the guide's own
field description calls ``end`` the date a *planned* hazard "is
**scheduled** to end" - true even once ``ended`` is true, since nothing
in the schema distinguishes a confirmed actual-completion timestamp from
the last-known schedule. So both map to ``proposed_start``/
``proposed_end`` with :attr:`~streetworks.common.DateConfidence.ESTIMATED`
throughout, never ``actual_start``/``actual_end`` - stating what the
source actually claims, not upgrading its confidence.

**The main ``roadwork`` layer genuinely does include local/council-road
works, confirmed live** - real ``isLocalRoad`` values split 357 "State
road" : 6 "Local road" (~1.7%) in one live pull of 363 features. This
settles what was Phase 1's open question 3: council works are **not**
siloed away in the separate ``regional-lga-*`` layers this module
doesn't fetch - they show up (rarely) in the main layer too. Given the
real split is overwhelmingly state-road with only a small genuine local
minority, ``network_scope`` is set to
:attr:`~streetworks.registry.NetworkScope.STRATEGIC` with this real
minority noted in the registry's ``scope_note``, the same "don't force a
finer split than the evidence warrants" treatment TrafficWatchNI/Saxony's
own two-tier real findings got, rather than promoting to
``COMPREHENSIVE`` on a ~1.7% real minority.

**Licence**: **Creative Commons Attribution (CC-BY)**, confirmed live via
the TfNSW Open Data Hub's own catalogue page for this dataset, tagged
directly as a coded licence facet, and confirmed a second way in every
real response's own ``rights.licence`` field (a URL,
``https://opendata.transport.nsw.gov.au/dataset/live-traffic-hazards``,
not a bare licence-name string). **Distinct from the Developer Guide
PDF's own copyright footer** (confirmed by reading the guide directly:
*"Users are welcome to copy, reproduce and distribute the information
contained in this report for non-commercial purposes only..."*) - that
line restricts the *document*, not the *feed*; this module consumes the
feed. Attribution to Transport for NSW is a genuine CC-BY requirement,
not a nicety - surface it wherever this data is displayed or
redistributed.

**Credentials**: free self-service registration on the `TfNSW API
Gateway <https://opendata.transport.nsw.gov.au/>`_. Env var:
``NSW_LIVETRAFFIC_API_KEY`` (see ``.env.example``,
``scripts/smoke_test.py``).

**What's still open** (not blocking - this module is Phase 2 confirmed,
but these details remain genuinely unverified):

1. Real coverage of ``encodedPolylines`` - never seen populated in any
   real record checked yet (382 real features across both layers, one
   live pull). The decoder is written to the standard published
   algorithm but has never decoded a real TfNSW value, **and whether a
   real value represents worksite linework or a broader affected-
   corridor/diversion extent is unconfirmed** - see the real Victoria
   precedent above, where the equivalent assumption was wrong.
2. Whether ``majorevent``'s ``mainCategory``/``CategoryIcon`` vocabulary
   is as consistent as the one real pull suggests (19/19 real records
   were uniformly ``"SPECIAL EVENT"``/``"PublicEvent"``) - a single
   pull's uniformity isn't proof it's always that narrow.
3. Whether real ``majorevent`` records ever carry ``isLocalRoad:
   "Local road"`` the way ``roadwork`` rarely does - not seen in the one
   real pull (19/19 were "State road"), but a small sample.
"""

from __future__ import annotations

from typing import Any, Literal

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "LAYERS", "NswLiveTrafficClient", "parse_features"]

JSON = dict[str, Any]
Layer = Literal["roadwork", "majorevent"]
Status = Literal["open", "closed", "all"]

BASE_URL = "https://api.transport.nsw.gov.au/v1/live/hazards"

#: The two *planned* (works-relevant) hazard layers this module covers -
#: see module docstring's "Architecture" note for why the four unplanned
#: layers and the regional-lga composites are deliberately out of scope.
LAYERS: tuple[Layer, ...] = ("roadwork", "majorevent")


def _path(layer: Layer, status: Status) -> str:
    """``<layer>/<status>`` - confirmed live against a real key (2026-07-30):
    ``roadwork/open``/``roadwork/closed``/``roadwork/all`` and
    ``majorevent/open`` all return real ``200`` data. The Developer
    Guide's own Table 1 literally names ``<layer>-<status>.json``-style
    filenames instead; a real key gets a genuine ``404`` on those (not an
    auth failure), proving the guide's documented naming doesn't match
    what the live gateway actually routes - see module docstring."""
    return f"{layer}/{status}"


#: Fields the Developer Guide states use 0/-1 as an explicit "no data"
#: sentinel, not a real zero - see module docstring.
_SENTINEL_FIELDS = ("expectedDelay", "speedLimit", "queueLength")


def _none_if_sentinel(properties: JSON, field: str) -> None:
    """Guide's own wording for ``expectedDelay``: "A value of 0 or -1
    indicates that there is no delay information available." Applied to
    ``speedLimit``/``queueLength`` too, per the investigation brief this
    module was built from - not independently re-confirmed in the guide's
    own text for those two this session."""
    value = properties.get(field)
    if value in (0, -1):
        properties[field] = None


def _clean_properties(properties: JSON) -> JSON:
    """The guide's own documented rule (section 3.1): disregard properties
    that are empty strings, whitespace-only strings, empty arrays, or
    null. Deliberately does **not** touch the literal string ``"null"``
    (a real, distinct footgun found in the sample data - see module
    docstring)."""
    cleaned: JSON = {}
    for key, value in properties.items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        if isinstance(value, list) and len(value) == 0:
            continue
        cleaned[key] = value
    for field in _SENTINEL_FIELDS:
        if field in cleaned:
            _none_if_sentinel(cleaned, field)
    return cleaned


#: Real layerName values carry a status suffix that varies by *which
#: status endpoint was queried*, not by what the hazard actually is -
#: confirmed live (2026-07-30): roadwork/open -> "Roadwork-Open",
#: roadwork/closed -> "Roadwork-Closed", roadwork/all -> bare "Roadwork"
#: (majorevent/* mirrors this exactly). Stripped here so the *same* real
#: hazard fetched via two different statuses normalises to the same
#: layer token - see _normalize_layer.
_STATUS_SUFFIXES = ("-open", "-closed")


def _normalize_layer(layer_name: str | None) -> str | None:
    """Strip a real, confirmed status suffix (``-Open``/``-Closed``, any
    casing) from a raw ``layerName``, so ``Works.reference`` stays stable
    for the same hazard regardless of which status endpoint returned it.
    Without this, a real hazard fetched via ``roadwork/open`` and again
    via ``roadwork/all`` would build two different composite references
    (``"Roadwork-Open:<id>"`` vs ``"Roadwork:<id>"``) for the same
    real-world thing - silently breaking any caller that deduplicates or
    tracks hazards by reference across calls with different ``status``."""
    if not layer_name:
        return layer_name
    lowered = layer_name.lower()
    for suffix in _STATUS_SUFFIXES:
        if lowered.endswith(suffix):
            return layer_name[: -len(suffix)]
    return layer_name


def parse_features(payload: JSON) -> list[JSON]:
    """Parse a real ``FeatureCollection`` response into a list of cleaned
    feature dicts (``{"layerName", "layer", "type", "id", "geometry",
    "properties"}``, empty/null properties stripped per
    :func:`_clean_properties`) - the shape
    :func:`streetworks.common.from_nsw_livetraffic.from_nsw_livetraffic`
    consumes. ``layerName`` is the collection's own real value, copied
    onto every feature verbatim (real features don't carry it
    themselves); ``layer`` is the same value with any real status suffix
    stripped via :func:`_normalize_layer` - use ``layer``, not
    ``layerName``, for anything that needs to identify the *same* hazard
    consistently across ``status`` values, per the module docstring."""
    features = payload.get("features") or []
    layer_name = payload.get("layerName")
    layer = _normalize_layer(layer_name)
    cleaned: list[JSON] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = _clean_properties(feature.get("properties") or {})
        cleaned.append(
            {**feature, "properties": properties, "layerName": layer_name, "layer": layer}
        )
    return cleaned


class NswLiveTrafficClient:
    """Fetch NSW roadwork hazards from TfNSW's Live Traffic Hazards API.
    **Pending live verification - see module docstring**, especially the
    unconfirmed ``Authorization`` header format.

    Requires a TfNSW API Gateway key (free self-service registration -
    see module docstring).

    >>> from streetworks.au.nsw import NswLiveTrafficClient
    >>> with NswLiveTrafficClient(api_key=api_key) as nsw:  # doctest: +SKIP
    ...     for feature in nsw.iter_roadworks():
    ...         print(feature["id"], feature["properties"].get("mainCategory"))
    """

    def __init__(
        self,
        *,
        api_key: str,
        header_format: str = "apikey {key}",
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.header_format = header_format
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_features(self, layer: Layer, *, status: Status = "open") -> JSON:
        """``GET <layer>-<status>.json`` (or ``<layer>.json`` for
        ``"all"``) - see module docstring for why these literal filenames
        are used rather than the investigation brief's ``<layer>/<status>``
        paraphrase, and for why only ``"roadwork"``/``"majorevent"`` are
        valid here (see :data:`LAYERS`). Returns the parsed JSON
        ``FeatureCollection``."""
        response = self._transport.request(
            "GET",
            f"{self.base_url}/{_path(layer, status)}",
            headers={"Authorization": self.header_format.format(key=self.api_key)},
        )
        return response.json()

    def iter_features(self, layer: Layer, *, status: Status = "open") -> list[JSON]:
        """Every feature for ``layer``, empty/null properties stripped and
        ``layerName`` attached to each (see :func:`parse_features`).
        Already filtered to ``layer`` by construction - no in-record
        filtering needed, see module docstring."""
        return parse_features(self.get_features(layer, status=status))

    def get_roadworks(self, *, status: Status = "open") -> JSON:
        """``layer="roadwork"`` convenience wrapper over
        :meth:`get_features` - this module's best-confirmed layer (a real
        embedded sample exists; see module docstring)."""
        return self.get_features("roadwork", status=status)

    def iter_roadworks(self, *, status: Status = "open") -> list[JSON]:
        """``layer="roadwork"`` convenience wrapper over
        :meth:`iter_features`."""
        return self.iter_features("roadwork", status=status)

    def get_major_events(self, *, status: Status = "open") -> JSON:
        """``layer="majorevent"`` convenience wrapper over
        :meth:`get_features` - **more speculative than** :meth:`get_roadworks`,
        no real major-event sample has been seen, see module docstring's
        "What's still open" item 5."""
        return self.get_features("majorevent", status=status)

    def iter_major_events(self, *, status: Status = "open") -> list[JSON]:
        """``layer="majorevent"`` convenience wrapper over
        :meth:`iter_features`. See :meth:`get_major_events`."""
        return self.iter_features("majorevent", status=status)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> NswLiveTrafficClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
