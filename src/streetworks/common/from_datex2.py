"""DATEX II -> streetworks.common converter.

Serves all DATEX adapters unchanged - NDW (Netherlands, XML), National
Highways (England SRN, JSON), Digitraffic (Finland, its own Simple-JSON -
see :mod:`streetworks.datex2.digitraffic` for why it still produces this
same model despite not being DATEX-shaped itself), IRCA (Iceland, XML -
:mod:`streetworks.datex2.irca`), Bison Futé (France, XML v2 -
:mod:`streetworks.datex2.bisonfute`), DGT (Spain, XML v3 -
:mod:`streetworks.datex2.dgt` - the one adapter whose roadworks records
carry no dedicated xsi:type at all, handled in the shared parser/model, not
here), Belgium/Flanders (XML v3 - :mod:`streetworks.datex2.belgium` - the
one adapter whose real coordinates are **not** WGS84, see ``crs`` below),
Luxembourg (XML v2.3 - :mod:`streetworks.datex2.luxembourg`), and Vegvesen
(Norway, **pending live verification** - see
:mod:`streetworks.datex2.vegvesen`) all normalise onto the same
:class:`~streetworks.datex2.Situation`/:class:`~streetworks.datex2.SituationRecord`
models, so one converter covers all of them; ``source_grade`` is always
:attr:`~streetworks.common.SourceGrade.OPERATOR` for DATEX per the spec's
provider table.

One :class:`~streetworks.common.WorksSite` per roadworks record
(``situation.roadworks`` - ``MaintenanceWorks``/``ConstructionWorks``); the
non-works measure records (lane closures, reroutings, speed limits...) are
deliberately left out of the common model, per spec - they're traffic-
management consequences, not works sites, and stay reachable natively via
``situation.measures``.

``territory``/``administrative_area`` can't be derived from a ``Situation``
alone - none of the three adapters' Situations state their own country, and
National Highways'/Digitraffic's ``source_name`` values aren't authority
names - so the caller states them explicitly rather than the converter
guessing which adapter produced the Situation:

- NDW: ``from_datex2(situation, territory="Netherlands")`` -
  ``administrative_area`` defaults to ``source_name`` (e.g.
  ``"Provincie Limburg"``), which is genuinely a province name there.
- National Highways: ``from_datex2(situation, territory="England",
  administrative_area="National Highways")`` - the operator IS the
  data-owning authority, so it's passed explicitly rather than trusting
  ``source_name`` (which is just the generic label ``"roadworks"``).
- Digitraffic (Finland): ``from_datex2(situation, territory="Finland",
  administrative_area=streetworks.datex2.digitraffic.provinces(payload).get(situation.id))`` -
  ``source_name`` there is a Fintraffic traffic-centre name, not a
  province, so relying on the default would be wrong; ``date_confidence``
  will come out ``UNKNOWN`` for every Finland site, honestly - Digitraffic
  has no active/planned/suspended-equivalent field for ``validity.status``
  to carry.
- IRCA (Iceland): ``from_datex2(situation, territory="Iceland")`` - no
  ``administrative_area`` is passed: checked exhaustively against the live
  feed, no region/authority-equivalent field exists there at all (see
  :mod:`streetworks.datex2.irca`). ``source_name`` also defaults to
  ``None`` here since no record carries a ``<source>`` element.
- Bison Futé (France): ``from_datex2(situation, territory="France",
  administrative_area=streetworks.datex2.bisonfute.dir_regions(situations).get(situation.id))``
  - ``source_name`` there is a fine-grained sub-office (e.g. ``"CEI de
  Rostrenen"``), not the DIR region; the DIR name (e.g. ``"Direction
  interdépartementale des routes/DIR Sud-Ouest"``) is genuinely stated but
  not on the shared model, so ``dir_regions()`` reads it from ``.raw``
  instead (see :mod:`streetworks.datex2.bisonfute`).
- DGT (Spain): ``from_datex2(situation, territory="Spain",
  administrative_area=streetworks.datex2.dgt.provinces(situations).get(situation.id))``
  - ``source_name`` is always ``None`` there (the ``<source>`` element states
  only ``sourceIdentification``, the operator ``"DGT"``, never a
  ``sourceName``), so relying on the default would leave
  ``administrative_area`` unset for every site; the real per-record
  ``province`` (e.g. ``"Toledo"``) is genuinely stated but, like France's DIR
  region, not on the shared model, so ``provinces()`` reads it from ``.raw``.
- Vegvesen (Norway, **pending live verification** - see
  :mod:`streetworks.datex2.vegvesen`): ``from_datex2(situation,
  territory="Norway")`` - no ``administrative_area`` is passed because no
  real Norwegian record has been inspected to confirm a genuinely-stated
  region field exists; it falls back to this converter's own default
  (``source_name``), which is itself unconfirmed to be an authority name for
  Norway. Revisit once Phase 2 shows real data.
- Belgium (Flanders): ``from_datex2(situation, territory="Belgium",
  administrative_area="Flanders", crs="EPSG:31370")`` - the ``crs``
  override is not optional here: confirmed live, every real coordinate in
  this feed is Belgian Lambert 72, not WGS84, despite the source XML using
  the same ``<latitude>``/``<longitude>`` tag names every WGS84 DATEX feed
  does. ``administrative_area="Flanders"`` is passed as a fixed literal,
  not read per-record, because the feed's own
  ``supplierIdentification/nationalIdentifier`` (``"BETICV"`` - Belgium
  Traffic Information Centre Vlaanderen) and dataset name
  ("Verkeerscentrum Vlaanderen") both confirm this source is Flanders-only,
  not all-Belgium; see :mod:`streetworks.datex2.belgium` for the coverage
  question and why Wallonia isn't covered here.
- Luxembourg: ``from_datex2(situation, territory="Luxembourg")`` - no
  ``administrative_area`` override needed: ``source_name`` is always the
  real, if abbreviated, authority initials (``"PCH"`` - Ponts et
  Chaussées), confirmed on 100% of real roadworks records, so the
  converter's own default already gives a meaningful value; see
  :mod:`streetworks.datex2.luxembourg`.
"""

