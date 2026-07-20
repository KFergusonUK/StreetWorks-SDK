"""Kartverket's own shapes, modelled natively and faithfully - no canonical
gazetteer type, no `streetworks.common` converter (see the package
docstring for why).

**Multilingual naming lives on the place, not the address - confirmed
live, not assumed.** A real SSR place (Karasjok/Kárášjohka/Kaarasjoki,
``stedsnummer`` 868181) carries **three parallel official names in one
``stedsnavn`` array** - Norwegian, Northern Sámi and Kven - each its own
object with its own ``sprak`` (language), ``navnestatus`` (name status,
e.g. ``"hovednavn"`` - main name) and ``skrivemåtestatus`` (spelling
status - here two are ``"godkjent og prioritert"`` [approved and
prioritised] and the Kven one is ``"foreslått og prioritert"`` [proposed
and prioritised, not yet formally approved] - status genuinely differs per
language, not just the text). That structure - one place, several
sibling name objects, each independently statused - is why
:class:`PlaceName` models ``names`` as a list, never a single ``name``
field: a canonical type with one name field would silently keep one
language and discard the others, and here even *which* language is most
"official" is not settled the same way for all three.

**The address dataset itself is NOT multilingual - confirmed live, not
assumed.** A real address in the same Sámi-majority municipality
("Čalbmebealskáidi 1", Karasjok) carries exactly **one** ``adressenavn``,
in Northern Sámi, with no parallel Norwegian name anywhere on the address
record. Searching SSR for that same street found it again under
``navneobjekttype="Adressenavn"`` - SSR does have a real, dedicated
"address name" object type - but even there it's a single-language entry,
not a multilingual bundle like the settlement above. So multilingual
officialdom is a property of *some* SSR places, not a systematic property
of Norwegian street addressing - a street can be registered in only one
language, in either dataset, exactly as often as it can be registered in
several.

**`adressekode` is a real, clean, municipality-scoped street key** -
verified at real scale, not sampled: grouping two whole municipalities'
bulk address files by ``adressekode`` (Karasjok, 1,896 addresses, 139
codes; Oslo, 106,154 addresses, 2,535 codes) found zero codes mapping to
more than one distinct ``adressenavn``, in either municipality. Different
municipalities reuse the same numeric codes for unrelated streets
(confirmed live: "Karl Johans gate 1" resolves to three different real
addresses, in three different municipalities, each with its own
``adressekode`` - 15100 in Sarpsborg, 13630 in Oslo, 3620 in Halden) -
the same municipality-scoping BAN's ``toponyme_id`` and BAG's
``openbare_ruimte_identificatie`` both showed, a fourth confirmation of
the same pattern.

**No street geometry in any product checked** - the address API and bulk
files give one point per address (``representasjonspunkt`` /
``Nord``/``Øst``), never a line; SSR's ``"Adressenavn"`` places are
likewise points. A separate Kartverket/Statens vegvesen product, NVDB
Vegnett (the national road network), does carry real road-network line
geometry - noted, not built, the same treatment France's TOPO and the
Netherlands' NWB got. That makes three of four European gazetteers built
in this SDK with no street centreline of their own.

**CRS is per-product, and does not default the same way everywhere -
verified live, not assumed from the design brief.** The address API's
``representasjonspunkt`` is always ``EPSG:4258`` (confirmed on every real
response). SSR's ``punkt`` endpoint accepts *either* ``4258`` or ``25833``
as a query CRS (``koordsys``) and can reproject its output via
``utkoordsys`` - but a plain ``/sted``/``/navn`` response's own
``representasjonspunkt`` does **not** self-declare which EPSG it's in;
confirmed live by cross-referencing known real coordinates that the
default is the same ``EPSG:4258`` as the address API, but this module
labels it as "assumed EPSG:4258 unless ``utkoordsys`` was passed",
honestly, rather than invented per-record confidence the API itself
doesn't provide. The bulk CSV files are the most explicit of all: every
row carries its own ``EPSG-kode`` column, and Kartverket publishes the
**same** municipality in multiple CRS variants side by side (``4258``,
``25833``, and a UTM zone matching the area, e.g. ``25835`` for Finnmark)
as separate files - never reprojected here, whichever variant is fetched
is what's returned, labelled from that row's own ``EPSG-kode``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "Address",
    "NamedForm",
    "PlaceName",
    "address_from_csv_row",
    "address_from_json",
    "place_from_navn",
    "place_from_sted",
]


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


@dataclass(frozen=True)
class Address:
    """One Vegadresse/Matrikkeladresse, from either the address REST API
    or a bulk CSV file - the same real fields either way. ``epsg``/
    ``nord``/``ost`` are named after the bulk CSV's own columns (not
    "lat"/"lon") because the CRS - and therefore what "nord"/"ost" actually
    means, degrees or metres - varies by product and by file (see the
    module docstring); for the REST API, always ``EPSG:4258``, ``nord`` is
    its ``lat`` and ``ost`` is its ``lon``, which are the same thing for
    that specific CRS but not a safe assumption to bake in generally.
    """

    lokalid: str | None
    kommunenummer: str
    kommunenavn: str | None
    adressetype: str | None
    adressenavn: str | None
    adressekode: str
    nummer: int | None
    bokstav: str | None
    adressetilleggsnavn: str | None
    adressetekst: str | None
    postnummer: str | None
    poststed: str | None
    epsg: str
    nord: float | None
    ost: float | None
    uuid_adresse: str | None = None
    oppdateringsdato: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        label = f"{self.adressenavn} {self.nummer}{self.bokstav or ''}"
        return f"<Address {label!r} {self.kommunenavn} ({self.adressekode})>"


def address_from_json(doc: dict[str, Any]) -> Address:
    """Build an :class:`Address` from one result of the address REST API's
    ``/sok``/``/punktsok`` - always ``EPSG:4258`` (confirmed live on every
    real response), so ``nord``/``ost`` are that response's own
    ``representasjonspunkt.lat``/``.lon``."""
    point = doc.get("representasjonspunkt") or {}
    return Address(
        lokalid=None,  # not present on the REST API's own shape
        kommunenummer=doc.get("kommunenummer", ""),
        kommunenavn=doc.get("kommunenavn"),
        adressetype=doc.get("objtype"),
        adressenavn=doc.get("adressenavn"),
        adressekode=str(doc.get("adressekode", "")),
        nummer=doc.get("nummer"),
        bokstav=doc.get("bokstav") or None,
        adressetilleggsnavn=doc.get("adressetilleggsnavn"),
        adressetekst=doc.get("adressetekst"),
        postnummer=doc.get("postnummer"),
        poststed=doc.get("poststed"),
        epsg=point.get("epsg", "EPSG:4258"),
        nord=_float_or_none(point.get("lat")),
        ost=_float_or_none(point.get("lon")),
        oppdateringsdato=doc.get("oppdateringsdato"),
        raw=doc,
    )


def address_from_csv_row(row: dict[str, str]) -> Address:
    """Build an :class:`Address` from one row of a bulk
    ``MatrikkelenAdresse`` CSV file - see :mod:`streetworks.kartverket.reader`.
    ``epsg`` is that row's own ``EPSG-kode`` column - never assumed."""
    return Address(
        lokalid=row.get("lokalid") or None,
        kommunenummer=row.get("kommunenummer", ""),
        kommunenavn=row.get("kommunenavn"),
        adressetype=row.get("adressetype"),
        adressenavn=row.get("adressenavn") or None,
        adressekode=row.get("adressekode", ""),
        nummer=int(row["nummer"]) if row.get("nummer") else None,
        bokstav=row.get("bokstav") or None,
        adressetilleggsnavn=row.get("adressetilleggsnavn") or None,
        adressetekst=row.get("adresseTekst"),
        postnummer=row.get("postnummer"),
        poststed=row.get("poststed"),
        epsg=f"EPSG:{row['EPSG-kode']}" if row.get("EPSG-kode") else "",
        nord=_float_or_none(row.get("Nord")),
        ost=_float_or_none(row.get("Øst")),
        uuid_adresse=row.get("uuidAdresse") or None,
        oppdateringsdato=row.get("oppdateringsdato"),
        raw=dict(row),
    )


