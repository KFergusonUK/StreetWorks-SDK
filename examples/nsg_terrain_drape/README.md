# Draping the UK NSG over terrain

A cool render first - a whole field of OS Open USRN centrelines rippling
over real Durham relief - with a free teaching foil riding along for
nothing: the drape is **derived**, not **stated**, and it breaks in
predictable, visible ways.

```bash
python -m examples.nsg_terrain_drape.generate_drape
```

Writes a self-contained `nsg_terrain_drape.html` (default; override with
`--out`), with a real **"Export for 3D Print" button** in the top-right
corner - see "3D-printing the AOI" below. First run downloads and caches
OS Open USRN (~300MB) and OS Terrain 50 (~160MB, the default terrain
source) - both one-time, cached in `./cache/` (override with editing
`CACHE_DIR` at the top of `generate_drape.py` if you need to). A cold run
over the default Durham AOI takes about two minutes on ordinary broadband,
almost entirely spent scanning OS Open USRN's ~1.4 million GB-wide streets
for the ~360 inside the AOI - see "A real, acknowledged limitation" below.

```bash
# Highlight one street within the full field, rather than isolating it -
# a lone ribbon with nothing around it loses the landscape that makes the
# drape read as 3D at all.
python -m examples.nsg_terrain_drape.generate_drape --usrn 11720052

# The 1m LIDAR wow-factor instead of the 50m baseline, on a close-up bbox
# (BNG metres) - slower, and most legible zoomed into one feature rather
# than the whole city.
python -m examples.nsg_terrain_drape.generate_drape --terrain lidar \
    --bbox 427000 542000 427300 542300

# The wider Durham showcase render (~870x1430m, 1m LIDAR) - the command
# behind the screenshot in this repo's own examples/. --bbox is always
# min_e min_n max_e max_n, ascending on both axes, or the WCS backend
# rejects it outright (an inverted N range 500s rather than silently
# swapping the order for you).
python -m examples.nsg_terrain_drape.generate_drape --terrain lidar \
    --bbox 426917 541641 427790 543069 -o durham_showcase.html
```

## The point, in one sentence

**A DEM sample is a guess at the ground under an XY, not a measurement of
the road at that XY** - and this example makes that failure visible rather
than hiding it, using two providers this SDK already has live access to
(OS Open USRN for geometry, Norway's NVDB for a real surveyed-Z
comparison) plus two new ones built for this example (OS Terrain 50, EA's
LIDAR Composite).

## Method

