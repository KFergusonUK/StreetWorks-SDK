"""NVDB's own shapes, modelled natively and faithfully - no canonical
street type, no `streetworks.common` converter (see the package docstring
for why).

**Finding 1: `veglenkesekvens` (road link sequence) is purely
topological - it has no name of its own.** Confirmed live against a real
national object (`veglenkesekvensid=1`): it carries `lengde` (length),
`porter` (the ports/nodes it connects to, each a real network junction),
and `veglenker` (its own sub-links, each with a `startposisjon`/
`sluttposisjon` linear-referencing range and its own geometry) - and
nothing resembling a name. This is Norway's organising principle: a
*network topology* run between junctions, not a named entity - a
genuinely different shape from France's `voie_nommee` (organised by
*name* - see :mod:`streetworks.bdtopo.models`), even though both are
described as "two-level spines."

**Finding 2: naming and addressing live in a separate object type
(`Adresse`, NVDB type 538), and it's the same `adressekode` this SDK
already models for `streetworks.kartverket`.** Confirmed live: a real
`Adresse` object (id 646, "Dalveien") carries `Adressekode` (1140) and
`Adressenavn` ("Dalveien") as its own properties - `Adressekode` is not a
new identifier space, it is confirmed to be the *same* `adressekode`
Kartverket's address API returns (same municipality-scoped integer
convention - see :mod:`streetworks.kartverket.models`). This is a real,
stated join to Matrikkelen addresses, the same standard NWB's `bag_orl`
and BD TOPO's `identifiant_voie_ban` set - never a name match.

**Finding 3 - the genuinely important structural disagreement: an
`Adresse` (one `adressekode`) can span *multiple* `veglenkesekvenser`,
confirmed live** - the real "Dalveien" object above attaches to two
different link sequences (`veglenkesekvensid` 384 and 2399262) via its
own `stedfestinger` (linear-referencing placements), each a
`startposisjon`-`sluttposisjon` range on its own sequence. So Norway's
naming layer and topological layer are not nested the way BD TOPO's
`voie_nommee`/`troncon_de_route` are (one `voie_nommee` aggregating a
clean set of *its own* segments via a direct link field) - here, a named
street's segments can be spread across topologically-independent link
sequences that share nothing but the address placed on top of them. Two
"two-level spines," two different organising principles - exactly the
disagreement this design strand needed (see the package docstring).

**Finding 4 - a third identifier system exists, independent of both**:
`vegsystemreferanser` (administrative road-numbering - `vegkategori`,
`nummer`, `strekning`, `delstrekning`, e.g. the real, human-readable
`kortform` ``"KV1140 S1D1 m0-65"`` - Kommunal Vei ["county/municipal
road"] 1140, section 1, sub-section 1, metres 0-65). Confirmed live on
the same real `Adresse` object. Not modelled as a first-class field here
(out of this brief's scope) but preserved in ``.raw`` - worth flagging to
the design session as a real third axis, not assumed away.

**CRS is EPSG:5973, not the design brief's expected EPSG:25833** -
confirmed live on every real geometry checked (`veglenkesekvens`,
`veglenke`, and `Adresse` alike). EPSG:5973 is
"ETRS89-NOR [EUREF89] / UTM zone 33N + NN2000 height" - a **compound 3D**
CRS, not a plain 2D UTM33 one: the brief's UTM33N guess was directionally
right for the horizontal component, but the real code is the 3D compound
that layers Norway's NN2000 height datum on top of it. This matches
finding 5: every real geometry is a genuine `LINESTRING Z`, not a 2D
`LINESTRING` - confirmed real altitude values throughout (e.g.
``110.02``, ``342.0`` metres), never assumed from documentation.

**Linear referencing is real and meaningful, not just documented** -
confirmed live: `veglenke.startposisjon`/`sluttposisjon` (a link's own
sub-range, relative 0.0-1.0, within its parent sequence) and
`stedfesting.startposisjon`/`sluttposisjon` (an `Adresse`'s placement
range on a sequence) both carry genuine fractional values on real
objects, not just 0.0/1.0 placeholders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "VegAdresse",
    "Veglenke",
    "Veglenkesekvens",
    "vegadresse_from_response",
    "veglenkesekvens_from_response",
]


def _egenskaper_by_name(egenskaper: list[dict[str, Any]]) -> dict[str, Any]:
    return {e["navn"]: e.get("verdi") for e in egenskaper if "navn" in e}


@dataclass(frozen=True)
class Veglenke:
    """One sub-link within a :class:`Veglenkesekvens` - the actual
    geometry-bearing unit, with its own linear-referencing range on the
    parent sequence. Every field not promoted here is in ``.raw``.

    ``type_veg``/``type_veg_sosi`` (the real ``typeVeg``/``typeVeg_sosi``
    fields) were promoted from ``.raw`` for the canonical-gazetteer model
    (``street_type`` - see :mod:`streetworks.common.gazetteer`): real road
    classification (e.g. ``"Enkel bilveg"``/``"enkelBilveg"``), previously
    only reachable via ``.raw``. Carried as stated, undecoded - a plain
    label plus a parallel SOSI code string, not a code needing a lookup.
    """

    veglenkenummer: int | None
    type: str | None
    startposisjon: float | None
    sluttposisjon: float | None
    lengde: float | None
    kommune: int | None
    geometry: str | None
    srid: int | None
    type_veg: str | None = None
    type_veg_sosi: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Veglenkesekvens:
    """One road link sequence - a purely topological unit (see the module
    docstring), made up of one or more :class:`Veglenke` sub-links.
    Carries no name of its own."""

    veglenkesekvensid: int
    lengde: float | None
    veglenker: tuple[Veglenke, ...]
    raw: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<Veglenkesekvens {self.veglenkesekvensid} ({len(self.veglenker)} veglenker)>"


@dataclass(frozen=True)
class VegAdresse:
    """One `Adresse` road object (NVDB type 538) - the naming/addressing
    layer, and the real join to Matrikkelen (see the module docstring).
    ``veglenkesekvens_ids`` lists every link sequence this address is
    placed on - see finding 3 for why that can be more than one."""

    id: int
    adressekode: str | None
    adressenavn: str | None
    kommune: str | None
    veglenkesekvens_ids: tuple[int, ...]
    geometry: str | None
    srid: int | None
    raw: dict[str, Any] = field(default_factory=dict)

    def toponyme_id(self) -> str | None:
        """The same real, stated join convention as
        :meth:`streetworks.nwb.models.Wegvak.toponyme_id_gauche` and
        :meth:`streetworks.bdtopo.models.Troncon.toponyme_id_gauche` -
        `adressekode`, never a name match. Also, confirmed live, exactly
        the identifier :mod:`streetworks.kartverket` already models."""
        return self.adressekode or None

    def __repr__(self) -> str:
        return f"<VegAdresse {self.adressenavn!r} ({self.adressekode})>"


def _veglenke_from_json(v: dict[str, Any]) -> Veglenke:
    geometri = v.get("geometri") or {}
    return Veglenke(
        veglenkenummer=v.get("veglenkenummer"),
        type=v.get("type"),
        startposisjon=v.get("startposisjon"),
        sluttposisjon=v.get("sluttposisjon"),
        lengde=v.get("lengde"),
        kommune=geometri.get("kommune"),
        geometry=geometri.get("wkt"),
        srid=geometri.get("srid"),
        type_veg=v.get("typeVeg"),
        type_veg_sosi=v.get("typeVeg_sosi"),
        raw=v,
    )


def veglenkesekvens_from_response(obj: dict[str, Any]) -> Veglenkesekvens:
    """Build a :class:`Veglenkesekvens` from one object of the
    `/vegnett/api/v4/veglenkesekvenser` response."""
    veglenker = tuple(_veglenke_from_json(v) for v in obj.get("veglenker", []))
    return Veglenkesekvens(
        veglenkesekvensid=obj.get("veglenkesekvensid", 0),
        lengde=obj.get("lengde"),
        veglenker=veglenker,
        raw=obj,
    )


def vegadresse_from_response(obj: dict[str, Any]) -> VegAdresse:
    """Build a :class:`VegAdresse` from one `Adresse` (type 538) object of
    the `/vegobjekter/api/v4/vegobjekter/538` response (with
    ``inkluder=alle`` - see :mod:`streetworks.nvdb.client`)."""
    egenskaper = _egenskaper_by_name(obj.get("egenskaper", []))
    lokasjon = obj.get("lokasjon") or {}
    stedfestinger = lokasjon.get("stedfestinger") or []
    sekvens_ids = tuple(
        s["veglenkesekvensid"] for s in stedfestinger if "veglenkesekvensid" in s
    )
    geometri = obj.get("geometri") or lokasjon.get("geometri") or {}
    adressekode = egenskaper.get("Adressekode")
    return VegAdresse(
        id=obj.get("id", 0),
        adressekode=str(adressekode) if adressekode is not None else None,
        adressenavn=egenskaper.get("Adressenavn"),
        kommune=egenskaper.get("Kommune"),
        veglenkesekvens_ids=sekvens_ids,
        geometry=geometri.get("wkt"),
        srid=geometri.get("srid"),
        raw=obj,
    )
