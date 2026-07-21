"""Private WKT -> :class:`.Coordinate` helper, shared by the gazetteer
converters whose native models carry geometry as a WKT string
(`bdtopo`, `nwb`, `nvdb`, `openusrn`) rather than GeoJSON coordinates
(`datavia`) or plain lon/lat floats (`ban`, `bag`, `kartverket` - those
build :class:`.Coordinate` directly, no parsing needed).

Handles exactly the shapes this SDK's own native readers produce:
``POINT``, ``LINESTRING``/``LINESTRING Z``, ``MULTILINESTRING``/
``MULTILINESTRING Z``. Not a general WKT parser - extend it if a future
source needs POLYGON or a geometry collection.
"""

from __future__ import annotations

import re

from .models import Coordinate, Point2D, Point3D

__all__ = ["coordinate_from_wkt"]

_HEADER = re.compile(r"^\s*([A-Z]+)\s*(Z)?\s*\((.*)\)\s*$", re.DOTALL)


def _point(text: str) -> Point2D | Point3D:
    values = tuple(float(v) for v in text.split())
    if len(values) == 3:
        return (values[0], values[1], values[2])
    return (values[0], values[1])


def _split_top_level(text: str, opener: str, closer: str) -> list[str]:
    """Split ``(a, b), (c, d)`` -> ``["(a, b)", "(c, d)"]`` - a plain comma
    split would break on the commas *inside* each ring/line."""
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(text):
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def _line(text: str) -> tuple[Point2D | Point3D, ...]:
    return tuple(_point(p) for p in text.split(","))


def coordinate_from_wkt(wkt: str | None, crs: str) -> Coordinate | None:
    """Parse a real WKT ``POINT``/``LINESTRING``/``MULTILINESTRING``
    (optionally ``Z``) string into a :class:`.Coordinate`. ``None`` in,
    ``None`` out - never fabricates a location from nothing (e.g. OS Open
    USRN's real NULL-geometry rows)."""
    if not wkt:
        return None
    match = _HEADER.match(wkt.strip())
    if not match:
        return None
    kind, _z, body = match.group(1), match.group(2), match.group(3)
    if kind == "POINT":
        value = _point(body)
        return Coordinate(value=value, crs=crs)
    if kind == "LINESTRING":
        points = _line(body)
        if not points:
            return None
        return Coordinate(value=points[0], crs=crs, points=points if len(points) > 1 else None)
    if kind == "MULTILINESTRING":
        rings = _split_top_level(body, "(", ")")
        parts = tuple(_line(r.strip("()")) for r in rings)
        parts = tuple(p for p in parts if p)
        if not parts:
            return None
        return Coordinate(value=parts[0][0], crs=crs, parts=parts)
    return None
