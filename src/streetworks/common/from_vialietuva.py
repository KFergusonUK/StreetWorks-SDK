"""Via Lietuva (Lithuania) -> streetworks.common converter.

One ``Works`` per :class:`~streetworks.vialietuva.models.RoadRepair` row -
the source states no grouping key linking separate repairs into one
project, unlike Autobahn's ``identifier_prefix``, so each row stands alone,
with exactly one ``WorksSite``. ``territory="Lithuania"``,
``administrative_area="Via Lietuva"`` - the national road authority IS the
data-owning operator, the same rule already applied to Autobahn GmbH/
National Highways, not something the caller states.

**CRS: real Lithuanian national grid, LKS-94 (``EPSG:3346``), not WGS84** -
the third non-WGS84 roadworks provider in this SDK (after Belgium's
Lambert 72), confirmed from real coordinate value ranges. Passed as this
converter's own ``crs`` parameter, default ``EPSG:3346`` since every real
row checked uses it - unlike Belgium's ``from_datex2`` (where WGS84 is
still the overwhelmingly common case and Belgium is the opt-in exception),
here the *source itself* is single-CRS, so defaulting to it is honest, not
an assumption papered over a mixed feed. Coordinates are carried through
unconverted either way, per this SDK's standing CRS policy.

**Axis order is also non-standard - confirmed live, not assumed.** The
source's own WKT states ``(Northing, Easting)``, not the usual
``(Easting, Northing)`` - see
:class:`~streetworks.vialietuva.models.RoadRepair`'s own docstring for the
value-range evidence. :func:`~streetworks.common._wkt.coordinate_from_wkt`
parses the two numbers positionally and no further - so ``Coordinate.value``
here is genuinely ``(northing, easting)``, not ``(easting, northing)``, a
real trap for a caller assuming typical WKT axis order without reading this
paragraph.

The repair's full path (``geometry_wkt``, a real ``MULTILINESTRING``) is
preferred when present (71.6% of real rows); the point pair
(``from_point_wkt``/``to_point_wkt``) is the fallback, using only
``from_point_wkt`` - ``to_point_wkt`` is genuinely redundant with the last
vertex of ``geometry_wkt`` when both are present (confirmed live), so
carrying both as separate ``Coordinate`` values would double up the same
information rather than add to it.
"""

from __future__ import annotations

from ..vialietuva.models import RoadRepair
from ._wkt import coordinate_from_wkt
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_vialietuva"]


def _coordinate(item: RoadRepair, *, crs: str) -> Coordinate | None:
    wkt = item.geometry_wkt or item.from_point_wkt
    return coordinate_from_wkt(wkt, crs=crs)


def _to_site(item: RoadRepair, *, crs: str) -> WorksSite:
    return WorksSite(
        reference=item.work_id,
        works_type="Remontas",
        coordinate=_coordinate(item, crs=crs),
        proposed_start=item.start,
        proposed_end=item.end,
        date_confidence=DateConfidence.ESTIMATED if item.start else DateConfidence.UNKNOWN,
        traffic_management=item.description,
        source_grade=SourceGrade.OPERATOR,
        raw=item,
    )


def from_vialietuva(items: list[RoadRepair], *, crs: str = "EPSG:3346") -> list[Works]:
    """Convert :class:`~streetworks.vialietuva.models.RoadRepair` rows
    (from :meth:`~streetworks.vialietuva.ViaLietuvaClient.road_repairs`)
    into :class:`~streetworks.common.Works` - one per row, each with a
    single ``WorksSite``. See module docstring for the CRS/axis-order
    findings and why grouping is one-to-one, unlike Autobahn's phased
    works."""
    return [
        Works(
            reference=item.work_id,
            coordinate=_coordinate(item, crs=crs),
            territory="Lithuania",
            administrative_area="Via Lietuva",
            source_grade=SourceGrade.OPERATOR,
            sites=(_to_site(item, crs=crs),),
            raw=item,
        )
        for item in items
    ]
