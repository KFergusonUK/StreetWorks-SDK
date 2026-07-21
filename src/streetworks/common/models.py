"""Canonical cross-provider types for works data.

Two levels, deliberately not three: :class:`Works` is the umbrella
(reference, location, promoter/source - no committed dates of its own);
:class:`WorksSite` is the dated, actionable unit under it (Street Manager's
``-01``/``-02`` permits, SRWR's phases, DATEX roadworks records all map
here). :class:`WorksPlanning` is a separate type for planning *artifacts*
(PAAs, Forward Plans) with indicative rather than committed dates - a
record that is *born* as a planning artifact maps here; a record that only
*transitions* through a planning-ish status (e.g. DATEX ``validityStatus =
planned``, an SRWR phase in "Advance Planning") stays a `WorksSite` with
that status exposed, so the same source record never migrates between
canonical types as its lifecycle progresses.

Converters live alongside the native, full-fidelity provider interfaces -
they never replace them. Every canonical object keeps ``.raw`` pointing back
at its source record(s), so nothing is lost by converting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

__all__ = [
    "SourceGrade",
    "DateConfidence",
    "Point2D",
    "Point3D",
    "Coordinate",
    "Identifier",
    "Notice",
    "WorksSite",
    "WorksPlanning",
    "Works",
]


class SourceGrade(str, Enum):
    """How trustworthy/authoritative a provider's data is - lets consumers
    filter without tribal knowledge of which providers are which."""

    REGISTER = "register"  #: statutory works registers (Street Manager, SRWR)
    OPERATOR = "operator"  #: road-operator published data (DATEX, WZDx)
    TRAVELLER_INFO = "traveller_info"  #: best-effort RSS extraction (TrafficWatchNI, Traffic Wales)


class DateConfidence(str, Enum):
    """How firm a :class:`WorksSite`'s dates are - computed per provider,
    never asserted by the source data itself."""

    VERIFIED = "verified"  #: an actual/active date is present
    ESTIMATED = "estimated"  #: only a proposed/planned date is present
    UNKNOWN = "unknown"  #: no date signal firm enough to grade


Point2D = tuple[float, float]
Point3D = tuple[float, float, float]


@dataclass(frozen=True)
class Coordinate:
    """A location value plus its coordinate reference system, explicit and
    never silently converted. UK register/gazetteer providers use British
    National Grid (``EPSG:27700`` easting/northing); DATEX providers use
    WGS84 (``EPSG:4326`` latitude/longitude). Mixed-CRS comparisons are the
    caller's informed choice, not something this SDK guesses at.

    ``value`` is always one representative point - the first vertex, for a
    line - so every existing point-only consumer keeps working unchanged.
    ``points`` is ``None`` for a genuine point location; when the source
    geometry is a real line (WZDx/Street Manager LineString, a DATEX
    ``LinearLocation``/TPEG segment), it holds every vertex in the same
    order/axis convention as ``value``, with ``points[0] == value`` always.
    Populated only where a converter has real multi-vertex geometry to give
    - never synthesised from a single point.

    **Z (added for the canonical-gazetteer model, streetworks 0.8.0):** every
    point - in ``value``, ``points``, or ``parts`` - is either a 2-tuple
    ``(x, y)`` or a 3-tuple ``(x, y, z)``. Additive and backwards-compatible:
    every existing converter still produces plain 2-tuples, unchanged. Z
    appears where a source states genuine 3D geometry (NVDB's real
    ``LINESTRING Z`` under EPSG:5973, a compound CRS - UTM33N + the NN2000
    height datum, already carried in the CRS label, so no separate datum
    field is needed) - never defaulted to 0 where a source is 2D, since a
    fabricated zero is indistinguishable from real sea level.

    **``parts`` (added alongside Z):** ``None`` for a single-line/point
    geometry (the existing, still-default shape). Populated only where a
    source states a genuine ``MultiLineString`` (DataVIA's ``StreetLines``:
    one ``Street`` aggregates several ESUs' worth of line geometry in one
    real MultiLineString) - each element is one part's ordered vertex tuple,
    in source order. ``value``/``points`` still describe the *first* part
    alone, so point-only and single-line consumers keep working unchanged;
    ``parts`` is the only place the other parts live. **Positional
    correspondence between ``parts`` and any sibling id list (e.g.
    ``Street.segment_refs`` from DataVIA's ``esuids``) is never assumed by
    this type or by any converter** - verify it against real data before
    relying on it, per the same source.
    """

    value: Point2D | Point3D
    crs: str
    points: tuple[Point2D | Point3D, ...] | None = None
    parts: tuple[tuple[Point2D | Point3D, ...], ...] | None = None


@dataclass(frozen=True)
class Identifier:
    """One identifier a source states for something - a street, segment or
    address. Lives here (not in :mod:`.gazetteer`) because it's shared by
    :class:`WorksSite.street_ref` as well as every gazetteer type.

    ``scope`` records the uniqueness scope, which matters because most
    European street/address identifiers are *municipality-scoped*, not
    nationally unique (BAN's ``toponyme_id`` splits at commune boundaries;
    Kartverket's ``adressekode`` is per-kommune, and the same code is real
    and reused for unrelated streets in different kommuner - confirmed live,
    e.g. code 1300 means different streets in different municipalities). A
    field called "identifier" holding a non-unique value on its own is a
    trap; ``scope`` (e.g. the commune/kommune code) is what makes it safe to
    compare. ``None`` where a source's identifier genuinely is nationally
    unique (e.g. DataVIA/OS Open USRN's ``usrn``, BD TOPO's ``cleabs``)."""

    scheme: str
    value: str
    scope: str | None = None


@dataclass
class Notice:
    """One entry in a :class:`WorksSite`'s noticing/paperwork event stream -
    only populated where the provider actually has one (Street Manager,
    SRWR's 006 records)."""

    notice_type: str | None = None
    text: str | None = None
    date: datetime | None = None
    raw: Any = None


@dataclass
class WorksSite:
    """A dated, actionable unit of works - the primary query surface
    ("what's happening on road X, when"). Emitted wherever the source
    genuinely carries dates/closure information, even if best-effort
    extracted; never fabricated where the source has none.

    ``street_ref`` (streetworks 0.8.0, the gazetteer-model connection point)
    is singular, unlike ``Segment.street_refs`` - a UK permit is per-USRN by
    statute (a job spanning two streets is several ``WorksSite`` records
    under one ``Works``), so singular reflects every built provider's real
    data, not a structural guarantee. **Populated only where a source states
    a street identifier** - Street Manager states a USRN per permit; most
    DATEX providers state a road name/number and no identifier, so those
    populate nothing here, per the name-is-not-a-join rule. Real data
    already found one source (SRWR) that states street identity at the
    *activity* level, potentially for more than one real street, with no
    stated per-phase/per-site join back to a specific ``WorksSite`` - see
    :mod:`.from_srwr`'s docstring for why that source leaves this ``None``
    rather than guessing which site a given street belongs to."""

    reference: str | None = None
    works_type: str | None = None
    status: str | None = None
    location_usrn: str | None = None
    location_description: str | None = None
    coordinate: Coordinate | None = None
    street_ref: Identifier | None = None
    proposed_start: datetime | None = None
    proposed_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    date_confidence: DateConfidence = DateConfidence.UNKNOWN
    operating_window: str | None = None
    traffic_management: str | None = None
    notices: tuple[Notice, ...] = ()
    source_grade: SourceGrade = SourceGrade.TRAVELLER_INFO
    raw: Any = None
    _works: Works | None = field(default=None, repr=False, compare=False)

    @property
    def territory(self) -> str | None:
        """Delegates to the parent :class:`Works` - wired automatically when
        this site is passed into ``Works(sites=...)``. ``None`` for a
        WorksSite constructed standalone, outside any Works."""
        return self._works.territory if self._works is not None else None

    @property
    def administrative_area(self) -> str | None:
        """Delegates to the parent :class:`Works` - see :attr:`territory`."""
        return self._works.administrative_area if self._works is not None else None


@dataclass
class WorksPlanning:
    """A planning artifact - PAA or Street Manager Forward Plan - with
    indicative, not committed, dates. ``works_reference`` is optional: a PAA
    is usually linked to a :class:`Works` umbrella, a Forward Plan is
    free-floating until (if) it converts to a permit."""

    kind: str = ""  # e.g. "paa", "forward_plan"
    works_reference: str | None = None
    indicative_start: datetime | None = None
    indicative_end: datetime | None = None
    source_grade: SourceGrade = SourceGrade.REGISTER
    raw: Any = None


@dataclass
class Works:
    """The umbrella works record - reference, location, promoter/source.
    Carries no committed dates of its own; those live on its `sites`.

    ``plannings`` holds any planning artifacts (PAAs, Forward Plans) sharing
    this Works' reference - in practice a provider's planning record often
    already carries the eventual work reference (observed on live Street
    Manager Forward Plan data, ahead of any permit existing under it), so
    it's a sibling of `sites` here rather than always floating free of any
    Works. A planning artifact with no linkable reference at all still gets
    its own free-standing :class:`WorksPlanning` outside any Works.

    ``territory``/``administrative_area`` are location-provenance, not
    location-geography: ``territory`` is the country/nation this data
    covers (UK nations count as countries - "Scotland", "England", ...,
    plus "USA", "Netherlands", etc; almost always set, mostly hardcoded per
    converter since each provider knows its own territory) and
    ``administrative_area`` is the sub-national body that *owns* the data
    one level down (a UK highway authority, a US state DOT, a Dutch
    province, or a national operator's own name where the operator IS the
    authority) - populated only where the provider genuinely states it,
    never inferred from a coordinate. ``administrative_area`` is consistent
    *within* a territory but not size-comparable *across* territories (a US
    state dwarfs a UK county) - filter by ``territory`` first before
    aggregating by area.
    """

    reference: str | None = None
    location_usrn: str | None = None
    coordinate: Coordinate | None = None
    promoter: str | None = None
    territory: str | None = None
    administrative_area: str | None = None
    source_grade: SourceGrade = SourceGrade.TRAVELLER_INFO
    sites: tuple[WorksSite, ...] = ()
    plannings: tuple[WorksPlanning, ...] = ()
    raw: Any = None

    def __post_init__(self) -> None:
        for site in self.sites:
            site._works = self
