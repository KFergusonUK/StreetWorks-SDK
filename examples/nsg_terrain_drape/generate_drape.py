#!/usr/bin/env python3
"""Drape the UK NSG over terrain - see README.md in this directory for the
whole point (a cool render, and a free lesson: derived Z vs Norway's real
stated Z), the guardrails, and example output.

Run (default: the whole USRN field over central Durham, OS Terrain 50):

    python -m examples.nsg_terrain_drape.generate_drape

Highlight one street within the field:

    python -m examples.nsg_terrain_drape.generate_drape --usrn 33909869

The 1m LIDAR wow-factor instead of the 50m baseline (slower - see
terrain.py's own module docstring on why EA's on-demand WCS is still the
better-shaped adapter even though this path is heavier):

    python -m examples.nsg_terrain_drape.generate_drape --terrain lidar

A close-up of your own choosing (BNG metres, min_e min_n max_e max_n) - the
design brief's own suggested failure-case hunting grounds (A1(M) junctions
around Durham for a flyover, the A19 Tyne Tunnel a little further north)
are real candidates worth trying here, not verified down to the metre in
this build:

    python -m examples.nsg_terrain_drape.generate_drape --terrain lidar \\
        --bbox 425000 540000 426000 541000

First run downloads and caches OS Open USRN (~300MB) and, for the default
terrain, OS Terrain 50 (~160MB) - both one-time, see README. Writes a
self-contained `nsg_terrain_drape.html` (override with `--out`) with a
real "Export for 3D Print" button in it, linking to a binary STL of the
same AOI - a solid, watertight terrain block with the USRN field embossed
into its own top surface as a raised ridge (see export_stl.py's own
docstring for the two deliberate distortions this makes, and why both are
reported on the page rather than left silent). Pass `--no-stl` to skip it.
"""

from __future__ import annotations

import argparse
import html as html_module
import sys
from pathlib import Path

from streetworks.openusrn import OpenUSRNClient, UsrnDatabase, extract_gpkg

from .drape import DrapedLine, drape_line, parse_wkt_parts
from .export_stl import (
    DEFAULT_FOOTPRINT_MM,
    DEFAULT_RIDGE_HEIGHT_MM,
    DEFAULT_VERTICAL_EXAGGERATION,
    PrintScale,
    build_print_mesh,
    write_binary_stl,
)
from .render import build_deck
from .terrain import EA_LIDAR_DTM_1M, EALidarWCSClient, ElevationGrid, OSTerrain50Client

#: Real Durham AOIs (BNG, EPSG:27700) - central Durham + the River Wear
#: valley slopes, chosen because a real live pull during this example's own
#: build confirmed genuine relief there (30-72m across a few hundred
#: metres), not guessed from a map.
AOIS = {
    "durham": (426500.0, 541500.0, 428500.0, 543500.0),
}

CACHE_DIR = Path(__file__).parent / "cache"

#: Ghost mesh cell target - independent of terrain resolution, so a 1m
#: LIDAR pull over a real AOI doesn't try to hand a browser millions of
#: GridCellLayer instances (see render.py's own docstring on why the ghost
#: mesh strides rather than smooths).
_GHOST_TARGET_CELLS = 8_000


def _default_ghost_stride(grid: ElevationGrid) -> int:
    total = grid.width * grid.height
    return max(1, round((total / _GHOST_TARGET_CELLS) ** 0.5))


def _usrn_database() -> UsrnDatabase:
    CACHE_DIR.mkdir(exist_ok=True)
    archive = CACHE_DIR / "osopenusrn.zip"
    if not archive.exists():
        print("Downloading OS Open USRN (~300MB, one-time, cached after)...")
        with OpenUSRNClient() as client:
            client.download(archive)
    gpkg = extract_gpkg(archive, CACHE_DIR)
    return UsrnDatabase(gpkg)


