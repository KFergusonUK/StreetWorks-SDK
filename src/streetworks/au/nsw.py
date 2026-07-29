"""New South Wales: TfNSW Live Traffic Hazards - roadworks, one of six
hazard types (Incident/Fire/Flood/Alpine/MajorEvent/Roadwork) published in
one shared GeoJSON API. This SDK's first Australian provider.

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
six hazard types, roadwork included. Confirmed directly from the guide's
own schema tables (not inferred): a ``FeatureCollection`` with
``rights``/``layerName``/``lastPublished``/``features``, each ``Feature``
a standard ``{type, id, geometry, properties}`` shape. ``layerName`` is
confirmed to be the literal string ``"RoadWork"`` for this endpoint.
Since these files are already filtered to roadworks by TfNSW (unlike
Sweden's own broader ``Situation`` feed - see
:mod:`streetworks.datex2.trafikverket`), no in-record roadworks
discriminator is needed here, the same shape of confidence Digitraffic's
endpoint has (see :mod:`streetworks.datex2.digitraffic`) - not something
derived from a field.

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
"""

from __future__ import annotations

import warnings
from typing import Any, Literal

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "NswLiveTrafficClient", "parse_features"]

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

BASE_URL = "https://api.transport.nsw.gov.au/v1/live/hazards"
_PATHS = {
    "open": "roadwork-open.json",
    "closed": "roadwork-closed.json",
    "all": "roadwork.json",
}

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
    feature dicts (``{"type", "id", "geometry", "properties"}``, empty/
    null properties stripped per :func:`_clean_properties`) - the shape
    :func:`streetworks.common.from_nsw_livetraffic` (not yet built - see
    the source investigation brief's own next-steps list) would consume."""
    features = payload.get("features") or []
    cleaned: list[JSON] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = _clean_properties(feature.get("properties") or {})
        cleaned.append({**feature, "properties": properties})
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

    def get_roadworks(self, *, status: Literal["open", "closed", "all"] = "open") -> JSON:
        """``GET roadwork-<status>.json`` (or ``roadwork.json`` for
        ``"all"``) - see module docstring for why these literal filenames
        are used rather than the investigation brief's ``roadwork/<status>``
        paraphrase. Returns the parsed JSON ``FeatureCollection``."""
        path = _PATHS[status]
        response = self._transport.request(
            "GET",
            f"{self.base_url}/{path}",
            headers={"Authorization": self.header_format.format(key=self.api_key)},
        )
        return response.json()

    def iter_roadworks(
        self, *, status: Literal["open", "closed", "all"] = "open"
    ) -> list[JSON]:
        """Every roadwork feature, empty/null properties stripped (see
        :func:`parse_features`). Already roadworks-only by construction -
        no in-record filtering needed, see module docstring."""
        return parse_features(self.get_roadworks(status=status))

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> NswLiveTrafficClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
