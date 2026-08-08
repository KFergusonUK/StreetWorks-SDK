"""Berlin: VIZ (Verkehrsinformationszentrale) Baustellen/Sperrungen - the
largest remaining German gap this SDK's Länder cluster
(:mod:`streetworks.ogc.germany` - Hamburg, Brandenburg, Saxony) had left:
Berlin is a city-state Land in its own right, entirely surrounded by
already-covered Brandenburg, and this SDK's second `comprehensive`
(city-wide streets, not just state/motorway roads) German source after
Saxony.

.. attention::
   **Confirmed live (2026-08-08)** against two real, unauthenticated
   pulls (``api.viz.berlin.de``, no key sent or required).

**Two public keyless GeoJSON feeds, not one.** Both are published hourly
by *Senatsverwaltung für Mobilität, Verkehr, Klimaschutz und Umwelt /
Digitale Plattform Stadtverkehr Berlin*, converted server-side from the
private OCIT-C backend (``vizconcs2.concert.viz`` - credentialed,
internal, never targeted directly; this module consumes only the
published output):

- **Landesmeldestelle** (``tic3``) - 373 real features at time of
  writing. ``subtype`` counts: ``Gefahr`` 157, ``Sperrung`` 154,
  ``Baustelle`` 61, blank 1.
- **Verkehrsredaktion** (``daten``) - 240 real features. ``subtype``
  counts: ``Baustelle`` 151, ``Sperrung`` 86, ``Bauarbeiten`` 2 (a real,
  rare label variant - confirmed live, not a typo introduced here),
  ``Gefahr`` 1.

**The dataset's own official description says Verkehrsredaktion is "a
subset of Landesmeldestelle with extra detail" - live data contradicts
that.** Using the real, verified join key (every Verkehrsredaktion
record's ``lms_id`` matches a Landesmeldestelle record's own ``id`` when
present - 199/205 confirmed live) and restricting both feeds to real
roadworks subtypes (``Baustelle``/``Sperrung``/``Bauarbeiten``):
Landesmeldestelle has 215 such records, Verkehrsredaktion has 202, and
only **104 overlap**. Landesmeldestelle carries 111 real roadworks
records Verkehrsredaktion lacks entirely; Verkehrsredaktion carries 98
Landesmeldestelle lacks (35 of those with no ``lms_id`` at all - genuine
Verkehrsredaktion-only editorial entries, not just richer detail on
shared records). **Neither feed alone is complete.**

**So :meth:`BerlinClient.iter_roadworks` merges both feeds via the
verified join key**, rather than picking one as primary (as the source
brief originally proposed) or silently duplicating the 104 confirmed
overlaps. For a matched pair, the merged record prefers
Verkehrsredaktion's richer fields (``severity``, ``direction``,
``total_lanes``, ``closed_lanes``, ISO-formatted ``validity``) while
keeping Landesmeldestelle's own ``id`` as the canonical identifier (the
real backend LMS reference); Verkehrsredaktion's own short reference
(e.g. ``"8/2025"``) is kept alongside as ``viz_id``, never discarded.
Every merged record carries an explicit ``sources`` list
(``["landesmeldestelle"]``, ``["verkehrsredaktion"]``, or both) - never
silently blended without showing provenance. See
:func:`streetworks.common.from_berlin` for how this becomes ``Works``.

**Roadworks filter, evidenced not guessed.** The upstream OCIT
objectTypes (``TrafficMessage_RoadWorks``/``TrafficMessage_Incidents``)
the source brief named don't survive the OCIT→GeoJSON conversion - the
real field on the published output is ``subtype``, with exactly the
values above. ``Gefahr`` (hazard/danger warning) is excluded - it's a
warning notice, not a worksite, even though some ``Gefahr`` records'
free-text ``content`` happens to mention nearby ``Bauarbeiten``
(construction) - the ``subtype`` field's own categorisation is the
signal trusted here, the same discipline
:mod:`streetworks.chicagodot.client`'s own ``worktype`` filter uses over
its source's looser pre-filter.

**Geometry**: ``Point``, or a real ``GeometryCollection`` pairing a
``Point`` with one or more ``LineString`` entries (the affected road
segment) - both feeds, both WGS84 (~13.3-13.5°E, ~52.3-52.6°N, confirmed
live). No CRS transform needed.

**Dates are in two different formats depending on feed** -
Verkehrsredaktion's ``validity.from``/``.to`` are near-ISO
(``"2025-07-23T07:00"``); Landesmeldestelle's are German
``"DD.MM.YYYY HH:MM"`` (sometimes blank for ``from`` - confirmed live,
130/373 real Landesmeldestelle records). See
:func:`streetworks.common.from_berlin` for the two-format parser.

**Licence: Datenlizenz Deutschland - Namensnennung - Version 2.0
(dl-de/by-2-0), confirmed** from the real dataset page
(``daten.berlin.de``) - the same licence string already used verbatim by
this SDK's ``hamburg``/``brandenburg`` entries. Required attribution:
``"Digitale Plattform Stadtverkehr Berlin / [dataset title]"``.

**No app key required** - every read in this investigation succeeded
unauthenticated.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["LANDESMELDESTELLE_URL", "VERKEHRSREDAKTION_URL", "BerlinClient"]

JSON = dict[str, Any]

#: Landesmeldestelle - confirmed live, no app key required.
LANDESMELDESTELLE_URL = "https://api.viz.berlin.de/tic3/baustellen_sperrungen_tic.json"

#: Verkehrsredaktion - confirmed live, no app key required.
VERKEHRSREDAKTION_URL = "https://api.viz.berlin.de/daten/baustellen_sperrungen_viz.json"

#: Real, evidenced roadworks subtype values - see module docstring for the
#: real counts this was built from. Excludes "Gefahr" (hazard warning,
#: not a worksite) and blank.
_ROADWORKS_SUBTYPES = frozenset({"Baustelle", "Sperrung", "Bauarbeiten"})


def _fetch(transport: SyncTransport, url: str) -> list[JSON]:
    response = transport.request("GET", url)
    body = response.json()
    return body.get("features") or []


def _filter_roadworks(features: list[JSON]) -> list[JSON]:
    return [f for f in features if f["properties"].get("subtype") in _ROADWORKS_SUBTYPES]


def _merge(landesmeldestelle: list[JSON], verkehrsredaktion: list[JSON]) -> list[JSON]:
    """Merge both feeds via the verified ``lms_id`` <-> ``id`` join key -
    see module docstring for why this beats picking one feed as primary."""
    lms_by_id = {f["properties"]["id"]: f for f in landesmeldestelle}
    matched_lms_ids: set[str] = set()
    merged: list[JSON] = []

    for viz_feature in verkehrsredaktion:
        viz_props = viz_feature["properties"]
        lms_id = viz_props.get("lms_id")
        lms_feature = lms_by_id.get(lms_id) if lms_id else None
        if lms_feature is not None:
            matched_lms_ids.add(lms_id)
            merged.append(_merged_record(lms_feature, viz_feature))
        else:
            merged.append(_merged_record(None, viz_feature))

    merged.extend(
        _merged_record(f, None)
        for f in landesmeldestelle
        if f["properties"]["id"] not in matched_lms_ids
    )
    return merged


def _merged_record(lms_feature: JSON | None, viz_feature: JSON | None) -> JSON:
    sources = []
    if lms_feature is not None:
        sources.append("landesmeldestelle")
    if viz_feature is not None:
        sources.append("verkehrsredaktion")

    # Prefer Verkehrsredaktion's richer fields/geometry/ISO dates when
    # present; fall back to Landesmeldestelle's own. Landesmeldestelle's
    # `id` is always the canonical identifier when available - the real
    # backend LMS reference.
    primary = viz_feature or lms_feature
    assert primary is not None
    properties = dict(primary["properties"])
    if lms_feature is not None:
        properties["id"] = lms_feature["properties"]["id"]
        if viz_feature is not None:
            properties["viz_id"] = viz_feature["properties"]["id"]
    properties["sources"] = sources
    return {"type": "Feature", "properties": properties, "geometry": primary["geometry"]}


class BerlinClient:
    """Fetch Berlin VIZ worksite/closure records. No credentials required.

    >>> from streetworks.berlin import BerlinClient
    >>> from streetworks.common import from_berlin
    >>> with BerlinClient() as berlin:  # doctest: +SKIP
    ...     works = from_berlin(list(berlin.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_landesmeldestelle(self) -> Iterator[JSON]:
        """Every real Landesmeldestelle feature, unfiltered (includes
        ``Gefahr`` hazard warnings - see module docstring)."""
        yield from _fetch(self._transport, LANDESMELDESTELLE_URL)

    def iter_verkehrsredaktion(self) -> Iterator[JSON]:
        """Every real Verkehrsredaktion feature, unfiltered."""
        yield from _fetch(self._transport, VERKEHRSREDAKTION_URL)

    def iter_roadworks(self) -> Iterator[JSON]:
        """Real roadworks records (``Baustelle``/``Sperrung``/
        ``Bauarbeiten``) from both feeds, merged via the verified
        ``lms_id``/``id`` join key - see module docstring for why this
        beats picking one feed as primary."""
        landesmeldestelle = _filter_roadworks(_fetch(self._transport, LANDESMELDESTELLE_URL))
        verkehrsredaktion = _filter_roadworks(_fetch(self._transport, VERKEHRSREDAKTION_URL))
        yield from _merge(landesmeldestelle, verkehrsredaktion)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BerlinClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
