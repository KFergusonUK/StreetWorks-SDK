"""OS Open USRN -> streetworks.common gazetteer converter.

The simplest native shape in this SDK - just ``usrn``+``geometry``, no name,
no classification, no administrative area. Maps to a bare
:class:`~streetworks.common.gazetteer.Street`: an identifier and a geometry,
nothing else to state.

``territory`` is a keyword argument, not hardcoded or derived, because OS
Open USRN covers Great Britain as one file (England, Scotland and Wales -
no Northern Ireland) with no per-feature nation field to key off, the same
reason ``from_datex2``/``from_wzdx`` take it as a keyword rather than
guessing.
"""

from __future__ import annotations

from ..openusrn.reader import UsrnStreet
from ._wkt import coordinate_from_wkt
from .gazetteer import GeometryGrade, Street
from .models import Identifier, SourceGrade

__all__ = ["from_openusrn"]


def from_openusrn(street: UsrnStreet, *, territory: str | None = None) -> Street:
    """Convert one :class:`~streetworks.openusrn.reader.UsrnStreet` into a
    :class:`~streetworks.common.gazetteer.Street`. USRN is nationally
    unique, so its :class:`~streetworks.common.models.Identifier` carries no
    ``scope``. ``geometry_grade`` is ``absent`` for the real NULL-geometry
    rows this format genuinely has (this SDK's own test fixture models one
    as a deliberate real case, not a hypothetical) - never fabricated."""
    geometry = coordinate_from_wkt(street.geometry, crs="EPSG:27700")
    return Street(
        identifiers=(Identifier(scheme="usrn", value=str(street.usrn)),),
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        territory=territory,
        source_grade=SourceGrade.REGISTER,
        raw=street,
    )
