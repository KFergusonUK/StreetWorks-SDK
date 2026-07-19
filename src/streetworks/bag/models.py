"""BAG's own shapes, modelled natively and faithfully - no canonical
gazetteer type, no `streetworks.common` converter (see the package
docstring for why).

**THE critical first check, answered against the real 7.8 GB national
GeoPackage (not a sample - the whole file, every table)**: ``openbare
ruimte`` does **not** exist as its own table. ``gpkg_contents`` lists
exactly five tables - ``woonplaats``, ``pand``, ``verblijfsobject``,
``standplaats``, ``ligplaats`` - and every one of them carries geometry
(confirmed: ``POINT``/``POLYGON``/``MULTIPOLYGON``, all ``srs_id=28992``).
Street identity survives only as two columns flattened onto every
addressable object's own row: ``openbare_ruimte_naam`` (the name) and
``openbare_ruimte_identificatie`` (the real, stable BAG object id - see
below). There is no ``nummeraanduiding`` table either; ``huisnummer``/
``huisletter``/``toevoeging``/``postcode``/
``nummeraanduiding_hoofdadres_identificatie`` are flattened the same way.
This is genuinely the design brief's second scenario ("street-implicit"),
but reached by a different route than France's: the identifier
(``openbare_ruimte_identificatie``) is real, stable, and traces back to an
authentic BAG object - it just isn't shipped as its own row **in this
product**. Verified at full national scale, not sampled: grouping every
one of the ~10.04M addressable objects (``verblijfsobject`` +
``standplaats`` + ``ligplaats``) by ``openbare_ruimte_identificatie`` gives
245,893 + 2,980 + 1,546 distinct real street ids, zero of which map to more
than one distinct ``openbare_ruimte_naam``, and zero rows with a `NULL`
street id anywhere.

**The full picture only emerges by also checking the (not-built) XML
extract**: there, ``openbare ruimte`` genuinely *is* its own first-class,
separately-versioned object (``Objecten:OpenbareRuimte``, confirmed across
all 36 real national member files) - its own ``identificatie`` (domain
``NL.IMBAG.Openbareruimte`` - the same identifier space as
``openbare_ruimte_identificatie`` above), ``naam``, ``type`` (real values
seen: ``Weg`` [road/street], ``Water``, ``Spoorbaan`` [railway],
``Kunstwerk`` [engineering structure, e.g. a bridge], ``Terrein``,
``Landschappelijk gebied``, ``Administratief gebied`` - "public space" is
broader than "street"), a real ``status`` lifecycle (e.g. ``Naamgeving
uitgegeven`` "naming issued" / ``Naamgeving ingetrokken`` "naming
withdrawn"), and a ``ligtIn`` reference to its ``Woonplaats``. **But still
no geometry, in either product** - no ``OpenbareRuimte`` record of any
``type``, in any of the 36 files, carries a ``<Objecten:geometrie>``
element, unlike ``Woonplaats``/``Standplaats``/``Ligplaats``, which all do
(a GML polygon each).

So the honest, complete answer has three parts, not two: (1) a street IS a
genuine first-class registered BAG object, with a real lifecycle and
history; (2) it never carries geometry, in any product checked; and (3)
*which* product you pull from changes whether you can see it directly -
the light GeoPackage this SDK reads denormalizes it onto every address
instead of giving it a row, while the full extract (investigated, not
built - see below) keeps it as its own object. That three-part shape -
not "explicit" or "implicit" as a fixed property of the country, but
something that depends on which real product you're looking at - is BAG's
own contribution to the canonical-gazetteer design session, distinct from
both the UK (street = geometry, one product) and France (street has
neither its own row nor geometry, and only one product exists to check).

**The temporal model** (``Historie:Voorkomen``) is bitemporal: each object
version (``voorkomenidentificatie``, incrementing) carries both a *validity*
period (``beginGeldigheid``/``eindGeldigheid`` - when the fact was true in
the world) and a *registration* period (``tijdstipRegistratie``/
``eindRegistratie``, and the LV-specific
``tijdstipRegistratieLV``/``tijdstipEindRegistratieLV`` - when the national
registry actually knew it). Confirmed live: a real ``OpenbareRuimte``
("Boerhamsterweg") has two ``Voorkomen`` entries - version 1 ends
(``eindGeldigheid``) exactly when version 2 begins, its ``status`` changing
from issued to withdrawn. **None of this is modelled here** - the
history-bearing XML extract is investigated, not parsed, per the design
brief; this module only reads ``bag-light.gpkg`` (current-status only, no
history) and the Locatieserver.

**Status/lifecycle fields do survive into the history-free GeoPackage** -
each table carries its own small, real ``status`` vocabulary: ``pand``
(building) has 7 values including ``Pand in gebruik`` ("in use"),
``Bouw gestart`` ("construction started"), ``Sloopvergunning verleend``
("demolition permit granted"); ``verblijfsobject`` (dwelling/premises) has
5, including ``Verblijfsobject gevormd`` ("formed") and
``... buiten gebruik`` ("out of use"); ``woonplaats``/``standplaats``/
``ligplaats`` each have exactly one (``... aangewezen``, "designated" -
these three change status rarely enough that only the current one is ever
seen in a national snapshot). This is the GeoPackage's honest current-state
answer to "what happened to this object" even with no history attached.
``gebruiksdoel`` (usage) and ``bouwjaar`` (construction year) are real,
``gebruiksdoel`` comma-multi-valued where a building serves several
purposes (e.g. ``"winkelfunctie,woonfunctie"`` - retail+residential),
confirmed against the real national data, matching the brief's claim
these are "the most-requested fields."

**File sizes and row counts, the real national file, not estimated**:
``woonplaats`` 2,502 rows; ``pand`` 11,407,303; ``verblijfsobject``
9,969,593; ``standplaats`` 53,261; ``ligplaats`` 12,747 - ~21.4M rows
total. The GeoPackage itself is 7,801,561,088 bytes (~7.8 GB, confirmed via
a full download, not the feed's stated length alone) and took ~26 minutes
over this session's connection. The full-history XML extract zip is
3,610,187,048 bytes (~3.6 GB) and, unzipped one level, is itself a
zip-of-zips - one member per BAG object type (plus ``Inactief``/
``InOnderzoek``/``NietBag`` status buckets not covered above), each
containing one XML file per (very roughly) 10,000-address batch.

**Gemeente (municipality) is not part of the BAG at all.** Confirmed from
Kadaster's own disclaimer in the (unofficial, explicitly-non-authoritative)
``GEM-WPL-RELATIE`` helper file: BAG registers ``Woonplaats`` (settlement)
as its authentic administrative concept; the municipality/settlement link
comes from a Ministry of BZK table the Kadaster merely republishes for
convenience. Real BAG data should be read as ``Woonplaats``-scoped, not
municipality-scoped, if this SDK ever adds an ``administrative_area``.

**A `"weg"` Locatieserver result can carry a real line geometry - but it
isn't BAG's.** With ``fl="*"``, a `"weg"` (street) result includes
``geometrie_ll``/``geometrie_rd`` as a full ``MULTILINESTRING``, not just
the ``centroide_ll``/``centroide_rd`` point (confirmed live: real
"Ruïnelaan, Lochem" data). That looks like it contradicts the
no-geometry-on-``OpenbareRuimte`` finding above, but the result's own
``bron`` (source) field says ``"BAG/NWB"`` - the line comes from NWB
(Nationaal Wegenbestand, a separate national roads dataset), cross-matched
into the Locatieserver's index by the BAG name/identity, not from BAG
itself. :class:`BAGLocation` only models the point
(``centroide_ll``/``centroide_rd``, always present, always a ``POINT``);
the linear geometry is real data but reachable only via ``.raw`` - not
promoted to a first-class field, so as not to imply it's a BAG-native
property it isn't.

**Licence correction**: the design brief named "Creative Commons Public
Domain Mark 1.0". The live Atom feed's own ``<rights>`` element instead
links to ``creativecommons.org/publicdomain/zero/1.0`` - **CC0 1.0
Universal**, not PDM. Both are highly permissive public-domain-equivalent
instruments, but they are different legal tools (PDM labels a work already
believed public domain; CC0 is an active waiver) - the feed's own element is
authoritative here over the brief.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["BAGLocation"]


@dataclass(frozen=True)
class BAGLocation:
    """One Locatieserver result - covers every real ``type`` the API
    returns (``adres``, ``weg``, ``woonplaats``, ``gemeente``, ``postcode``,
    ...), since they share one flat field set with a `type`-dependent
    subset actually populated, faithfully to how the API itself works.

    ``id`` is the Locatieserver's own composite key (e.g.
    ``"adr-2a8dc1af055da20b8bcdc8e4dbda1eaa"``); ``identificatie`` is the
    real BAG object id embedded in the result where present. For a `"weg"`
    result (an ``openbare ruimte``), ``identificatie`` and
    ``openbareruimte_id`` are confirmed live to be the same value - the
    same real BAG street identifier described in the module docstring.
    """

    id: str
    type: str
    weergavenaam: str
    identificatie: str | None = None
    openbareruimte_id: str | None = None
    nummeraanduiding_id: str | None = None
    straatnaam: str | None = None
    huisnummer: int | None = None
    postcode: str | None = None
    woonplaatsnaam: str | None = None
    gemeentenaam: str | None = None
    provincienaam: str | None = None
    lon: float | None = None
    lat: float | None = None
    rd_x: float | None = None
    rd_y: float | None = None
    score: float | None = None
    afstand: float | None = None  # metres - only present on reverse() results
    raw: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<BAGLocation {self.weergavenaam!r} ({self.type}, {self.id})>"


def _parse_wkt_point(value: str | None) -> tuple[float, float] | None:
    """Locatieserver returns coordinates as ``POINT(x y)`` WKT strings, not
    GeoJSON - confirmed live for both ``centroide_ll``/``geometrie_ll``
    (WGS84 lon/lat) and ``centroide_rd``/``geometrie_rd`` (RD, EPSG:28992
    x/y). Never reprojected between the two - both are carried through as
    the API states them."""
    if not value or not value.startswith("POINT("):
        return None
    inner = value[len("POINT(") : -1]
    x_str, y_str = inner.split()
    return float(x_str), float(y_str)


def location_from_doc(doc: dict[str, Any]) -> BAGLocation:
    """Build a :class:`BAGLocation` from one Locatieserver response ``doc``
    (from ``free``/``suggest``/``reverse``/``lookup`` - the same shape,
    field richness varying by endpoint/``fl``, see the client module)."""
    lon_lat = _parse_wkt_point(doc.get("centroide_ll") or doc.get("geometrie_ll"))
    rd = _parse_wkt_point(doc.get("centroide_rd") or doc.get("geometrie_rd"))
    return BAGLocation(
        id=doc.get("id", ""),
        type=doc.get("type", ""),
        weergavenaam=doc.get("weergavenaam", ""),
        identificatie=doc.get("identificatie"),
        openbareruimte_id=doc.get("openbareruimte_id"),
        nummeraanduiding_id=doc.get("nummeraanduiding_id"),
        straatnaam=doc.get("straatnaam"),
        huisnummer=doc.get("huisnummer"),
        postcode=doc.get("postcode"),
        woonplaatsnaam=doc.get("woonplaatsnaam"),
        gemeentenaam=doc.get("gemeentenaam"),
        provincienaam=doc.get("provincienaam"),
        lon=lon_lat[0] if lon_lat else None,
        lat=lon_lat[1] if lon_lat else None,
        rd_x=rd[0] if rd else None,
        rd_y=rd[1] if rd else None,
        score=doc.get("score"),
        afstand=doc.get("afstand"),
        raw=doc,
    )
