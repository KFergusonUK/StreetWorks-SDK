"""Digiroad (Finland) -> streetworks.common converter.

**A real `Street`, one per real WFS feature - the same 1:1
(no grouping/dedupe) treatment Jersey's/Gibraltar's/Iceland's own
multi-row-per-name streets get.** Real names on the large majority of
features checked (a live Helsinki sample: 4,198/5,000 with a Finnish
name).

**Bilingual names carried as two real `Name`s, not merged - Finland's
genuine official bilingual convention, the same `Name.language`
mechanism the NSG's `_eng`/`_cym` pairs already use.** `tienimi_su`
(Finnish) becomes ``Name(value=..., language="fi")``; `tienimi_ru`
(Swedish) becomes ``Name(value=..., language="sv")`` where real and
non-blank - both populated on the large majority of real named
segments checked live.

``identifiers`` carries the real `link_id` (scheme `"link_id"`, scoped
`"Finland"` - Digiroad's own real segment-level UUID, suffixed with a
real sub-segment index, e.g. `"f4062096-...:1"`), the real `link_mmlid`
(scheme `"mml_id"` - a second real identifier, Maanmittauslaitos' own,
independently stated alongside Digiroad's) and, where stated, the real
`kuntakoodi` (scheme `"kuntakoodi"` - a real municipality code, never
promoted to `administrative_area` since no decoded municipality-name
field exists anywhere on this layer to honestly populate it with).

``street_type`` carries the real `hallinn_lk` (administrative class)
value undecoded, as a code - no lookup table bundled, the same
treatment NWB's own `bst_code` gets.

**Geometry: real 3D coordinates, `Z` never defaulted to zero.** Every
real vertex checked carries a genuine elevation value in metres -
preserved through `Coordinate`'s existing `Point3D` support, the same
discipline NVDB's own `LINESTRING Z` data already established.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import GeometryGrade, Name, Street, StreetType
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_digiroad_street"]

JSON = dict[str, Any]

#: Confirmed live: this layer's native CRS is EPSG:3067; real WGS84
#: output requires an explicit request - see streetworks.digiroad
#: .client's module docstring. This converter assumes the caller
#: requested EPSG:4326, matching streetworks.digiroad.DigiroadClient's
#: own default.
_CRS = "EPSG:4326"


def _geometry(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    coords = geometry.get("coordinates")
    kind = geometry.get("type")
    if kind == "LineString" and coords:
        points = tuple(tuple(c) for c in coords)
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
    if kind == "MultiLineString" and coords:
        parts = tuple(tuple(tuple(c) for c in line) for line in coords if line)
        if not parts:
            return None
        if len(parts) == 1:
            points = parts[0]
            return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
        return Coordinate(value=parts[0][0], crs=_CRS, parts=parts)
    return None


def from_digiroad_street(feature: JSON) -> Street:
    """Convert one real Digiroad road-link GeoJSON ``Feature`` (from
    :meth:`streetworks.digiroad.DigiroadClient.iter_streets`) into a
    :class:`~streetworks.common.gazetteer.Street`."""
    properties = feature.get("properties", {})
    geometry = _geometry(feature.get("geometry"))
    if geometry is None:
        link_id = properties.get("link_id")
        raise ValueError(f"Digiroad feature link_id={link_id!r} has no geometry to convert")

    names = []
    fi_name = properties.get("tienimi_su")
    if fi_name and fi_name.strip():
        names.append(Name(value=fi_name, language="fi"))
    sv_name = properties.get("tienimi_ru")
    if sv_name and sv_name.strip():
        names.append(Name(value=sv_name, language="sv"))

    identifiers = []
    link_id = properties.get("link_id")
    if link_id:
        identifiers.append(Identifier(scheme="link_id", value=link_id, scope="Finland"))
    link_mmlid = properties.get("link_mmlid")
    if link_mmlid:
        identifiers.append(Identifier(scheme="mml_id", value=str(link_mmlid), scope="Finland"))
    kuntakoodi = properties.get("kuntakoodi")
    if kuntakoodi is not None:
        identifiers.append(
            Identifier(scheme="kuntakoodi", value=str(kuntakoodi), scope="Finland")
        )

    hallinn_lk = properties.get("hallinn_lk")

    return Street(
        identifiers=tuple(identifiers),
        names=tuple(names),
        street_type=StreetType(code=str(hallinn_lk)) if hallinn_lk is not None else None,
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED,
        territory="Finland",
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )
