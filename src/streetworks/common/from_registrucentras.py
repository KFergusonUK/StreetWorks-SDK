"""Lithuania (Registrų centras, Adresų registras street register) ->
streetworks.common converter.

**A genuine ``Street``, one per real row - 100% carry a real name,
confirmed against the complete national dataset (22,547 rows), zero
duplicate street codes.** The register's own subject is street names
with real geometry, not an unlabelled segment network.

**Real WKT geometry, reprojected client-side from LKS-94 with a real
axis-order swap applied first.** ``gatves`` states real
``LINESTRING``/``MULTILINESTRING`` WKT, but with coordinate pairs
ordered ``(Northing, Easting)`` - confirmed live, see
:mod:`streetworks.registrucentras.client`'s own docstring for the bounds
-check evidence. This parser reads each pair as ``(northing, easting)``
and calls :func:`streetworks.common._lks94.lks94_to_wgs84` with the
correctly-ordered ``(easting, northing)`` arguments, then swaps its
``(lon, lat)`` return to this SDK's own stated ``(lat, lon)`` convention
(the same swap ``from_copenhagen``/``from_dar_street`` already apply to
their own real WGS84 sources).

**Genuinely multi-part ``MULTILINESTRING`` on a real minority of rows**
(21/22,547 in the complete dataset) - parsed into ``Coordinate.parts``,
the same discipline ``from_gibraltar``/``from_tigerweb``/``from_dar_street``
already established, never a first-part-only shortcut.

``administrative_area`` is never populated - a real, disclosed gap, not
an oversight; see :mod:`streetworks.registrucentras.client`'s own
docstring for why the real settlement reference
(``gyvenamoji_vietove``) is left unresolved rather than joined against a
disproportionately large 127 MB lookup dataset. ``gat_r`` (always
``null`` across the complete dataset, confirmed live) and ``gat_ilgis``
(a real stated length in metres) have no dedicated home on this model -
kept `.raw`-only.
"""

from __future__ import annotations

import re
from typing import Any

from ._lks94 import lks94_to_wgs84
from .gazetteer import GeometryGrade, Name, Street
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_registrucentras_street"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"

_LINESTRING_RE = re.compile(r"LINESTRING\s*\((.*)\)\s*$", re.DOTALL)
_MULTILINESTRING_RE = re.compile(r"MULTILINESTRING\s*\((.*)\)\s*$", re.DOTALL)


def _parse_points(raw_part: str) -> tuple[tuple[float, float], ...]:
    points = []
    for pair in raw_part.split(","):
        northing_str, easting_str = pair.split()
        lon, lat = lks94_to_wgs84(float(easting_str), float(northing_str))
        points.append((lat, lon))
    return tuple(points)


def _geometry(wkt: str | None) -> Coordinate | None:
    if not wkt:
        return None
    wkt = wkt.strip()

    multi_match = _MULTILINESTRING_RE.match(wkt)
    if multi_match:
        body = multi_match.group(1).strip()
        parts = tuple(
            _parse_points(raw_part) for raw_part in re.findall(r"\(([^()]*)\)", body)
        )
        parts = tuple(p for p in parts if p)
        if not parts:
            return None
        if len(parts) == 1:
            points = parts[0]
            return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
        return Coordinate(value=parts[0][0], crs=_CRS, parts=parts)

    line_match = _LINESTRING_RE.match(wkt)
    if line_match:
        points = _parse_points(line_match.group(1).strip())
        if not points:
            return None
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)

    return None


def from_registrucentras_street(record: JSON) -> Street:
    """Convert one real Registrų centras ``GraGatve`` record (from
    :meth:`streetworks.registrucentras.RegistruCentrasStreetsClient.iter_streets`)
    into a :class:`~streetworks.common.gazetteer.Street`."""
    geometry = _geometry(record.get("gatves"))

    name = record.get("pavadinimas")
    names = (Name(value=name),) if name and name.strip() else ()

    identifiers = []
    gat_kodas = record.get("gat_kodas")
    if gat_kodas is not None:
        identifiers.append(
            Identifier(scheme="gat_kodas", value=str(gat_kodas), scope="Lithuania")
        )

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        territory="Lithuania",
        source_grade=SourceGrade.REGISTER,
        raw=record,
    )