from __future__ import annotations

from datetime import datetime

from ..datex2.models import Situation, SituationRecord
from ._crs import CrsProfile, resolve_coordinate_crs
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_datex2"]

#: validityStatus values that describe a real, already-committed occurrence
#: (genuine validity dates, not indicative ones) - confirmed against the
#: real National Highways fixture, which carries all three observed values.
#: "suspended" means temporarily paused, not that the dates are estimates,
#: so it's named here rather than falling through an unlabelled else.
_VERIFIED_STATUSES = frozenset({"active", "suspended"})
_ESTIMATED_STATUSES = frozenset({"planned"})


def _date_confidence(status: str | None) -> DateConfidence:
    if status in _VERIFIED_STATUSES:
        return DateConfidence.VERIFIED
    if status in _ESTIMATED_STATUSES:
        return DateConfidence.ESTIMATED
    return DateConfidence.UNKNOWN


def _location_description(record: SituationRecord) -> str | None:
    parts = [record.location.road_number, record.location.carriageway]
    text = ", ".join(p for p in parts if p)
    return text or None


def _coordinate(
    location_points: tuple[tuple[float, float], ...],
    *,
    crs: str = "EPSG:4326",
    srs_name: str | None = None,
    crs_candidates: tuple[CrsProfile, ...] | None = None,
) -> Coordinate | None:
    """DATEX ``Location.points`` is already in whatever order/CRS the
    source states - no flip, no reprojection. 2+ points is real line
    geometry (a ``LinearLocation``/posList, or a TPEG segment's from/to
    pair) - kept whole on ``points``, not just the first vertex; see
    ``Coordinate`` for why that used to be a loss.

    ``crs`` defaults to ``EPSG:4326`` (WGS84), true for every DATEX
    adapter checked before Belgium - but Belgium's own feed (Flanders,
    Verkeerscentrum) states real geometry in **EPSG:31370** (Belgian
    Lambert 72), confirmed live: every ``srsName`` attribute in the feed
    says so, and the values themselves (hundred-thousands, not the ~49-52/
    ~2-6 degree range Belgium's real latitude/longitude would be) confirm
    it - even though the source XML tags are still literally named
    ``<latitude>``/``<longitude>``, which is genuinely misleading if taken
    at face value. Per this SDK's standing CRS policy (never silently
    reproject), the caller states the real CRS explicitly rather than this
    function assuming WGS84 for everyone.

    ``crs_candidates`` is the opt-in escape hatch for feeds that mix more
    than one real CRS *within the same feed* (confirmed live: Vegvesen/
    Norway, ~76% UTM zone 33N, ~24% WGS84 - a single ``crs=`` override
    can't express that; see :mod:`streetworks.common._crs`). ``None``
    (the default) is zero behaviour change - every other adapter never
    passes it. When given, this record's own ``srs_name`` plus its first
    point's values are resolved via
    :func:`~streetworks.common._crs.resolve_coordinate_crs` against
    ``crs_candidates``; the winning CRS and axis order are then applied to
    every vertex in this record (not re-resolved per vertex - a single
    ``gmlLineString``/posList shares one CRS and axis convention for all
    its points, confirmed live). Resolution status (declared/inferred/
    corrected/unresolved) is deliberately not stored anywhere on
    ``Coordinate`` - it's telemetry only (see ``_crs`` module docstring)."""
    if not location_points:
        return None
    resolved_crs = crs
    points = location_points
    if crs_candidates is not None:
        raw_a, raw_b = location_points[0]
        resolution = resolve_coordinate_crs(
            srs_name=srs_name,
            raw_a=raw_a,
            raw_b=raw_b,
            encoding_default=crs,
            candidates=crs_candidates,
        )
        resolved_crs = resolution.epsg
        if resolution.ordered == (raw_b, raw_a):
            points = tuple((b, a) for a, b in location_points)
    return Coordinate(
        value=points[0],
        crs=resolved_crs,
        points=points if len(points) > 1 else None,
    )


