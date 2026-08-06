"""Tests for examples/nsg_terrain_drape/render.py's pure data-shaping
logic (not pydeck's own rendering, which this doesn't attempt to verify -
see the module docstring's honest note on OrbitView zoom not being
independently re-verified against a real browser render)."""

from __future__ import annotations

import pytest

from examples.nsg_terrain_drape.drape import DrapedLine
from examples.nsg_terrain_drape.render import (
    _ghost_cell_heights,
    _initial_view,
    _lift_above_ghost,
    _strided_cell,
    build_deck,
    draped_field_layers,
    ghost_terrain_layer,
)
from examples.nsg_terrain_drape.terrain import ElevationGrid


def _grid() -> ElevationGrid:
    return ElevationGrid(
        values=((10.0, 20.0), (30.0, 40.0)),
        origin_x=0.0, origin_y=0.0, pixel_size_x=10.0, pixel_size_y=-10.0,
        width=2, height=2, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
    )


def _line(usrn: int, *parts: tuple[tuple[float, float, float], ...]) -> DrapedLine:
    return DrapedLine(
        usrn=usrn, parts=parts, gap_count=0, surface_model="DTM", vertical_datum="test"
    )


def test_ghost_terrain_layer_emits_one_cell_per_real_grid_value():
    grid = _grid()
    layer = ghost_terrain_layer(grid)
    assert len(layer.data) == 4
    elevations = sorted(d["elevation"] for d in layer.data)
    assert elevations == [10.0, 20.0, 30.0, 40.0]


def test_ghost_terrain_layer_stride_subsamples():
    grid = ElevationGrid(
        values=tuple(tuple(float(r * 10 + c) for c in range(10)) for r in range(10)),
        origin_x=0.0, origin_y=0.0, pixel_size_x=1.0, pixel_size_y=-1.0,
        width=10, height=10, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
    )
    layer = ghost_terrain_layer(grid, stride=5)
    assert len(layer.data) == 4  # rows/cols 0 and 5 only


def test_ghost_terrain_layer_skips_nodata_cells():
    grid = ElevationGrid(
        values=((10.0, -9999.0), (30.0, 40.0)),
        origin_x=0.0, origin_y=0.0, pixel_size_x=10.0, pixel_size_y=-10.0,
        width=2, height=2, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
        nodata=-9999.0,
    )
    layer = ghost_terrain_layer(grid)
    assert len(layer.data) == 3
    assert all(d["elevation"] != -9999.0 for d in layer.data)


def test_ghost_terrain_layer_no_lines_is_unchanged_from_before():
    """Regression: ghost_terrain_layer(grid) with no lines= must behave
    exactly as it did before embossing was added."""
    grid = _grid()
    assert ghost_terrain_layer(grid).data == ghost_terrain_layer(grid, lines=None).data


def test_ghost_terrain_layer_embosses_the_cell_a_road_passes_through():
    grid = _grid()  # 2x2, 10m cells, values 10/20/30/40
    # A road through the (row=0, col=1) cell only - offset from the exact
    # cell-boundary midpoint (which round()'s banker's rounding resolves
    # unpredictably) so it lands unambiguously in that one cell.
    line = _line(1, ((12.0, -2.0, 999.0), (12.0, -2.0, 999.0)))
    plain = {tuple(d["position"]): d["elevation"] for d in ghost_terrain_layer(grid).data}
    embossed = {
        tuple(d["position"]): d["elevation"] for d in ghost_terrain_layer(grid, lines=[line]).data
    }
    changed = {k: v for k, v in embossed.items() if v != plain[k]}
    assert len(changed) == 1
    (only_key, only_value) = next(iter(changed.items()))
    assert only_value > plain[only_key]


def test_draped_field_layers_no_highlight_is_one_layer():
    lines = [_line(1, ((0.0, 0.0, 5.0), (1.0, 1.0, 6.0)))]
    layers = draped_field_layers(lines)
    assert len(layers) == 1
    assert len(layers[0].data) == 1


def test_draped_field_layers_multipart_emits_one_path_per_part():
    lines = [
        _line(
            1,
            ((0.0, 0.0, 5.0), (1.0, 1.0, 6.0)),
            ((5.0, 5.0, 7.0), (6.0, 6.0, 8.0)),
        )
    ]
    layers = draped_field_layers(lines)
    assert len(layers[0].data) == 2
    assert all(d["usrn"] == 1 for d in layers[0].data)


def test_draped_field_layers_with_highlight_splits_into_two_layers():
    lines = [
        _line(1, ((0.0, 0.0, 5.0), (1.0, 1.0, 6.0))),
        _line(2, ((10.0, 10.0, 5.0), (11.0, 11.0, 6.0))),
    ]
    layers = draped_field_layers(lines, highlight_usrn=2)
    assert len(layers) == 2
    field_layer, highlight_layer = layers
    assert len(field_layer.data) == 1
    assert field_layer.data[0]["usrn"] == 1
    assert len(highlight_layer.data) == 1
    assert highlight_layer.data[0]["usrn"] == 2


def test_draped_field_layers_highlight_not_present_yields_no_second_layer():
    lines = [_line(1, ((0.0, 0.0, 5.0), (1.0, 1.0, 6.0)))]
    layers = draped_field_layers(lines, highlight_usrn=999)
    assert len(layers) == 1


