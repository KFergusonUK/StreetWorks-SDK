"""IDEE (Spain transport network) -> streetworks.common gazetteer
converter.

One real ``tn-ro:Road`` is a genuine, independently-published named street
entity - never synthesised by grouping ``RoadLink``s - so it maps directly
to :class:`~streetworks.common.gazetteer.Street`, per this model's "no
synthetic streets" rule. ``streetworks.idee`` does not emit a
:class:`~streetworks.common.gazetteer.Segment` per constituent
``RoadLink`` (a real, deliberate scope choice, not a gap - see
:mod:`streetworks.idee.client`'s own module docstring for why the
already-necessary two-hop join doesn't extend to a third hop for
per-link classification data this model's three use cases don't need),
so ``Street.segment_refs`` stays empty.
"""

from __future__ import annotations

from ..idee.models import Road
from .gazetteer import GeometryGrade, Name, Street
from .models import Identifier, SourceGrade

__all__ = ["from_idee"]


def from_idee(road: Road) -> Street:
    """Convert one real :class:`~streetworks.idee.models.Road` into a
    :class:`~streetworks.common.gazetteer.Street`.

    Two real, independently-stated identifiers, both kept: the WFS's own
    internal ``gml:id`` (what ``RESOURCEID`` takes) and the separately
    stated INSPIRE ``base:localId``/``base:namespace`` pair - related but
    not textually identical, see :class:`~streetworks.idee.models.Road`'s
    own docstring. ``national_road_code``/``local_road_code`` become
    further :class:`~streetworks.common.Identifier`\\ s, undecoded and
    carried exactly as stated - ``local_road_code`` is real but genuinely
    municipality-scoped, with no stated scope to record honestly, so its
    ``scope`` stays ``None`` rather than a fabricated value.
    """
    identifiers = [Identifier(scheme="gmlId", value=road.id)]
    if road.inspire_local_id:
        identifiers.append(
            Identifier(
                scheme="inspireId",
                value=road.inspire_local_id,
                scope=road.inspire_namespace,
            )
        )
    if road.national_road_code:
        identifiers.append(
            Identifier(scheme="nationalRoadCode", value=road.national_road_code)
        )
    if road.local_road_code:
        identifiers.append(
            Identifier(scheme="localRoadCode", value=road.local_road_code)
        )

    return Street(
        identifiers=tuple(identifiers),
        names=(Name(value=road.name),) if road.name else (),
        geometry=road.geometry,
        geometry_grade=GeometryGrade.PUBLISHED if road.geometry else GeometryGrade.ABSENT,
        territory="Spain",
        source_grade=SourceGrade.REGISTER,
        raw=road,
    )
