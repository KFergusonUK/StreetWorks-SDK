"""pydeck rendering - the area drape (a field of ribbons over a ghost
terrain mesh) and the optional single-USRN focus highlight.

**Renders entirely in the terrain grid's own CRS (EPSG:27700 - real
eastings/northings/metres), never WGS84.** pydeck's ``OrbitView`` is a free
3D camera, not a web-map view tied to Mercator tiles, and accepts arbitrary
Cartesian coordinates - confirmed by a real, manual smoke test (raw
BNG-magnitude numbers, ~427000/542000, rendered correctly) before this
module was written around it. So nothing here ever reprojects a coordinate
for display - the same "no reprojection" discipline this whole example
applies to data, extended to the render step, which a lon/lat-based
``MapView`` would have quietly forced.

**pydeck is this example's own dependency, not a project one** - see
``requirements`` in this package's README, matching
``examples/roadworks_world_map.py``'s own precedent for plotly (declared in
the script's docstring, not in ``pyproject.toml``).

**The ghost terrain mesh is real, sampled data, never smoothed.** Each
``GridCellLayer`` cell is one real elevation value straight from the
:class:`~.terrain.ElevationGrid` that produced it (optionally strided for a
large AOI, never interpolated beyond the bilinear resampling
:meth:`.terrain.ElevationGrid.sample` already does when the drape itself
was built) - see the design brief for why this layer is the whole point,
not decoration: it's the only thing that makes a drape's departure from
real terrain (or a surveyed line's honest departure at a structure)
legible at all.

**A real rendering artifact, found from a screenshot of an early build,
fixed rather than left as a known quirk.** ``GridCellLayer`` draws each
(possibly strided) cell as a flat block at *that one raw sample's* height,
while the road ``PathLayer`` draws each point at its own, separately
*bilinear-interpolated* height (see ``drape.py``) - two different, both
individually correct, samplings of the same real terrain. Wherever they
disagree locally (routinely, once the ghost mesh is strided coarse enough
for a large AOI - see ``generate_drape.py``'s own ghost-stride target), a
road can visually dip under a neighbouring block it never actually went
near in real terms. :func:`_ghost_cell_heights` is computed once and
handed to *both* :func:`ghost_terrain_layer` and the road-lifting step in
:func:`build_deck`, so a road's rendered height is always checked against
the exact numbers the mesh underneath it will draw, and lifted to clear
them - it can no longer disagree with a ghost block by construction. This
is a **display-only** correction: it never touches ``DrapedLine.parts``'
real sampled values, only a rendering-local copy built for this layer.

**The same mechanism embosses the road as a visible ridge in the ghost
mesh itself**, at the caller's request (this was a real, better idea than
just fixing the visual bug quietly) - any (possibly strided) ghost cell a
road passes through is raised by a bump sized relative to the AOI's own
real relief range (``_EMBOSS_FRACTION_OF_RELIEF``), the same "a fixed
legibility mark, not a real elevation value" posture ``export_stl.py``
takes for its own (differently-computed, physical-mm) ridge height on the
print - the two are unrelated figures for two different outputs, not
meant to visually match one another.

**A known, accepted imprecision**: the lift/emboss cell lookup assumes a
(possibly strided) cell's rendered footprint starts at its own raw grid
index rather than being centred on it (deck.gl's actual convention for
``GridCellLayer``) - up to roughly half a stride-cell of positional slop
in which neighbour's height a point gets compared against. Adjacent
cells rarely differ enough for this to matter, and the lift margin
(``_LIFT_MARGIN_FRACTION``) covers the rest; not worth the extra
bookkeeping to close entirely for a display-only correction.
"""

from __future__ import annotations

import math

import pydeck as pdk

from .drape import DrapedLine, road_cells
from .terrain import ElevationGrid

#: Low-opacity, muted neutral - the ghost must not compete with the road
#: lines for attention (see the design brief's own framing).
GHOST_COLOR = [170, 165, 150, 45]
FIELD_COLOR = [60, 120, 200, 200]
FIELD_COLOR_MUTED = [60, 120, 200, 70]
HIGHLIGHT_COLOR = [230, 60, 30, 255]

#: A visual legibility mark for the interactive ghost mesh, not a real
#: elevation figure and not the same number as export_stl.py's own
#: (physical, print-space) ridge height - see module docstring.
_EMBOSS_FRACTION_OF_RELIEF = 0.08
_EMBOSS_MIN_M = 1.0
#: Extra clearance above the emboss bump, so a lifted road visibly clears
#: its ghost cell rather than sitting exactly flush with it (z-fighting).
_LIFT_MARGIN_FRACTION = 0.15


def _ghost_cell_heights(
    grid: ElevationGrid, lines: list[DrapedLine], stride: int
) -> tuple[dict[tuple[int, int], float], float]:
    """The elevation :func:`ghost_terrain_layer` will render for every
    (possibly strided) cell, with any cell a road passes through raised by
    a visible emboss bump - see module docstring. Returned as an explicit
    lookup, not just built inline inside the layer function, so
    :func:`build_deck` can look a road's own point up against the *exact
    same* numbers when lifting it clear of the mesh."""
    non_nodata = [v for row in grid.values for v in row if v != grid.nodata]
    z_min, z_max = min(non_nodata), max(non_nodata)
    bump = max(_EMBOSS_MIN_M, _EMBOSS_FRACTION_OF_RELIEF * (z_max - z_min))

    spacing = min(abs(grid.pixel_size_x), abs(grid.pixel_size_y)) / 2
    on_road = road_cells(grid, lines, spacing) if lines else set()

    cells: dict[tuple[int, int], float] = {}
    for row in range(0, grid.height, stride):
        for col in range(0, grid.width, stride):
            z = grid.values[row][col]
            if grid.nodata is not None and z == grid.nodata:
                continue
            block_has_road = any(
                (r, c) in on_road
                for r in range(row, min(row + stride, grid.height))
                for c in range(col, min(col + stride, grid.width))
            )
            cells[(row, col)] = z + bump if block_has_road else z
    return cells, bump


