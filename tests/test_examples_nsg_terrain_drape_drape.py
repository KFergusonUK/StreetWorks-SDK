"""Tests for examples/nsg_terrain_drape/drape.py - densify/sample/emit,
the derived consumer of terrain.py's stated elevation (see that module's
own docstring for why this logic lives here and not there)."""

from __future__ import annotations

import pytest

from examples.nsg_terrain_drape.drape import (
    DENSIFY_SPACING_M,
    DrapedLine,
    densify,
    drape_line,
    parse_wkt_parts,
    road_cells,
)
from examples.nsg_terrain_drape.terrain import ElevationGrid


def test_parse_wkt_parts_linestring():
    # A real OS Open USRN shape (see UsrnDatabase.get()'s own docstring
    # example, USRN 33909869) - not an actual live pull, but the exact
    # format streetworks.openusrn.reader emits (plain, un-nested, 2D).
    wkt = "LINESTRING (429000.1 541000.2, 429010.5 541005.7, 429020.0 541012.3)"
    parts = parse_wkt_parts(wkt)
    assert parts == (((429000.1, 541000.2), (429010.5, 541005.7), (429020.0, 541012.3)),)


def test_parse_wkt_parts_multilinestring_real_shape():
    # A real OS Open USRN shape, confirmed live during this example's own
    # build (67% of a 200,000-street sample were MULTILINESTRING, not an
    # edge case - see drape.py's own module docstring). Verbatim prefix of
    # a real USRN 28104228 pull, trimmed to keep the fixture small.
    wkt = (
        "MULTILINESTRING ((635856.316 328365.956, 635836.66 328094.479), "
        "(635699.029 327276.829, 635670.21 327584.094))"
    )
    parts = parse_wkt_parts(wkt)
    assert parts == (
        ((635856.316, 328365.956), (635836.66, 328094.479)),
        ((635699.029, 327276.829), (635670.21, 327584.094)),
    )


def test_parse_wkt_parts_multilinestring_three_or_more_parts():
    wkt = "MULTILINESTRING ((0 0, 1 1), (2 2, 3 3), (4 4, 5 5))"
    parts = parse_wkt_parts(wkt)
    assert len(parts) == 3
    assert parts[2] == ((4.0, 4.0), (5.0, 5.0))


def test_parse_wkt_parts_rejects_other_shapes():
    with pytest.raises(ValueError, match="LINESTRING"):
        parse_wkt_parts("POINT (1 2)")


def test_densify_short_segment_keeps_endpoints_only():
    line = ((0.0, 0.0), (5.0, 0.0))  # 5m, under the 10m default spacing
    out = densify(line)
    assert out == ((0.0, 0.0), (5.0, 0.0))


def test_densify_inserts_even_subdivisions():
    line = ((0.0, 0.0), (25.0, 0.0))  # 25m -> round(25/10)=2 steps? no, round(2.5)=2
    out = densify(line, spacing=10.0)
    # 25m / round(2.5)=2 steps of 12.5m each - even subdivision, not a
    # short leftover step.
    xs = [p[0] for p in out]
    assert xs[0] == pytest.approx(0.0)
    assert xs[-1] == pytest.approx(25.0)
    for a, b in zip(xs, xs[1:]):  # noqa: B905 - deliberately pairwise
        assert (b - a) == pytest.approx(12.5)


def test_densify_multi_segment_line():
    line = ((0.0, 0.0), (20.0, 0.0), (20.0, 20.0))
    out = densify(line, spacing=10.0)
    assert out[0] == (0.0, 0.0)
    assert out[-1] == (20.0, 20.0)
    assert (20.0, 0.0) in out  # original mid-vertex preserved exactly


def test_densify_single_point_line_is_unchanged():
    assert densify(((1.0, 2.0),)) == ((1.0, 2.0),)


def test_densify_default_spacing_matches_brief():
    assert DENSIFY_SPACING_M == 10.0


def _flat_grid(z: float, nodata: float | None = None) -> ElevationGrid:
    return ElevationGrid(
        values=((z, z), (z, z)),
        origin_x=0.0, origin_y=0.0, pixel_size_x=100.0, pixel_size_y=-100.0,
        width=2, height=2, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
        nodata=nodata,
    )


