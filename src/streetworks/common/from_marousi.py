"""Δήμος Αμαρουσίου (Marousi, Greece) -> streetworks.common converter.

**Geometry always absent on the canonical model - not a gap, a real
schema fact.** This layer states no point/line field at all - only the
real street-extent polygon itself. Per the same discipline
`from_guernsey_street` established for its own real polygon-only
layer (`Coordinate.points` is documented for line vertices, not polygon
rings - forcing one in would misuse that contract), this converter
never does so: every real :class:`~streetworks.common.gazetteer.Street`
here carries `geometry=None`, `GeometryGrade.ABSENT`. The real polygon
(confirmed live to be genuine WGS84 when requested - see
:mod:`streetworks.marousi.client`'s module docstring) is preserved
unmodified in `Street.raw` for any caller that needs the real footprint.

``identifiers`` carries the real per-feature `id` (scheme `"id"`,
scoped `"Marousi"` - a real, layer-local integer, not a national
register number).

``administrative_area`` is always `"Marousi"` - a real, fixed constant
for this single-municipality provider, not a per-record field (this
layer states no separate administrative-area field of its own).
"""

from __future__ import annotations

from typing import Any

from .gazetteer import GeometryGrade, Name, Street
from .models import Identifier, SourceGrade

__all__ = ["from_marousi_street"]

JSON = dict[str, Any]


def from_marousi_street(feature: JSON) -> Street:
    """Convert one real Marousi street GeoJSON ``Feature`` (from
    :meth:`streetworks.marousi.MarousiStreetsClient.iter_streets`) into
    a :class:`~streetworks.common.gazetteer.Street`."""
    properties = feature.get("properties", {})

    name = properties.get("onoma_is")
    names = (Name(value=name),) if name and name.strip() else ()

    feature_id = properties.get("id")
    identifiers = (
        (Identifier(scheme="id", value=str(feature_id), scope="Marousi"),)
        if feature_id is not None
        else ()
    )

    return Street(
        identifiers=identifiers,
        names=names,
        geometry=None,
        geometry_grade=GeometryGrade.ABSENT,
        territory="Greece",
        administrative_area="Marousi",
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )
