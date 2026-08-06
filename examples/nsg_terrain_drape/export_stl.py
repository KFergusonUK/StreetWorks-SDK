"""3D-print export - a solid heightmap block of the real terrain, with the
USRN field embossed onto its own top surface as a raised ridge line.

A **derived** consumer of ``terrain.py``'s stated elevation, exactly like
``drape.py``/``render.py`` (see ``terrain.py``'s own module-boundary note) -
kept as its own module rather than folded into either of them, since it
makes its own separate distorting choices neither of those modules needs
to know about.

**This is derived output, twice over - and both distortions are reported
back, never silent.** A drape is already a sampled guess at the ground
under an XY (see ``drape.py``'s own docstring); a 3D print of it adds a
second, deliberate distortion on top - a physical scale, and a vertical
exaggeration - because without either, a print of gentle Durham-scale
relief (tens of metres over a couple of kilometres) compressed to a
150mm desktop-printer footprint would be almost perfectly flat, both
optically and to the touch. :class:`PrintScale` is handed back with every
export specifically so a caller reports what was done, rather than
presenting a "realistic" model that silently wasn't one.

**Recommended vertical exaggeration: about 2.5x.** Enough that the relief
is genuinely tactile under a finger; not so much that a gentle valley
reads as a canyon or a real slope's steepness becomes actively
misleading. This is a judgement call, not a computed optimum - open to
being wrong - but it sits inside the range terrain-model hobbyists
typically use for lowland relief (roughly 1.5x-3x), and 2.5x is stated
explicitly on every generated model's own web page (see
``generate_drape.py``) rather than picked and left unmentioned.

**The road ridge's height is a fixed physical constant
(``DEFAULT_RIDGE_HEIGHT_MM``), independent of vertical exaggeration - it
is a legibility mark, not a piece of real elevation data, and doesn't get
exaggerated along with the terrain.** Its *width*, deliberately, is not a
separate parameter at all: a road is marked by raising whichever terrain
grid cell each (finely re-densified) road vertex falls in, so the ridge is
always exactly one grid cell wide - coarser and chunkier on the 50m OS
Terrain 50 default, finer on a 1m LIDAR pull, tied to the same resolution
the terrain itself is honest about, rather than asserting a realistic
road width no grid this coarse could actually support.

**The terrain always prints as a single continuous solid - the ridge is
baked into the same heightmap surface, not a separate part.** A raised
line resting on top of an otherwise-separate object wouldn't be
printable as one piece (and wouldn't need to be - see the module's own
review of this exact question). Because the ridge is just a taller value
at certain cells of the *same* grid that becomes the top surface, walls,
and base of one watertight mesh, there is no assembly step and no
support-structure question: the terrain supports the road by construction.

**Refuses rather than fabricates ground under real gaps.** If the
requested grid contains any real no-data cell, :func:`build_print_mesh`
raises rather than filling the hole with an invented height - the same
"never infer" principle ``terrain.py``'s own module-boundary note applies
to the data itself, extended to this derived, physical output.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .drape import DrapedLine, road_cells
from .terrain import ElevationGrid

Vertex = tuple[float, float, float]

#: A judgement call, not a computed optimum - see module docstring.
DEFAULT_VERTICAL_EXAGGERATION = 2.5
#: Fits comfortably on entry-level desktop printer beds (typically
#: 180-220mm square).
DEFAULT_FOOTPRINT_MM = 150.0
#: Physical, not exaggerated - see module docstring.
DEFAULT_RIDGE_HEIGHT_MM = 1.2
#: Solid material under even the lowest terrain point, so the model has a
#: real base to stand on rather than a feathered zero-thickness edge.
DEFAULT_BASE_THICKNESS_MM = 3.0


@dataclass(frozen=True)
class PrintScale:
    """What this export actually did to the real numbers, reported back
    rather than left implicit - see module docstring."""

    scale_mm_per_m: float
    vertical_exaggeration: float
    footprint_mm: tuple[float, float]
    real_extent_m: tuple[float, float]
    ridge_height_mm: float


def _oriented(v0: Vertex, v1: Vertex, v2: Vertex, outward: Vertex) -> tuple[Vertex, Vertex, Vertex]:
    """Return the three vertices in whichever winding order makes the
    triangle's own normal point (approximately) toward ``outward``, so
    every face - top, bottom, and each of the four walls - is corrected by
    the same rule rather than by hand-derived per-case winding."""
    ux, uy, uz = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    vx, vy, vz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    dot = nx * outward[0] + ny * outward[1] + nz * outward[2]
    return (v0, v1, v2) if dot >= 0 else (v0, v2, v1)


def build_print_mesh(
    grid: ElevationGrid,
    lines: list[DrapedLine],
    *,
    footprint_mm: float = DEFAULT_FOOTPRINT_MM,
    vertical_exaggeration: float = DEFAULT_VERTICAL_EXAGGERATION,
    ridge_height_mm: float = DEFAULT_RIDGE_HEIGHT_MM,
    base_thickness_mm: float = DEFAULT_BASE_THICKNESS_MM,
) -> tuple[list[tuple[Vertex, Vertex, Vertex]], PrintScale]:
    """Build a watertight triangle mesh - terrain top surface, flat base,
    and connecting side walls, one continuous solid - with ``lines``
    embossed onto the top surface as a raised ridge. Raises ``ValueError``
    if ``grid`` contains any real no-data cell (see module docstring)."""
    flat = [v for row in grid.values for v in row]
    if grid.nodata is not None and any(v == grid.nodata for v in flat):
        raise ValueError(
            "can't 3D-print a grid with real no-data cells in it - "
            "pick a smaller or different AOI with full coverage"
        )

    extent_x = (grid.width - 1) * abs(grid.pixel_size_x)
    extent_y = (grid.height - 1) * abs(grid.pixel_size_y)
    scale = footprint_mm / max(extent_x, extent_y)
    z_min = min(flat)

    # Re-densify at half a grid cell so no cell along a road's path is
    # skipped, regardless of how coarse or fine this particular grid is.
    spacing = min(abs(grid.pixel_size_x), abs(grid.pixel_size_y)) / 2
    on_road = road_cells(grid, lines, spacing)
    # A fixed *physical* bump, independent of vertical exaggeration - see
    # module docstring - so divide it back out before it gets multiplied
    # in again below.
    ridge_bump_m = ridge_height_mm / (scale * vertical_exaggeration)

    min_real_x = grid.origin_x
    min_real_y = grid.origin_y + (grid.height - 1) * grid.pixel_size_y

    top: list[list[Vertex]] = [[(0.0, 0.0, 0.0)] * grid.width for _ in range(grid.height)]
    bottom: list[list[Vertex]] = [[(0.0, 0.0, 0.0)] * grid.width for _ in range(grid.height)]
    for row in range(grid.height):
        real_y = grid.origin_y + row * grid.pixel_size_y
        py = (real_y - min_real_y) * scale
        for col in range(grid.width):
            real_x = grid.origin_x + col * grid.pixel_size_x
            px = (real_x - min_real_x) * scale
            z = grid.values[row][col]
            if (row, col) in on_road:
                z += ridge_bump_m
            pz = base_thickness_mm + (z - z_min) * scale * vertical_exaggeration
            top[row][col] = (px, py, pz)
            bottom[row][col] = (px, py, 0.0)

    triangles: list[tuple[Vertex, Vertex, Vertex]] = []
    for row in range(grid.height - 1):
        for col in range(grid.width - 1):
            a, b, c, d = top[row][col], top[row][col + 1], top[row + 1][col], top[row + 1][col + 1]
            triangles.append(_oriented(a, b, d, (0.0, 0.0, 1.0)))
            triangles.append(_oriented(a, d, c, (0.0, 0.0, 1.0)))
            ba, bb = bottom[row][col], bottom[row][col + 1]
            bc, bd = bottom[row + 1][col], bottom[row + 1][col + 1]
            triangles.append(_oriented(ba, bb, bd, (0.0, 0.0, -1.0)))
            triangles.append(_oriented(ba, bd, bc, (0.0, 0.0, -1.0)))

    def _wall(t0: Vertex, t1: Vertex, b0: Vertex, b1: Vertex, outward: Vertex) -> None:
        triangles.append(_oriented(t0, t1, b1, outward))
        triangles.append(_oriented(t0, b1, b0, outward))

    last_row = grid.height - 1
    last_col = grid.width - 1
    for col in range(grid.width - 1):
        _wall(top[0][col], top[0][col + 1], bottom[0][col], bottom[0][col + 1], (0.0, 1.0, 0.0))
        _wall(
            top[last_row][col], top[last_row][col + 1],
            bottom[last_row][col], bottom[last_row][col + 1], (0.0, -1.0, 0.0),
        )
    for row in range(grid.height - 1):
        _wall(top[row][0], top[row + 1][0], bottom[row][0], bottom[row + 1][0], (-1.0, 0.0, 0.0))
        _wall(
            top[row][last_col], top[row + 1][last_col],
            bottom[row][last_col], bottom[row + 1][last_col], (1.0, 0.0, 0.0),
        )

    print_scale = PrintScale(
        scale_mm_per_m=scale,
        vertical_exaggeration=vertical_exaggeration,
        footprint_mm=(extent_x * scale, extent_y * scale),
        real_extent_m=(extent_x, extent_y),
        ridge_height_mm=ridge_height_mm,
    )
    return triangles, print_scale


def write_binary_stl(triangles: list[tuple[Vertex, Vertex, Vertex]], path: str) -> None:
    """Write ``triangles`` as a binary STL file - stdlib ``struct`` only,
    same "no mesh library" ethos as ``terrain.py``'s own GeoTIFF reader."""
    header = b"streetworks nsg_terrain_drape - derived, exaggerated relief"
    with open(path, "wb") as f:
        f.write(header.ljust(80, b"\0")[:80])
        f.write(struct.pack("<I", len(triangles)))
        for v0, v1, v2 in triangles:
            ux, uy, uz = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
            vx, vy, vz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            length = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
            f.write(struct.pack("<3f", nx / length, ny / length, nz / length))
            for v in (v0, v1, v2):
                f.write(struct.pack("<3f", *v))
            f.write(struct.pack("<H", 0))
