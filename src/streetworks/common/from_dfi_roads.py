"""DfI Roads (Northern Ireland Highway Network) -> streetworks.common
gazetteer converter.

A real ``Section_Code`` per maintained-road section, never a named
street entity on its own - DfI publishes sections, not streets, so this
maps to :class:`~streetworks.common.gazetteer.Segment`, never a
synthesised :class:`~streetworks.common.gazetteer.Street` (per this
model's "no synthetic streets" rule). ``SECTION_NA`` (e.g. "BELFAST RD")
is a real, repeated attribute across several distinct sections, not a
separate published entity to derive a `Street` from - the second real
source (after BD TOPO) to populate `Segment.names`.
"""

from __future__ import annotations

from ..dfi_roads.models import RoadSection
from .gazetteer import Name, Segment, StreetType
from .models import Identifier

__all__ = ["from_dfi_roads"]


def from_dfi_roads(section: RoadSection) -> Segment:
    """Convert one real :class:`~streetworks.dfi_roads.models.RoadSection`
    into a :class:`~streetworks.common.gazetteer.Segment`. ``street_refs``
    stays empty - no separate street entity exists to reference, see the
    module docstring. ``adoption_status``/``section_type``/
    ``shape_length`` have no canonical home and stay on ``.raw`` only,
    same "real field, no promotion without a stated consumer" discipline
    every other gazetteer converter follows.
    """
    return Segment(
        geometry=section.geometry,
        identifiers=(Identifier(scheme="section_code", value=section.section_code),),
        names=(Name(value=section.section_name),) if section.section_name else (),
        street_type=StreetType(label=section.class_name) if section.class_name else None,
        administrative_area=section.section_office_name or None,
        raw=section,
    )
