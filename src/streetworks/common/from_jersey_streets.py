"""Jersey Street Gazetteer -> streetworks.common converter. This SDK's
first Channel Islands *streets* coverage (Jersey RoadWorkx, its roadworks
sibling, converts via :mod:`streetworks.common.from_jersey` instead).

**Geometry: the real stated ``USRN_XY1``/``USRN_XY2`` point pair, not the
polygon - see** :mod:`streetworks.arcgis.jersey`'s module docstring for
the full live-verified CRS story (the real polygon geometry is WGS84;
these two attribute fields are a separate, real, native-``EPSG:3109``
start/end pair, never touched by any reprojection). Per the same
discipline :mod:`.from_paris` established for a real polygon-only
footprint, a ring is never forced into ``Coordinate.points`` - that
field is documented for line vertices. So this converter reads the real
``"easting,northing"`` pair as a genuine two-point line where both are
stated (confirmed live: 89.7% of real ``FEATURE='Road'`` rows), and
leaves geometry ``None``/``GeometryGrade.ABSENT`` otherwise - never a
fabricated centroid. The real WGS84 polygon is preserved unmodified in
``Street.raw`` regardless.

``identifiers`` carries the real ``USRN`` (scheme ``"usrn"``, scoped
``"Jersey"`` - a distinct Crown-Dependency numbering block from Great
Britain's own NSG/OS Open USRN range, so scoped rather than treated as
globally unique) and, where stated, the real ``BKSTOID`` per-polygon area
id (scheme ``"bkstoid"``).

``street_type`` is never populated - ``OBJ_TYPE``/``OBJ_CAT`` are real
fields but inconsistently populated on live data (blank on almost every
real ``FEATURE='Road'`` row sampled), not a reliable classification to
carry.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import GeometryGrade, Name, Street
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_jersey_street"]

JSON = dict[str, Any]

#: Native CRS of the real USRN_XY1/USRN_XY2 attribute pair - confirmed
#: live, see streetworks.arcgis.jersey's module docstring. Not the CRS of
#: this layer's own polygon geometry (real WGS84 instead), which this
#: converter does not use - see module docstring.
_CRS = "EPSG:3109"


def _xy(value: str | None) -> tuple[float, float] | None:
    if not value or not value.strip():
        return None
    parts = value.split(",")
    if len(parts) != 2:
        return None
    try:
        return (float(parts[0]), float(parts[1]))
    except ValueError:
        return None


def _usrn_str(value: float | None) -> str | None:
    """Jersey's real USRN is always a whole integer (confirmed live) -
    formatted without a trailing ``.0``."""
    if value is None:
        return None
    return str(int(value)) if value == int(value) else str(value)


def from_jersey_street(feature: JSON) -> Street:
    """Convert one real Jersey street GeoJSON ``Feature`` (from
    :meth:`streetworks.arcgis.jersey.JerseyStreetsClient.iter_streets`)
    into a :class:`~streetworks.common.gazetteer.Street`."""
    properties = feature.get("properties", {})

    real_name = properties.get("REAL_NAME")
    names = (Name(value=real_name),) if real_name and real_name.strip() else ()

    usrn = _usrn_str(properties.get("USRN"))
    bkstoid = properties.get("BKSTOID")
    identifiers = []
    if usrn:
        identifiers.append(Identifier(scheme="usrn", value=usrn, scope="Jersey"))
    if bkstoid and bkstoid.strip():
        identifiers.append(Identifier(scheme="bkstoid", value=bkstoid))

    xy1 = _xy(properties.get("USRN_XY1"))
    xy2 = _xy(properties.get("USRN_XY2"))
    if xy1 is not None:
        points = (xy1, xy2) if xy2 is not None and xy2 != xy1 else None
        geometry: Coordinate | None = Coordinate(value=xy1, crs=_CRS, points=points)
        geometry_grade = GeometryGrade.PUBLISHED
    else:
        geometry = None
        geometry_grade = GeometryGrade.ABSENT

    parish = properties.get("PARISH")

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        geometry=geometry,
        geometry_grade=geometry_grade,
        territory="Jersey",
        administrative_area=parish if parish and parish.strip() else None,
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )
