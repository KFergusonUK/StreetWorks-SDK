"""Oslo (SøkSys activities) -> streetworks.common converter. See
:mod:`streetworks.oslo.client`'s own module docstring for the full
investigation - in particular why the real source isn't what the
investigation brief guessed, and the real dedupe/grouping finding this
converter is built around.

**Dedupe by exact ``id`` first, then group by ``activity_id`` - a real
umbrella grouping, the same shape as Jersey's ``PROJID``/NYC DOT's
``applicationtrackingid``, not Copenhagen's "pick one representative
geometry" pattern.** Confirmed live that 256 of 261 real multi-row
permits are pure duplicate artifacts (identical ``id``, identical
geometry - a tiling artifact of querying a wide bbox); those collapse to
one row via the ``id`` dedupe. The handful of permits left with more
than one row afterwards genuinely span several distinct real sub-areas
(different ``id``, different real coordinates) - each becomes its own
``WorksSite`` under one ``Works``, keyed on the shared ``file_number``.

**Coordinates stay plain ``(x, y)`` = ``(easting, northing)``, never
swapped.** ``EPSG:25832`` (ETRS89/UTM zone 32N) is a genuinely projected
CRS, not WGS84 - this SDK's ``(lat, lon)`` convention only applies to
EPSG:4326 (see ``from_sct``/``from_wzdx``/``from_autobahn``'s own
docstrings); projected coordinates are stored as-is, the same discipline
``from_streetmanager`` already applies to British National Grid and
Jersey/NYC DOT/Via Lietuva apply to their own projected sources.

**Polygon geometry (the majority real shape here) uses its own first
ring's first vertex as ``Coordinate.value`` only** -
``Coordinate.points``/``.parts`` are documented for line-geometry
vertices, not polygon rings, so forcing a ring into either would misuse
that contract, the same discipline :mod:`.from_paris` already applies to
its own polygon case. The full raw geometry is preserved in
``WorksSite.raw`` regardless.

**Dates are real ISO-shaped text, timezone-naive** - ``start_date``/
``end_date`` parse via the shared :func:`~streetworks._dt.parse_iso8601`
(no bespoke format needed, unlike Copenhagen's Danish ``DD-MM-YY``). No
timezone is stated anywhere in the schema. ``date_confidence`` is
``ESTIMATED`` even though the real ``status`` is always ``"Innvilget"``
(Approved) under the default filter - a granted permit is not an
independently confirmed "work is happening" signal, the same discipline
Copenhagen/NYC DOT/Chicago/Paris apply.

**``street_ref`` is never populated** - only free-text ``addresses``
exist, no street/segment identifier, the same discipline every other
municipal-permit converter in this SDK applies.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_oslo"]

JSON = dict[str, Any]

_CRS = "EPSG:25832"
_TERRITORY = "Norway"
_ADMINISTRATIVE_AREA = "Oslo kommune"


def _coordinate(feature: JSON) -> Coordinate | None:
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    kind = geometry.get("type")
    if not coords:
        return None
    if kind == "Point":
        return Coordinate(value=(float(coords[0]), float(coords[1])), crs=_CRS)
    if kind == "LineString":
        points = tuple((float(v[0]), float(v[1])) for v in coords)
        if not points:
            return None
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
    if kind == "Polygon":
        # Ring vertices don't fit Coordinate.points'/.parts' line-geometry
        # contract - the first ring's first vertex is used as a
        # representative point only, see module docstring.
        ring = coords[0] if coords else None
        if not ring:
            return None
        first = ring[0]
        return Coordinate(value=(float(first[0]), float(first[1])), crs=_CRS)
    return None


def _location_description(properties: JSON) -> str | None:
    addresses = properties.get("addresses") or []
    return ", ".join(addresses) or None


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    start = parse_iso8601(properties.get("start_date"))
    end = parse_iso8601(properties.get("end_date"))
    return WorksSite(
        reference=properties.get("id"),
        works_type=properties.get("activity_type"),
        status=properties.get("status"),
        location_description=_location_description(properties),
        coordinate=_coordinate(feature),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN,
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )


def from_oslo(features: list[JSON]) -> list[Works]:
    """Convert real Oslo SøkSys activity features (from
    :meth:`streetworks.oslo.OsloClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - deduped by exact ``id`` (drops
    real tiling-duplicate rows), then grouped by ``activity_id`` into one
    ``Works`` with one ``WorksSite`` per surviving distinct geometry row.
    See module docstring."""
    seen_ids: set[Any] = set()
    deduped: list[JSON] = []
    for feature in features:
        row_id = (feature.get("properties") or {}).get("id")
        if row_id is not None:
            if row_id in seen_ids:
                continue
            seen_ids.add(row_id)
        deduped.append(feature)

    by_activity: dict[Any, list[JSON]] = defaultdict(list)
    unresolved: list[JSON] = []
    for feature in deduped:
        activity_id = (feature.get("properties") or {}).get("activity_id")
        if activity_id is not None:
            by_activity[activity_id].append(feature)
        else:
            unresolved.append(feature)

    works_list: list[Works] = []
    for group in by_activity.values():
        sites = [_to_site(f) for f in group]
        header = (group[0].get("properties") or {})
        works_list.append(
            Works(
                reference=header.get("file_number"),
                coordinate=sites[0].coordinate if sites else None,
                promoter=header.get("sender"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.REGISTER,
                sites=tuple(sites),
                raw=group,
            )
        )
    for feature in unresolved:
        properties = feature.get("properties") or {}
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=properties.get("file_number"),
                coordinate=site.coordinate,
                promoter=properties.get("sender"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.REGISTER,
                sites=(site,),
                raw=[feature],
            )
        )
    return works_list