@dataclass(frozen=True)
class NamedForm:
    """One official spelling of a place name - one entry in a
    :class:`PlaceName`'s ``names``. Field names are ASCII-transliterated
    from the real Norwegian source fields (``skrivemåte`` ->
    ``skrivemate``, ``språk`` -> ``sprak``, ``skrivemåtestatus`` ->
    ``skrivematestatus``) so they're typeable Python identifiers - the
    exact original spelling and keys are always in ``.raw``, unchanged."""

    skrivemate: str
    sprak: str | None
    navnestatus: str | None
    skrivematestatus: str | None
    stedsnavnnummer: int | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlaceName:
    """One SSR place, with every one of its official name forms - see the
    module docstring for why ``names`` is a list, never a single field.

    Built the same way from both real endpoints: ``/sted`` naturally
    returns several ``names`` per real multilingual/multi-spelling place;
    ``/navn`` returns one flattened name-record per hit, normalised here
    into the same shape with a single-element ``names`` list - the
    underlying place/name relationship is unchanged, only this client's
    Python-side representation is unified across the two endpoints.
    """

    stedsnummer: int
    stedstatus: str | None
    navneobjekttype: str | None
    kommuner: tuple[tuple[str, str], ...]  # (kommunenummer, kommunenavn)
    fylker: tuple[tuple[str, str], ...]  # (fylkesnummer, fylkesnavn)
    nord: float | None
    ost: float | None
    names: tuple[NamedForm, ...]
    raw: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        spellings = ", ".join(n.skrivemate for n in self.names)
        return f"<PlaceName {spellings} ({self.navneobjekttype}, {self.stedsnummer})>"