def _fetch_terrain(source: str, bbox: tuple[float, float, float, float]) -> ElevationGrid:
    min_e, min_n, max_e, max_n = bbox
    if source == "lidar":
        with EALidarWCSClient(EA_LIDAR_DTM_1M) as client:
            return client.fetch(min_e=min_e, min_n=min_n, max_e=max_e, max_n=max_n)
    with OSTerrain50Client(cache_dir=CACHE_DIR) as client:
        return client.fetch(min_e=min_e, min_n=min_n, max_e=max_e, max_n=max_n)


def _usrns_in_bbox(
    db: UsrnDatabase, bbox: tuple[float, float, float, float]
) -> list[tuple[int, str]]:
    """Every USRN whose geometry overlaps `bbox`. UsrnDatabase has no
    spatial index (a plain GeoPackage read - see its own docstring), so
    this scans every GB street once per run; fine for a one-off AOI pull,
    not meant for repeated/interactive querying."""
    min_e, min_n, max_e, max_n = bbox
    hits = []
    for street in db.iter_streets():
        if street.geometry is None:
            continue
        parts = parse_wkt_parts(street.geometry)
        xs = [p[0] for part in parts for p in part]
        ys = [p[1] for part in parts for p in part]
        if max(xs) < min_e or min(xs) > max_e or max(ys) < min_n or min(ys) > max_n:
            continue
        hits.append((street.usrn, street.geometry))
    return hits


def build_field(
    db: UsrnDatabase, bbox: tuple[float, float, float, float], grid: ElevationGrid
) -> tuple[list[DrapedLine], int, int]:
    """Fetch every USRN in `bbox`, drape each over `grid`. Returns
    (draped lines, total USRNs found, total individual vertex gaps
    dropped) - the caller reports these, never silently."""
    streets = _usrns_in_bbox(db, bbox)
    lines = []
    total_gaps = 0
    for usrn, wkt in streets:
        draped = drape_line(usrn, parse_wkt_parts(wkt), grid)
        if draped is not None:
            lines.append(draped)
            total_gaps += draped.gap_count
    return lines, len(streets), total_gaps


