"""German state (Bundesland) roadworks - a declarative field-map registry
over :class:`~streetworks.ogc.client.OGCFeaturesClient`.

Adding a new state is writing a new :class:`StateFieldMap` entry, not a new
converter - :func:`streetworks.common.from_ogc_features` reads the map
generically. Two states are live, both verified against real data,
2026-07:

- **Hamburg** (``de.hh.up:baustelle``, WFS 2.0.0/1.1.0): 130 real features,
  ``Point`` geometry, dates ``DD.MM.YYYY`` (``baubeginn``/``bauende``).
  **Access mode resolved, not assumed**: the state's open-data catalogue
  also lists a "direct GeoJSON download" - confirmed live to be a ZIP
  wrapper around this same WFS (containing
  ``de_hh_up_baustelle_EPSG_4326.json``), not a separate source. The direct
  WFS ``GetFeature`` call is the canonical path here - one HTTP request,
  no archive to unpack, identical data. No road number/name field exists
  anywhere in the real data (checked all 130 features, 0 road-like keys) -
  left unmapped rather than extracted from ``titel`` text, which would be
  inference. No clean single status field either (six independent boolean
  flags instead - ``iststoerung``, ``istfreigegeben``,
  ``istoepnveingeschraenkt``, ... - all preserved in ``.raw``, none forced
  into ``WorksSite.status``).
- **Brandenburg** (``app:baustelleninfo``, WFS 2.0.0): 487 real features,
  ``LineString`` geometry (2 vertices per segment in the live sample),
  dates ISO (``Baustellen_Beginn``/``Baustellen_Ende``, bare dates, no
  time component - always 10 characters, checked across the whole feed).
  The OGC API Features URL from the original design notes 404s live; the
  WFS is the confirmed-working path. One real field name differs from
  what was documented before checking: it's ``Straßenummner`` (double
  "n") - a typo baked into the source schema itself, not
  ``Straßennummer``. The WFS's own capabilities document states its data
  ultimately originates from a Mobilithek DATEX II feed, republished as
  WFS/GeoJSON server-side - convenient for this client (no DATEX parsing
  needed) but noted here since it explains the schema's shape.
  **Grouping deliberately not attempted**: the ``ID`` field has real
  prefix/suffix structure (``"267201193_1"``, ``"_2"``, ``"_3"``, ...) -
  140 of 164 distinct prefixes are multi-record - but agreement within a
  group is only ~81-88% (dates, type, road), nowhere near Autobahn's
  clean 100%, and there's no independent field corroborating it the way
  Autobahn's "Gesamtmaßnahme" date does. Per the project's record-identity
  discipline (raise a grouping signal, don't act on it unilaterally
  without stronger evidence), this ships 1:1 like every other state.

**Parked, not built**: Mecklenburg-Vorpommern - confirmed live GML-only
(``application/geo+json`` explicitly rejected by the WFS with an
``InvalidParameterValue`` exception) and its licence is only vaguely
stated ("Urheberrecht", no specific Datenlizenz Deutschland citation
unlike Hamburg/Brandenburg's explicit dl-de/by-2-0). Two independent
reasons to park, not one.

Both live states publish under **Datenlizenz Deutschland - Namensnennung -
Version 2.0** (dl-de/by-2-0), confirmed directly from each WFS's own
``GetCapabilities`` document - free reuse, redistribution, and commercial
exploitation permitted with attribution. Exact attribution text is on each
:class:`StateFieldMap` entry below.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from .client import OGCFeaturesClient

__all__ = ["DateField", "StateFieldMap", "FIELD_MAPS", "GermanRoadworksClient"]

JSON = dict[str, Any]

#: Germany's real bounds, with a small margin - used to sanity-check that a
#: state's WFS genuinely returned lon/lat (GeoJSON order), not lat/lon (the
#: WFS 1.3.0/2.0 EPSG:4326 axis order some servers hand back regardless of
#: the requested output format). See the module-level bounds check the
#: tests run against every fixture, and run again yourself against any new
#: state's first live fetch before trusting it.
GERMANY_LON_RANGE = (5.6, 15.3)
GERMANY_LAT_RANGE = (47.0, 55.3)


@dataclass(frozen=True)
class DateField:
    """One date-bearing property: which field, and which format it's in.
    Both formats seen live are date-only (no time component) - represented
    as midnight Europe/Berlin, not naive, so every datetime in this SDK
    stays comparable."""

    field: str
    format: Literal["iso", "de"] = "iso"  #: "iso" = YYYY-MM-DD, "de" = DD.MM.YYYY


@dataclass(frozen=True)
class StateFieldMap:
    """Declarative mapping from one German state's WFS feature properties
    onto the canonical concepts :func:`streetworks.common.from_ogc_features`
    needs. Everything not mapped here still survives - the whole feature is
    kept on ``WorksSite.raw``, per the project's "canonicalise the shared,
    preserve the specific" rule.

    ``administrative_area`` for every feature this map produces is
    ``state`` - **endpoint provenance, not a record field**. There is no
    ``bundesland`` property on these features; the state is known because
    this map is bound to one state's own endpoint, the same mechanism by
    which National Highways' DATEX adapter states
    ``administrative_area="National Highways"`` explicitly rather than
    reading it off a field. Different from Spain's ``provinces()``, which
    reads a real per-record field - don't go looking for one here.
    """

    state: str
    base_url: str
    type_name: str
    title_field: str | None = None
    promoter_field: str | None = None
    start: DateField | None = None
    end: DateField | None = None
    road_field: str | None = None
    status_field: str | None = None
    licence: str = ""
    attribution: str = ""
    version: str = "2.0.0"


HAMBURG = StateFieldMap(
    state="Hamburg",
    base_url="https://geodienste.hamburg.de/hh_wfs_baustellen",
    type_name="de.hh.up:baustelle",
    title_field="titel",
    promoter_field="organisation",
    start=DateField("baubeginn", "de"),
    end=DateField("bauende", "de"),
    road_field=None,  # genuinely absent - see module docstring
    status_field=None,  # six independent booleans instead - see module docstring
    licence="Datenlizenz Deutschland - Namensnennung - Version 2.0 (dl-de/by-2-0)",
    attribution="Freie und Hansestadt Hamburg, Behörde für Verkehr und Mobilitätswende",
)

BRANDENBURG = StateFieldMap(
    state="Brandenburg",
    base_url="https://isk.geobasis-bb.de/ows/baustelleninfo_wfs",
    type_name="app:baustelleninfo",
    title_field="Art",
    promoter_field=None,
    start=DateField("Baustellen_Beginn", "iso"),
    end=DateField("Baustellen_Ende", "iso"),
    road_field="Straßenummner",  # sic - the real field name, not "Straßennummer"
    status_field="Status_Fahrstreifen",
    licence="Datenlizenz Deutschland - Namensnennung - Version 2.0 (dl-de/by-2-0)",
    attribution="© Landesbetrieb Straßenwesen Brandenburg, dl-de/by-2-0, (Daten geändert)",
)

FIELD_MAPS: dict[str, StateFieldMap] = {
    "Hamburg": HAMBURG,
    "Brandenburg": BRANDENBURG,
}


class GermanRoadworksClient:
    """Fetch German state roadworks via the field maps in :data:`FIELD_MAPS`.
    No credentials required.

    >>> from streetworks.ogc.germany import GermanRoadworksClient
    >>> from streetworks.common import from_ogc_features
    >>> with GermanRoadworksClient() as germany:
    ...     features = germany.fetch("Hamburg")
    >>> works = from_ogc_features(features, HAMBURG)
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def fetch(self, state: str) -> list[JSON]:
        """Fetch every current feature for ``state`` (a key of
        :data:`FIELD_MAPS`, e.g. ``"Hamburg"``) - the raw GeoJSON Feature
        dicts, unconverted. Pass these straight to
        :func:`streetworks.common.from_ogc_features` with the same state's
        :class:`StateFieldMap`."""
        field_map = FIELD_MAPS[state]
        payload = self._ogc.get_wfs_features(
            field_map.base_url, type_name=field_map.type_name, version=field_map.version
        )
        return list(payload.get("features") or ())

    def iter_all(self, states: list[str] | None = None) -> Iterator[tuple[str, JSON]]:
        """Yield ``(state, feature)`` for every feature across ``states``
        (default: every state in :data:`FIELD_MAPS`)."""
        for state in states if states is not None else FIELD_MAPS:
            for feature in self.fetch(state):
                yield state, feature

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> GermanRoadworksClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
