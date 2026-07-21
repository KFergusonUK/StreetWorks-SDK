"""Canonical cross-provider types for gazetteer data (streetworks 0.8.0).

The gazetteer equivalent of what :mod:`.models` did for works data at 0.5.0
- designed *after* the native adapters, from their real shapes, not before.
Converters live alongside the native, full-fidelity provider interfaces -
they never replace them. Every canonical object keeps ``.raw`` pointing back
at its source record(s).

**The trim test.** This model serves three use cases and no more: plotting
streets on a map, linking streets to roadworks, and pulling street names
from address gazetteers. Anything more complex is expected to use the
native interfaces directly. If a field doesn't serve one of those three, it
doesn't belong here - *unless* a source genuinely states it and dropping it
would lose real data, which this project does not do; where those two
principles conflict, the field is kept and marked optional.

**Evidence discipline.** Every field traces to a real payload from a real
provider - nothing here is speculative. Where a field is supported by only
*one* provider, its docstring says so; those are the model's weakest points,
kept because stated data is never dropped, not because they're load-bearing.

**Three types, not two.** :class:`Segment` is independent, not a child list
of :class:`Street` - the relationship is many-to-many, proven by two
independent real sources: DataVIA's ``ESUStreets.usrns`` is plural (a real
ESU, e.g. ``esuid`` ``4276210541888`` in Durham, carries
``usrns="11713562;11713561"`` - one physical segment serving two distinct
designated streets, Church Street and Church Street Villas), and NVDB's real
"Dalveien" address (``adressekode`` 1140) spans two topologically-unrelated
``veglenkesekvenser``. Containment would misstate both.

**No synthetic streets.** A :class:`Street` is only ever emitted by a
provider that publishes a street entity - never derived from grouping
addresses or segments. Consequence, stated plainly rather than worked
around: ``from_nwb`` emits no ``Street`` at all. NWB publishes segments with
a ``bag_orl`` reference; BAG's GeoPackage (this SDK's only built BAG route)
has no street row of its own - only the (not built) full XML extract does.
So Dutch street names arrive via ``Address.street_name``, never via a
Dutch ``Street``. This is a real gap with a real fix waiting (the BAG XML
extract), not a design flaw to route around.

**Never infer, never reproject, never fabricate.** Links are stated
identifiers only - a name match is not a join (NWB's own name-based grouping
is measurably worse: 7 of 385 real groups span two different ``bag_orl``
values). CRS is labelled as given and never reprojected - it varies by
*route*, not just by provider (BD TOPO: Lambert-93 bulk, WGS84 over WFS;
Kartverket addresses EPSG:4258 vs. NVDB EPSG:5973). Segment order is
preserved from the source, never inferred, and segments are never assumed
contiguous or end-to-end traceable (see the Dalveien case above). Z is
preserved where present, never defaulted to 0 - see :class:`.Coordinate`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

from .models import Coordinate, Identifier, SourceGrade

__all__ = [
    "GeometryGrade",
    "Name",
    "StreetType",
    "AddressRange",
    "Street",
    "Segment",
    "Address",
]


class GeometryGrade(str, Enum):
    """Whether a :class:`Street`'s geometry is present - not a data-quality
    score. There is deliberately no ``derived`` value: a canonical `Street`
    never synthesises geometry (e.g. by unioning its segments' lines) that
    the source itself didn't publish - see the module docstring's
    "no synthetic streets" rule."""

    PUBLISHED = "published"
    ABSENT = "absent"  #: e.g. OS Open USRN's real NULL-geometry rows


@dataclass(frozen=True)
class Name:
    """One name a source states, with whatever it states alongside it - all
    optional except ``value`` because no single source states all of them.

    ``language`` where stated (the NSG's ``_eng``/``_cym`` pairs each become
    their own `Name`; Norway's SSR states language directly per name).
    ``status`` where stated (SSR: approved vs. proposed - real values seen
    include ``"godkjent og prioritert"``/``"foreslått og prioritert"``).
    ``side`` where the source distinguishes left/right (BD TOPO only, so
    far - ``nom_voie_ban_gauche``/``_droite``)."""

    value: str
    language: str | None = None
    status: str | None = None
    side: str | None = None


@dataclass(frozen=True)
class StreetType:
    """A street/road classification as the source states it - either
    ``code`` or ``label`` may be absent, and some sources give both (NWB's
    ``bst_code``: a short code like ``"VP"`` needing an external lookup,
    with no plain-label counterpart carried by this SDK; BD TOPO's
    ``nature``: a plain label like ``"Route à 1 chaussée"``, no code; NVDB's
    ``typeVeg``/``typeVeg_sosi``: both a plain label and a parallel SOSI
    code). This SDK does not bundle lookup tables and does not decode
    codes - whatever the source states is what's carried."""

    code: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class AddressRange:
    """A house-number range stated directly on a street segment - NWB only,
    so far (its six real ``hnrstrlnks``/``hnrstrrhts``/``e_hnr_lnks``/
    ``e_hnr_rhts``/``l_hnr_lnks``/``l_hnr_rhts`` fields, one pair per side).
    A *third* address-street linking mechanism, alongside a stated
    identifier and a name match: it lets a caller place an address on a
    street without consulting the address register at all.

    ``structure`` carries whatever NWB's own ``hnrstrlnks``/``hnrstrrhts``
    value is for that side, undecoded - real values observed so far are
    ``"N"``, ``"E"`` and empty (-> ``None``); NWB's own domain for this
    field runs wider than what this SDK has independently confirmed live,
    so it is carried as a code, not decoded into a label."""

    side: str | None
    first: int | None
    last: int | None
    structure: str | None = None


@dataclass
class Street:
    """A named, published street entity - only ever emitted by a provider
    that publishes one; see the module docstring's "no synthetic streets"
    rule. ``segment_refs`` and ``address_links`` are references, not
    embedded objects - resolving them is a separate, explicit, opt-in
    operation this model does not perform (merging providers would silently
    combine licences, CRSs and update cadences)."""

    identifiers: tuple[Identifier, ...] = ()
    names: tuple[Name, ...] = ()
    street_type: StreetType | None = None
    geometry: Coordinate | None = None
    geometry_grade: GeometryGrade = GeometryGrade.ABSENT
    segment_refs: tuple[Identifier, ...] = ()
    address_links: tuple[Identifier, ...] = ()
    as_at: date | None = None
    territory: str | None = None
    administrative_area: str | None = None
    source_grade: SourceGrade = SourceGrade.REGISTER
    raw: Any = None

    @property
    def name(self) -> str | None:
        """The first name **in source order** - never a ranking this SDK
        invents. Mirrors :attr:`.Coordinate.value`/``.points``: a
        convenience for the common case, with every stated name still
        reachable via ``names``."""
        return self.names[0].value if self.names else None


@dataclass
class Segment:
    """A part of a street - never a street itself. ``street_refs`` is
    **plural**: this is the entire point of :class:`Segment` being
    independent of :class:`Street` rather than a child of it - see the
    module docstring for the two real sources that prove the relationship
    is many-to-many, not one-to-many.

    ``administrative_area`` is on the segment, not just the parent street,
    because BD TOPO states different INSEE commune codes per side of one
    `troncon_de_route` - a real segment can genuinely straddle two
    communes, something the street level alone can't express."""

    geometry: Coordinate
    identifiers: tuple[Identifier, ...] = ()
    names: tuple[Name, ...] = ()  # optional; BD TOPO only, so far
    street_refs: tuple[Identifier, ...] = ()
    street_type: StreetType | None = None
    address_ranges: tuple[AddressRange, ...] = ()  # optional; NWB only, so far
    administrative_area: str | None = None
    as_at: date | None = None
    raw: Any = None


@dataclass
class Address:
    """One address, from any of the three built address registers.
    ``street_name`` is stated by all three (`ban`, `bag`, `kartverket`) and
    is the direct answer to this model's third use case (pulling street
    names from address gazetteers).

    ``housenumber``/``suffix``, not ``number``/``unit`` - no built source
    has a `unit`/flat concept. BAN states `numero`+`suffixe` (real example:
    numero ``4``, suffixe ``"bis"``); Kartverket states `nummer`+`bokstav`;
    BAG currently only models `huisnummer` (see :mod:`.from_bag`).
    **Route-dependency**: BAN's geocoding API folds any suffix into
    `housenumber` and never populates `suffix` separately - only its bulk
    CSV routes decompose it. Converters never fabricate a split; where a
    source doesn't decompose, `suffix` is `None` and the whole value sits in
    `housenumber`, exactly as the source gave it."""

    geometry: Coordinate
    identifiers: tuple[Identifier, ...] = ()
    housenumber: str | None = None
    suffix: str | None = None
    street_name: str | None = None
    street_links: tuple[Identifier, ...] = ()
    as_at: date | None = None
    territory: str | None = None
    administrative_area: str | None = None
    source_grade: SourceGrade = SourceGrade.REGISTER
    raw: Any = None
