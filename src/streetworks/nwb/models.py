"""NWB's own shape, modelled natively and faithfully - no canonical
street-network type, no `streetworks.common` converter (see the package
docstring for why).

**A "street" is a set of wegvakken (road segments), not one feature -
confirmed live, not assumed.** Separated carriageways are real, separate
wegvakken (e.g. a dual carriageway's two directions), and any street of
useful length is several. How they group back into one real street was
this brief's key open question, and the honest answer has two parts,
verified at real municipality scale (Harlingen, 1,886 wegvakken), not
sampled:

* **`bag_orl` is a real, stated join to BAG** - not a name match. Its
  format (a commune-code-prefixed numeric string, e.g.
  ``"0072300000285375"`` for Harlingen, commune code ``72``) matches
  BAG's own ``openbare_ruimte_identificatie`` exactly (see
  :mod:`streetworks.bag.models`), and grouping by it is clean: 378 real
  groups, **zero** mapping to more than one distinct street name. This
  makes the Netherlands the first territory in this SDK where an address
  register and a street-geometry register can be joined by a stated
  identifier, not a name.
* **But `bag_orl` isn't universal** - confirmed live: ~5% of Harlingen's
  wegvakken (96 of 1,886) carry no `bag_orl` at all. And name-based
  grouping alone is measurably less reliable than the id: of 385 real
  (municipality, street name) groups, **7 span more than one distinct
  `bag_orl`** - e.g. "Sédyk" and "Buorren" each cover two different real
  BAG street objects under one display name. Falling back to name
  matching where the id is missing would silently over-merge in exactly
  these cases - flagged, not hidden, and not silently resolved by this
  SDK either; :func:`toponyme_id` (see below) returns the `bag_orl` where
  present and `None` otherwise, rather than guessing from the name.

**Access confirmed live, correcting the design brief's own warning**: the
WFS endpoint does honour `count`/paging - what actually happened on
the brief's two failed attempts was almost certainly the un-encoded
`+` in `outputFormat=application/geopackage+sqlite3`; a bare `+` in a
query string decodes as a literal space server-side
(`"application/geopackage sqlite3"`, confirmed as the exact rejection
message live), not the intended MIME type - properly percent-encoded
(`%2B`), `count=1` returns exactly one real feature, and `CQL_FILTER`
(a real GeoServer extension, e.g. `gme_naam='Harlingen'`) works too.
httpx's own `params=` dict encodes this correctly, so this SDK's own
client was never at risk of the bug - documented here so nobody
re-diagnoses it as "WFS ignores paging" a second time.

**PDOK and Rijkswaterstaat serve the identical *unfiltered* dataset, but
only one of them actually filters - confirmed live, and a genuine bug,
not a style choice.** The same real wegvak (`wvk_id` 314551046) comes
back identical from both `geo.rijkswaterstaat.nl`'s WFS and
`service.pdok.nl/rws/nwbwegen`'s WFS (same street name, same geometry,
same every field - PDOK's JSON output happens to use camelCase property
names, RWS's snake_case, matching its raw GeoPackage columns exactly - a
serialisation difference, not a data difference). But a real
`CQL_FILTER` (e.g. `gme_naam='Harlingen'`, one real municipality) is
**silently ignored by PDOK** - a "filtered" request returned wegvakken
from 280 different municipalities, unfiltered, both for actual features
and for `resultType=hits` counts - while the identical query against
Rijkswaterstaat directly returns exactly the requested municipality
(confirmed: 1,886 real matching features, 0 from anywhere else). Since
filtering is the entire point of a live-query route,
:class:`~streetworks.nwb.client.NWBClient`'s `query()`/`count()` target
Rijkswaterstaat directly; the bulk GeoPackage download stays on PDOK's
Atom feed (a static file, unaffected - see
:mod:`streetworks.nwb.atom`), matching this SDK's existing convention for
other Dutch open data (`streetworks.bag`).

**Licence corrected, the same way BAG's was**: the design brief's own
instruction was to check the Atom feed's `<rights>` element rather than
trust a portal page - done, live: **CC0 1.0 Universal**
(`creativecommons.org/publicdomain/zero/1.0`), matching BAG exactly, not
the vaguer "open data" a portal page alone would suggest.

**CRS confirmed EPSG:28992** (Amersfoort / RD New) on every geometry
column and every real feature checked, matching BAG. **Geometry type is
route-dependent, confirmed live, not assumed from one access route
alone**: the WFS's own GeoJSON output reports each wegvak as a plain
`LineString`, but the bulk GeoPackage - this module's primary route -
encodes every real wegvak as a `MULTILINESTRING` wrapping exactly one
`LineString` part (confirmed across 5,000 real national features sampled,
0 with a genuine second part) - a GeoPackage/FME export convention, not
evidence of genuinely multi-part road segments. `Wegvak.geometry` carries
whatever WKT the access route actually produced, unconverted - never
silently unwrapped to a bare `LineString` to paper over the difference.

The separate, non-authoritative `nwb_light` layer (small-scale
cartographic display) also uses `MultiLineString`, but is not modelled at
all - see below.

**Only named or numbered roads are included, and that does include
standalone foot/cycle paths** - confirmed live via `bst_code` (a real
surface/segment-type code): a real municipality sample (Harlingen) has
239 `"FP"` (fietspad, cycle path) and 125 `"VP"` (voetpad, footpath)
wegvakken alongside 1,396 ordinary carriageway (`"RB"`) segments. Purely
numbered roads (a national route with no separate street name) do appear,
but even they carry *some* `stt_naam` value - confirmed live: a real A79
motorway segment has `stt_naam="A79"` (i.e. the route number itself,
promoted into the name field) rather than an empty name paired with only
`wegnummer`/`routenr`.

**Road authority is real and worth its own fields**, the
`administrative_area`-adjacent information the brief asked about:
`wegbehsrt`/`wegbehcode`/`wegbehnaam` (e.g. `"G"`/`"72"`/`"Harlingen"` -
Gemeente, Provincie, Rijk and one further code confirmed live across a
real sample) identify who actually manages a given wegvak, independently
of which municipality it geographically sits in (`gme_id`/`gme_naam`).

Not modelled here, noted only: `hectopunten` (hectometre points, ~161,893
real features nationally, confirmed live - close to, and updating, the
design brief's ~159,000 figure - each referencing a `wvk_id`), the
`mutaties_wegvakken`/`mutaties_hectopunten` change-log layers, and
`nwb_light` (a generalised/simplified geometry layer for small-scale
rendering). All are real WFS layers this SDK's client can reach but does
not wrap - the brief's scope is roads (`wegvakken`) only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Wegvak", "wegvak_from_feature", "wegvak_from_row"]


@dataclass(frozen=True)
class Wegvak:
    """One NWB road segment (wegvak) - a *part* of a street, not a street
    itself; see the module docstring for how they group. Every field not
    promoted here (there are ~55 real columns) is preserved in ``.raw``.

    ``wvk_begdat`` and the six ``*hnr*`` fields were promoted from ``.raw``
    for the canonical-gazetteer model (``as_at``/``address_ranges`` -
    see :mod:`streetworks.common.gazetteer`): real, present in every
    sampled fixture, previously only reachable via ``.raw``.
    """

    wvk_id: int
    stt_naam: str | None
    gme_id: int | None
    gme_naam: str | None
    wpsnaam: str | None
    wegbehsrt: str | None
    wegbehcode: str | None
    wegbehnaam: str | None
    bst_code: str | None
    frc: str | None
    fow: str | None
    wegnummer: str | None
    routeltr: str | None
    routenr: int | None
    bag_orl: str | None
    jte_id_beg: int | None
    jte_id_end: int | None
    rijrichtng: str | None
    wvk_begdat: str | None = None
    hnrstrlnks: str | None = None
    hnrstrrhts: str | None = None
    e_hnr_lnks: int | None = None
    e_hnr_rhts: int | None = None
    l_hnr_lnks: int | None = None
    l_hnr_rhts: int | None = None
    geometry: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def toponyme_id(self) -> str | None:
        """The real, stated join to BAG's ``openbare_ruimte_identificatie``
        (see :mod:`streetworks.bag.models`) - ``None`` where NWB's own
        `bag_orl` is absent (a real, if uncommon, case - see the module
        docstring). Never falls back to name matching, which is
        measurably less reliable here - see the module docstring for the
        real over-merge counts that make that a deliberate choice, not an
        oversight."""
        return self.bag_orl or None

    def __repr__(self) -> str:
        return f"<Wegvak {self.stt_naam!r} {self.gme_naam} ({self.wvk_id})>"


def _int_or_none(value: Any) -> int | None:
    if value in (None, "", "#"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    if value in (None, "", "#"):
        return None
    return str(value)


def wegvak_from_row(row: dict[str, Any], *, geometry: str | None = None) -> Wegvak:
    """Build a :class:`Wegvak` from one row's field mapping - shared by
    both the GeoPackage reader (snake_case column names) and the WFS JSON
    client (camelCase property names), each normalising to this same
    lower-snake-case key set before calling this."""
    return Wegvak(
        wvk_id=int(row["wvk_id"]),
        stt_naam=_str_or_none(row.get("stt_naam")),
        gme_id=_int_or_none(row.get("gme_id")),
        gme_naam=_str_or_none(row.get("gme_naam")),
        wpsnaam=_str_or_none(row.get("wpsnaam")),
        wegbehsrt=_str_or_none(row.get("wegbehsrt")),
        wegbehcode=_str_or_none(row.get("wegbehcode")),
        wegbehnaam=_str_or_none(row.get("wegbehnaam")),
        bst_code=_str_or_none(row.get("bst_code")),
        frc=_str_or_none(row.get("frc")),
        fow=_str_or_none(row.get("fow")),
        wegnummer=_str_or_none(row.get("wegnummer")),
        routeltr=_str_or_none(row.get("routeltr")),
        routenr=_int_or_none(row.get("routenr")),
        bag_orl=_str_or_none(row.get("bag_orl")),
        jte_id_beg=_int_or_none(row.get("jte_id_beg")),
        jte_id_end=_int_or_none(row.get("jte_id_end")),
        rijrichtng=_str_or_none(row.get("rijrichtng")),
        wvk_begdat=_str_or_none(row.get("wvk_begdat")),
        hnrstrlnks=_str_or_none(row.get("hnrstrlnks")),
        hnrstrrhts=_str_or_none(row.get("hnrstrrhts")),
        e_hnr_lnks=_int_or_none(row.get("e_hnr_lnks")),
        e_hnr_rhts=_int_or_none(row.get("e_hnr_rhts")),
        l_hnr_lnks=_int_or_none(row.get("l_hnr_lnks")),
        l_hnr_rhts=_int_or_none(row.get("l_hnr_rhts")),
        geometry=geometry,
        raw=dict(row),
    )


def wegvak_from_feature(feature: dict[str, Any]) -> Wegvak:
    """Build a :class:`Wegvak` from one GeoJSON feature of the WFS's
    ``outputFormat=application/json`` response. Rijkswaterstaat's own
    property names are already lower-snake-case (e.g. ``wvk_id``,
    ``stt_naam``) - confirmed live, identical to the GeoPackage's own
    column names - so no field-name mapping is needed here, unlike PDOK's
    proxy, which serialises the same data with camelCase property names
    (``wvkId``) and is not this client's WFS route - see
    :mod:`streetworks.nwb.client` for why."""
    row = feature.get("properties", {})
    geometry = None
    geom = feature.get("geometry")
    if geom and geom.get("type") == "LineString":
        coords = geom.get("coordinates", [])
        points = ", ".join(f"{x} {y}" for x, y in coords)
        geometry = f"LINESTRING ({points})"
    return wegvak_from_row(row, geometry=geometry)