def _inject_stl_button(page_html: str, stl_filename: str, scale: PrintScale) -> str:
    """Splice a real download link for the sibling STL file into pydeck's
    own generated page, just before ``</body>``. A plain ``<a href=...
    download>`` - clicking it downloads the file this run already wrote to
    disk, it doesn't generate anything itself (a static HTML file has no
    way to run Python), so the button only ever appears when a real STL
    exists to back it (see ``main()`` - this is only called when one was
    written)."""
    caption = (
        f"Solid terrain block, {scale.footprint_mm[0]:.0f}x{scale.footprint_mm[1]:.0f}mm "
        f"({scale.real_extent_m[0]:.0f}x{scale.real_extent_m[1]:.0f}m real extent, "
        f"1:{1000 / scale.scale_mm_per_m:.0f} scale). Height exaggerated "
        f"{scale.vertical_exaggeration:g}x - a print at true scale of this real, "
        f"gentle relief would be close to flat. Road ridge is a fixed "
        f"{scale.ridge_height_mm:g}mm, not exaggerated."
    )
    button = f"""
<a id="stl-download" href="{html_module.escape(stl_filename)}" download
   title="{html_module.escape(caption)}"
   style="position:fixed;top:12px;right:12px;z-index:999;
          background:#1b1f27;color:#fff;padding:10px 16px;
          border-radius:6px;font:14px/1.3 -apple-system,sans-serif;
          text-decoration:none;box-shadow:0 2px 8px rgba(0,0,0,.35);">
  &#8681; Export for 3D Print
</a>
"""
    return page_html.replace("</body>", button + "</body>", 1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Drape the UK NSG over terrain (streetworks example).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--aoi", choices=sorted(AOIS), default="durham")
    ap.add_argument(
        "--bbox", type=float, nargs=4, metavar=("MIN_E", "MIN_N", "MAX_E", "MAX_N"),
        help="override --aoi with your own BNG bbox",
    )
    ap.add_argument("--usrn", type=int, default=None, help="highlight one USRN within the field")
    ap.add_argument(
        "--terrain", choices=("os50", "lidar"), default="os50",
        help="os50 = OS Terrain 50, 50m, GB-wide bulk download (default); "
        "lidar = EA LIDAR Composite DTM, 1m, on-demand - see README",
    )
    ap.add_argument("--ghost-stride", type=int, default=None, help="override the ghost-mesh stride")
    ap.add_argument("-o", "--out", default="nsg_terrain_drape.html")
    ap.add_argument(
        "--no-stl", action="store_true",
        help="skip the STL export and the 'Export for 3D Print' button",
    )
    ap.add_argument("--stl-out", default=None, help="STL path (default: --out with a .stl suffix)")
    ap.add_argument(
        "--print-footprint-mm", type=float, default=DEFAULT_FOOTPRINT_MM,
        help=f"longest print-bed edge in mm (default {DEFAULT_FOOTPRINT_MM:g})",
    )
    ap.add_argument(
        "--vertical-exaggeration", type=float, default=DEFAULT_VERTICAL_EXAGGERATION,
        help=f"terrain height multiplier (default {DEFAULT_VERTICAL_EXAGGERATION:g}x - see "
        "export_stl.py's own docstring for why this figure specifically)",
    )
    ap.add_argument(
        "--ridge-height-mm", type=float, default=DEFAULT_RIDGE_HEIGHT_MM,
        help=f"road ridge's fixed physical height in mm (default {DEFAULT_RIDGE_HEIGHT_MM:g})",
    )
    args = ap.parse_args(argv)

    bbox = tuple(args.bbox) if args.bbox else AOIS[args.aoi]

    print(f"Fetching {args.terrain} terrain for bbox {bbox}...")
    grid = _fetch_terrain(args.terrain, bbox)
    print(f"  {grid.width}x{grid.height} real cells, {grid.surface_model}, {grid.vertical_datum}")

    with _usrn_database() as db:
        lines, n_streets, total_gaps = build_field(db, bbox, grid)
    print(
        f"  {n_streets} USRNs in AOI, {len(lines)} draped "
        f"({n_streets - len(lines)} wholly outside the terrain grid, "
        f"{total_gaps} individual vertex gaps dropped)."
    )
    if not lines:
        print(
            "Nothing to render - no USRN in this AOI had two or more real samples.",
            file=sys.stderr,
        )
        return 1

    if args.usrn is not None and not any(line.usrn == args.usrn for line in lines):
        print(
            f"  Note: USRN {args.usrn} isn't drapeable in this AOI - "
            "showing the full field with no highlight.",
            file=sys.stderr,
        )

    stride = args.ghost_stride or _default_ghost_stride(grid)
    deck = build_deck(lines, grid, highlight_usrn=args.usrn, ghost_stride=stride)
    page_html = deck.to_html(
        None, notebook_display=False, open_browser=False, as_string=True
    )

    out_path = Path(args.out)
    if not args.no_stl:
        stl_path = Path(args.stl_out) if args.stl_out else out_path.with_suffix(".stl")
        print("Building the 3D-print mesh (a solid terrain block, road embossed)...")
        try:
            triangles, scale = build_print_mesh(
                grid, lines,
                footprint_mm=args.print_footprint_mm,
                vertical_exaggeration=args.vertical_exaggeration,
                ridge_height_mm=args.ridge_height_mm,
            )
        except ValueError as exc:
            print(f"  Skipping STL export: {exc}", file=sys.stderr)
        else:
            write_binary_stl(triangles, str(stl_path))
            print(
                f"  Wrote {stl_path} ({len(triangles):,} triangles) - "
                f"{scale.footprint_mm[0]:.0f}x{scale.footprint_mm[1]:.0f}mm "
                f"(1:{1000 / scale.scale_mm_per_m:.0f} scale), height exaggerated "
                f"{scale.vertical_exaggeration:g}x, {scale.real_extent_m[0]:.0f}x"
                f"{scale.real_extent_m[1]:.0f}m real extent - both distortions stated, "
                "never left implicit."
            )
            page_html = _inject_stl_button(page_html, stl_path.name, scale)

    out_path.write_text(page_html, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
