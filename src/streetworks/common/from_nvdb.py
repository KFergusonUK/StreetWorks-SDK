"""NVDB -> streetworks.common gazetteer converter.

Dispatches on the real native type - and, unlike BD TOPO, the two types
are **not nested the same way** (see :mod:`streetworks.nvdb.models` for the
full finding): :class:`~streetworks.nvdb.models.Veglenkesekvens` (purely
topological, no name of its own) -> :class:`~streetworks.common.gazetteer.Segment`;
:class:`~streetworks.nvdb.models.VegAdresse` (the naming/addressing layer,
NVDB type 538) -> :class:`~streetworks.common.gazetteer.Street`.
``VegAdresse.veglenkesekvens_ids`` feeds ``Street.segment_refs`` - and a
real address can state **more than one** (confirmed live: "Dalveien" spans
two topologically-unrelated sequences), which is exactly why this model
makes ``Segment.street_refs`` plural rather than nesting `Segment` under
`Street`.

A ``Veglenkesekvens``'s own sub-links (``veglenker``) each carry their own
geometry and linear-referencing range; where there is more than one, their
lines become the ``parts`` of one ``Coordinate`` (real, not fabricated -
DataVIA's per-ESU ``MultiLineString`` needed the same shape). Linear
referencing itself (``startposisjon``/``sluttposisjon``) is out of scope
for this model - preserved in ``.raw``, not promoted, per the design
brief's own instruction.
"""

from __future__ import annotations

from ..nvdb.models import VegAdresse, Veglenkesekvens
from ._wkt import coordinate_from_wkt
from .gazetteer import GeometryGrade, Name, Segment, Street, StreetType
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_nvdb"]


def _segment(sekvens: Veglenkesekvens, *, crs: str) -> Segment:
    parts: list[tuple] = []
    for link in sekvens.veglenker:
        link_crs = f"EPSG:{link.srid}" if link.srid else crs
        coord = coordinate_from_wkt(link.geometry, crs=link_crs)
        if coord is not None:
            if coord.parts:
                parts.extend(coord.parts)
            elif coord.points:
                parts.append(coord.points)
            else:
                parts.append((coord.value,))
    if not parts:
        raise ValueError(f"Veglenkesekvens {sekvens.veglenkesekvensid} has no geometry to convert")
    resolved_crs = f"EPSG:{sekvens.veglenker[0].srid}" if sekvens.veglenker[0].srid else crs
    if len(parts) == 1:
        line = parts[0]
        geometry = Coordinate(
            value=line[0], crs=resolved_crs, points=line if len(line) > 1 else None
        )
    else:
        geometry = Coordinate(value=parts[0][0], crs=resolved_crs, parts=tuple(parts))

    first_typed = next((v for v in sekvens.veglenker if v.type_veg), None)
    street_type = (
        StreetType(label=first_typed.type_veg, code=first_typed.type_veg_sosi)
        if first_typed
        else None
    )

    return Segment(
        geometry=geometry,
        identifiers=(Identifier(scheme="veglenkesekvensid", value=str(sekvens.veglenkesekvensid)),),
        street_type=street_type,
        raw=sekvens,
    )


def _street(adresse: VegAdresse, *, crs: str) -> Street:
    adresse_crs = f"EPSG:{adresse.srid}" if adresse.srid else crs
    geometry = coordinate_from_wkt(adresse.geometry, crs=adresse_crs)
    return Street(
        identifiers=(
            Identifier(scheme="adressekode", value=adresse.adressekode, scope=adresse.kommune)
            if adresse.adressekode
            else Identifier(scheme="nvdb_id", value=str(adresse.id)),
        ),
        names=(Name(value=adresse.adressenavn),) if adresse.adressenavn else (),
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        segment_refs=tuple(
            Identifier(scheme="veglenkesekvensid", value=str(i))
            for i in adresse.veglenkesekvens_ids
        ),
        territory="Norway",
        administrative_area=adresse.kommune,
        source_grade=SourceGrade.REGISTER,
        raw=adresse,
    )


def from_nvdb(
    obj: Veglenkesekvens | VegAdresse, *, crs: str = "EPSG:5973"
) -> Segment | Street:
    """Convert one real :class:`~streetworks.nvdb.models.Veglenkesekvens` or
    :class:`~streetworks.nvdb.models.VegAdresse` into a
    :class:`~streetworks.common.gazetteer.Segment` or
    :class:`~streetworks.common.gazetteer.Street` respectively. ``crs`` is a
    fallback only - every real geometry carries its own ``srid``
    (confirmed live: ``5973``, "ETRS89-NOR [EUREF89] / UTM zone 33N +
    NN2000 height", a compound 3D CRS - not the design brief's originally
    expected plain UTM33N), which is used in preference where present.
    """
    if isinstance(obj, Veglenkesekvens):
        return _segment(obj, crs=crs)
    return _street(obj, crs=crs)