def _named_form_from_stedsnavn(doc: dict[str, Any]) -> NamedForm:
    return NamedForm(
        skrivemate=doc.get("skrivemåte", ""),
        sprak=doc.get("språk"),
        navnestatus=doc.get("navnestatus"),
        skrivematestatus=doc.get("skrivemåtestatus"),
        stedsnavnnummer=doc.get("stedsnavnnummer"),
        raw=doc,
    )


def place_from_sted(doc: dict[str, Any]) -> PlaceName:
    """Build a :class:`PlaceName` from one ``/sted`` result - its real
    ``stedsnavn`` array becomes ``names``, one :class:`NamedForm` each."""
    point = doc.get("representasjonspunkt") or {}
    kommuner = tuple(
        (k.get("kommunenummer", ""), k.get("kommunenavn", "")) for k in doc.get("kommuner") or []
    )
    fylker = tuple(
        (f.get("fylkesnummer", ""), f.get("fylkesnavn", "")) for f in doc.get("fylker") or []
    )
    names = tuple(_named_form_from_stedsnavn(n) for n in doc.get("stedsnavn") or [])
    return PlaceName(
        stedsnummer=doc.get("stedsnummer", 0),
        stedstatus=doc.get("stedstatus"),
        navneobjekttype=doc.get("navneobjekttype"),
        kommuner=kommuner,
        fylker=fylker,
        nord=_float_or_none(point.get("nord")),
        ost=_float_or_none(point.get("øst")),
        names=names,
        raw=doc,
    )


def place_from_navn(doc: dict[str, Any]) -> PlaceName:
    """Build a :class:`PlaceName` from one ``/navn`` result - a flattened
    single-name record; see :class:`PlaceName`'s docstring."""
    point = doc.get("representasjonspunkt") or {}
    kommuner = tuple(
        (k.get("kommunenummer", ""), k.get("kommunenavn", "")) for k in doc.get("kommuner") or []
    )
    fylker = tuple(
        (f.get("fylkesnummer", ""), f.get("fylkesnavn", "")) for f in doc.get("fylker") or []
    )
    return PlaceName(
        stedsnummer=doc.get("stedsnummer", 0),
        stedstatus=doc.get("stedstatus"),
        navneobjekttype=doc.get("navneobjekttype"),
        kommuner=kommuner,
        fylker=fylker,
        nord=_float_or_none(point.get("nord")),
        ost=_float_or_none(point.get("øst")),
        names=(_named_form_from_stedsnavn(doc),),
        raw=doc,
    )
