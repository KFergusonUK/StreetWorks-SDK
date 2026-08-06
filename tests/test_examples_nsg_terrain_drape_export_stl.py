"""Tests for examples/nsg_terrain_drape/export_stl.py - the 3D-print
mesh builder and binary STL writer."""

from __future__ import annotations

import struct

import pytest

from examples.nsg_terrain_drape.drape import DrapedLine
from examples.nsg_terrain_drape.export_stl import (
    DEFAULT_RIDGE_HEIGHT_MM,
    DEFAULT_VERTICAL_EXAGGERATION,
    build_print_mesh,
    write_binary_stl,
)
from examples.nsg_terrain_drape.terrain import ElevationGrid


def _flat_grid(width: int = 4, height: int = 4, z: float = 100.0, nodata=None) -> ElevationGrid:
    return ElevationGrid(
        values=tuple(tuple(z for _ in range(width)) for _ in range(height)),
        origin_x=0.0, origin_y=0.0, pixel_size_x=10.0, pixel_size_y=-10.0,
        width=width, height=height, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
        nodata=nodata,
    )


def _line(usrn: int, *parts) -> DrapedLine:
    return DrapedLine(
        usrn=usrn, parts=parts, gap_count=0, surface_model="DTM", vertical_datum="test"
    )


# ---------------------------------------------------------------------------
# build_print_mesh
# ---------------------------------------------------------------------------


def test_build_print_mesh_refuses_nodata():
    grid = ElevationGrid(
        values=((100.0, -9999.0), (100.0, 100.0)),
        origin_x=0.0, origin_y=0.0, pixel_size_x=10.0, pixel_size_y=-10.0,
        width=2, height=2, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
        nodata=-9999.0,
    )
    with pytest.raises(ValueError, match="no-data"):
        build_print_mesh(grid, [])


def test_build_print_mesh_triangle_count_matches_formula():
    grid = _flat_grid(width=4, height=4)
    triangles, _scale = build_print_mesh(grid, [])
    # top: (w-1)*(h-1)*2, bottom: same, walls: 2*(w-1)*2 + 2*(h-1)*2
    w, h = 4, 4
    expected = (w - 1) * (h - 1) * 2 * 2 + 2 * (w - 1) * 2 + 2 * (h - 1) * 2
    assert len(triangles) == expected


def test_build_print_mesh_is_watertight_edge_count():
    """Every edge in a closed 2-manifold mesh is shared by exactly two
    triangles. Not a full manifold checker, but catches the classic 'missed
    a wall' or 'double-counted a corner' mistakes a heightmap-to-solid
    builder is prone to."""
    grid = _flat_grid(width=5, height=3)
    triangles, _ = build_print_mesh(grid, [])
    edge_counts: dict[frozenset, int] = {}
    for v0, v1, v2 in triangles:
        for a, b in ((v0, v1), (v1, v2), (v2, v0)):
            key = frozenset((a, b))
            edge_counts[key] = edge_counts.get(key, 0) + 1
    assert all(count == 2 for count in edge_counts.values())


def test_build_print_mesh_footprint_matches_requested():
    grid = _flat_grid(width=10, height=20)  # extent_x=90, extent_y=190 (10m cells)
    _, scale = build_print_mesh(grid, [], footprint_mm=150.0)
    assert max(scale.footprint_mm) == pytest.approx(150.0)
    assert scale.real_extent_m == (90.0, 190.0)


def test_build_print_mesh_default_exaggeration_and_ridge_reported():
    grid = _flat_grid()
    _, scale = build_print_mesh(grid, [])
    assert scale.vertical_exaggeration == DEFAULT_VERTICAL_EXAGGERATION
    assert scale.ridge_height_mm == DEFAULT_RIDGE_HEIGHT_MM


def test_build_print_mesh_taller_terrain_gives_taller_print_range():
    flat = _flat_grid(z=100.0)
    hilly = ElevationGrid(
        values=((100.0, 100.0, 100.0, 100.0),) * 3 + ((100.0, 100.0, 200.0, 100.0),),
        origin_x=0.0, origin_y=0.0, pixel_size_x=10.0, pixel_size_y=-10.0,
        width=4, height=4, crs="EPSG:27700", vertical_datum="test", surface_model="DTM",
    )
    tri_flat, _ = build_print_mesh(flat, [])
    tri_hilly, _ = build_print_mesh(hilly, [])
    flat_zs = [v[2] for t in tri_flat for v in t]
    hilly_zs = [v[2] for t in tri_hilly for v in t]
    z_range_flat = max(flat_zs) - min(flat_zs)
    z_range_hilly = max(hilly_zs) - min(hilly_zs)
    assert z_range_hilly > z_range_flat


def test_build_print_mesh_road_raises_the_top_surface():
    grid = _flat_grid(width=4, height=4, z=100.0)
    # A road straight along the middle row.
    line = _line(1, ((15.0, -15.0, 999.0), (25.0, -15.0, 999.0)))
    triangles_no_road, _ = build_print_mesh(grid, [])
    triangles_with_road, _ = build_print_mesh(grid, [line])
    max_z_no_road = max(v[2] for t in triangles_no_road for v in t)
    max_z_with_road = max(v[2] for t in triangles_with_road for v in t)
    assert max_z_with_road > max_z_no_road


def test_build_print_mesh_ridge_height_is_a_fixed_physical_value():
    """The ridge's printed height shouldn't itself get multiplied by
    vertical exaggeration - see module docstring."""
    grid = _flat_grid(width=4, height=4, z=100.0)
    line = _line(1, ((15.0, -15.0, 999.0), (25.0, -15.0, 999.0)))
    tri_low_exag, _ = build_print_mesh(grid, [line], vertical_exaggeration=1.0)
    tri_high_exag, _ = build_print_mesh(grid, [line], vertical_exaggeration=5.0)
    base_low = min(v[2] for t in tri_low_exag for v in t if v[2] > 0)
    base_high = min(v[2] for t in tri_high_exag for v in t if v[2] > 0)
    ridge_bump_low = max(v[2] for t in tri_low_exag for v in t) - base_low
    ridge_bump_high = max(v[2] for t in tri_high_exag for v in t) - base_high
    assert ridge_bump_low == pytest.approx(ridge_bump_high, rel=0.05)


# ---------------------------------------------------------------------------
# write_binary_stl
# ---------------------------------------------------------------------------


def test_write_binary_stl_roundtrip(tmp_path):
    grid = _flat_grid(width=3, height=3)
    triangles, _ = build_print_mesh(grid, [])
    path = tmp_path / "out.stl"
    write_binary_stl(triangles, str(path))

    data = path.read_bytes()
    assert len(data) == 80 + 4 + 50 * len(triangles)
    (count,) = struct.unpack("<I", data[80:84])
    assert count == len(triangles)

    # Parse the first triangle back out and check it's a real, non-
    # degenerate face with a unit normal.
    offset = 84
    normal = struct.unpack("<3f", data[offset : offset + 12])
    length = sum(n * n for n in normal) ** 0.5
    assert length == pytest.approx(1.0, rel=1e-4)