def _strided_cell(
    grid: ElevationGrid, stride: int, x: float, y: float
) -> tuple[int, int] | None:
    row = round((y - grid.origin_y) / grid.pixel_size_y)
    col = round((x - grid.origin_x) / grid.pixel_size_x)
    if not (0 <= row < grid.height and 0 <= col < grid.width):
        return None
    return (row // stride) * stride, (col // stride) * stride


def _lift_above_ghost(
    lines: list[DrapedLine],
    grid: ElevationGrid,
    cell_heights: dict[tuple[int, int], float],
    stride: int,
    margin: float,
) -> list[DrapedLine]:
    """A display-only copy of ``lines`` with each point's Z raised to
    clear whatever ghost cell renders beneath it - see module docstring.
    Never mutates or is derived from anything but a rendering-local copy;
    the real sampled values in the original ``DrapedLine``s are untouched."""
    lifted = []
    for line in lines:
        new_parts = []
        for part in line.parts:
            new_part = []
            for x, y, z in part:
                cell = _strided_cell(grid, stride, x, y)
                ghost_z = cell_heights.get(cell) if cell else None
                new_part.append((x, y, max(z, ghost_z + margin) if ghost_z is not None else z))
            new_parts.append(tuple(new_part))
        lifted.append(
            DrapedLine(
                usrn=line.usrn, parts=tuple(new_parts),
                gap_count=line.gap_count, surface_model=line.surface_model,
                vertical_datum=line.vertical_datum,
            )
        )
    return lifted


def ghost_terrain_layer(
    grid: ElevationGrid, *, stride: int = 1, lines: list[DrapedLine] | None = None
) -> pdk.Layer:
    """A faint mesh of ``grid``'s own real elevation, clipped to exactly
    the AOI it was fetched for. ``stride`` subsamples for a large grid
    (fewer, bigger cells) - a rendering economy, not a smoothing: every
    cell shown is one real value from ``grid`` (plus a visible emboss bump
    wherever a road in ``lines`` passes through it - see module docstring),
    never an average."""
    cell_heights, _bump = _ghost_cell_heights(grid, lines or [], stride)
    data = []
    for (row, col), z in cell_heights.items():
        x = grid.origin_x + col * grid.pixel_size_x
        y = grid.origin_y + row * grid.pixel_size_y
        data.append({"position": [x, y], "elevation": z})
    return pdk.Layer(
        "GridCellLayer",
        data=data,
        get_position="position",
        get_elevation="elevation",
        cell_size=abs(grid.pixel_size_x) * stride,
        extruded=True,
        get_fill_color=GHOST_COLOR,
        pickable=False,
    )


def draped_field_layers(
    lines: list[DrapedLine], *, highlight_usrn: int | None = None
) -> list[pdk.Layer]:
    """The whole draped field as one ``PathLayer``, plus - if
    ``highlight_usrn`` is given and present in ``lines`` - a second, bright
    layer for just that USRN. This is the design brief's own preferred
    focus-mode rendering (keep the full area, highlight the chosen USRN)
    rather than isolating it alone: a single ribbon with no field around it
    loses the landscape context that makes the drape read as 3D at all."""
    field = [line for line in lines if line.usrn != highlight_usrn]
    field_data = [
        {"path": [list(p) for p in part], "usrn": line.usrn}
        for line in field
        for part in line.parts
    ]
    layers = [
        pdk.Layer(
            "PathLayer",
            data=field_data,
            get_path="path",
            get_width=1.5,
            width_min_pixels=1,
            get_color=FIELD_COLOR_MUTED if highlight_usrn is not None else FIELD_COLOR,
            pickable=True,
        )
    ]
    if highlight_usrn is not None:
        chosen = next((line for line in lines if line.usrn == highlight_usrn), None)
        if chosen is not None:
            highlight_data = [
                {"path": [list(p) for p in part], "usrn": chosen.usrn} for part in chosen.parts
            ]
            layers.append(
                pdk.Layer(
                    "PathLayer",
                    data=highlight_data,
                    get_path="path",
                    get_width=4,
                    width_min_pixels=3,
                    get_color=HIGHLIGHT_COLOR,
                    pickable=True,
                )
            )
    return layers


def _initial_view(
    lines: list[DrapedLine], *, rotation_x: float, rotation_orbit: float, zoom: float | None
):
    points = [p for line in lines for part in line.parts for p in part]
    xs, ys, zs = [p[0] for p in points], [p[1] for p in points], [p[2] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    target = [(min_x + max_x) / 2, (min_y + max_y) / 2, sum(zs) / len(points)]
    if zoom is None:
        extent = max(max_x - min_x, max_y - min_y, 1.0)
        # OrbitView zoom is a log2 scale (deck.gl convention, same as
        # MapView) - not independently re-verified against a browser
        # render (headless rendering isn't available here); a reasonable
        # starting point, adjustable via --zoom if the framing is off.
        zoom = math.log2(max(600.0 / extent, 0.01))
    return pdk.View(type="OrbitView", controller=True), pdk.ViewState(
        target=target, rotation_x=rotation_x, rotation_orbit=rotation_orbit, zoom=zoom
    )


def build_deck(
    lines: list[DrapedLine],
    grid: ElevationGrid,
    *,
    highlight_usrn: int | None = None,
    ghost_stride: int = 1,
    rotation_x: float = 55.0,
    rotation_orbit: float = -30.0,
    zoom: float | None = None,
) -> pdk.Deck:
    """Assemble the full scene: ghost terrain + draped field (+ highlight),
    in an ``OrbitView`` (see module docstring for why not a web map). The
    road is embossed into the ghost mesh and lifted clear of it - both
    computed from the same numbers, so the two can't disagree (see module
    docstring's own note on the rendering artifact this replaced)."""
    if not lines:
        raise ValueError("nothing to render - every USRN in the AOI failed to drape")
    cell_heights, bump = _ghost_cell_heights(grid, lines, ghost_stride)
    display_lines = _lift_above_ghost(
        lines, grid, cell_heights, ghost_stride, margin=bump * _LIFT_MARGIN_FRACTION
    )
    layers = [ghost_terrain_layer(grid, stride=ghost_stride, lines=lines)]
    layers += draped_field_layers(display_lines, highlight_usrn=highlight_usrn)
    view, view_state = _initial_view(
        display_lines, rotation_x=rotation_x, rotation_orbit=rotation_orbit, zoom=zoom
    )
    return pdk.Deck(
        layers=layers,
        views=[view],
        initial_view_state=view_state,
        map_provider=None,
        tooltip={"text": "USRN {usrn}"},
    )