def test_drape_line_flat_grid_gives_constant_z():
    grid = _flat_grid(50.0)
    result = drape_line(1, (((0.0, 0.0), (50.0, -50.0)),), grid, spacing=25.0)
    assert result is not None
    assert result.usrn == 1
    assert len(result.parts) == 1
    assert all(z == pytest.approx(50.0) for _, _, z in result.parts[0])
    assert result.gap_count == 0
    assert result.surface_model == "DTM"


def test_drape_line_wholly_outside_grid_returns_none():
    grid = _flat_grid(50.0)
    result = drape_line(1, (((1000.0, 1000.0), (1010.0, 1010.0)),), grid)
    assert result is None


def test_drape_line_partial_gap_is_dropped_not_carried_forward():
    """One endpoint is inside the grid, the other well outside it - the
    out-of-range vertex must be dropped, never filled with the last real
    sample (that would fabricate a value the terrain layer never stated)."""
    grid = _flat_grid(50.0)  # grid spans x:[0,100], y:[-100,0]
    result = drape_line(1, (((10.0, -10.0), (5000.0, -10.0)),), grid, spacing=20.0)
    assert result is not None
    assert all(z == pytest.approx(50.0) for part in result.parts for _, _, z in part)
    assert result.gap_count > 0


def test_drape_line_too_few_real_samples_returns_none():
    grid = _flat_grid(50.0)
    # Only one endpoint lands inside the grid - one real sample isn't
    # enough to draw a line through.
    result = drape_line(
        1, (((50.0, -50.0), (9999.0, -9999.0)),), grid, spacing=1_000_000.0
    )
    assert result is None


def test_drape_line_multipart_one_part_inside_one_wholly_outside():
    """A real MULTILINESTRING-shaped USRN where one disconnected part is
    inside the terrain AOI and the other is nowhere near it - the outside
    part is dropped, the inside one survives, matching the module
    docstring's "any part keeps two or more real samples" rule."""
    grid = _flat_grid(50.0)  # spans x:[0,100], y:[-100,0]
    parts = (
        ((10.0, -10.0), (90.0, -90.0)),  # inside
        ((5000.0, 5000.0), (5010.0, 5010.0)),  # wholly outside
    )
    result = drape_line(1, parts, grid, spacing=40.0)
    assert result is not None
    assert len(result.parts) == 1
    assert all(z == pytest.approx(50.0) for _, _, z in result.parts[0])


def test_drape_line_multipart_all_parts_outside_returns_none():
    grid = _flat_grid(50.0)
    parts = (
        ((5000.0, 5000.0), (5010.0, 5010.0)),
        ((6000.0, 6000.0), (6010.0, 6010.0)),
    )
    result = drape_line(1, parts, grid)
    assert result is None


# ---------------------------------------------------------------------------
# road_cells - shared by export_stl.py (which cell to emboss on the print)
# and render.py (which cell to emboss/lift in the interactive ghost mesh)
# ---------------------------------------------------------------------------


def _sized_grid(width: int, height: int, z: float = 100.0) -> ElevationGrid:
    return ElevationGrid(
        values=tuple(tuple(z for _ in range(width)) for _ in range(height)),
        origin_x=0.0, origin_y=0.0, pixel_size_x=10.0, pixel_size_y=-10.0,
        width=width, height=height, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
    )


def _road_line(usrn: int, *parts: tuple[tuple[float, float, float], ...]) -> DrapedLine:
    return DrapedLine(
        usrn=usrn, parts=parts, gap_count=0, surface_model="DTM", vertical_datum="test"
    )


def test_road_cells_marks_the_cell_a_vertex_falls_in():
    grid = _sized_grid(4, 4)  # origin (0,0), 10m cells, north-up
    line = _road_line(1, ((5.0, -5.0, 0.0),))  # lands inside the grid somewhere
    cells = road_cells(grid, [line], spacing=5.0)
    assert len(cells) >= 1
    for row, col in cells:
        assert 0 <= row < grid.height
        assert 0 <= col < grid.width


def test_road_cells_ignores_points_outside_the_grid():
    grid = _sized_grid(4, 4)
    line = _road_line(1, ((9999.0, -9999.0, 0.0),))
    cells = road_cells(grid, [line], spacing=5.0)
    assert cells == set()


def test_road_cells_covers_a_continuous_path_no_gaps():
    grid = _sized_grid(10, 2)
    line = _road_line(1, ((0.0, -5.0, 0.0), (95.0, -5.0, 0.0)))
    cells = road_cells(grid, [line], spacing=5.0)
    cols_hit = {c for _r, c in cells}
    assert cols_hit == set(range(10))  # every column along the path is hit