def _to_site(
    record: SituationRecord, *, crs: str, crs_candidates: tuple[CrsProfile, ...] | None = None
) -> WorksSite:
    status = record.validity.status
    confidence = _date_confidence(status)
    overall_start = record.validity.overall_start
    overall_end = record.validity.overall_end
    # A "verified" status confirms the site has genuinely started; the end
    # is still just the validity window's expectation either way, so only
    # actual_start (never actual_end) is inferred from it.
    actual_start: datetime | None = (
        overall_start if confidence is DateConfidence.VERIFIED else None
    )
    works_type = (
        record.road_maintenance_type
        or record.construction_work_type
        or record.road_or_carriageway_or_lane_management_type
        or record.record_type
    )

    return WorksSite(
        reference=record.id,
        works_type=works_type,
        status=status,
        location_description=_location_description(record),
        coordinate=_coordinate(
            record.location.points,
            crs=crs,
            srs_name=record.location.srs_name,
            crs_candidates=crs_candidates,
        ),
        proposed_start=overall_start,
        proposed_end=overall_end,
        actual_start=actual_start,
        date_confidence=confidence,
        traffic_management=", ".join(record.comments) or None,
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_datex2(
    situation: Situation,
    *,
    territory: str | None = None,
    administrative_area: str | None = None,
    crs: str = "EPSG:4326",
    crs_candidates: tuple[CrsProfile, ...] | None = None,
) -> Works:
    """Convert one DATEX II :class:`~streetworks.datex2.Situation` (from
    either the NDW or National Highways adapter) into a
    :class:`~streetworks.common.Works`. See module docstring for
    ``territory``/``administrative_area`` - they can't be derived from the
    Situation alone, so pass them explicitly.

    ``crs`` defaults to ``EPSG:4326`` (WGS84), true for every DATEX
    adapter except Belgium (Flanders) - pass ``crs="EPSG:31370"`` for that
    one; see :func:`_coordinate`'s own docstring for how that was
    confirmed live, not assumed.

    ``crs_candidates`` is ``None`` by default - zero behaviour change for
    every adapter that doesn't pass it. Vegvesen (Norway) is the one real
    feed that needs it (genuinely mixed CRS within one feed, not just one
    non-WGS84 override like Belgium); callers there should use
    :func:`streetworks.common.from_vegvesen.from_vegvesen` rather than
    passing candidates here directly. See :func:`_coordinate` and
    :mod:`streetworks.common._crs` for the resolution rule."""
    roadworks = situation.roadworks
    first = roadworks[0] if roadworks else None
    return Works(
        reference=situation.id,
        promoter=first.source_name if first else None,
        coordinate=(
            _coordinate(
                first.location.points,
                crs=crs,
                srs_name=first.location.srs_name,
                crs_candidates=crs_candidates,
            )
            if first is not None
            else None
        ),
        territory=territory,
        administrative_area=(
            administrative_area
            if administrative_area is not None
            else (first.source_name if first else None)
        ),
        source_grade=SourceGrade.OPERATOR,
        sites=tuple(
            _to_site(record, crs=crs, crs_candidates=crs_candidates) for record in roadworks
        ),
        raw=situation,
    )