def test_initial_view_centroid_and_bounds():
    """Regression test: an earlier version computed xs/ys/zs as generators
    and called min() then max() on the same one, exhausting it before the
    second call - only caught by actually running the CLI end-to-end, not
    by any test, hence this one existing now."""
    lines = [
        _line(1, ((0.0, 0.0, 10.0), (10.0, 0.0, 20.0))),
        _line(2, ((0.0, 10.0, 30.0), (10.0, 10.0, 40.0))),
    ]
    view, view_state = _initial_view(lines, rotation_x=55.0, rotation_orbit=-30.0, zoom=None)
    assert view.__class__.__name__ == "View"
    assert view_state.target == pytest.approx([5.0, 5.0, 25.0])
    assert view_state.zoom is not None


def test_initial_view_explicit_zoom_is_respected():
    lines = [_line(1, ((0.0, 0.0, 10.0), (10.0, 0.0, 20.0)))]
    _, view_state = _initial_view(lines, rotation_x=55.0, rotation_orbit=-30.0, zoom=7.5)
    assert view_state.zoom == 7.5


# ---------------------------------------------------------------------------
# The road-clipping-under-the-ghost-mesh fix (see module docstring)
# ---------------------------------------------------------------------------


def test_strided_cell_maps_to_its_own_group_origin():
    grid = _grid()
    # Off the exact cell-boundary midpoint - see the emboss test's own note
    # on round()'s banker's rounding at .5.
    assert _strided_cell(grid, 1, 12.0, -2.0) == (0, 1)


def test_strided_cell_outside_grid_is_none():
    grid = _grid()
    assert _strided_cell(grid, 1, 9999.0, -9999.0) is None


def test_ghost_cell_heights_no_road_matches_raw_grid():
    grid = _grid()
    cells, _bump = _ghost_cell_heights(grid, [], stride=1)
    assert cells == {(0, 0): 10.0, (0, 1): 20.0, (1, 0): 30.0, (1, 1): 40.0}


def test_ghost_cell_heights_bump_is_positive_and_relative_to_relief():
    flat_grid = ElevationGrid(
        values=((100.0, 100.0), (100.0, 100.0)),
        origin_x=0.0, origin_y=0.0, pixel_size_x=10.0, pixel_size_y=-10.0,
        width=2, height=2, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
    )
    hilly_grid = ElevationGrid(
        values=((100.0, 200.0), (100.0, 100.0)),
        origin_x=0.0, origin_y=0.0, pixel_size_x=10.0, pixel_size_y=-10.0,
        width=2, height=2, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
    )
    _cells_flat, bump_flat = _ghost_cell_heights(flat_grid, [], stride=1)
    _cells_hilly, bump_hilly = _ghost_cell_heights(hilly_grid, [], stride=1)
    assert bump_flat > 0  # the floor (_EMBOSS_MIN_M), even with zero relief
    assert bump_hilly > bump_flat  # scales up with real relief


def test_lift_above_ghost_raises_a_point_below_its_ghost_cell():
    grid = _grid()
    cell_heights = {(0, 0): 500.0}  # far above the road's own sampled z
    lines = [_line(1, ((5.0, -5.0, 10.0),))]  # falls in cell (0, 0)
    lifted = _lift_above_ghost(lines, grid, cell_heights, stride=1, margin=2.0)
    assert lifted[0].parts[0][0][2] == pytest.approx(502.0)


def test_lift_above_ghost_leaves_a_point_already_above_its_ghost_cell():
    grid = _grid()
    cell_heights = {(0, 0): 5.0}  # well below the road's own sampled z
    lines = [_line(1, ((5.0, -5.0, 100.0),))]
    lifted = _lift_above_ghost(lines, grid, cell_heights, stride=1, margin=2.0)
    assert lifted[0].parts[0][0][2] == pytest.approx(100.0)


def test_lift_above_ghost_point_outside_grid_is_unchanged():
    grid = _grid()
    lines = [_line(1, ((9999.0, -9999.0, 42.0),))]
    lifted = _lift_above_ghost(lines, grid, {}, stride=1, margin=2.0)
    assert lifted[0].parts[0][0][2] == pytest.approx(42.0)


def test_build_deck_road_never_renders_below_its_ghost_cell():
    """The actual guarantee the fix provides: every rendered road point's
    Z is at or above whatever ghost cell will be drawn at that location -
    the exact artifact from the screenshot this was built to fix."""
    grid = ElevationGrid(
        values=((10.0, 90.0), (30.0, 40.0)),  # a sharp, blocky jump - the worst case
        origin_x=0.0, origin_y=0.0, pixel_size_x=10.0, pixel_size_y=-10.0,
        width=2, height=2, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
    )
    # A road sampled at a bilinear-interpolated height (12.0) that's well
    # below the blocky neighbour cell (90.0) it's rendered next to.
    lines = [_line(1, ((15.0, -5.0, 12.0),))]
    deck = build_deck(lines, grid, ghost_stride=1)
    ghost_layer, path_layer = deck.layers
    ghost_by_position = {tuple(d["position"]): d["elevation"] for d in ghost_layer.data}
    for entry in path_layer.data:
        for x, y, z in entry["path"]:
            cell = _strided_cell(grid, 1, x, y)
            if cell is None:
                continue
            ghost_position = (
                grid.origin_x + cell[1] * grid.pixel_size_x,
                grid.origin_y + cell[0] * grid.pixel_size_y,
            )
            assert z >= ghost_by_position[ghost_position]


def test_build_deck_no_lines_raises():
    grid = _grid()
    with pytest.raises(ValueError, match="nothing to render"):
        build_deck([], grid)
