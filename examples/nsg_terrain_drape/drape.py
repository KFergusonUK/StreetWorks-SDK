"""Densify, sample, emit - the drape itself.

A **derived** consumer of ``terrain.py``'s stated elevation, deliberately
kept out of that module (see its own module-boundary note): this is where
the "guess at the ground under an XY" choices live - how finely to
densify, what to do with a vertex the terrain grid has no stated value
for - never inside the module that hands back stated Z.

**Never write this output into ``streetworks.common.models.Coordinate``.**
A :class:`DrapedLine` is example-local, throwaway render geometry - a
sampled guess at the ground under a real, flat, XY-only USRN centreline,
not a measurement of the road itself. Every real gazetteer/works
``Coordinate`` this SDK produces elsewhere keeps its stated provenance
(2D, from OS Open USRN, in this case) untouched. That boundary is the
entire teaching point of this example - see the design brief and this
package's README.

**Gaps are dropped, never carried forward or interpolated across.** A
densified vertex the terrain grid has no stated value for (outside the
fetched AOI, or landing on a real NODATA cell) is simply omitted from the
draped line - re-using the last real sample would silently flatten a real
gap into a fabricated plateau, exactly the kind of inference
``terrain.py``'s own module-boundary note exists to keep out of the
elevation layer.

**MULTILINESTRING is the majority real shape, not an edge case - confirmed
live, not assumed from the one LINESTRING example in
``openusrn_lookup.py``'s own docstring.** A real 200,000-street sample
during this example's own build came back 67% MULTILINESTRING (multiple
physically disconnected parts under one USRN - e.g. a street split by a
roundabout island) against 33% plain LINESTRING. :func:`parse_wkt_parts`
and :class:`DrapedLine` treat "one or more disconnected parts" as the
normal case throughout - mirroring
:class:`streetworks.common.models.Coordinate`'s own ``parts`` field for
exactly this shape, not bolted on as a special case after the fact. Each
part is densified, sampled, and gap-dropped independently; a USRN
survives (:func:`drape_line` returns non-``None``) if *any* part keeps two
or more real samples, even if others are dropped entirely.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from .terrain import ElevationGrid

__all__ = [
    "DENSIFY_SPACING_M",
    "DrapedLine",
    "densify",
    "drape_line",
    "parse_wkt_parts",
    "road_cells",
]

Point2D = tuple[float, float]
Point3D = tuple[float, float, float]

#: USRN vertices are sparse - a raw sample between two distant original
#: vertices would chord across the terrain rather than follow it (see the
#: design brief this example was built from). 10m is the brief's own figure.
DENSIFY_SPACING_M = 10.0


def _split_top_level(text: str) -> list[str]:
    """``"(a, b), (c, d)"`` -> ``["(a, b)", "(c, d)"]`` - same bracket-depth
    approach as :mod:`streetworks.common._wkt`'s own helper (not imported
    from there - this module stays free of reaching into that package's
    private internals; see the design brief's module-boundary note)."""
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def _parse_one_part(body: str) -> tuple[Point2D, ...]:
    points = []
    for pair in body.split(","):
        x_str, y_str = pair.split()
        points.append((float(x_str), float(y_str)))
    return tuple(points)


def parse_wkt_parts(wkt: str) -> tuple[tuple[Point2D, ...], ...]:
    """Parse the two WKT shapes OS Open USRN actually emits, confirmed
    live (see module docstring): plain ``LINESTRING`` and
    ``MULTILINESTRING``. Always returns one or more parts - a
    ``LINESTRING`` is a single-part result - so callers never special-case
    "is this multi". Not a general WKT parser; if a future source needs
    more (polygons, Z, ...), extend it or reach for
    :mod:`streetworks.common._wkt` instead of widening this."""
    if wkt.startswith("MULTILINESTRING"):
        inner = wkt[wkt.index("(") + 1 : wkt.rindex(")")]
        return tuple(_parse_one_part(part.strip("()")) for part in _split_top_level(inner))
    if wkt.startswith("LINESTRING"):
        return (_parse_one_part(wkt[wkt.index("(") + 1 : wkt.rindex(")")]),)
    raise ValueError(f"expected LINESTRING or MULTILINESTRING, got: {wkt[:30]!r}")


