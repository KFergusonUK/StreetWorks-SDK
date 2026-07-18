"""Autobahn (Germany) -> streetworks.common converter.

**Two-level spine, confirmed live, not assumed**: :class:`~streetworks.autobahn.models.Roadworks`
records sharing an :attr:`~streetworks.autobahn.models.Roadworks.identifier_prefix`
are genuinely phases of one works, not a coincidence - in a full 113-road
fetch (2,873 records, 997 distinct prefixes, 599 multi-record groups), every
single multi-record group agrees on its ``overall_end`` (the "Ende der
Gesamtmaßnahme" date), 599/599, zero disagreements.

**Grouping is cross-road, not per-road** - the one thing that needed
verifying before trusting the prefix at all. 50/997 real prefixes span more
than one road (up to 5), because a works project at a junction gets listed
under every connecting road's own ``services/roadworks`` response - e.g.
prefix ``"2023-000045"`` (an A1/A61 junction near Erftstadt) has 3 records
under ``A1`` and 2 under ``A61``, all genuinely one works. Confirmed safe to
merge: zero full ``identifier`` values are ever duplicated across roads
(each record appears under exactly one road's response), so grouping by
``identifier_prefix`` alone, across the whole fetch, never double-counts a
record - it just reunites a junction works that the source itself splits
across two API responses.

One ``Works`` per ``identifier_prefix``; one ``WorksSite`` per record.
``territory="Germany"``, ``administrative_area="Autobahn GmbH"`` - the
national motorway operator IS the data-owning authority, same rule as
National Highways for England.
"""

from __future__ import annotations

from collections import defaultdict

from ..autobahn.models import Roadworks
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_autobahn"]


def _coordinate(item: Roadworks) -> Coordinate | None:
    """``Roadworks.points`` is native GeoJSON ``(lon, lat)``; every other
    EPSG:4326 ``Coordinate`` in this SDK is ``(lat, lon)`` - flipped here,
    same as ``from_wzdx``. Line geometry (2-767 vertices, confirmed on
    100% of real records) is kept whole, not collapsed to a point."""
    if not item.points:
        return None
    flipped = tuple((lat, lon) for lon, lat in item.points)
    return Coordinate(
        value=flipped[0], crs="EPSG:4326", points=flipped if len(flipped) > 1 else None
    )


def _location_description(item: Roadworks) -> str | None:
    parts = [item.title, (item.subtitle or "").strip() or None]
    return " - ".join(p for p in parts if p) or None


def _date_confidence(item: Roadworks) -> DateConfidence:
    if item.is_start_verified:
        return DateConfidence.VERIFIED
    if item.start is not None:
        return DateConfidence.ESTIMATED
    return DateConfidence.UNKNOWN


def _to_site(item: Roadworks) -> WorksSite:
    confidence = _date_confidence(item)
    return WorksSite(
        reference=item.identifier,
        works_type=item.display_type,
        location_description=_location_description(item),
        coordinate=_coordinate(item),
        proposed_start=item.start,
        proposed_end=item.end,
        actual_start=item.start if confidence is DateConfidence.VERIFIED else None,
        date_confidence=confidence,
        traffic_management=", ".join(item.impact_symbols) or None,
        source_grade=SourceGrade.OPERATOR,
        raw=item,
    )


def from_autobahn(items: list[Roadworks]) -> list[Works]:
    """Convert :class:`~streetworks.autobahn.models.Roadworks` records into
    :class:`~streetworks.common.Works` - one per ``identifier_prefix``
    (across every road in ``items``, see module docstring), with one
    ``WorksSite`` per underlying record. ``items`` is expected to span
    however many roads you fetched (a single :meth:`~streetworks.autobahn.AutobahnClient.roadworks`
    call or the full :meth:`~streetworks.autobahn.AutobahnClient.iter_all_roadworks`) -
    grouping is safe either way, since it's the prefix, not the road, that
    identifies one works."""
    grouped: dict[str, list[Roadworks]] = defaultdict(list)
    for item in items:
        grouped[item.identifier_prefix].append(item)

    return [
        Works(
            reference=prefix,
            coordinate=_coordinate(group[0]),
            territory="Germany",
            administrative_area="Autobahn GmbH",
            source_grade=SourceGrade.OPERATOR,
            sites=tuple(_to_site(item) for item in group),
            raw=group,
        )
        for prefix, group in grouped.items()
    ]
