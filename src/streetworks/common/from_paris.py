"""Paris "Chantiers à Paris" -> streetworks.common converter. This SDK's
fourth ``source_grade=register`` source (after England's Street Manager,
NYC DOT, and Chicago CDOT) - see :mod:`streetworks.paris.client`'s own
module docstring for the full investigation behind every claim below.

**A real Works-umbrella grouping, the same shape as NYC's
``applicationtrackingid``/Chicago's ``applicationnumber``.**
``chantier_cite_id`` genuinely groups multiple real emprise rows under
one parent chantier (a real 3-emprise example, ``329467``, a green-space
maintenance job spanning 3 distinct real polygons). So ``from_paris``
groups by it the same way, one ``Works`` per chantier, one ``WorksSite``
per emprise row under it. A row with no ``chantier_cite_id`` (not
observed live, but never assumed absent) falls back to a thin, one-site
``Works`` keyed on its own ``num_emprise``.

**``street_ref`` is never populated** - the real schema has no segment/
street identifier field, only ``cp_arrondissement`` (postcode) and the
geometry itself. Same NYC/Chicago/Roads-ACT discipline.

**``date_confidence`` is uniformly ``ESTIMATED``, never ``VERIFIED``** -
there is no status field at all (not even an application-lifecycle one
like NYC/Chicago have) to ground a firmer signal. ``date_debut``/
``date_fin`` map to ``proposed_start``/``proposed_end`` only;
``actual_start``/``actual_end`` stay ``None``.

**Geometry: the representative point only, not the full polygon.**
``geo_shape`` is a real GeoJSON ``Polygon`` (the emprise footprint), but
``Coordinate.points``/``.parts`` are documented for line-geometry
vertices, not polygon rings - forcing a ring into either would misuse
that contract. So ``_coordinate`` uses ``geo_point_2d`` (ODS's own
representative point for the shape) as ``Coordinate.value``, a
deliberate, documented simplification, not an oversight. The full
``geo_shape`` polygon is preserved unmodified in ``WorksSite.raw`` for
any caller that needs the real footprint.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_paris"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "France"
_ADMINISTRATIVE_AREA = "Ville de Paris - Direction de la Voirie et des Déplacements"


def _coordinate(record: JSON) -> Coordinate | None:
    point = record.get("geo_point_2d")
    if not point:
        return None
    lon, lat = point.get("lon"), point.get("lat")
    if lon is None or lat is None:
        return None
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def _to_site(record: JSON) -> WorksSite:
    return WorksSite(
        reference=record.get("num_emprise"),
        works_type=record.get("chantier_synthese"),
        location_description=record.get("cp_arrondissement"),
        coordinate=_coordinate(record),
        proposed_start=parse_iso8601(record.get("date_debut")),
        proposed_end=parse_iso8601(record.get("date_fin")),
        date_confidence=DateConfidence.ESTIMATED,
        source_grade=SourceGrade.REGISTER,
        raw=record,
    )


def from_paris(records: list[JSON]) -> list[Works]:
    """Convert real "Chantiers à Paris" emprise rows (plain dicts from
    :meth:`streetworks.paris.ParisClient.iter_permits`/``iter_roadworks``)
    into :class:`~streetworks.common.Works`. Date fields are real
    ``YYYY-MM-DD`` text, parsed via the shared
    :func:`~streetworks._dt.parse_iso8601`."""
    grouped: dict[str, list[JSON]] = defaultdict(list)
    thin: list[JSON] = []
    for record in records:
        chantier_id = record.get("chantier_cite_id")
        if chantier_id:
            grouped[chantier_id].append(record)
        else:
            thin.append(record)

    works_list = [
        Works(
            reference=chantier_id,
            coordinate=_coordinate(group[0]),
            promoter=group[0].get("moa_principal"),
            territory=_TERRITORY,
            administrative_area=_ADMINISTRATIVE_AREA,
            source_grade=SourceGrade.REGISTER,
            sites=tuple(_to_site(r) for r in group),
            raw=group,
        )
        for chantier_id, group in grouped.items()
    ]
    works_list.extend(
        Works(
            reference=record.get("num_emprise"),
            coordinate=_coordinate(record),
            promoter=record.get("moa_principal"),
            territory=_TERRITORY,
            administrative_area=_ADMINISTRATIVE_AREA,
            source_grade=SourceGrade.REGISTER,
            sites=(_to_site(record),),
            raw=[record],
        )
        for record in thin
    )
    return works_list