def densify(line: tuple[Point2D, ...], spacing: float = DENSIFY_SPACING_M) -> tuple[Point2D, ...]:
    """Insert extra vertices along a 2D line so consecutive points are no
    more than ``spacing`` metres apart, by even subdivision of each
    original segment (not a fixed step from the line's start - a segment
    slightly longer than a whole number of steps gets slightly-shorter-
    than-``spacing`` steps rather than one short leftover step)."""
    if len(line) < 2:
        return line
    out = [line[0]]
    for (x0, y0), (x1, y1) in zip(line, line[1:]):  # noqa: B905 - deliberately pairwise
        seg_len = hypot(x1 - x0, y1 - y0)
        n_steps = max(1, round(seg_len / spacing))
        for i in range(1, n_steps + 1):
            t = i / n_steps
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return tuple(out)


@dataclass(frozen=True)
class DrapedLine:
    """One USRN, densified and draped over a real, stated elevation grid -
    example-local render geometry only (see module docstring).
    ``parts`` mirrors :class:`streetworks.common.models.Coordinate`'s own
    ``parts`` field: one or more physically disconnected 3D polylines (see
    module docstring on why that's the normal case, not an edge case).
    ``gap_count`` is how many densified vertices, summed across every part,
    the grid had no stated value for and were dropped - a real, reportable
    data-quality figure, not swept away."""

    usrn: int
    parts: tuple[tuple[Point3D, ...], ...]
    gap_count: int
    surface_model: str
    vertical_datum: str


def _drape_part(
    line: tuple[Point2D, ...], grid: ElevationGrid, spacing: float
) -> tuple[tuple[Point3D, ...], int]:
    points: list[Point3D] = []
    gap_count = 0
    for x, y in densify(line, spacing):
        z = grid.sample(x, y)
        if z is None:
            gap_count += 1
            continue
        points.append((x, y, z))
    return tuple(points), gap_count


def drape_line(
    usrn: int,
    parts: tuple[tuple[Point2D, ...], ...],
    grid: ElevationGrid,
    *,
    spacing: float = DENSIFY_SPACING_M,
) -> DrapedLine | None:
    """Densify and sample every part of ``parts`` (see :func:`parse_wkt_parts`)
    against ``grid``, dropping any part left with fewer than two real
    samples. ``None`` only if *every* part was dropped - e.g. a USRN
    wholly outside the terrain AOI."""
    draped_parts: list[tuple[Point3D, ...]] = []
    total_gaps = 0
    for line in parts:
        points, gap_count = _drape_part(line, grid, spacing)
        total_gaps += gap_count
        if len(points) >= 2:
            draped_parts.append(points)
    if not draped_parts:
        return None
    return DrapedLine(
        usrn=usrn, parts=tuple(draped_parts), gap_count=total_gaps,
        surface_model=grid.surface_model, vertical_datum=grid.vertical_datum,
    )


def road_cells(
    grid: ElevationGrid, lines: list[DrapedLine], spacing: float
) -> set[tuple[int, int]]:
    """Every ``(row, col)`` terrain grid cell a road passes through, found
    by re-densifying each draped part's XY (Z discarded - callers compare
    against the *terrain's own* value at that cell, not the drape's, so
    results stay correct even where the drape itself had real gaps) at
    ``spacing`` fine enough that no cell along the path is skipped -
    typically half the grid's own pixel size. Shared by ``export_stl.py``
    (which cell to emboss on the print) and ``render.py`` (which cell to
    emboss - and lift the road above - in the interactive ghost mesh);
    lives here because it's fundamentally a drape-geometry question
    ("which of the terrain's own cells does this path touch"), not a
    printing or rendering one."""
    cells: set[tuple[int, int]] = set()
    for line in lines:
        for part in line.parts:
            xy: tuple[Point2D, ...] = tuple((x, y) for x, y, _z in part)
            for x, y in densify(xy, spacing=spacing):
                col = round((x - grid.origin_x) / grid.pixel_size_x)
                row = round((y - grid.origin_y) / grid.pixel_size_y)
                if 0 <= row < grid.height and 0 <= col < grid.width:
                    cells.add((row, col))
    return cells
