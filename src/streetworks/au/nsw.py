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
   **PENDING LIVE VERIFICATION.** Built directly from Transport for NSW's
   own "Live Traffic NSW Developer Guide" (v1.9, read in full this session,
   not just summarised) plus a live, credential-free probe of the real
   endpoint - see "What's confirmed" below - but no authenticated response
   has been seen. Grouped with Norway/Sweden/Denmark under the README's
   **Credentials wanted** section. Better-confirmed than any of those three
   were at the same stage in one respect - the guide embeds one genuine,
   complete real roadwork feature (id ``82681``, "Nelligen Bridge
   replacement project"), used verbatim as this module's test fixture,
   under CC-BY - not a synthetic reconstruction.

**What's confirmed, live, credential-free (2026-07)**: a bare request
against the real endpoint returns a genuine, structured rejection from a
real API gateway, not a generic error page::

    GET https://api.transport.nsw.gov.au/v1/live/hazards/roadwork-open.json
    -> HTTP 401, server: Layer7-API-Gateway
    {"ErrorDetails":{"...","Message":"The calling application is
    unauthenticated.","RequestedUrl":"/v1/live/hazards/roadwork-open.json",...}}

This confirms the endpoint and this exact path live, independent of the
Developer Guide's own claims. Sending a plausible-looking (invalid)
``Authorization: apikey ...`` or ``Authorization: Bearer ...`` header
produces the **identical** generic message either way - the gateway
authenticates before it will say anything scheme-specific, so this probe
could not narrow down the real header format (see "Auth" below).

**A correction to the source investigation brief this module was built
from**: the brief described the roadwork endpoints as ``roadwork/open``/
``roadwork/closed``/``roadwork/all``. Reading the Developer Guide's own
Table 1 directly gives different literal filenames -
``roadwork-open.json``/``roadwork-closed.json``/``roadwork.json``,
appended to the base URL. Both path shapes return the identical generic
401 from the gateway (see above), so this couldn't be settled by a live
probe alone; the guide's own literal text is followed here as the more
authoritative source. **Worth re-checking in Phase 2** if a real key
returns 404 rather than real data.

**Not DATEX II - TfNSW's own hazards GeoJSON schema**, shared across all
six hazard types. Confirmed directly from the guide's own schema tables
(not inferred): a ``FeatureCollection`` with ``rights``/``layerName``/
``lastPublished``/``features``, each ``Feature`` a standard
``{type, id, geometry, properties}`` shape. ``layerName`` is confirmed to
be the literal string ``"RoadWork"`` for the roadwork endpoint (the
guide's own schema table also lists ``"MajorEvent"`` as a valid value,
though no real ``majorevent`` sample was available to confirm it against
- see "What's still open" below). Since these files are already filtered
by layer by TfNSW (unlike Sweden's own broader ``Situation`` feed - see
:mod:`streetworks.datex2.trafikverket`), no in-record discriminator is
needed to tell roadwork/major-event features apart from other hazard
types - the same shape of confidence Digitraffic's endpoint has (see
:mod:`streetworks.datex2.digitraffic`).

**``id`` is unique only within a layer, confirmed from the guide's own
property table** ("Uniquely identifies this hazard from all other
hazards in the same layer") - a real roadwork ``82681`` and a real
major-event ``82681`` are not guaranteed distinct. Every parsed feature
carries ``layerName`` alongside ``id`` (see :func:`parse_features`), and
:func:`streetworks.common.from_nsw_livetraffic.from_nsw_livetraffic`
builds ``Works.reference`` as the composite ``f"{layerName}:{id}"`` -
never the bare ``id`` alone, once a caller might mix layers.

**Auth**: an ``Authorization`` header carrying an API key from free
self-service registration on the TfNSW API Gateway (confirmed: the guide
states this in prose, and the live 401 above confirms a header is
checked) - but **the exact header value format is not stated anywhere in
the 42-page Developer Guide** (searched the full document text directly
for "Authorization"/"apikey"/"Bearer" - zero matches). This module
defaults to ``f"apikey {api_key}"``, the convention publicly documented
for other TfNSW Open Data APIs (Trip Planner, GTFS-Realtime) - a
reasonable default, **not independently confirmed for this specific API**.
Override via ``header_format`` (e.g. ``header_format="Bearer {key}"``) if
Phase 2 shows this default is wrong - no code change needed.

**Geometry**: real coordinates are GeoJSON-native ``[lon, lat]``
(confirmed from the real embedded sample: ``[150.1431796, -35.6474524]`` -
150°E/35°S is genuinely coastal NSW; the reverse would place it in the
Southern Ocean). Carried through in that native order, never flipped to
DATEX's ``(lat, lon)`` convention - stated explicitly, per this SDK's
standing CRS/axis-order policy. **``geometry.type`` casing is
inconsistent across hazard types** (the guide's own roadwork/incident
examples use ``"Point"``; its fire example and schema table use
``"POINT"``) - matched case-insensitively here, not on exact string.
**A hazard's point geometry is a centroid, not its true extent** - the
affected road linework is separately encoded in ``encodedPolylines``
(Google's Encoded Polyline Algorithm Format, decoded by a small local
decoder in :mod:`streetworks.common.from_nsw_livetraffic` - no new
dependency) when present; the real Nelligen Bridge sample has none
(``"encodedPolylines":[]``), so ``Coordinate.points`` is ``None`` for
that fixture record, not because decoding failed.

**Semantic sentinels, confirmed from the guide's own field descriptions,
not just its general "disregard empty/null" warning**: ``expectedDelay``
of ``0`` *or* ``-1`` means "no delay information available", not zero
delay (guide's own wording, quoted in :func:`_none_if_sentinel`'s
docstring) - the same convention applies to ``speedLimit``/
``queueLength`` per the investigation brief this module was built from,
though only ``expectedDelay``'s wording was directly confirmed against
the guide's own text this session. Coerced to ``None`` before any field
mapping, so a genuine "no data" ``0``/``-1`` is never mistaken for a real
value.

**A real, previously-unflagged footgun found while reading the actual
fixture data**: the real sample's ``subCategoryA`` field holds the
**literal string** ``"null"`` (four characters), not the JSON value
``null``. :func:`_clean_properties` (the guide's own documented
"disregard empty/null properties" rule) deliberately does **not** treat
this string as empty - only real ``None``/``""``/whitespace-only/``[]``
are stripped, per the guide's literal wording. A string that merely
*looks* like a null deserves the same scepticism this SDK gives every
other secondhand claim: kept, not "fixed" by guessing intent.

**No gazetteer join key exists anywhere in this feed** - confirmed
directly against the real sample: ``roads[]`` is free text only
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

**Licence**: **Creative Commons Attribution (CC-BY)**, confirmed live via
the TfNSW Open Data Hub's own catalogue page for this dataset, tagged
directly as a coded licence facet. **Distinct from the Developer Guide
PDF's own copyright footer** (confirmed by reading the guide directly:
*"Users are welcome to copy, reproduce and distribute the information
contained in this report for non-commercial purposes only..."*) - that
line restricts the *document*, not the *feed*; this module consumes the
feed. Attribution to Transport for NSW is a genuine CC-BY requirement,
not a nicety - surface it wherever this data is displayed or
redistributed.

**Credentials**: free self-service registration on the `TfNSW API
Gateway <https://opendata.transport.nsw.gov.au/>`_ (per the investigation
brief this module was built from - not independently re-registered this
session). Env var: ``NSW_LIVETRAFFIC_API_KEY`` (see ``.env.example``,
``scripts/smoke_test.py``).

**What's still open until Phase 2** (a real credentialed pull):

1. The real ``Authorization`` header format (see "Auth" above).
2. Whether the real endpoint paths are ``roadwork-open.json``-style (this
   module's choice, per the guide's own Table 1) or ``roadwork/open``-style
   (the investigation brief's paraphrase) - a 404 vs real data will settle
   it.
3. Whether the main ``roadwork`` layer carries council/local-road works,
   or whether those are siloed in the separate ``regional-lga-*`` layers
   this module doesn't fetch - genuinely unconfirmed, hence
   ``network_scope=NetworkScope.UNKNOWN`` rather than a guessed value.
4. Real coverage of ``encodedPolylines`` (the one real sample has none) -
   the local decoder is written to the standard published algorithm but
   has never decoded a real TfNSW polyline.
5. **``majorevent`` has no real sample at all** - the guide's schema
   table lists identical fields to ``roadwork`` and confirms
   ``"MajorEvent"`` as a valid ``layerName``, but every field-population
   claim in this module was checked against a *roadwork* example only.
   Treat :meth:`~NswLiveTrafficClient.get_major_events`/
   :meth:`~NswLiveTrafficClient.iter_major_events` as more speculative
   than the ``roadwork`` methods until a real major-event feature is
   seen.
"""

from __future__ import annotations

import warnings
from typing import Any, Literal

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "LAYERS", "NswLiveTrafficClient", "parse_features"]

warnings.warn(
    "streetworks.au.nsw is a Credentials-wanted scaffold: built to TfNSW's "
    "documented API shape (see module docstring), not yet verified against "
    "a real authenticated response. Have a TfNSW API Gateway key? Running "
    "the smoke test and reporting back one real trimmed record would "
    "confirm this adapter - see the 'help wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues for exactly "
    "what's needed.",
    UserWarning,
    stacklevel=2,
)

JSON = dict[str, Any]
Layer = Literal["roadwork", "majorevent"]
Status = Literal["open", "closed", "all"]

BASE_URL = "https://api.transport.nsw.gov.au/v1/live/hazards"

#: The two *planned* (works-relevant) hazard layers this module covers -
#: see module docstring's "Architecture" note for why the four unplanned
#: layers and the regional-lga composites are deliberately out of scope.
LAYERS: tuple[Layer, ...] = ("roadwork", "majorevent")


def _path(layer: Layer, status: Status) -> str:
    """Every layer shares the same ``<layer>-<status>.json``/``<layer>.json``
    filename convention, confirmed from the guide's own Table 1 for
    ``roadwork`` - not independently re-confirmed for ``majorevent``,
    which the table describes identically but no live probe has targeted."""
    if status == "all":
        return f"{layer}.json"
    return f"{layer}-{status}.json"


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


def parse_features(payload: JSON) -> list[JSON]:
    """Parse a real ``FeatureCollection`` response into a list of cleaned
    feature dicts (``{"layerName", "type", "id", "geometry", "properties"}``,
    empty/null properties stripped per :func:`_clean_properties`) - the
    shape :func:`streetworks.common.from_nsw_livetraffic.from_nsw_livetraffic`
    consumes. ``layerName`` is copied from the collection onto every
    feature (real features don't carry it themselves - only the
    surrounding ``FeatureCollection`` does) since ``id`` is only unique
    *within* a layer - see module docstring."""
    features = payload.get("features") or []
    layer_name = payload.get("layerName")
    cleaned: list[JSON] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = _clean_properties(feature.get("properties") or {})
        cleaned.append({**feature, "properties": properties, "layerName": layer_name})
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