1. **Geometry**: `streetworks.openusrn` (already in this SDK) for every
   USRN centreline in the AOI - British National Grid, EPSG:27700,
   confirmed live to be a genuine mix of `LINESTRING` and (the *majority*
   shape, 67% in a 200,000-street sample - see `drape.py`'s own docstring)
   `MULTILINESTRING`, for USRNs whose real geometry is disconnected (e.g.
   split by a roundabout island).
2. **Terrain**: `terrain.py` in this package (see its own module docstring
   for the full detail) - a stdlib-only GeoTIFF/ESRI ASCII Grid reader,
   plus two real, live, credential-free clients: `OSTerrain50Client` (the
   default - 50m posts, GB-wide, bulk-download-then-cache) and
   `EALidarWCSClient` (1m posts, on-demand OGC WCS, the "wow factor" close-
   up option - `--terrain lidar`).
3. **Densify**: `drape.py`'s `densify()` inserts vertices every ~10m along
   each USRN part before sampling - USRN vertices are sparse, and a raw
   sample between two distant original vertices would chord across the
   terrain rather than follow it.
4. **Sample**: bilinear interpolation (`ElevationGrid.sample()`), never
   nearest-neighbour (which stair-steps) - and never fabricated: a
   densified vertex the terrain grid has no real value for is dropped, not
   carried forward from the last real sample.
5. **Render**: `render.py`, pydeck, entirely in the terrain grid's own
   EPSG:27700 metres via an `OrbitView` (a free 3D camera, not a web map) -
   so nothing here ever reprojects a coordinate for display either. A
   faint, semi-transparent "ghost" mesh of the same real terrain sits
   underneath the draped field - not decoration, the reference frame that
   makes the failure legible at all (see below).

## Why the CRS lines up for free

OS Open USRN, OS Terrain 50, and EA's LIDAR Composite are all EPSG:27700.
The drape never reprojects a single XY to combine them - `terrain.py`
refuses (raises, not guesses) rather than silently transform a source it
found in a different CRS.

## The ghost terrain layer, and why it's the whole point

The muted mesh underneath the draped field isn't decoration - it's what
turns "here's a wiggly 3D line" into "here's the one thing that can never
leave the ground, next to the one thing that's allowed to." Because the
draped line is *sampled from* that same surface, it is welded to it by
construction and can never depart from it - which is exactly the tell that
it's a guess: a real road bridges, cuts, and bores, and this one can't.

## 3D-printing the AOI

The generated page's "Export for 3D Print" button downloads a real binary
STL (`export_stl.py`) - a solid, watertight terrain block for the same
AOI, with the USRN field embossed onto its own top surface as a raised
ridge line. It's a real file sitting next to the HTML the moment the page
was generated (a static page can't run Python on click), so the button
only appears when one was actually written - pass `--no-stl` to skip both.

**Two deliberate distortions, both reported rather than hidden - one
picked for you, one you asked about directly:**

- **Physical scale** - the AOI is fitted to a `--print-footprint-mm`
  square (150mm by default, comfortable on most desktop printer beds).
  Unavoidable and not really a "distortion" so much as just what scale
  means.
- **Vertical exaggeration, 2.5x by default (`--vertical-exaggeration`).**
  This one's a real judgement call, not a computed optimum. Durham's real
  relief here is tens of metres over a couple of kilometres - at true
  scale, compressed onto a 150mm block, it would be close to flat, both
  to the eye and to a finger. 2.5x is enough to make it genuinely tactile
  without turning a gentle valley into a canyon or misrepresenting how
  steep anything actually is - a real road bridging a real dip should
  still read as *plausible*, not cartoonish. It sits inside the range
  terrain-model hobbyists typically use for lowland relief (roughly
  1.5x-3x); push much past 3x on terrain this gentle and the model starts
  actively lying about slope. Both this factor and the physical scale it
  was applied at are printed on the model's own page (hover the button)
  and to the console on every run - a "realistic" print that quietly
  wasn't one is exactly the kind of silent distortion this whole example
  exists to call out, so the print doesn't get a pass the drape itself
  doesn't.

**The road ridge is baked into the same surface, not a separate part -
which is also why the terrain has to print whole to support it.** Each
grid cell a road passes through (found by re-densifying the USRN path at
half the terrain grid's own resolution, so no cell along the way is
skipped) is raised by a fixed **1.2mm** (`--ridge-height-mm`) *above
whatever the terrain's own real sample at that cell already is* - a
legibility mark, not a piece of elevation data, so it deliberately isn't
multiplied by the vertical exaggeration too. Because it's just a taller
value at certain cells of the one heightmap that becomes the top surface,
walls, and base of a single mesh, there's no separate road part to
assemble and no support structure to design around: the terrain supports
the road by construction, the same way the whole point of this example is
that the drape is welded to the ground it was sampled from.

The ridge's *width* isn't a separate parameter - it's always exactly one
grid cell, so it comes out chunkier on the 50m OS Terrain 50 default and
finer on a 1m LIDAR pull (`--terrain lidar`), tied honestly to whatever
resolution the terrain itself actually is rather than asserting a
realistic road width the grid can't back up.

**The print was never exposed to the interactive view's own "road renders
under a blocky ghost cell" artifact** (see `render.py`'s module docstring
for that fix), because the two builds are structurally different, not
because the same fix was reapplied here. The interactive ghost mesh
strides for a large AOI (fewer, bigger `GridCellLayer` blocks) and draws
the road as a *separate* `PathLayer` sampled at full bilinear resolution -
two independently-sampled things that can disagree. `export_stl.py` never
strides (always the full-resolution grid) and never draws a separate road
object at all - the ridge is just a taller value baked into certain cells
of the *one* mesh before it's triangulated, so there's nothing else for it
to visually disagree with.

**Refuses instead of guessing across a hole.** If the requested AOI
contains any real EA/OS no-data cell, `export_stl.py` raises rather than
filling it with an invented height - the model just doesn't get built for
that AOI (the HTML still does, without the button) - same "never infer"
rule as everywhere else here, extended to a physical object.

```bash
# A closer, higher-resolution print of one feature, not the whole city -
# 1m LIDAR gives a genuinely finer ridge and terrain detail than the 50m
# default, at the cost of a much bigger mesh (hundreds of thousands of
# triangles over even a 300m square - keep LIDAR prints to a close-up).
python -m examples.nsg_terrain_drape.generate_drape --terrain lidar \
    --bbox 427000 542000 427300 542300 --vertical-exaggeration 3
```

## The Norway foil - investigated, not shipped this pass

The design brief wanted a Norwegian NVDB street's real, surveyed Z (which
departs from the ground at a flyover or tunnel - a genuine measurement, not
a guess) rendered next to the UK's derived drape as a single, visual
stated-vs-derived argument. This was investigated far enough to have a real
starting point for whoever picks it up next, then deliberately parked
rather than blocking the render on it (this example is aesthetic-first; the
foil is a bonus, and a stalled render beats a rushed foil):

- NVDB's real bridge/tunnel object types are confirmed and identified:
  `60` ("Bru"), `67`/`447`/`503`/`581` (various "Tunnelløp"/"Tunnel"
  variants) - fetchable via
  `https://nvdbapiles.atlas.vegvesen.no/vegobjekter/api/v4/vegobjekter/60`
  (no credentials needed, same as the rest of `streetworks.nvdb`).
- A real bridge was pulled (`"Ise"`, object id 272296863, road-link
  sequence 971677) and its geometry genuinely carries real Z (SRID 5973,
  `LINESTRING Z`, 34-80m across the sequence) - but the sequence spans 43
  sub-links across what turns out to be a wider road corridor, not one
  isolated span, so the raw pull doesn't yet isolate a single clean
  "elevated over a dip" profile without further real extraction work
  (picking out the one sub-link that *is* the bridge deck, and a real
  terrain source for Norway to show what it's rising above - neither
  attempted here).
