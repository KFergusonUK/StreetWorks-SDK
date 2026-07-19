"""BAN's own address shape - modelled faithfully, not forced into a
street-centric model. See the package docstring for why.

Real data (both the geocoding API and the ``csv-bal`` bulk format, live
2026-07) carries **two independent identifier spaces per address**, not one:

* ``id`` (bulk ``csv``/``csv-bal``'s ``cle_interop``, and the API's ``id``) -
  a compact, hierarchical, human-legible key: ``{commune_insee}_{street
  code}_{numero}[_{suffix}]`` (e.g. ``"75101_4461_00008"``). Confirmed
  identical across all three shapes for the same real address.
* ``ban_id`` (the API's ``banId``; the ``@a:`` UUID inside ``csv-bal``'s
  ``uid_adresse``) - a permanent UUID, independent of any renumbering.
  Confirmed live: the same real address (267 Le Mas Renouard, Allenc,
  Lozère) returns ``banId`` ``26377563-...`` from the API and
  ``uid_adresse`` ``... @a:26377563-... @v:... @c:...`` from the bulk
  ``csv-bal`` file - these are the same identifier, not coincidentally
  similar ones. The plain ``csv`` bulk format does **not** carry this UUID
  at all, only ``id``/``id_fantoir`` - one reason ``csv-bal`` is this
  adapter's canonical bulk format (see :mod:`streetworks.ban.reader`).

**There is no ``id_ban_toponyme`` field.** Real BAL 1.4 data (checked
across two départements, Lozère and Finistère) does not carry that column
under any format currently served. What *is* real: the street/lieu-dit
("toponyme") that an address sits on is never published as its own row -
BAN is an address base, not a street register (see the package docstring) -
but its identity is recoverable, because every real ``id``/``cle_interop``
seen is exactly ``{toponyme prefix}_{numero}[_{suffix}]``, and stripping
the numero/suffix consistently reproduces the same prefix for every address
on the same street within one commune (verified: 6/6 real addresses on
Impasse des Chênes, Argol, share the prefix ``29001_428m6b``). ``toponyme_id``
below is that derived prefix - **derived by this SDK, not a literal BAN
field** - so a caller can group addresses by street without this SDK
inventing a canonical street type to do it (out of scope here, see the
package docstring).

Because the identifier's own first token is the commune's INSEE code, a
street crossing a commune boundary necessarily gets a different
``toponyme_id`` on each side - not observed in one specific example, but
true by construction of the identifier itself.

**A street's *name* and a street's *position* are maintained by two
different bodies in two different datasets - this SDK only builds the
second one.** FANTOIR (the cadastral street register the design brief
named) was replaced in July 2023 by **TOPO**, DGFiP's TOPAD referential -
confirmed live: data.gouv.fr flags the old FANTOIR dataset
``"[Obsolète]"`` with no real update since 2023-04, while
"Fichier des entités topographiques (TOPO) DGFiP" (published via
data.economie.gouv.fr, Licence Ouverte v2.0 - same licence as BAN) was
last updated 2026-07-13 and holds 7,933,091 live records. TOPO has **no
geometry column at all** - confirmed against real records - so even a
perfect BAN/TOPO join buys a street's authoritative name and history,
never a centreline.

The plain ``csv`` bulk format's ``id_fantoir`` column (see
:func:`address_from_csv_row`) is *not* stale despite its name: every
populated real value checked (3 mainland départements + 2 overseas, 44-90%
of rows populated depending on département) is exactly 9 characters once
the underscore separator is stripped - the new TOPO-length code, never the
old 10-character FANTOIR one. The join to TOPO is real and clean: BAN
row ``id_fantoir="48003_C365"`` (Lozère, "Le Mas Pouget") splits into
TOPO's own key (``code_dep="48"``, ``code_commune="003"``,
``code_voie="C365"``) and returns TOPO record ``libelle="LE MAS POUGET"``
- confirmed live against the real TOPO API, not assumed from the code
shape alone. ``csv-bal`` and the geocoding API carry no equivalent column
at all - this join is only reachable via the plain ``csv`` bulk format.

Investigated, not built: TOPO is a real, live, complementary register this
SDK does not yet wrap - a `streetworks.topo` module (or folding it into
this one) is a decision for the canonical-gazetteer design session, once
BAN's own shape has settled, not this brief's scope.

**Coordinates are WGS84 (``lon``/``lat``)** - present, and consistent, in
every shape checked (the API's GeoJSON ``geometry.coordinates``, and both
bulk formats' ``lon``/``lat`` or ``long``/``lat`` columns), across mainland
France and every overseas département sampled (971/972/973/974/976). The
``x``/``y`` columns are also real and are preserved in ``.raw``, but are
**not** modelled as a coordinate here: mainland France uses Lambert-93
(EPSG:2154) but each overseas département uses its own local projection
(confirmed by their very different ``x``/``y`` ranges), and the file itself
never states which - labelling them correctly would mean hardcoding a
per-département EPSG lookup this SDK has not verified. WGS84 needs no such
guess and is what every shape actually agrees on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["BANAddress"]


def _toponyme_id(address_id: str, numero: str | None, suffix: str | None) -> str:
    """Derive the street/lieu-dit ("toponyme") identifier by stripping the
    address-level numero/suffix suffix from ``address_id``/``cle_interop`` -
    see the module docstring. Falls back to ``address_id`` unchanged if
    ``numero`` is absent (already a street-level result, e.g. the
    geocoding API's ``type="street"`` hits) or doesn't match the expected
    shape (never observed live, but the identifier isn't a contract)."""
    if not numero:
        return address_id
    suffix_part = f"_{suffix}" if suffix else ""
    tail = f"_{int(numero):05d}{suffix_part}"
    if address_id.endswith(tail):
        return address_id[: -len(tail)]
    return address_id


@dataclass(frozen=True)
class BANAddress:
    """One BAN address, from either access route (the geocoding API or a
    bulk ``csv``/``csv-bal`` file) - the same real fields either way, see
    the module docstring for the two identifier spaces and why ``toponyme_id``
    is derived rather than a literal BAN field.

    ``ban_id`` is ``None`` when parsed from the plain ``csv`` bulk format,
    which doesn't carry it (see the module docstring) - never guessed.
    """

    id: str
    toponyme_id: str
    commune_insee: str
    commune_nom: str | None
    housenumber: str | None
    suffix: str | None
    street: str | None
    postcode: str | None
    lon: float | None
    lat: float | None
    ban_id: str | None = None
    locality: str | None = None  # nom_ld / lieudit_complement_nom
    position: str | None = None  # type_position / position - what the point represents
    source: str | None = None  # source_position / source - who supplied the position
    raw: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        label = f"{self.housenumber} {self.street}" if self.housenumber else self.street
        return f"<BANAddress {label!r} {self.commune_nom} ({self.id})>"


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def address_from_api_feature(feature: dict[str, Any]) -> BANAddress:
    """Build a :class:`BANAddress` from one GeoJSON feature of a
    ``search``/``reverse`` response - see :mod:`streetworks.ban.client`."""
    props = feature.get("properties", {})
    lon, lat = None, None
    geometry = feature.get("geometry")
    if geometry and geometry.get("type") == "Point":
        coords = geometry.get("coordinates")
        if coords and len(coords) >= 2:
            lon, lat = float(coords[0]), float(coords[1])
    address_id = props.get("id", "")
    numero = props.get("housenumber")
    return BANAddress(
        id=address_id,
        toponyme_id=_toponyme_id(address_id, numero, None),
        ban_id=props.get("banId"),
        commune_insee=props.get("citycode", ""),
        commune_nom=props.get("city"),
        housenumber=numero,
        suffix=None,  # the API folds any suffix into `housenumber` itself
        street=props.get("street") or props.get("name"),
        postcode=props.get("postcode"),
        lon=lon,
        lat=lat,
        raw=feature,
    )


def address_from_bal_row(row: dict[str, str]) -> BANAddress:
    """Build a :class:`BANAddress` from one row of a ``csv-bal`` bulk file -
    see :mod:`streetworks.ban.reader`. ``ban_id`` is the ``@a:`` UUID
    embedded in ``uid_adresse`` (see the module docstring)."""
    address_id = row.get("cle_interop", "")
    numero = row.get("numero") or None
    suffix = row.get("suffixe") or None
    uid_adresse = row.get("uid_adresse", "")
    ban_id = None
    if "@a:" in uid_adresse:
        ban_id = uid_adresse.split("@a:", 1)[1].split(" ", 1)[0].strip()
    return BANAddress(
        id=address_id,
        toponyme_id=_toponyme_id(address_id, numero, suffix),
        ban_id=ban_id,
        commune_insee=row.get("commune_insee", ""),
        commune_nom=row.get("commune_nom"),
        housenumber=numero,
        suffix=suffix,
        street=row.get("voie_nom") or None,
        locality=row.get("lieudit_complement_nom") or None,
        postcode=None,  # not a csv-bal column - see the reader module docstring
        lon=_float_or_none(row.get("long")),
        lat=_float_or_none(row.get("lat")),
        position=row.get("position") or None,
        source=row.get("source") or None,
        raw=dict(row),
    )


def address_from_csv_row(row: dict[str, str]) -> BANAddress:
    """Build a :class:`BANAddress` from one row of the plain ``csv`` bulk
    format - no ``ban_id`` (see the module docstring), but includes
    ``id_fantoir``, a (despite the name) TOPO-length street code that joins
    to DGFiP's TOPO register, in ``.raw`` - see the module docstring."""
    address_id = row.get("id", "")
    numero = row.get("numero") or None
    suffix = row.get("rep") or None
    return BANAddress(
        id=address_id,
        toponyme_id=_toponyme_id(address_id, numero, suffix),
        ban_id=None,
        commune_insee=row.get("code_insee", ""),
        commune_nom=row.get("nom_commune"),
        housenumber=numero,
        suffix=suffix,
        street=row.get("nom_voie") or None,
        locality=row.get("nom_ld") or None,
        postcode=row.get("code_postal") or None,
        lon=_float_or_none(row.get("lon")),
        lat=_float_or_none(row.get("lat")),
        position=row.get("type_position") or None,
        source=row.get("source_position") or None,
        raw=dict(row),
    )
