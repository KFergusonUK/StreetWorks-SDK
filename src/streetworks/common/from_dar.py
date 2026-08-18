"""Denmark's Danmarks Adresseregister (DAR) ``Navngivenvej`` (named-road)
entity -> streetworks.common converter.

**A genuine ``Street``, one per real record - the register's own subject
is named roads, not an unlabelled segment network.** ``vejnavn`` is
real and populated on 4998/5000 (99.96%) of a live sample - the highest
name coverage of any streets provider this SDK has built - the two
genuine gaps (``status`` ``5``) are kept with ``names=()`` rather than
skipped or fabricated.

**Geometry is reprojected client-side from ETRS89/UTM32N
(``EPSG:25832``), the only CRS this endpoint states - see
:mod:`streetworks.dar.client`'s own docstring for why no server-side
option exists.** :func:`streetworks.common._utm32n.utm32n_to_wgs84`
handles the transform; this module then swaps its ``(lon, lat)`` return
to this SDK's own stated ``(lat, lon)`` convention (see
``from_copenhagen``'s docstring for the same swap over the same real
Danish geography).

**A real, three-tier geometry fallback, found live rather than assumed
uniform.** 3/5000 (0.06%) of a live sample carry a real ``null`` in
``vejnavnebeliggenhed_vejnavnelinje`` (the line) - but 2 of those 3
still carry a real ``vejnavnebeliggenhed_vejtilslutningspunkter``
("road connection points", a WKT ``MULTIPOINT``) alongside a real
``vejnavnebeliggenhed_vejnavneområde`` ("road name area", a WKT
``POLYGON``). This module prefers the line where stated; falls back to
the *first* real connection point (``GeometryGrade.PUBLISHED`` - a real,
if point-only, coordinate, not a gap) where there's no line but a real
point exists; and only grades ``GeometryGrade.ABSENT`` where neither is
stated (the third of the three, confirmed live: no line, no point, no
polygon at all). The polygon itself is **never** read into
``Coordinate`` - kept `.raw`-only always, the same "no polygon ring
forced into a line/point field" discipline ``from_marousi_street``/
``from_guernsey_street`` already established.

**Real WKT ``MULTILINESTRING`` is genuinely multi-part on most records**
(a named road rarely reduces to one unbroken line) - parsed into
``Coordinate.parts``, the same discipline ``from_gibraltar``/
``from_tigerweb``/``from_lmi`` already established, never a
first-part-only shortcut.

``administrative_area`` carries the real ``administreresAfKommune``
4-digit kommune code, kept as the raw code rather than resolved to a
name - no kommune-code-to-name lookup is fetched by this converter (DAR
states the code directly; resolving it would mean a second live call
per record this converter doesn't make).
"""

from __future__ import annotations

import re
from typing import Any

from ._utm32n import utm32n_to_wgs84
from .gazetteer import GeometryGrade, Name, Street
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_dar_street"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"

_MULTILINESTRING_RE = re.compile(r"MULTILINESTRING\s*\((.*)\)\s*$", re.DOTALL)
_MULTIPOINT_RE = re.compile(r"MULTIPOINT\s*\((.*)\)\s*$", re.DOTALL)


def _parse_multilinestring(wkt: str) -> tuple[tuple[tuple[float, float], ...], ...] | None:
    """Parse a real ``MULTILINESTRING((x y,x y),(x y,...))`` WKT string
    (DAR's own geometry encoding) into ``((lat, lon), ...)`` parts,
    reprojected from UTM32N. Returns ``None`` for anything that doesn't
    match a real multi-part linestring (including the empty-parens case,
    never observed live but handled rather than assumed impossible)."""
    match = _MULTILINESTRING_RE.match(wkt.strip())
    if not match:
        return None
    body = match.group(1).strip()
    if not body:
        return None
    parts = []
    for raw_part in re.findall(r"\(([^()]*)\)", body):
        points = []
        for pair in raw_part.split(","):
            easting_str, northing_str = pair.split()
            lon, lat = utm32n_to_wgs84(float(easting_str), float(northing_str))
            points.append((lat, lon))
        if points:
            parts.append(tuple(points))
    return tuple(parts) if parts else None


def _parse_multipoint(wkt: str) -> tuple[float, float] | None:
    """Parse a real ``MULTIPOINT(x y,x y,...)`` WKT string (DAR's own
    ``vejtilslutningspunkter`` "road connection points" field) and
    return only the *first* real point, reprojected from UTM32N -
    one representative point, the same "value is always one
    representative point" convention :class:`~streetworks.common.models.Coordinate`
    itself documents, not every connection point this road has."""
    match = _MULTIPOINT_RE.match(wkt.strip())
    if not match:
        return None
    body = match.group(1).strip()
    if not body:
        return None
    first = body.split(",")[0].strip().strip("()")
    if not first:
        return None
    easting_str, northing_str = first.split()
    lon, lat = utm32n_to_wgs84(float(easting_str), float(northing_str))
    return (lat, lon)


def _geometry(record: JSON) -> Coordinate | None:
    line_wkt = record.get("vejnavnebeliggenhed_vejnavnelinje")
    if line_wkt:
        parts = _parse_multilinestring(line_wkt)
        if parts:
            if len(parts) == 1:
                points = parts[0]
                return Coordinate(
                    value=points[0], crs=_CRS, points=points if len(points) > 1 else None
                )
            return Coordinate(value=parts[0][0], crs=_CRS, parts=parts)

    point_wkt = record.get("vejnavnebeliggenhed_vejtilslutningspunkter")
    if point_wkt:
        point = _parse_multipoint(point_wkt)
        if point:
            return Coordinate(value=point, crs=_CRS)

    return None


def from_dar_street(record: JSON) -> Street:
    """Convert one real DAR ``Navngivenvej`` record (from
    :meth:`streetworks.dar.DarClient.iter_streets`) into a
    :class:`~streetworks.common.gazetteer.Street`."""
    geometry = _geometry(record)

    name = record.get("vejnavn")
    names = (Name(value=name),) if name and name.strip() else ()

    identifiers = []
    id_lokal = record.get("id_lokalId")
    if id_lokal:
        identifiers.append(Identifier(scheme="id_lokalId", value=id_lokal, scope="Denmark"))

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        territory="Denmark",
        administrative_area=record.get("administreresAfKommune"),
        source_grade=SourceGrade.REGISTER,
        raw=record,
    )