- Whoever picks this up next has a real starting point, not a blank page:
  the object types, one real bridge id, and the exact reason a naive pull
  doesn't immediately give a clean picture.

## The failure cases (try `--terrain lidar` on these)

Bare-earth DTM ≠ carriageway height, in three predictable places - feature
these deliberately if you're picking bboxes to demo:

- **Flyover / grade-separated junction** - the DTM samples the ground
  *under* the structure, so the drape plunges to the valley floor beneath
  it. The A1(M) junctions around Durham are real candidates, not verified
  down to the metre in this build - pick a slip road that bridges over and
  watch its drape collapse.
- **Tunnel** - the DTM samples the hillside *above* the bore, so the drape
  sits metres higher than any real road could. The A19 Tyne Tunnel, just
  north of the default AOI, is the clean concrete case.
- **Embankment / cutting** - OS Terrain 50's 50m posts smooth these away;
  the 1m LIDAR catches them sharply. Run the same bbox with both
  `--terrain os50` and `--terrain lidar` for a direct "resolution changes
  the lie" comparison.

## Guardrails (non-negotiable - see `terrain.py`'s own docstring for the
full module-boundary note this was built against)

- **Derived Z lives only in this example's own render geometry.**
  `streetworks.common.models.Coordinate` stays XY with stated provenance,
  untouched, everywhere else in this SDK. Nothing here writes a sampled Z
  back into it.
- **DTM, never DSM, for the drape** - `terrain.py`'s reader is
  surface-model-agnostic on principle (a future line-of-sight consumer
  would want the DSM instead - buildings and vegetation block sight, bare
  earth doesn't), but this example always asks for bare earth
  (`EA_LIDAR_DTM_1M`, not `EA_LIDAR_DSM_1M`).
- **No reprojection anywhere** - not between data sources (all real
  27700), and not for display (pydeck's `OrbitView` renders the real
  eastings/northings/metres directly, no WGS84 conversion).
- **Gaps are dropped, never inferred across.** See `drape.py`'s own
  docstring.
- **Every distortion the 3D print applies (physical scale, vertical
  exaggeration) is reported back, on the page and to the console - never
  a "realistic" model that quietly wasn't one.** See "3D-printing the
  AOI" above and `export_stl.py`'s own docstring.
- **Datum labelling travels with the data, never assumed equal across
  providers even when it turns out to agree** - OS Terrain 50 and EA's
  LIDAR Composite both real-state ODN (Ordnance Datum Newlyn), confirmed
  independently per source (see `terrain.py`), not assumed from one
  another or from both being British. Norway's own NN2000 (see
  `streetworks/nvdb/models.py`) is a different real datum again - the
  vertical axis gets the same "state honestly, never assume" discipline
  this SDK already applies horizontally.

## Module-boundary note

`terrain.py` is written to module standard (see its own docstring) on the
chance it's promoted out of `examples/` into a public `streetworks`
package one day - the "is this SDK street-works-only, or does it grow into
a general highways-geospatial client?" question is real and not yet
decided. No public API surface is being declared by building it here.
If it is promoted, two lines don't move: the terrain layer serves **stated
elevation only**, never inference; and drape/viewshed/line-of-sight stay
**derived consumers** on the example/analysis side, never folded into the
terrain client itself. `drape.py` and `export_stl.py` in this package are
two such consumers, kept deliberately separate from `terrain.py` (and from
each other - the print makes its own distorting choices neither the drape
nor the terrain layer needs to know about) even though all three currently
live in the same example.

## A real, acknowledged limitation

`streetworks.openusrn.UsrnDatabase` has no spatial index (it's a plain
GeoPackage/SQLite read - see its own docstring) - finding the USRNs inside
one AOI means scanning all ~1.4 million GB-wide streets once per run. Fine
for a one-off render (a couple of minutes, dominated by this scan rather
than any network call), not meant for repeated or interactive querying. A
real spatial index (e.g. a bbox pre-filter using the GeoPackage's own
R-tree, if the download ships one) would be the fix, and hasn't been
built here.

## Dependencies

This SDK's own `streetworks` package, plus **pydeck** (`pip install
pydeck`) - this example's own dependency, not a project one, matching
`examples/roadworks_world_map.py`'s own precedent for plotly. Everything
else (`terrain.py`'s GeoTIFF/ASCII Grid reader, WKT parsing) is standard
library only, on purpose - see `terrain.py`'s own docstring.

## Licence / attribution

OS Open USRN, OS Terrain 50, and the EA LIDAR Composite DTM are all Open
Government Licence v3.0. NVDB (referenced in the Norway-foil investigation
above, not currently rendered) is NLOD 1.0 - see
`streetworks/nvdb/__init__.py`'s own docstring for why that's a different
licence from Kartverket's Elveg, despite the same underlying network.
Live-fetch needs no vendoring and no attribution burden on the framework;
if you cache tiles into the repo for reproducibility, that's vendored real
data bytes and OGL attribution applies (same exception as everywhere else
in this SDK).
