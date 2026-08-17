# Changelog

## [Unreleased]

### Added — Digiroad (Finland), this SDK's first Finnish streets provider (2026-08-17)

`streetworks.digiroad.DigiroadClient` / `streetworks.common
.from_digiroad_street` - Finland's real national road/street database,
over Väylävirasto's own genuinely keyless WFS.

```python
from streetworks.digiroad import DigiroadClient
from streetworks.common import from_digiroad_street

helsinki_bbox = (24.90, 60.14, 25.00, 60.22)
with DigiroadClient() as digiroad:
    streets = [from_digiroad_street(f) for f in digiroad.iter_streets(bbox=helsinki_bbox)]
```

- **Chose a different agency after the obvious one required an account**:
  Maanmittauslaitos' own Maastotietokanta genuinely needs a self-service
  API key (confirmed live via a real `401`) - per this project's own
  access-boundary rules, not registered on the project's behalf.
  Väylävirasto's separate WFS deployment is genuinely keyless instead,
  and turned out to carry Digiroad - Finland's real national road/street
  database - not just the state road-asset-management layers that
  dominate the same 328-layer deployment.
- **A real cartographic-view duplication caught before picking a
  layer** - three real layer names all resolve to the identical
  underlying table (confirmed via `DescribeFeatureType` and
  `resultType=hits`), the same trap TIGERweb's own layers 0-9 were.
- **Real bilingual names** (Finnish/Swedish, Finland's genuine official
  convention) carried as two `Name` objects via `Name.language`, never
  merged - real examples confirmed live: `"Mannerheimintie"`/
  `"Mannerheimvägen"` (Helsinki's most famous street).
- **Real 3D geometry** - `Z` genuinely present on every vertex checked
  and preserved through reprojection, never defaulted to zero.
- **3,363,654 real national features** - TIGERweb/NRN-scale, bbox-
  queryable, with a real ~5,000-feature-per-request cap the client
  pages past automatically.
- **Licence**: Creative Commons Attribution 4.0 International,
  confirmed live from the dataset's own `avoindata.fi` catalogue entry.

### Investigated — Bulgaria streets gazetteer, ruled out on a provenance judgement call (2026-08-17)

Not a technical blocker - a deliberate scope decision. The national
cadastre agency's real ArcGIS/WFS deployment has no street/road layer
at all (its "Geo_Names" layer is real but is rivers, not streets - the
same "general place-names register, not streets" trap Gibraltar's own
`GN_GeographicalNames` was); the national open-data portal genuinely
blocks automated access (a real 403, not routed around). Sofia
Municipality's own open-data platform does have a real, live, keyless,
comprehensive streets dataset (46,017 features, 51.9% named) - but it's
an explicit republish of OpenStreetMap data (`provider: "ОСМ"`), not an
independent government survey, and the project owner chose not to make
this SDK's first exception to that convention. Two smaller, genuinely
non-OSM alternatives exist but are too narrow (a 618-row single-area
survey, a 216-row cultural-heritage subset). See
`docs/providers/pending.md`.

### Added — Landmælingar Íslands (IS 50V), this SDK's first Icelandic streets provider (2026-08-17)

`streetworks.lmi.LmiStreetsClient` / `streetworks.common.from_lmi_street`
- a real sibling to Iceland's existing roadworks coverage
(IRCA/Vegagerðin): both this layer's own `gagnaeigandi` field and
IRCA's own feed point to the same real agency, Vegagerðin, confirmed
live not assumed.

```python
from streetworks.lmi import LmiStreetsClient
from streetworks.common import from_lmi_street

with LmiStreetsClient() as lmi:
    streets = [from_lmi_street(f) for f in lmi.iter_streets()]
```

- **58,266 real national road-segment features**, found by walking the
  service's own full `GetCapabilities` (473 real layers) rather than
  assuming a promising layer name. A separate INSPIRE Transport
  Networks layer on the same deployment carries no name field at all -
  the same outcome Germany's BKG and Gibraltar's own INSPIRE layer had
  - so this native `IS_50V:samgongur_linur` layer was built instead.
- **A real self-caught measurement error, corrected before shipping**:
  a first `nafnfitju IS NOT NULL` check suggested 99.98% real name
  coverage. Checking against the complete real dataset (not a sample)
  found the true figure is 84.0% (48,959/58,266) - most unnamed rows
  store a literal single-space string, not a database `NULL`, which
  the naive filter missed. Both are treated as no name, never
  fabricated.
- Real coverage spans the full density range: `"Gnúpverjavegur"` (a
  rural connecting road, with a real Vegagerðin route number
  alongside its name) and `"Laugavegur"` (Reykjavík's own main
  shopping street, 63 real segments, genuinely no route number - urban
  streets are named, not numbered, unlike Ireland's own rural Monaghan
  roads).
- Genuinely multi-part `MultiLineString` geometry on a real minority of
  records - `Coordinate.parts` always used, the same discipline
  `from_gibraltar`/`from_tigerweb` already established.
- **Licence**: Creative Commons Attribution 4.0 International,
  confirmed live directly from Landmælingar Íslands' own licence page.

### Added — `AGENTS.md` and `llms.txt` (2026-08-16)

`AGENTS.md` (repo root): a load-bearing quick-reference for coding
agents - the verify-live discipline, never-fabricate/never-silently-
reproject rules, access boundaries, licensing judgement calls, and the
"adding a new provider" checklist this session followed throughout -
linking out to `docs/contributing/agent-boundaries.md`,
`docs/concepts/data-integrity.md`, `docs/contributing/scaffolds.md` and
`CONTRIBUTING.md` for full detail rather than duplicating it.
`llms.txt` (repo root): a concise, structured project summary and docs
map for external LLMs/crawlers, following the emerging `llms.txt`
convention - discoverability, not contribution guidance.

### Added — Monaghan County Council road network, this SDK's first Irish gazetteer coverage (2026-08-16)

`streetworks.arcgis.monaghan.MonaghanRoadsClient` / `streetworks.common
.from_monaghan_road` - reopens the Ireland streets question from a
different angle after the national-level ruling below: a real,
genuine county-council pilot rather than a national build. Ireland
now moves from "in progress" to "live" in the coverage roster, the
same way Canada/Portugal/Austria did on a real partial build.

```python
from streetworks.arcgis.monaghan import MonaghanRoadsClient
from streetworks.common import from_monaghan_road

with MonaghanRoadsClient() as monaghan:
    segments = [from_monaghan_road(f) for f in monaghan.iter_roads("local")]
```

- **`Segment` only, and deliberately never a fabricated `Street`** -
  real Irish rural roads genuinely have no name (confirmed live, see
  the investigation below); `Road_Name` is Ireland's own official route
  number (`"L-31011-0"`), carried as a real `Identifier`
  (`scheme="road_number"`) rather than misrepresented as a street name.
  `names` is always the empty tuple on every real record this converter
  produces - the same honest "no synthetic streets" discipline
  TIGERweb's and NRN's own converters already established.
- **Three real, distinct road-class services** (National: 27 real
  segments, Regional: 122, Local: 1,612), all on the same hosted
  ArcGIS deployment. `Road_Class` becomes `StreetType.label`;
  `Municipal_District` becomes `administrative_area` where stated
  (checked live: absent on every real `National_Roads` record).
- **Real WGS84 GeoJSON by default** - the service's stated native
  reference is `EPSG:2157` (Irish Transverse Mercator), but a plain
  request with no `outSR` already returns genuine WGS84, the same real
  behaviour TIGERweb's and NRN's own services show.
- **Licence unconfirmed** - no explicit statement found on the real
  ArcGIS Online items checked, the same open-by-design situation
  Jersey's own services have; built on the project owner's explicit
  instruction.
- Ireland's docs moved to their own page,
  [`docs/providers/ireland.md`](docs/providers/ireland.md) (MapRoad's
  existing content relocated verbatim from `europe.md`, no change),
  now that there's a real live provider alongside it.

### Investigated — Ireland streets gazetteer, ruled out on a real structural finding (2026-08-16)

Not a missing-data gap - Ireland's road network outside towns is
genuinely organised by route *number*, not name. Tailte Éireann's own
open-data catalogue (CC BY 4.0) has boundaries and a nameless
1:250,000-scale road layer; TII's live "National Road Network 2024" is
motorways/N-roads only, `Road` field a real route code (`"M7"`). Two
real County Council pilots checked (a real per-authority fan-out, the
same shape Germany's states have) both confirmed the pattern: Donegal's
Road Network has no name field at all (`Road_id="N-13-21"`); Monaghan's
Local_Roads' own `Road_Name` field is itself a route number
(`"L-31011-0"`). No Dublin City Council ArcGIS Online org was found to
check the one place urban street names would most plausibly appear in
the open. See `docs/providers/pending.md`.

### Added — Gibraltar Street Gazetteer, this SDK's first British Overseas Territory coverage (2026-08-16)

`streetworks.gibraltar.GibraltarStreetsClient` / `streetworks.common
.from_gibraltar_street` - found by checking two things flagged
as possibly missed: the Shetland Isles (confirmed already fully covered
by existing `srwr`/`openusrn` national coverage, nothing to build) and
Gibraltar (genuinely new - not built at all before this).

```python
from streetworks.gibraltar import GibraltarStreetsClient
from streetworks.common import from_gibraltar_street

with GibraltarStreetsClient() as gibraltar:
    streets = [from_gibraltar_street(f) for f in gibraltar.iter_streets()]
```

- **Shetland confirmed covered, not a gap** - a real SRWR daily extract's
  own `099` (District) reference records show Shetland Islands Council
  (org code `009010`) reporting into the same single national register
  as every other Scottish authority; OS Open USRN's Scotland coverage is
  equally nationwide. See `docs/providers/uk.md`.
- **Gibraltar's INSPIRE-mandated road layer has no name field at all**
  (the same "geometry with no identity" outcome Germany's BKG WFS had) -
  found instead by walking the Geoportal's *service-wide* WFS
  capabilities rather than just the INSPIRE workspace: `gibgis:roads_lb_vw`,
  a real, live, keyless, named-road layer (277 real streets).
- **`label` is a composed display string, not a single real name** -
  confirmed live across the full layer, not assumed from a small sample:
  `label` and `name` genuinely differ on 21% of records, always
  `"{name} - {collname1}[ - {collname2}]"` (a real English name plus a
  real Llanito/Spanish local name). `from_gibraltar_street` reads
  `name`/`collname1`/`collname2` individually, never `label` itself -
  fusing them would produce an unsearchable compound string.
- **Genuinely multi-part `MultiLineString` geometry on 54% of records** -
  `Coordinate.parts` always used, the same real handling `from_tigerweb`
  already established, never a first-line-only shortcut.
- **A real GeoServer pagination quirk found and worked around**: this
  view-backed layer's `count`+`startIndex` combination fails outright
  without an explicit `sortBy` (`Cannot do natural order without a
  primary key`) - confirmed live, handled by always sorting on
  `inspireId` and checking `numberMatched` rather than trusting a short
  page.
- **Licence**: no single confirmed open document found - built on the
  project owner's explicit instruction, the same basis Jersey shipped
  on, stated honestly rather than overclaimed.
- **Roadworks checked and ruled out, not just unbuilt** - a real
  `gibgis:under_construction` layer exists (23 real features) but its
  schema carries only a geometry field, no attributes at all; genuinely
  unusable as a works feed. See `docs/providers/pending.md`.

### Added — National Road Network (NRN), this SDK's first Canadian streets/gazetteer provider (2026-08-16)

`streetworks.arcgis.nrn.NrnClient` / `streetworks.common.from_nrn` -
Statistics Canada / Natural Resources Canada's real, live, keyless
ArcGIS REST service, found via the same `open.canada.ca` catalogue-entry
route that gave IDEE Transportes its shape for Spain. TIGERweb-scale on
purpose - the user asked for a full national build, not a single-
province pilot.

```python
from streetworks.arcgis.nrn import NrnClient, LAYER_IDS
from streetworks.common import from_nrn

toronto_bbox = (-79.40, 43.64, -79.38, 43.66)
layer = LAYER_IDS["local_roads"]["ON"]
with NrnClient() as nrn:
    segments = [from_nrn(f) for f in nrn.iter_roads(layer, bbox=toronto_bbox)]
```

- **Segment only** - the same TIGERweb/NWB outcome, confirmed live: no
  separate named-street entity exists anywhere in this REST service.
- **65 real, genuinely non-redundant layers** - 5 road-class tiers x 13
  provinces/territories, confirmed live by comparing feature counts
  (Alberta: 2,556/7,700/55,876/443,392/443,593 - five different totals,
  not a cartographic pyramid the way TIGERweb's own layers 0-9 turned
  out to be).
- **A real `"Unknown"` placeholder** - NRN's own stated convention for
  "genuinely no name recorded" - applies to both street names and place
  names (confirmed live on a real 13% of a 644,758-record Ontario
  sample for place names alone); treated as no value at all, never
  carried through literally.
- **`administrative_area` uses the same shared-value-only discipline**
  `from_bdtopo` established for its own real left/right commune split:
  a real Ontario segment's `l_placenam`/`r_placenam` genuinely diverge
  on an actual township boundary - stays `None` rather than an
  arbitrary pick.
- **No genuine per-segment identifier exposed over this REST service**
  (unlike the bulk GeoPackage product's own real `NID` field) -
  `Segment.identifiers` stays empty on every real record.
- **CRS**: stated native NAD83(CSRS) (`wkid 4140`/`4617`), but real
  `f=geojson` output is genuinely WGS84-shaped regardless of `outSR` -
  the same real behaviour TIGERweb's own service exhibits. Licence:
  Open Government Licence - Canada.

### Added — Jersey and Guernsey Street Gazetteers, this SDK's first Channel Islands streets coverage (2026-08-16)

`streetworks.arcgis.jersey.JerseyStreetsClient` / `streetworks.common
.from_jersey_street` and `streetworks.arcgis.guernsey.GuernseyStreetsClient`
/ `streetworks.common.from_guernsey_street` - found by asking "does Jersey
RoadWorkx's own ArcGIS deployment have a streets sibling, and does
Guernsey have the same setup Jersey does?" Both real, live, credential-free.

```python
from streetworks.arcgis.jersey import JerseyStreetsClient
from streetworks.common import from_jersey_street

with JerseyStreetsClient() as jersey:
    streets = [from_jersey_street(f) for f in jersey.iter_streets()]
```

- **Jersey**: a real second service (`JSearch`, not `JSWFeatureService`)
  on the same `roadworks.gov.je` deployment. 2,159 real named streets
  (`FEATURE='Road'`, decodable field, excludes `'Pavement'`). Real
  GB-NSG-style USRNs in a distinct Crown-Dependency block. A genuine
  two-CRS-in-one-record situation confirmed live: the real polygon
  geometry is WGS84, but the real, separately-stated `USRN_XY1`/
  `USRN_XY2` attribute pair stays in native `EPSG:3109`, never
  reprojected - used as `Coordinate.value`/`.points` where stated
  (89.7% of real rows), `GeometryGrade.ABSENT` otherwise, never a
  fabricated centroid (the same discipline `from_paris` established for
  a real polygon-only footprint).
- **Guernsey**: found by checking whether Jersey's real setup has a
  sibling - it does, `roadworks.gov.gg`'s own `GSearch` service. 2,591
  real named streets; no clean type field exists to separate genuine
  street names from other real `ROAD` values sharing the same field
  (e.g. `"CAR PARK"`), so every non-blank one converts. Real USRNs
  include genuine fractional subdivisions (e.g. parent `20194` with
  child polygons `20194.02`/`20194.04`/...), formatted to 2dp to mask
  real float-encoding noise. `CRS: ESRI:102070 "Guernsey_Grid"` (a real
  named Channel Islands local grid, confirmed live via an external
  projection registry) is the layer's *stated* CRS - not its real
  returned geometry, which is WGS84 regardless, the same split Jersey's
  own two services show. No stated point/line field exists at all here
  (unlike Jersey's real `USRN_XY1`/`USRN_XY2`) - every `Street` carries
  `GeometryGrade.ABSENT`, the real polygon preserved in `.raw` only.
- **Isle of Man checked too, genuinely not found open** - the Island's
  real ArcGIS Online organisation (329 items) and its own hosted ArcGIS
  REST deployment were both walked in full; no street/road layer exists
  in either. A real Street Gazetteer product exists but sits behind an
  academic-only (Chest/JISC) licensing scheme, not a public endpoint.
  See `docs/providers/pending.md`.

### Added — `av_route_avoiding_works.py`, a real Newton Aycliffe last-mile routing example (2026-08-16)

A new `examples/` script: plans a pickup -> dropoff route across Newton
Aycliffe (OSRM's public demo server, real OpenStreetMap roads), checks
it against Street Manager's real, live, in-progress works, and reroutes
around any that sit within `--threshold-m` (default 40m) of the route -
or says so honestly when no detour clears them, rather than pretending
success. Default pickup/dropoff are real, Nominatim-geocoded Newton
Aycliffe streets (Emerson Way, Van Mildert Road); real production
Street Manager data for that pair currently has one real conflict, on
Greville Way, which the script successfully routes around via Central
Avenue. `--map [PATH]` writes a Plotly/CartoDB map matching the style
of `compare_active_works.py`/`collaboration_finder.py`.

- **Newton Aycliffe chosen over Durham City's historic core, based on
  live testing, not assumed.** Durham station -> Market Place (the
  original candidate pickup/dropoff pair) has exactly one real
  conflict, on Leazes Road - and no detour, tried at any of many
  offsets, ever clears it. That's a genuine chokepoint on Durham's
  river-loop peninsula (too few road crossings), not a bug - confirmed
  by finding a real, successful reroute elsewhere (Newton Hall's
  grid-street estate) under the same code path. Newton Aycliffe, a
  planned town with a proper street grid, was picked as the shipped
  default specifically because it offers genuine parallel-street
  alternatives a detour can use.
- **A real bug found and fixed via live testing, not assumed correct
  from code review: a single fixed 180m detour offset was too small.**
  OSRM's own waypoint-snapping behaviour means a modest offset can
  still route back onto the same road the conflict sits on - confirmed
  live in Newton Hall, where a 180m offset left the route passing
  exactly back through the conflict point (0.0m clearance) while 200m
  cleared it via a genuinely different parallel street. Fixed by trying
  a short escalating list of offsets (150/250/400/600/900m), both
  sides, smallest first - still one bounded heuristic, not a search
  algorithm, just one that actually succeeds when a real detour exists.


`streetworks.anncsu` / `streetworks.common.from_anncsu` - Italy's real
national street-name register, jointly run by Agenzia delle Entrate (the
tax/cadastre agency) and ISTAT since DPCM 12 May 2016. Unlike Germany's
BKG and Portugal's IP/DGT (both investigated and ruled out this same
day), this one is genuinely buildable.

```python
from streetworks.anncsu import AnncsuClient
from streetworks.common import from_anncsu

with AnncsuClient() as anncsu:
    streets = [from_anncsu(o) for o in anncsu.iter_odonimi()]
```

- **1,219,990 real street names, confirmed live, credential-free.**
  Real entries verified live: "Arco degli Acetari," "Bastioni di Porta
  Nuova." Updated 2026-08-03 at investigation time.
- **Two real access routes exist; the bulk one is used deliberately.**
  A real, live, keyless point-query API also exists, but only supports
  lookup by municipality code plus a (partial) name match - enumerating
  all ~7,900 real Italian municipalities one at a time would be
  impractical for a full national pull. Uses the real national bulk
  download instead (`getds.php?STRAD_ITA`) - a genuine bare-flag query
  parameter, confirmed live: a plain `?STRAD_ITA=` (what a normal params
  dict would send) is rejected by the server with a real structured
  error, not silently accepted.
- **No geometry anywhere in this resource - a real, defining
  characteristic, not a gap in this build.** `odonimi` is a pure name
  registry: real street name, real national/municipal identifiers, a
  real stated count of address points on that street - nothing spatial.
  Every canonical `Street` carries `GeometryGrade.ABSENT`, the same
  documented "real NULL-geometry rows" state OS Open USRN already
  establishes, never synthesised.
- **Encoding confirmed by decoding real accented content, not
  assumed.** The raw byte range first suggested Windows-1252, but that
  encoding actually fails to decode a real byte in this file - UTF-8
  decodes cleanly and produces genuine text (confirmed live: "LOCALITÀ
  CASTELLUCCIO," a real value, only decodes correctly as UTF-8).
- **Two real, independently-stated municipality identifiers, both
  kept** - the traditional "Belfiore" cadastral/tax code and ISTAT's own
  numeric municipality code, related but not interchangeable.
- No credentials. Licence: **CC BY 4.0**, confirmed live from the
  dataset's own catalogue metadata on dati.gov.it. Registry entry
  (`anncsu`, `kind=streets`), new tests against a real trimmed live-pull
  ZIP fixture, and a `scripts/smoke_test.py` check.
- **The address/civic-number side of the same registry (`accessi`) was
  deliberately scoped out, not blocked** - real, live, CC BY 4.0, but
  only ~20% coordinate coverage confirmed live in a real regional
  sample. Documented in `docs/providers/pending.md`, not silently
  dropped.

### Changed — Portugal streets gazetteer investigated and ruled out at the national level, matching Germany's outcome (2026-08-16)

Followed up an older, partial finding in `docs/nap-survey.md` that had
never made it into `docs/providers/pending.md`. Full findings now in
`docs/portugal-streets-investigation.md`.

- **Infraestruturas de Portugal (IP)'s promoted national road-network
  distribution is shapefile-only, confirmed live.** DGT's own INSPIRE
  ATOM feed for the national 1:200,000 Transport Networks dataset
  contains the spec's optional WFS-link element still commented out,
  with the literal unfilled template placeholder
  (`href="http://xyz.org/wfs?..."`) - a decisive confirmation no
  direct-access query service was ever wired up, not an oversight in
  the search. The same feed states a real licence discrepancy against
  `dados.gov.pt`'s `cc-by` label for the nominally same data
  (`<rights>Sujeito a licenciamento</rights>`), not reconciled.
- **A real, live, keyless, queryable ArcGIS MapServer exists anyway -
  found by tracing IP's own public map viewer**, the same technique that
  found DfI Roads' real backend. Its full real field list
  (`roadnumber`/`jurisdicao`/`gestao`/`road1`) carries no name field at
  all; real sample values (`roadnumber="A1"`/`road1="IC1"`) are
  route-classification codes, not street names - the same "real
  geometry, no named-street identity" outcome Germany's BKG landed on,
  confirmed by content, not assumed from the dataset's coarse scale.
- IMT's national NAP remains exactly as previously found - an Angular
  SPA with no discoverable backend, genuinely unresolved, not
  ruled out. Municipal fallback (Porto and others) remains real,
  open-ended, unchecked work - the same shape as Germany's own state
  fan-out.

### Changed — Dedicated docs sections for four Credentials-wanted scaffolds that only had table/blockquote mentions (2026-08-16)

`streetworks.datex2.trafikverket`, `streetworks.datex2.vejdirektoratet`,
`streetworks.datex2.austria` (ASFINAG), and `streetworks.stockholm` were
each already registered and listed in `docs/providers/index.md`'s
Credentials-wanted table, but had no dedicated `##` section of their
own anywhere in `docs/providers/` - only a blockquote cross-reference in
their country's page. Added full sections (`docs/providers/europe.md`
for Trafikverket and Stockholm, matching the existing Ireland/Greece
precedent of keeping scaffold-only countries in `europe.md` rather than
a dedicated file; `docs/providers/denmark.md` for Vejdirektoratet;
`docs/providers/austria.md` for ASFINAG), each condensed from the real
module docstring's own findings - no new investigation, just giving
existing evidence a proper home. Also caught two more stray unexplained
"brief" references in `docs/providers/denmark.md` that an earlier
cleanup pass missed.

### Added — DfI Roads Highway Network centreline, the geometry counterpart to OSNI Streetnames (2026-08-16)

`streetworks.dfi_roads` / `streetworks.common.from_dfi_roads` - DfI
(Department for Infrastructure) Roads' own real maintained-road network
centreline for Northern Ireland - real line geometry, sitting beside
OSNI Streetnames' name+point gazetteer above.

```python
from streetworks.dfi_roads import DfiRoadsClient
from streetworks.common import from_dfi_roads

with DfiRoadsClient() as dfi:
    segments = [from_dfi_roads(s) for s in dfi.iter_road_sections()]  # adopted only
```

- **The promoted "open data" downloads (CSV/XML via
  `dfi.highway-iams.uk`, OGL v3.0) are genuinely attribute-only - checked
  live, not assumed.** Both carry the same 8 columns and zero geometry,
  despite the dataset being titled a "centreline" product. The real
  geometry lives behind the linked ArcGIS Experience Builder public
  viewer instead - found by tracing that app's own item -> web map ->
  operational layer's `FeatureServer` URL, the same technique that found
  Roma's/Lisboa's/Oslo's real backends.
- **Not built on this SDK's shared `streetworks.arcgis` client - a
  real, checked reason, not a style choice.** That client always
  requests `f=geojson` first and only falls back to Esri's native
  `f=json` format when the geojson response fails to parse as a genuine
  `FeatureCollection`. This service's `f=geojson` output *is* a genuine,
  valid `FeatureCollection` - it just silently reprojects to WGS84
  (confirmed live). So the shared client's fallback would never trigger
  here; this client requests `f=json` directly instead.
- **CRS confirmed live, directly from this service's own
  `spatialReference`** - `{"wkid": 29900, "latestWkid": 29902}`. `29900`
  (TM65 / Irish National Grid) is EPSG-deprecated in favour of `29902`
  (TM65 / Irish Grid) - a genuine, direct live read, which is what
  prompted correcting OSNI Streetnames' own inferred CRS label to match
  (see below).
- **Pagination confirmed live to genuinely advance, not assumed from
  stated capability** - `resultOffset` checked two pages deep (`[1, 2,
  3]` then `[4, 5, 6]`), not Jersey's own silently-repeating first-page
  trap. `exceededTransferLimit` correctly signals more pages remain
  (`maxRecordCount` is 2,000 real records); raises
  `TruncatedResultError` rather than silently returning a partial result
  if a page is ever empty while still signalling more data.
- **A real, genuinely two-valued `ADOPTION_S` field, confirmed live** -
  `Adopted` (70,522 of 71,596 real sections) and `Unadopted` (1,074).
  `iter_road_sections()` defaults to adopted-only, with an escape hatch
  for the unfiltered set.
- **Sections, not streets - maps to `Segment`, never a synthesised
  `Street`.** DfI publishes road sections with a repeated name attribute
  (multiple distinct sections all named e.g. "BELFAST RD"), not a
  separate named-street entity - the second real source (after BD TOPO)
  to populate `Segment.names`. A genuine multi-path section exists
  (confirmed live, 2 of 10,000 sampled) and maps to `Coordinate.parts`,
  never silently collapsed to its first path.
- No USRN or USRN-shaped field exists anywhere in this schema -
  confirmed by the full real field list, unlike OSNI Streetnames' own
  surprise. No credentials. Licence: Open Government Licence v3.0.
  Registry entry (`dfi_roads`, `kind=streets`), new tests against a real
  trimmed live-pull JSON fixture, and a `scripts/smoke_test.py` check.

### Fixed — OSNI Streetnames' inferred CRS corrected from EPSG:29903 to EPSG:29902 (2026-08-16)

While investigating DfI Roads (above), that service's own
`spatialReference` gave a real, direct live read for the same Irish Grid
coordinate family OSNI Streetnames uses - `EPSG:29902` (TM65 / Irish
Grid), not the `EPSG:29903` (TM75 / Irish Grid) originally inferred from
coordinate plausibility alone, since OSNI's own endpoint (which would
state this directly) is still down. `29900` (TM65 / Irish National Grid,
DfI's own stated `wkid`) is EPSG-deprecated in favour of `29902`,
confirmed via the EPSG registry, not assumed - `29903` is a real,
formally distinct code, not the better-evidenced one here. Updated
`streetworks.osni`'s CRS label, docstring, registry `scope_note`, docs,
and tests to match - still not a direct live read of OSNI's own CRS,
stated honestly as corrected-by-analogy, not confirmed.

### Added — OSNI Streetnames, this SDK's first Northern Ireland gazetteer (2026-08-16)

`streetworks.osni` / `streetworks.common.from_osni` - Ordnance Survey
Northern Ireland's "Open Data - Gazetteer - Streetnames": a street name
plus one representative point, for every real street in Northern
Ireland. Jurisdiction-distinct, the same treatment Jersey and Scotland
already get - never folded under a generic UK territory.

```python
from streetworks.osni import OsniStreetnamesClient
from streetworks.common import from_osni

with OsniStreetnamesClient() as osni:
    streets = [from_osni(s) for s in osni.iter_streetnames()]
```

- **Not built the way this was originally scoped - the documented
  ArcGIS REST MapServer endpoint is genuinely down, not a stale URL.**
  The whole `services.spatialni.gov.uk` domain redirects every request
  (`GetCapabilities`, a plain root probe, everything tried) to
  `holdingpage.nics.gov.uk`, a Northern Ireland Civil Service holding
  page that itself doesn't respond - confirmed systemic, not one broken
  path. Built instead against a real bulk-download route (CSV/SHP/KML/
  GeoJSON via OpenDataNI), confirmed live end-to-end - the download URL
  302s to a signed, time-limited Cloudflare R2 URL, followed rather than
  hardcoded.
- **A real, load-bearing CRS disagreement within the one file, found and
  resolved, not assumed.** The GeoJSON's own `geometry` is reprojected
  to WGS84 by this download route, but every real feature also carries
  separate `X_Coord`/`Y_Coord` properties, real Irish Grid values, not
  WGS84. Uses `X_Coord`/`Y_Coord`, never the reprojected `geometry` -
  labelled **`EPSG:29902` (TM65 / Irish Grid)**, corrected from an
  initial `EPSG:29903` guess once a directly comparable NI government
  service (DfI Roads' Highway Network centreline, checked the same
  week) confirmed `EPSG:29902` live for the same coordinate family -
  `29903` is a real, formally distinct code, not the better-evidenced
  one here. Still not a direct live read of this dataset's own CRS,
  since the endpoint that would state it explicitly is the same one
  that's down.
- **A real, live-confirmed `USRN` field, genuinely surprising - kept,
  but scoped honestly, not assumed to match the initial framing.**
  Every one of 25,643 real features carries a populated, unique `USRN`
  value. Northern Ireland is not part of GB's national USRN/NSG scheme,
  so this is not presented as a cross-referencing national identifier -
  it's OSNI's own field, promoted as `Identifier(scheme="usrn",
  scope="OSNI")` rather than silently dropped or conflated with the GB
  scheme.
- **Graded honestly as a name+point gazetteer, not a street-geometry or
  address register** - one name plus one point, no ASD-style richness,
  no address points; `Street.segment_refs` stays empty. 7 of 25,643 real
  `STREETNAME` values are road numbers (`A0002`, `M2`, `M3`, `M5`,
  `M12`, `M22`) rather than street names - genuine content, kept as-is.
- No credentials. Licence: Open Government Licence v3.0. Registry entry
  (`osni`, `kind=streets`), new tests against a real trimmed live-pull
  GeoJSON fixture, and a `scripts/smoke_test.py` check.

### Added — IDEE Transportes (Spain national road network), this SDK's first Spanish `streets` gazetteer (2026-08-15)

`streetworks.idee` / `streetworks.common.from_idee` - Spain's national
road-transport network, published by IGN (Instituto Geográfico Nacional)
over IDEE's INSPIRE WFS. A different agency and data class from this
SDK's existing Spanish roadworks coverage (DGT, Consell de Mallorca,
SCT) - not a duplicate.

```python
from streetworks.idee import IdeeTransportesClient
from streetworks.common import from_idee

with IdeeTransportesClient() as idee:
    streets = [from_idee(road) for road in idee.iter_roads()]
```

- **Built directly from a prior, dedicated investigation
  (`docs/inspire-gml-investigation.md`) that had found the real shape
  but never shipped it - re-verified live before writing any new code,
  and every finding still held.** The real, decisive problem: `RoadLink`
  (the feature type carrying geometry) states no name at all - confirmed
  at the schema level (`RoadLinkType` extends the shared base type with
  an empty `<sequence/>`) and live (the one schema-legal inline name
  field is absent on every real `RoadLink` sampled). Name, road codes,
  and the list of constituent `RoadLink`s all live one hop up, on
  `Road`.
- **`RESOLVE` doesn't work, confirmed dead both ways, re-verified.**
  Neither no resolve parameter nor `RESOLVE=local` (matching the
  service's own declared `ResolveLocalScope=*`) inlines the referenced
  feature - both leave a bare `xlink:href`. So the client follows the
  href's own URL fragment (the real `gml:id` after `#`) directly rather
  than asking for resolve.
- **WFS 2.0's `RESOURCEID` genuinely accepts a same-type batch -
  re-confirmed live.** One `GetFeature&RESOURCEID=id1,id2,...` returns
  every requested `RoadLink`, geometry included, in one round trip. A
  mixed `RoadLink`+`RoadNode` batch was tried live and returned a real
  `HTTP 500`, so same-type batching only. Real shape per page of
  `Road`s: one paged `GetFeature` for `Road` (following the server's own
  stated `next` link, never computed `STARTINDEX` math), then one
  batched `RESOURCEID` call covering every distinct `RoadLink` id that
  page's `Road`s reference - two requests total, not one per `Road`.
- **A broken cross-reference is a confirmed, real, non-fatal case, not
  assumed impossible.** The original investigation found 1 of 3 real
  hrefs it followed returned a genuine
  `403 OperationProcessingFailed: feature not found`. An unresolved
  `net:link` is skipped and counted on `Road.unresolved_links`, never
  raised - `Road.geometry` is `None` only when every real link on that
  Road failed to resolve.
- **Geometry aggregation reuses the same multi-line shape DataVIA's
  `StreetLines` already established** - a `Road` genuinely spans several
  `RoadLink`s (up to 40 seen live in this build's own sampling), each
  its own real `LineString`; one part per successfully-resolved
  `RoadLink` goes into `Coordinate.parts`, in the `Road`'s own stated
  order. No `Segment` is emitted per `RoadLink` - a real classification
  layer (`FunctionalRoadClass`/`FormOfWay`/`NumberOfLanes`) exists one
  hop further but would mean per-attribute-type round trips beyond this
  bounded two-hop shape, for data this model's three use cases don't
  need.
- **CRS confirmed live: `EPSG:4258` (ETRS89), genuine lat/lon axis
  order** - every real `srsName` is the OGC "http URI" form; a real
  vertex `41.613948 2.291140` places the road in Barcelona, not the
  Mediterranean, confirming no swap is needed. No credentials. Licence
  CC BY 4.0.
- **Coverage confirmed live to include the Balearic Islands (Mallorca) -
  but the service's own declared bounding box does not.**
  `GetCapabilities` states an `ows:WGS84BoundingBox` reaching only to
  `3.20°E`, which would exclude part of Mallorca - a real spatial query
  (`fes:BBOX` against `RoadLink`, since `Road` has no geometry property
  to filter on) returned real features at `3.24-3.26°E`, genuinely east
  of the stated box. The capabilities bounding box understates real
  coverage; only a live query confirms what's actually in scope. Plain
  KVP `BBOX=` filtering timed out repeatedly and was abandoned - a
  proper `fes:Filter` POST request is what works. A different data class
  from the existing Consell de Mallorca roadworks provider covering the
  same island - no dedup conflict.
- **Spain's separate INSPIRE Addresses service (Catastro) was
  investigated the same day and deliberately not built alongside this.**
  Its documented WFS endpoint no longer responds to any request variant
  tried; a real ATOM bulk-download route is confirmed live instead. More
  significantly, Catastro's own confirmed licence explicitly prohibits
  redistributing the *original* data over the internet in unmodified
  form, conflicting with this SDK's usual real-fixture test convention -
  genuinely unresolved, not silently dropped, see
  `docs/providers/pending.md`.
- Registry entry (`idee`, `kind=streets`), new tests against real
  trimmed live-pull XML fixtures (roads, a paginated page, and a batched
  RoadLink response) plus one synthetic fixture for the non-reproducible
  broken-cross-reference case, and a `scripts/smoke_test.py` check.

### Added — NUAR (National Underground Asset Register), a testing-only reference model (2026-08-15)

`streetworks.nuar` - not a live provider, and not registered as one:
there is no NUAR consumption API yet to connect to. A secure Sandbox
opened 2026-08-07 (synthetic data) to test access routes, including a
future consumption API, but its endpoints, auth and wire format are
unpublished - that's the one real blocker. The *data model*, however, is
already public: the NUAR Harmonised Data Model
(`github.com/national-underground-asset-register/nuar-datamodel`, OGL
v3.0, a UK profile of the approved OGC MUDDI standard) ships XMI + PostGIS
DDL encodings with geometries defaulting to EPSG:27700 (BNG).

- **`UndergroundAsset`** - a native model (no `streetworks.common`
  converter, the same discipline `streetworks.kartverket` uses), derived
  from the published DDL column names, not guessed. First non-roadworks,
  non-gazetteer entity in this SDK - buried utility assets (pipes,
  cables, ducts, chambers), never coerced into `Works`/`WorksSite`.
- Depth and positional-quality fields are preserved as stated `Measure`s
  with their own units, never defaulted - a fabricated zero depth for a
  buried asset would be a safety lie, not a harmless default.
- **Geometry is deliberately left to the caller.** The published schema
  fixes the attributes but not how a future API will encode geometry on
  the wire - `underground_asset_from_nhdm_row` accepts a ready-built
  `Coordinate` and never parses geometry itself.
- **Not registered, not queryable, not counted as coverage.**
  `NUAR_CONNECTOR_LIVE` is `False`; importing `streetworks.nuar` warns;
  `docs/providers/index.md`'s roadworks matrix is untouched. Added to
  `docs/providers/pending.md` instead, and to `tests/test_registry.py`'s
  non-provider-module allowlist, since there is genuinely nothing to
  query yet - only a shape ready for when the sandbox transport lands.
- Even once a connector exists, NUAR *data* stays bring-your-own-
  credentials only (legally enforceable access agreements) - never
  bundled, unlike the freely-reusable OGL-licensed schema itself.
- New `tests/test_nuar_model.py` (mocked, no network - there is no
  endpoint).

## [0.9.0] - 2026-08-15

### Changed — Documentation jargon cleanup, plus a new Common Model concepts page (2026-08-15)

Every remaining end-user-facing doc still carried the same unexplained
external-reference jargon the registry rewrite (below) had already been
flagged for - internal investigation-document phrasing readers had never
seen, and couldn't resolve. Removed from `docs/providers/*.md`,
`docs/concepts/*.md`, `docs/examples.md`, and `docs/governance/licensing.md` -
every finding now states itself directly ("a real correction", "checked
live", "confirmed") rather than pointing at a document outside the docs
tree.

- **New: `docs/concepts/common-model.md`** - a practical, converter-by-
  converter index of every `from_<provider>` function across both
  canonical families: Works-model converters (`from_streetmanager`,
  `from_wzdx`, `from_paris`, `from_vienna`, ... 34 in total, each with a
  one-line note on its real grouping/dedup/gap behaviour) and gazetteer
  converters (`from_ban`, `from_gnaf_address`, `from_datavia`, ... 11 in
  total, one canonical record in, one out, never a list). Ends with a
  worked cross-provider comparison (Street Manager + Paris, the same
  pattern `compare_active_works.py` runs live) and the standing
  never-deduplicate-across-providers rule.
- Cross-linked from `docs/concepts/data-model.md`'s own type reference and
  `docs/index.md`'s map, alongside the existing architecture/data-model/
  data-integrity/CRS-and-datums/write-path pages.
- No code or behaviour change - documentation only.

### Changed — Registry `scope_note` text rewritten to stand on its own for end users (2026-08-15)

`src/streetworks/registry.py` - roughly 20 `scope_note` entries (Madrid,
ASFINAG, Berlin, Chicago, TfL, DriveBC, Roma, Copenhagen, Oslo, Milano,
Vienna, Stockholm, Roads ACT, NZTA, GNAF, Helsinki) referred an end user
running `sw.providers()` to internal investigation documents they'd never
seen and have no way to open - a real usability gap in output that's
supposed to be self-explanatory. Rewritten so every `scope_note` reads as
a complete, standalone statement of what that provider covers and why it's
scoped that way - no external pointer left unexplained. No functional
change - `providers()`/`get_provider()` behaviour, filtering, and every
other registry field are unchanged.

### Added — TfL (Road Disruption), this SDK's first standalone London roadworks provider (2026-08-15)

`streetworks.tfl` / `streetworks.common.from_tfl` - London already had
roadworks coverage via Street Manager (the England-wide statutory permit
register, gated behind an account), but nothing keyless and London-
specific until now. TfL's Road Disruption feed is the accessible
complement, not a replacement.

```python
from streetworks.tfl import TflClient
from streetworks.common import from_tfl

with TflClient() as tfl:
    disruptions = tfl.iter_roadworks()  # category == "Works" only
works = from_tfl(disruptions)
```

- **Genuinely keyless, confirmed live, better than commonly assumed.**
  `GET https://api.tfl.gov.uk/Road/all/Disruption` returns full real data
  (118 real disruption rows at investigation time) with no `app_key` at
  all - TfL's free 500-requests-a-minute key plan is real but purely an
  optional rate-limit courtesy, the same role Socrata's `X-App-Token`
  plays for `SodaClient`.
- **`category == "Works"` is a real, clean filter** - 116/118 real live
  records; the other 2 (`Hazards`/Fire, `Network delays`/Heavy traffic)
  were checked directly and are genuinely not roadworks.
- **The cleanest CRS situation of any provider in this SDK** - every
  record states its own CRS explicitly (`"crs": {"type": "name",
  "properties": {"name": "EPSG:4326"}}`), genuine WGS84, no inference or
  cross-checking needed. Only `Point` geometry was ever seen live -
  `roadDisruptionLines` exists in the schema but was empty on every real
  record checked, so it isn't handled.
- **A real correction to "TLRN, not all-London."** `corridorIds` (a
  plausible road-number field) is genuinely incomplete - only 51/116
  (44%) of real Works records carry one, including just 11/21 of the core
  "TfL works" subcategory itself - not a reliable network-membership
  signal, never promoted to `street_ref`.
- `status` was `"Active"` on every real record checked, driving real
  `VERIFIED` date-confidence grading - this endpoint only returns
  currently-active disruptions, a genuinely different epistemic class
  from a permit application's own scheduled dates.
- **Do-not-dedupe against Street Manager** - a works on a TLRN red route
  can genuinely appear in both (Street Manager as the all-borough permit
  record, TfL as the live operational disruption); they answer different
  questions for different audiences.
- **Licence: TfL's own OGL v2.0-with-amendments terms, confirmed live** -
  requiring three real attribution statements, not just the commonly-
  quoted one: "Powered by TfL Open Data", "Contains OS data (c) Crown
  copyright and database rights 2016", and "Geomni UK Map data (c) and
  database rights [2019]".
- Registry entry (`tfl`, `network_scope=strategic`), a London map centroid
  added to `examples/roadworks_world_map.py`, and new tests against a real
  fixture covering the category filter and the incomplete `corridorIds`
  field.

### Added — Vienna (verkehrswirksame Baustellen), this SDK's second Austria roadworks provider (2026-08-14)

`streetworks.vienna` / `streetworks.common.from_vienna` - Stadt Wien's own
register of current and future traffic-relevant roadworks and closures on
the city's higher-order road network.

```python
from streetworks.vienna import ViennaClient
from streetworks.common import from_vienna

with ViennaClient() as vienna:
    features = vienna.iter_roadworks()  # both real layers, combined
works = from_vienna(features)
```

- **The first candidate URL (`data.gv.at`) turned out to be a JS-rendered
  SPA - the real data lives directly on Vienna's own GeoServer WFS
  instead.** A plain unauthenticated fetch of any `data.gv.at` catalogue
  page returns an identical empty shell. The real endpoint,
  `https://data.wien.gv.at/daten/geo`, is a real, live, 377-layer WFS,
  confirmed reachable with no key.
- **Two real layers, genuinely disjoint** - `BAUSTELLENPKTOGD` (Point, 39
  real features) and `BAUSTELLENLINOGD` (LineString, 72 real features) -
  confirmed live: zero real `OBJECTID` overlap and zero location-name
  overlap between them. Each worksite is recorded once, as either a point
  or a line; both layers are fetched and combined (111 real works total).
- **Two real server quirks, found by reading response bodies, not just
  status codes.** This GeoServer returns a genuine `HTTP 200` wrapping an
  XML `InvalidParameterValue` exception for the shared client's own
  `application/geo+json` default - plain `application/json` is what
  actually returns real GeoJSON. It also rejects both WFS 2.0.0's and
  1.1.0's plural `TYPENAMES` alone - it needs 1.1.0's singular `TYPENAME`
  sent alongside it.
- **CRS confirmed live, cross-verified two ways**: `EPSG:31256` (MGI /
  Austria GK East), stated in `GetCapabilities` and confirmed by
  reprojecting a real feature to `EPSG:4326` and landing on real Vienna
  coordinates matching that feature's own stated district. Stored
  unswapped.
- **A real correction to the initial framing: this is a permit register,
  not an operator publishing only its own works.** `ANTRAGSTELLER`
  (applicant) shows genuine third-party applicants - the electricity/gas
  utility, the transit operator, the sewage utility, even a private
  developer - alongside city departments. Ships `source_grade=REGISTER`,
  the same tier as Copenhagen/Helsinki/NYC DOT/Chicago, correcting the
  initial "operator" assumption.
- **A real, confirmed CPython date-parsing quirk, not a bug in this SDK.**
  Real dates are shaped `"2026-08-10Z"` (a bare date plus a bare `Z`) -
  `datetime.fromisoformat` silently drops the offset and returns a naive
  datetime, confirmed in a plain Python shell independent of this SDK's
  own code.
- Licence: Stadt Wien's stated general CC BY 4.0 open-data policy,
  confirmed live - a general stated practice, not this specific dataset's
  own confirmed per-record licence field. `network_scope` scoped honestly
  to the "higher-order road network," not every residential street.
- Registry entry (`vienna`), a Vienna map centroid, `scripts/smoke_test.py`
  check, and new tests against a real fixture.

### Added — Kanton Zürich and Stadt Zürich, this SDK's first Swiss roadworks providers (2026-08-14)

`streetworks.canton_zurich` / `streetworks.zurich` /
`streetworks.common.from_canton_zurich` / `from_zurich` - two deliberately
separate providers, a cantonal-road register and a city-streets register,
built together and confirmed genuinely non-overlapping (neither dataset's
records appear in the other) - the same do-not-dedupe discipline as every
other national/regional-vs-municipal pair in this SDK.

```python
from streetworks.canton_zurich import CantonZurichClient
from streetworks.zurich import ZurichClient
from streetworks.common import from_canton_zurich, from_zurich
```

- **Both found via opendata.swiss's own CKAN catalogue**, each over its
  own real GeoServer WFS - the canton's `TbaBaustellenZHWFS` (Tiefbauamt,
  civil engineering office, 66 real features) and the city's own WFS
  (140 real features). Both keyless.
- **Kanton Zürich: two real layers carry the same closures, not disjoint
  data** - confirmed live, every sampled feature's non-geometry properties
  match 1:1 across both; the richer real `Polygon` detail layer is used.
  **No unique identifier field exists anywhere in the schema** - a
  composite key is 65/66 unique, but the one real collision is two
  genuinely distinct closures (opposite directions, different times)
  sharing every composite field - `reference` stays `None` rather than a
  fabricated key that would misrepresent two real works as one.
  `status_baustelle` is a real, informative two-value field
  (`aktiv`/`zukünftig`) driving real VERIFIED/ESTIMATED grading.
- **Stadt Zürich: a real, confirmed 100%-unique identifier** (`baunr`),
  unlike the canton's dataset. Two real server quirks confirmed live: only
  `application/vnd.geo+json` works (not the shared client's default), and
  the server 500s on WFS 2.0.0's plural `TYPENAMES` alone. CRS is
  genuinely WGS84, confirmed empirically (real coordinates match the
  layer's own stated bounding box) despite an empty `DefaultSRS`
  capabilities tag. `kategorie` is a constant `"Grössere Baustelle"` -
  this feed is already curated to significant projects, stated honestly
  rather than implied exhaustive.
- **CRS**: the canton's is `EPSG:2056` (Swiss LV95), stored unswapped as
  `(easting, northing)`.
- **Neither dataset names an organisation as contact** - `ansprechperson`/
  `projektleiter` name individual staff members, never promoted to
  `promoter`, which would misrepresent a person as a company.
- **Licence: opendata.swiss's "Open use" tier for both, confirmed live -
  but not from the obvious field.** Both datasets' CKAN `license_id` is
  empty; the real licence surfaced only via the WFS resource's own
  separate `rights` field. That tier permits commercial use with no
  attribution required.
- Registry entries (`canton_zurich`, `zurich`), a Zürich map centroid,
  `scripts/smoke_test.py` checks, and new tests against real fixtures for
  both.

### Added — ASFINAG (Austria) as a Credentials-wanted DATEX II scaffold (2026-08-14)

`streetworks.datex2.austria` - Austria's national motorway network,
genuinely separate from Vienna's municipal coverage above (the same
national-vs-municipal split as every other pair in this SDK). Ships as a
Phase 0 scaffold, worse-off than most other Credentials-wanted rows: even
the authentication mechanism is unconfirmed, not just the credential
itself.

- **A real dataset confirmed to exist, not guessed at** - ASFINAG's own
  official dataset page confirms a genuine DATEX II Situations/
  SituationRecords roadworks dataset (`Baustellen`/
  `Instandhaltungsarbeiten`/`Sanierungen`), CC-BY-4.0 licensed with real
  supplementary conditions, confirmed live.
- **A hoped-for keyless shortcut was checked live and ruled out, not
  assumed to fail.** A candidate RSS feed was tested directly - it carries
  only unplanned/safety events, no roadworks at all.
- **Genuinely unknown: the pull URL and the auth scheme itself.** Checked
  the dataset page, the licence page, and the registration portal's own
  JS bundle - none states whether access is API-key, Basic, or Bearer, or
  whether the response is a bare DATEX document or wrapped in an
  envelope. Registration is real and reachable (ASFINAG Content Portal,
  `contentportal.asfinag.at`) but the flow wasn't walked through this
  session.
- `AsfinagClient` (once built) will follow this SDK's shared
  `streetworks.datex2` parser, the same pattern already verified against
  NDW/National Highways/Digitraffic/DGT/Statens vegvesen - implemented to
  the documented shape and covered by mocked tests, never run against a
  real authenticated response.
- Added to the Credentials-wanted table in `docs/providers/index.md` and
  the drafted issue text in `docs/credentials-wanted-issues.md` (`help
  wanted` only). Import-time `UserWarning`, excluded from the verified-
  providers claim until confirmed.

### Added — Milan (Avvisi di manomissione), this SDK's second Italy municipal provider (2026-08-14)

`streetworks.milano` / `streetworks.common.from_milano` - Comune di
Milano's own road-excavation-notice register, resolving the "populous
cities" pivot's own open question left by Rome falling off-board
(Roma si trasforma is a general capital-projects tracker, not a
dedicated roadworks register - see the earlier Roma entry).

```python
from streetworks.milano import MilanoClient
from streetworks.common import from_milano

with MilanoClient() as milano:
    notices = list(milano.iter_roadworks())  # raw, unfiltered
works = from_milano(notices)
```

- **Neither obvious source held up.** Checked live: no Milan or Città
  Metropolitana di Milano dataset exists on the Lombardy regional Socrata
  portal (`dati.lombardia.it`) at all, despite it hosting real "Cantieri
  stradali attivi" datasets for smaller Lombardy towns. Milan's own CKAN
  portal has nothing named "cantieri" either - searching "scavo"
  (excavation) surfaced the real dataset, `ds925_avvisi-di-manomissione`,
  the real Italian legal term for a road-excavation notice, not the
  first-guessed term.
- Maintained by Comune di Milano - Direzione Mobilità e Trasporti,
  updated daily, CC-BY, direct GeoJSON download - no API, no WFS, no key.
- **A real, confirmed quirk: the download URL is filename-agnostic.** The
  CKAN resource's stated `url` embeds a daily generation timestamp, but
  CKAN resolves purely by resource UUID - a request substituting an
  arbitrary filename returned identical live content. A stable,
  non-timestamped filename is used deliberately so it keeps serving each
  day's fresh file without going stale.
- **Geometry: real `Point`, native WGS84 - not the first-guessed
  Monte Mario/ETRF2000 projected CRS.** Every feature states
  `"crs": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}` and separately
  carries explicit `LONG_X_4326`/`LAT_Y_4326` properties confirming it -
  flipped to `(lat, lon)`.
- **A utility-operator excavation register, the Milan equivalent of
  Paris's "Opérateurs de réseau" category** - real promoters seen live:
  `MM Spa` (water), `Unareti S.p.A` (gas/electricity), `A2A Calore &
  Servizi` (district heating). Every real row carries a unique protocol
  number (139/139) - one `Works` per feature, no grouping, the same shape
  as Lisboa.
- 138/139 real rows have a planned end date current or future - this
  "final" download is already close to active-scoped, not a full
  historical archive. No explicit status field - `date_confidence` is
  uniformly `ESTIMATED`.
- Licence: CC-BY, confirmed live from the dataset's own CKAN metadata.
- Same commit fixed a login-tier world-map marker bug found while wiring
  Milan in.
- Registry entry (`milano`), a Milan map centroid, `scripts/smoke_test.py`
  check, and new tests against a real fixture.

### Added — Stockholm as a Credentials-wanted scaffold (2026-08-13)

`streetworks.stockholm` - resolves a real risk flagged early across the
Nordic capitals rather than disproving it. Every real surface tested on
Trafikkontoret's own geodata platform (both WFS and WMS
`GetCapabilities`) requires an API key before revealing even a layer
name, let alone whether a `vägarbete` (roadworks) dataset exists on it at
all.

- **Worse-off than every other Credentials-wanted row: no schema of any
  kind confirmed.** Only that the platform genuinely exists and requires
  a key - a real `HTTP 401` (`text/plain`, "You must provide a valid key
  to consume this API.") confirmed on both `GetCapabilities` endpoints.
- **A promising "regional roadworks coordination map" lead was checked
  and traces back to the already credential-parked national Trafikverket
  system**, not a separate Stockholm dataset - not a new lead, a
  dead end already accounted for.
- Ships as a Phase 0 scaffold (implemented to the one confirmed real auth
  shape - a documented Parking-API `apiKey=` example, unconfirmed for WFS
  specifically - and covered by mocked tests only), rather than a
  live-verified build.
- Added to the Credentials-wanted table in `docs/providers/index.md` and
  `docs/providers/denmark.md`'s "The rest of the Danish landscape"
  section (which also now records Oslo and Helsinki as resolved). Import-
  time `UserWarning`, excluded from the verified-providers claim until
  confirmed.

### Added — Helsinki (Kaivuilmoitus), this SDK's third Nordic roadworks provider (2026-08-13)

`streetworks.helsinki` / `streetworks.common.from_helsinki` - City of
Helsinki's own excavation-notification register, alongside the separate,
already-built national Digitraffic DATEX II feed.

```python
from streetworks.helsinki import HelsinkiClient
from streetworks.common import from_helsinki

with HelsinkiClient() as helsinki:
    features = list(helsinki.iter_roadworks())  # raw, ungrouped
works = from_helsinki(features)  # grouped by hakemustunnus
```

- **Resolves a real open question left unconfirmed by earlier
  investigation** - whether a roadworks (`kaivulupa`/excavation-permits)
  dataset exists on Helsinki Region Infoshare at all. Checked live via
  HRI's own CKAN `package_search` API: every excavation/permit search term
  surfaces one real dataset, backed by a live GeoServer WFS, layer
  `Kaivuilmoitus_alue`. Keyless - 3,431 real features at investigation
  time.
- **CRS confirmed live: `EPSG:3879`** (ETRS-GK25FIN), a genuinely
  projected CRS - the WFS can reproject to WGS84 on request but this SDK
  carries the native CRS through explicitly instead, per its standing
  policy. Stored unswapped as `(easting, northing)`.
- **A real, load-bearing grouping finding, Oslo-shaped not Copenhagen-
  shaped.** `id` is genuinely unique across every row (no tiling-
  duplicate problem, unlike Oslo) - but `hakemustunnus` (application
  reference) repeats heavily, up to 164 real rows under one reference,
  confirmed to be one notification genuinely spanning many real segmented
  dig zones. `from_helsinki` groups by it into one `Works` with one
  `WorksSite` per surviving geometry row.
- **Two other real layers on this WFS, checked live and deliberately not
  used** - the point-version layer is confirmed a redundant subset (not
  additional coverage), and a "temporary traffic arrangement" layer is a
  genuinely different application type, left for a future investigation.
- **`status` is genuinely informative, unlike Oslo's always-"granted"
  status** - `Käynnissä` (in progress, 3,223/3,431) and `Tuleva` (upcoming,
  208/3,431), cross-checked live against a date-based future/past split
  and matching exactly. Drives real VERIFIED/ESTIMATED date-confidence
  grading, unlike Oslo's always-ESTIMATED.
- `promoter` is never populated - a real, confirmed absence, not a gap:
  both applicant and contractor fields are empty on all 3,431 real rows,
  matching the dataset's own published description.
- Licence: CC-BY-4.0, confirmed live via the dataset's own CKAN metadata.
- Registry entry (`helsinki`), a Helsinki map centroid,
  `scripts/smoke_test.py` check, and new tests against a real fixture.

### Fixed — Street Manager Reporting API filter usage in two examples, new coordination/comparison maps (2026-08-13)

The Reporting API's `permits` endpoint has no working `town`/`swa_code`/
`highway_authority` filter - live-verified against both sandbox and
production: every variant returned identical results, scoped only to the
authenticated account's own registration. An unfiltered production pull
was traced past 2000 rows with no end in sight before being killed by its
own timeout - this is what "the feed wasn't loading anything" actually
was. The Reporting API's own documented resource guide names real filters
that do work, checked live one at a time:

- **`compare_active_works.py`** now uses `work_status="in_progress"` +
  `street_descriptor` (defaults to `"DURHAM CITY"`, not bare `"DURHAM"` -
  live-verified the bare form also matches unrelated towns via street-
  name substring hits) instead of the old full-account pull. Production
  now completes in ~2s instead of never finishing. `--sm-since-days`
  exposes the real `work_start_date_from` filter, off by default since
  combined with `work_status` it can genuinely return few or none. New
  `--map` writes a side-by-side comparison map (Plotly `Scattermap`,
  free CartoDB street tiles).
- **`collaboration_finder.py`** now pulls `work_status="planned"` and
  `"in_progress"`, each capped - live-verified `"planned"` alone doesn't
  terminate within 60s uncapped in production (future work genuinely
  outnumbers current work by a wide margin); capped, it completes in
  ~12s. Only future-starting permits are now considered, since a permit
  that already started can't be usefully coordinated around. The single
  most obviously-should-have-coordinated pair gets its own callout. New
  `--map` draws one line per coordination pair, the callout pair
  highlighted in red - hover text was later extended (2026-08-13, same
  cluster) to show promoter and traffic-management type, not just the
  permit reference, alongside a real generated map screenshot
  highlighting a real pair confirmed (via a full `WorkAPI.get_permit`
  lookup) to have neither `collaborative_working` nor
  `others_can_collaborate_on_work` set - the tool genuinely surfacing a
  gap the promoters hadn't flagged themselves.
- **CartoDB street tiles, not Plotly's other free "open-street-map"
  style** - real testing found the latter gets blocked (403) by OSM's own
  tile-server usage policy for this kind of embedded use.
- A coverage-map image and description were also added to the README/docs
  this same day, with two small follow-up wording/formatting passes.

### Added — Oslo (SøkSys) as this SDK's second Nordic roadworks provider (2026-08-10)

`streetworks.oslo` / `streetworks.common.from_oslo` - Oslo kommune's real
digging/work-permit case system, alongside the separate, already-verified
national Statens vegvesen DATEX II feed.

```python
from streetworks.oslo import OsloClient
from streetworks.common import from_oslo

with OsloClient() as oslo:
    features = list(oslo.iter_roadworks())  # Containerutsett excluded
works = from_oslo(features)  # id-deduped, activity_id-grouped
```

- **Neither early-guessed backend matched reality.** A web search for
  Oslo kommune's own page on this system found "SøkSys" - a
  2024-introduced permit/case system run on Oslo's behalf by Geomatikk, a
  real Norwegian utility-location company - not the guessed Origo/
  Bymiljøetaten GeoServer layer or the national NVDB. The real internal
  API (`pub.soksys.no/api/map/soksys-activities`) was found by reading the
  public map's own `map.js` bundle directly. Keyless - 1,354 real
  features at investigation time.
- **The response body double-encodes its own JSON** - the raw HTTP body
  is a JSON string literal containing escaped GeoJSON, needing
  `json.loads` twice - handled inside `OsloClient` so callers never see
  the intermediate string.
- **CRS confirmed live: `EPSG:25832`** (ETRS89/UTM zone 32N), a genuinely
  projected CRS - stored unswapped as `(easting, northing)`, unlike
  Copenhagen's genuine WGS84 source.
- **Roadworks filter, evidenced not guessed**: `activity_type` has 3 real
  values - `Arbeidstillatelse` (work permit, 934/1354), `Gravearbeid`
  (excavation, 412/1354), `Containerutsett` (container placement,
  8/1354, excluded - real senders are the city agency or property
  managers, not construction).
- **A real, load-bearing geometry/grouping finding, genuinely different
  from Copenhagen's own dedupe pattern.** 1354 raw rows collapse to 631
  distinct `activity_id`s; 256 multi-row groups are pure duplicate
  artifacts (identical id and geometry, a tiling/extent artifact of
  querying a wide bbox) but a real handful of permits genuinely span
  several distinct sub-areas - `from_oslo` dedupes by exact `id` first,
  then groups survivors by `activity_id`.
- Polygon geometry (the majority shape here, unlike Copenhagen where it
  was always droppable) uses its first ring's first vertex only.
- Licence: genuinely unconfirmed - checked both the live map page and
  Oslo kommune's own explainer page, no statement found on either.
- Registry entry (`oslo`), an Oslo map centroid, `scripts/smoke_test.py`
  check, and new tests against a real fixture.

### Added — Roma Capitale (Roma si trasforma) as this SDK's second Italy provider (2026-08-10)

`streetworks.roma` / `streetworks.common.from_roma` - Roma Capitale's own
civic-interventions tracker, filtered to real, currently in-progress
street/infrastructure work.

```python
from streetworks.roma import RomaClient
from streetworks.common import from_roma

with RomaClient() as roma:
    interventi = list(roma.iter_roadworks())  # Strade e infrastrutture + Cantiere only
works = from_roma(interventi)
```

- **The most obvious candidate source doesn't exist as expected.** Roma
  Servizi per la Mobilità's ArcGIS Hub was checked live first - 81 real
  datasets, none roadworks-related. Roma Capitale's own CKAN portal was
  checked next - zero real results for "cantieri"/"lavori"/"viabilità"/
  "opere". The real source is a third site neither candidate named -
  `romasitrasforma.it`, a Drupal-based civic-projects portal, found by
  reading its own bundled JS, the same technique that found Lisboa's and
  Road Report NT's real backends.
- **A genuinely broader scope than "roadworks" - Rome's general
  capital-projects tracker, not a dedicated register.** 1215 real records
  span four macro-themes; street/road work is one sub-tag among many.
  **This is the thinnest real roadworks signal of any municipal provider
  this SDK has built** - only 69/1215 (5.7%) of the source feed pass the
  real filter (`field_tag_temi` contains "Strade e infrastrutture" AND
  `field_stato_lavori == "Cantiere"`).
- **A real bug in the source, found and corrected, not reproduced.** The
  `field_posizione` object's own key names are swapped relative to true
  geography - what it calls `"lon"` holds latitude-range values and vice
  versa, confirmed against every real coordinate in the pull.
  `from_roma` reads them by their correct meaning, not the source's own
  key names.
- **No date fields exist anywhere in this schema** - a first for a
  municipal provider in this SDK. `date_confidence` is always `UNKNOWN`.
- Geolocation is genuinely partial even within the filtered subset -
  35/69 real records carry a coordinate; the rest have only a
  district-level value.
- Licence: genuinely unconfirmed - checked the live site's page text,
  footer, and common Italian open-data terms; none found.
- Same investigation folded an Athens check into Greece's existing docs -
  confirmed no roadworks open data exists for the City of Athens at any
  level either, extending rather than duplicating the existing Greece
  finding.
- Registry entry (`roma`), a Rome map centroid, `scripts/smoke_test.py`
  check, and new tests against a real fixture.

### Added — Copenhagen (Gravetilladelser) as this SDK's first Nordic roadworks provider (2026-08-10)

`streetworks.copenhagen` / `streetworks.common.from_copenhagen` -
Københavns Kommune's own excavation-permit register, alongside the
separate credential-parked national Vejdirektoratet feed.

```python
from streetworks.copenhagen import CopenhagenClient
from streetworks.common import from_copenhagen

with CopenhagenClient() as copenhagen:
    features = list(copenhagen.iter_roadworks())  # raw, undeduped
works = from_copenhagen(features)  # deduped by sagsnr, one Works each
```

- **Live verification corrected several early guesses before any code was
  written.** The first guess was a dataset named "vejarbejde" over an
  assumed ArcGIS Hub/OGC API Features backend - checked directly on
  `opendata.dk`, the real dataset is titled "Gravetilladelser", over a
  classic WFS 1.0.0 GetFeature endpoint, not ArcGIS/OGC Features. Layer
  `gravetilladelser_aktiv_aabne` is already server-side filtered to
  current permits - 2240 real rows confirmed.
- **A real, load-bearing geometry finding not anticipated going in: this
  layer mixes `Point`, `LineString` and `Polygon`, and the same real
  permit is recorded once per geometry shape it has, not once per
  permit.** Grouping by `sagsnr` gives 1241 distinct real permits; every
  multi-row permit has identical non-geometry properties across its rows.
  Confirmed live: zero of the 1241 real permits are Polygon-only, so
  `from_copenhagen` dedupes by `sagsnr` and prefers LineString over
  Point, never needing to handle a polygon ring.
- Coordinates are genuine WGS84, confirmed in the response's own embedded
  `crs` block - swapped to `(lat, lon)`.
- **Real schema, 12 fields, confirmed 100% populated, zero nulls across
  all 2240 rows** - including real Danish `DD-MM-YY` dates (parsed via a
  bespoke `strptime`) and `entreprenoer` (the contractor), folded into
  `traffic_management` rather than dropped.
- `date_confidence` is `ESTIMATED`, never `VERIFIED` - a granted permit's
  stated window isn't an independently confirmed "work is happening"
  signal. `street_ref` is never populated - only free-text `lokation`
  exists.
- `source_grade="register"` - a formal municipal permit register, the
  same tier as Street Manager/NYC DOT/Chicago/Paris/Jersey.
- Licence: CC-BY-4.0, confirmed live via the dataset's own CKAN metadata -
  no hedging required. No credentials required anywhere in this build.
- Registry entry (`copenhagen`), a Copenhagen map centroid,
  `scripts/smoke_test.py` check, and new tests against a real fixture.

### Fixed — 4 pre-existing mypy findings: a bad `iter[]` type hint, 3 sites where None-narrowing didn't survive a stored boolean (2026-08-10)

`srwr/client.py`'s three reader wrappers were annotated
`-> iter[Record]`/`iter[Activity]`, using the builtin `iter` as a generic
type - not valid syntax, previously silenced with `# noqa: F821` rather
than fixed. Now `Iterator[...]` from `collections.abc`, matching every
other iterator-returning method in this SDK.

`vegvesen.py` and both `datavia/client.py` constructors computed
`basic = username is not None and password is not None`, then guarded
`BasicAuth(username, password)` on that stored bool - correct at runtime,
but mypy can't narrow `username`/`password` through an intermediate
variable. Inlined the None-checks at the point of use so mypy can
actually prove what was already true.

No behaviour change; all 1035 tests still pass. mypy error count on these
files: 9 -> 0. A handful of other pre-existing, unrelated mypy findings
remain (`opendata/sns.py`, `datex2/parser.py`,
`datex2/nationalhighways.py`, `srwr/reader.py`, `smoke_test.py`) - each is
a real optionality the type system can't narrow at a specific known-good
call site, not a runtime bug, and left alone.

### Fixed — EPSG:4326 coordinate axis order at the source across 8 converters, widen the world-map example's US/live coverage (2026-08-10)

A live pull surfaced Australian roadworks plotting near Antarctica: WA,
SA, ACT, TAS, QLD, NSW, VIC and NZTA were each storing raw, unswapped
GeoJSON `(lon, lat)` in `Coordinate.value` instead of this SDK's own
stated `(lat, lon)` WGS84 convention.

- Fixed at the source in each converter (`from_au_wa_mainroads`,
  `from_au_sa_trafficsa`, `from_au_act_ttm`, `from_au_tas_roadworks`,
  `from_au_qld_qldtraffic`, `from_nsw_livetraffic`, `from_vic_disruptions`,
  `from_nzta`) - not just patched in the example script - with every
  affected test updated to match.
- **Jersey, NYC DOT and Via Lietuva were checked and deliberately left
  alone** - their CRSs are genuinely projected (`EPSG:3109`/`2263`/
  `3346`), where `(x, y)` unswapped is correct, matching this SDK's
  existing British National Grid handling.
- A real secondary bug fixed in the same converter pass:
  `from_nsw_livetraffic` used to leave `Coordinate.value` and
  `Coordinate.points` on the same object in two genuinely different axis
  orders (`points`, decoded from Google's Encoded Polyline format, was
  already `(lat, lon)` per that algorithm's own convention) - fixing
  `value` removes that internal mismatch too, not just the external one.
- Also widens `roadworks_world_map.py`'s live coverage: WZDx now sweeps
  up to 25 keyless US/regional feeds (was 5), and NYC DOT pulls a larger
  raw sample since only ~87% of its rows carry usable geometry. Removes
  the now-redundant `_LONLAT_NATIVE` per-key workaround the source fix
  makes unnecessary, and adds a real `--live` run's output image to
  `docs/examples.md`.

### Added — coverage-map example relocated, shrunk, and cross-linked; real example output images embedded in the docs (2026-08-08 to 2026-08-09)

`examples/map.html` and its screenshot were loose in `examples/` root -
moved into `examples/roadworks_world_map/`, matching the folder-per-
example pattern already used for `nsg_terrain_drape/`/`crime_context/`.
The screenshot was 902KB at 3428x1970 - resized to <=1200px wide and
re-encoded as an adaptive-palette PNG (48KB), the same treatment applied
earlier the same cluster to two other example images (2.3MB -> 96KB,
712KB -> 122KB) for the same repo-history-weight reason. Adds a one-line
pointer from `docs/providers/index.md`'s Coverage section to the map
example - it's registry-driven, so it's a genuine visual complement to
that exact roster, not just a generic example. A day earlier, both real
output images (`WorksiteRisk.png`, the terrain-drape screenshot) were
verified as genuine example output rather than mockups and embedded
inline in `docs/examples.md` next to their entries, instead of just
linked out.

### Added — Câmara Municipal de Lisboa (Condicionamentos de Trânsito), this SDK's first Portugal provider (2026-08-09)

`streetworks.lisboa` / `streetworks.common.from_lisboa` - active and
planned traffic-restriction feed for the city, sidestepping the still
credential-parked national IMT National Access Point entirely.

```python
from streetworks.lisboa import LisboaClient
from streetworks.common import from_lisboa

with LisboaClient() as lisboa:
    features = list(lisboa.iter_roadworks())  # evidence-based motivo filter
works = from_lisboa(features)
```

- **A key gating check - is the live platform actually current, or a
  stale 2023 snapshot? - resolved before writing any client code.** The
  catalogue record states "última atualização: 22 de maio de 2023" -
  exactly the kind of stale-portal signal that's meant a dead dataset
  elsewhere in this SDK. But CML's real live platform (a live Angular
  SPA) has a backend found by reading its own bundled JS - genuinely
  current: 453/694 real features carry a 2026 case-reference id.
- **The real endpoint isn't documented anywhere public** - found in the
  app's own `environment` config. A single keyless `GET` returns the
  full real GeoJSON FeatureCollection - 694 real features, no pagination.
- **Roadworks filter: `motivo` (free-text reason), evidence-based, not a
  clean boolean like Madrid's `es_obras`.** 27 real distinct values exist;
  473/694 (68%) classify as roadworks (anything containing "OBRA", plus a
  small explicit construction-activity set) - genuinely ambiguous values
  (`LIGAÇÃO DE RAMAL`, `AUTOGRUA`) are excluded rather than guessed
  either way.
- **Geometry: real `MultiLineString`, not `Point`/`LineString` like this
  SDK's other municipal sources.** Only the first sub-line's vertices are
  used, the same simplification `from_berlin` already makes for a
  `GeometryCollection`. CRS `EPSG:4326`, evidenced from the app's own WMS
  requests.
- **Dates: `periodos_condicionamentos` is a list, not one window** -
  richer than Madrid/DriveBC's single start/end, up to 4 real periods on
  some records, including a real `is_interrupted` flag (true on 583/727
  real periods, the majority, not an edge case).
- Network scope `comprehensive` - 27 distinct freguesias confirmed live.
  Licence: CC BY 4.0, confirmed live at `dados.gov.pt`'s catalogue page.
- Registry entry (`lisboa`), a Lisbon map centroid,
  `scripts/smoke_test.py` check, README/docs section, and new tests
  against a real fixture.

### Added — DriveBC (British Columbia) as this SDK's first Canadian roadworks provider (2026-08-08)

`streetworks.drivebc` / `streetworks.common.from_drivebc` - British
Columbia's own implementation of Open511, a Canadian-origin multi-
jurisdiction road-events standard.

```python
from streetworks.drivebc import DriveBCClient
from streetworks.common import from_drivebc

with DriveBCClient() as drivebc:
    events = list(drivebc.iter_roadworks())  # event_type == "CONSTRUCTION" only
works = from_drivebc(events)
```

- **Bespoke, not a general `streetworks.open511` parser.** DriveBC is the
  only real, confirmed roadworks-events Open511 implementation found live
  - Bay Area 511's own Open511 use is transit data, a different resource
  entirely. Per this SDK's "extract shared code only on the second real
  consumer" pattern (the same reasoning that kept Paris Chantiers
  bespoke), this ships as `streetworks.drivebc`.
- Keyless `GET` on `api.open511.gov.bc.ca/events`, confirmed live (246
  real events at investigation time). `limit`/`offset` pagination, max
  `limit=500` confirmed via the API's own structured error.
- **Roadworks filter: `event_type == "CONSTRUCTION"`** - confirmed live,
  194/246 real events; `INCIDENT`/`ROAD_CONDITION`/`WEATHER_CONDITION`
  excluded.
- **Two real, mutually-exclusive schedule shapes, beyond the original
  plan.** 222/246 real events state `schedule.intervals` (ISO-8601
  interval strings); the other 24 state `schedule.recurring_schedules`
  instead - a weekday work-window shape `intervals` can't express. No
  event carries both or neither; `from_drivebc` reconciles both into one
  `WorksSite` window each.
- Interval date-times carry no UTC offset, unlike the top-level
  `created`/`updated` fields - almost certainly local BC time (the
  jurisdiction resource states `"America/Vancouver"`) but parsed naive
  rather than a timezone silently attached.
- Geometry: real GeoJSON, `Point` or `LineString`, native WGS84.
  `roads[]` is free-text - no join key, `street_ref` stays unpopulated.
- **Licence: Open Government Licence - British Columbia (OGL-BC),
  confirmed live from the API's own `/help` page** - the jurisdiction
  resource's own `license_url` field is a dead PDF link, confirmed
  404-redirecting; the real, live OGL-BC text is cited instead.
- Registry entry (`drivebc`), a BC map centroid, `scripts/smoke_test.py`
  check, README/docs section, and new tests against a real fixture.

### Added — Madrid (INFORMO) as this SDK's fourth Spanish provider (2026-08-08)

`streetworks.madrid` / `streetworks.common.from_madrid` - Madrid's own
municipal traffic-incidents feed, the gap DGT's national coverage
explicitly doesn't reach (DGT never touches municipal streets).

```python
from streetworks.madrid import MadridClient
from streetworks.common import from_madrid

with MadridClient() as madrid:
    incidents = list(madrid.iter_roadworks())  # es_obras == "S" only
works = from_madrid(incidents)
```

- **The first-tried URL is dead - checked live before writing any code.**
  `informo.munimadrid.es` returns `NXDOMAIN` on two independent
  resolvers. Madrid relaunched its entire open-data portal on a new CKAN
  platform in February 2026 - the real current host is
  `informo.madrid.es` (`munimadrid.es` -> `madrid.es`, not just a path
  change), targeted directly rather than via the CKAN redirect hop.
- **The live wire date format also doesn't match the portal's own
  documentation.** The PDF states a UTC-offset format; every one of 217
  real records checked live instead uses no offset and seven fractional-
  second digits - one more than Python's `%f` accepts.
  `from_madrid` truncates rather than failing.
- **Roadworks filter: the source's own `es_obras` flag, not a free-text
  type guess.** Real evidence: `cortes de carriles` (lane closures) and
  `operación asfalto` (asphalt resurfacing) are both real and common but
  neither is flagged `es_obras` - excluded. The asphalt exclusion is a
  genuine surprise (it reads like roadworks to a human) but the source's
  own classification is trusted over what the label sounds like.
- **`source_grade="operator"`, not the `traveller_info` first guessed** -
  Madrid's own field dictionary states its codes follow DATEX 2 practice,
  published directly by the city's traffic-circulation directorate, not
  a separate editorial relay.
- Coordinates given directly, labelled `EPSG:4258` (ETRS89) rather than
  silently assumed WGS84 - the source states its UTM pair is
  `EPSG:25830` explicitly, so the geographic pair is used and labelled
  from the same reference frame.
- `id_incidencia` is the reliable reference, not `codigo` - `codigo` is
  unique on only 212/217 real records (6 share the literal placeholder
  `"2025/0"`, a real source data-quality gap).
- Network scope `comprehensive` - real records span named residential
  streets to motorway sections across the whole municipality.
- Licence: CC BY, confirmed live at `nap.dgt.es`'s dataset page.
- Registry entry (`madrid`), a Madrid map centroid,
  `scripts/smoke_test.py` check, README/docs section, and new tests
  against a real fixture.

### Changed — Documentation restructure: migrated README into a docs/ tree (2026-08-08)

Non-functional - no code or behaviour changes. The README had grown into
a single sprawling document; migrated into a proper `docs/` tree in two
phases, both now complete (see `docs/index.md`'s own "Status of this
migration" section).

- **Phase one**: a lossless, extract-and-relocate migration of every
  README section into `docs/` (providers by territory, concepts,
  examples, governance, domain notes) - editorial changes deliberately
  deferred to phase two. Documented personal-capacity framing, Chris
  Carlon attribution, UK permit/S50 domain notes, excluded territories,
  agent boundaries, and pending providers along the way.
- **Phase two**: slimmed the README itself down to a front door (badges,
  install, a working quickstart, and links into the docs tree) now that
  every removed block had a confirmed docs home. Added an examples index
  and front-door link, fixing two stale S50 claims found while writing
  it. Repointed the README-parsing test at `docs/`, making
  `docs/providers/index.md` the canonical coverage roster rather than the
  README's own copy.
- **Two real coverage-roster errors were found and fixed while doing
  this** - Jersey was missing from the roster entirely, and Canada's
  coverage was overstated. Also reworded the opening line to name
  Australia/New Zealand explicitly and replaced "well-tested" with
  "verification-first" (a more accurate description of this SDK's actual
  discipline), and added a "Why?" section explaining the integration
  problem this SDK solves.
- The pre-slim README is preserved in git history, not archived
  separately.

### Added — Berlin VIZ roadworks provider (Baustellen/Sperrungen) (2026-08-08)

`streetworks.berlin` / `streetworks.common.from_berlin` - the largest
remaining German gap this cluster had: Berlin is a city-state Land in its
own right, entirely surrounded by the already-covered Brandenburg. A
genuinely different platform from the Hamburg/Brandenburg/Saxony WFS/
GeoJSON cluster - two public, keyless GeoJSON feeds published hourly by
VIZ (Verkehrsinformationszentrale), each a plain static file.

```python
from streetworks.berlin import BerlinClient
from streetworks.common import from_berlin

with BerlinClient() as berlin:
    works_list = from_berlin(list(berlin.iter_roadworks()))
```

- **Two feeds, and the initial assumption about them turned out wrong
  once checked live.** The dataset's own description says
  Verkehrsredaktion is "a subset of Landesmeldestelle with extra detail."
  Live data disagrees: using the real, verified join key (`lms_id` ->
  `id`, confirmed live on 199/205 records) and restricting both to real
  roadworks values, Landesmeldestelle has 215 such records,
  Verkehrsredaktion has 202, and only 104 overlap - neither feed alone is
  complete. `iter_roadworks()` merges both via the verified join key
  rather than picking one as primary, preferring Verkehrsredaktion's
  richer fields on a matched pair while keeping Landesmeldestelle's `id`
  as the canonical reference. Every merged record carries an explicit
  `sources` list.
- **Roadworks filter, evidenced not the initially assumed upstream
  values.** The real field on the published output is `subtype`, with
  exactly three roadworks-relevant values plus `Gefahr` (hazard warning,
  excluded even though some free text happens to mention nearby
  construction).
- Two date formats depending on feed (near-ISO vs. German
  `DD.MM.YYYY HH:MM`, sometimes blank). Geometry is `Point` or a real
  `GeometryCollection` pairing a Point with LineString entries - the
  first LineString's vertices map to `Coordinate.points`.
- No grouping - no umbrella-application field exists in either real feed,
  so one `Works` per record. `source_grade="traveller_info"` - VIZ is a
  traffic-information/editorial source, not a statutory register.
- Licence: Datenlizenz Deutschland - Namensnennung - Version 2.0
  (dl-de/by-2-0), the same licence Hamburg/Brandenburg already publish
  under.
- Registry entry (`berlin`), a Berlin map centroid,
  `scripts/smoke_test.py` check, README/docs section, and new tests
  against a real fixture.

### Added — Paris municipal roadworks provider (Chantiers à Paris) (2026-08-06)

`streetworks.paris` / `streetworks.common.from_paris` - this SDK's third
municipal permit register, and the French analogue of NYC DOT/Chicago
CDOT (same `source_grade=register` tier, same "one application groups
several sites" shape), but the first provider on OpenDataSoft rather
than Socrata.

```python
from streetworks.paris import ParisClient
from streetworks.common import from_paris

with ParisClient() as paris:
    works_list = from_paris(list(paris.iter_roadworks()))
```

- **Built bespoke, not a shared `streetworks.opendatasoft` client** - the
  same sequence that produced `streetworks.socrata`'s `SodaClient`
  (bespoke first, shared only once a second same-platform provider needs
  the identical shape).
- **Municipal, not national - deliberately not deduplicated against
  Bison Futé.** France is already covered nationally, but that coverage
  doesn't reach Paris city streets.
- **Roadworks-vs-private filter, evidenced not guessed.** The real
  `chantier_categorie` field has 3 live values - "Ville de Paris" (598
  rows) and "Opérateurs de réseau" (1,191 rows) are genuine street/
  public-space works; "Tiers (travaux sur bâtiment)" (2,918 rows, private
  building works) is excluded.
- **Geometry is already WGS84, despite the underlying survey CRS being
  Lambert 93** - OpenDataSoft reprojects on the way out, so no CRS
  transform was needed. The full polygon is preserved in
  `WorksSite.raw`; `Coordinate.value` uses the representative point.
- A real Works-umbrella grouping - `chantier_cite_id` genuinely groups
  multiple real emprise rows under one parent chantier (a real example
  spanning 3 genuinely different polygons).
- No stated join to a street register - `street_ref` never populated.
  Licence: ODbL 1.0 (Open Database License, share-alike), confirmed from
  the dataset's own metadata - meaning an adapted/derived database must
  itself be released under ODbL or a compatible licence.
- Registry entry (`paris`), a Paris map centroid, `scripts/smoke_test.py`
  check, README/docs section, new tests against a real fixture, and
  `compare_active_works.py` repointed at Durham City vs. Paris as its own
  worked cross-provider example.

### Added — Section 50 licence connector for Street Manager, the write path (2026-08-06)

`examples/streetmanager_section_50.py` - applying for, starting, and
stopping a Section 50 licence works record under a highway authority's
own promoter account. Transport and identity injection only: reprojects
the applicant's WGS84 extent to BNG, stamps the SWA codes and
`activity_type`/`work_type`, passes everything else through unchanged.
The reusable request-assembly logic lives in
`streetworks.streetmanager.utils.section_50_utils`; the WGS84<->BNG
transform (no `pyproj` - a pure-Python implementation of Ordnance
Survey's own published Helmert + Transverse Mercator formulas) lives in
`streetworks.common._bng`.

- **Sandbox-verified end-to-end 2026-08-06** - `create_work`,
  `start_work`, and `stop_work` all succeeded against a real sandbox
  record. Needs Promoter-role sandbox credentials specifically, not the
  Highway Authority login the other Street Manager examples use - an
  HA-role login got 400s and would likely 403 on `create_work` regardless
  of payload correctness. Production remains untouched.
- Field disposition checked field-by-field against the real Durham S50/01
  paper form: structured fields (licensee identity, apparatus
  description, drawn location, road/USRN, traffic management, duration)
  land on `WorkCreateRequest`; free-text supporting info fits
  `additional_info`; genuinely out-of-scope items (contractor identity
  distinct from the licensee, accreditation, insurance, Land Registry
  references, adoption agreements, signed declarations) are the evidence/
  accreditation/land-title/legal work a licensing authority needs to
  grant a licence, not a works-coordination permit's job.
- **`examples/streetmanager_section_50_form.html`** (added the same day)
  is a static, disconnected visual mockup of the applicant-facing flow -
  no server, nothing calls Street Manager - but its "Build request"
  buttons run a real, faithful in-page port of both the BNG reprojection
  and the request-assembly logic, so the JSON shown is genuinely what the
  Python connector would send. Restyled 2026-08-10 from a parchment/
  dossier look to an official council-portal aesthetic, and given a real
  screenshot 2026-08-11.
- **Evidence attachment, sandbox-verified 2026-08-12**: two placeholder
  files uploaded via `WorkAPI.upload_file` (already a generic wrapper, no
  new `client.py` method needed), the real returned `file_id`s included
  on `WorkCreateRequest.file_ids`, and `create_work` still succeeding
  with that field present - a real run produced real ids
  (`file_ids=[80475, 80476]`) against a real created work
  (`UG05046633203`), not a mocked assertion.
- **An illustrative bond estimate, added the same day**: `calculate_bond`,
  a pure function computing itemised per-surface costs from the drawn
  extent's own real BNG area via a shoelace formula, times council rates -
  folded into `additional_info` as a labelled note, never a structured
  field. What's real: the upload calls, the returned ids, and the area
  arithmetic. What's illustrative: the placeholder documents and the bond
  rates - both flagged for replacement with real evidence and a real
  council's current schedule. Amended 2026-08-12.
- See [`docs/concepts/write-path.md`](../docs/concepts/write-path.md) for
  the fee-suppression behaviour this connector's own docstring can't
  show - Street Manager, not the connector, decides not to bill an S50.

### Added — crime_context_lsoa sample outputs (2026-08-06)

`examples/crime_context_lsoa/WorksiteRisk.png` (a real worksite-risk map
image) and `worksite_context.html` (a real generated example HTML
report) - sample outputs for the existing `crime_context_lsoa` example,
demonstrating what its worker-safety context signal actually produces
against real UK Police/Census data, not just describing it in prose.

### Added — nsg_terrain_drape: drape OS Open USRN over real terrain, plus 3D-print export (2026-08-06)

A new example - a field of USRN centrelines draped over real OS Terrain
50 / EA LIDAR Composite relief, rendered with `pydeck`. Doubles as a live
teaching example for stated-vs-derived elevation: the drape is a sampled
guess at the ground, never written back into `Coordinate`.

- `terrain.py` is a stdlib-only single-band raster reader (tiled/stripped
  GeoTIFF, ESRI ASCII Grid) with two live clients - `EALidarWCSClient`
  (on-demand OGC WCS, the first-class adapter) and `OSTerrain50Client`
  (bulk-download-then-cache, the awkward fallback) - built and tested
  against real captured fixtures, no GDAL/rasterio.
- `drape.py` densifies and bilinear-samples USRN geometry, handling
  `MULTILINESTRING` as the normal case after a live pull showed it's 67%
  of real USRN geometries, not an edge case.
- `export_stl.py` adds a real "Export for 3D Print" button: a watertight
  heightmap mesh of the AOI (stdlib `struct`, no mesh library) with the
  USRN field embossed into its own top surface as a raised ridge, so the
  terrain supports the road by construction. Both deliberate distortions
  (print scale, 2.5x vertical exaggeration) are reported on the page and
  console, never applied silently.
- **A real rendering artifact found from a live screenshot, fixed not
  left in**: the ghost terrain mesh's blocky (strided) cells and the
  road's separately bilinear-sampled height could visibly disagree,
  letting a road appear to dip under the mesh. `render.py` now embosses
  the road into the ghost mesh and lifts it to clear whatever cell
  renders beneath it, both computed from the same numbers so they can't
  disagree - verified against real Durham LIDAR data with zero
  violations.
- A generated real-output HTML showcase and screenshot were added the
  same day, alongside two small test-infrastructure fixes (a missing
  `pytest` import, skipping tests cleanly when `pydeck` isn't installed).

### Added — Greece, a documented-unavailable scaffold (2026-08-03)

`streetworks.greece` - Greece is now registered (`verified=False`)
rather than left off the board, the same honest treatment Road Report
NT and MapRoad Roadworks Licensing already established.

- **Greece's real NAP (`nap.gov.gr`, confirmed as the official
  MMTIS/RTTI/SRTI/SSTP access point per the European Commission's own
  October 2025 NAP list) carries no roadworks source at all** - a
  decentralised metadata catalogue (CKAN), not a centralised DATEX II
  feed. Its own real dataset titles were checked directly: truck
  parking, KTEL timetables, Thessaloniki floating car data, and real
  toll-operator sensor feeds (Attiki Odos VDS, Egnatia Odos RWIS,
  Hellastron VMS) - POI/sensor data, no roadworks or Situation
  publication anywhere.
- **A second, independent reason: the portal is genuinely down right
  now** - confirmed live (2026-08-03), a real 502 Bad Gateway on its own
  CKAN backend (both the dataset list and its own
  `/api/3/action/package_list` endpoint), and a TLS handshake hang on
  its `imet.gr` mirror.
- `GreeceClient()` always raises the existing `ProviderUnavailableError`
  immediately, no network call, mirroring NT/MapRoad's own
  documented-scaffold shape exactly.
- Registry entry (`greece`, `verified=False`), import-time
  `UserWarning`, a drafted GitHub issue in
  `docs/credentials-wanted-issues.md` (`help wanted` only), a new
  README section, and 7 new tests covering the informative raise and
  registry consistency.
- `examples/roadworks_world_map.py` gained real Italy and Greece
  centroids, so both now plot correctly alongside every other
  registered territory.

### Added — CCISS (Italy), this SDK's first Italian coverage, a keyless RSS win (2026-08-03)

`streetworks.cciss` / `streetworks.common.from_cciss` - Italy's own
confirmed official RTTI/SRTI National Access Point (per the European
Commission's own October 2025 NAP list, `cciss.it` is listed for both
delegated regulations), reached via its real, public, keyless RSS feed
rather than the registration-gated DATEX II route the source
investigation only considered.

- **A real, immediately-buildable win the source investigation didn't
  find** - confirmed live: 100 real items, 78 real roadworks after
  classification, no credentials, no registration. The registration-
  gated DATEX II route (same domain, richer structured data) remains a
  real, separate, later option.
- **Same shape as TrafficWatchNI/Traffic Wales, genuinely different
  content mix** - reuses the established traveller-info RSS pattern
  directly, but unlike those two (already roadworks-only feeds), CCISS
  publishes one real stream mixing roadworks with weather, breakdowns,
  accidents, demonstrations and debris/spill incidents -
  `item.is_roadworks` is a real, evidenced classification (contains
  `lavori`/`personale su strada`/`pulizia del manto stradale`), not a
  closed enum, given the genuine variety of real Italian event-type
  text observed live.
- **No geometry** - confirmed directly against the real live XML,
  correcting an earlier AI-summarised claim (from reading the CCISS
  homepage, not the actual feed) that items were georeferenced.
- **A real multi-day date-range parser** for Italian temporal clauses
  (e.g. `"dalle 21:35 del 3 alle 05:00 del 4 agosto 2026"` - day 3 to
  day 4, month/year stated once) - verified against real live examples,
  not synthetic.
- **A false lead caught and ruled out before it shipped**: an early
  regex-based check suggested each item's embedded road name was offset
  by one from its own title - re-checked via proper XML parsing and
  found to be a self-inflicted extraction bug, not a real feed defect,
  flagged in the module docstring so it isn't rediscovered.
- Registry entry (`cciss`, `source_grade=traveller_info`,
  `network_scope=STRATEGIC`, licence unconfirmed), `scripts/smoke_test.py`
  check, README section, and 14 new tests against a real 8-item fixture
  covering every real temporal/spatial clause shape found live.

### Added — Chicago CDOT Street Closures, this SDK's second US city permit register (2026-08-03)

`streetworks.chicagodot` / `streetworks.common.from_chicagodot` -
reuses `streetworks.socrata` and the NYC permit-register pattern
directly, confirming the multi-city Socrata shape works a second time.

- **The obvious primary dataset id is dead - found live, not
  guessed.** `6fd2-pzze` ("CDOT Permits") returns a genuinely empty
  schema (`X-SODA2-Fields: []`) despite 2.3M historical rows. The real,
  current dataset is `jdis-5sry` ("...- Street Closures", 46 columns,
  466,829 real rows, confirmed updated the same day as this build) - a
  Chicago-maintained view already filtered to 3 of 11 real
  `applicationtype` values.
- **Genuinely cleaner than NYC in two real ways** - native WGS84 GeoJSON
  Point geometry (no WKT/State-Plane CRS question), and both geometry
  and dates populated on 99.94% of real rows (vs. NYC's own 80.5%
  geometry rate).
- **The view's own pre-filter alone isn't sufficient** - a finer real
  field, `worktype`, still mixes in confirmed non-roadworks activity
  even within the pre-filtered applicationtypes (`BlockParty`, 53,679
  real rows; `Festival`; `Filming`; `Parade`; ...) - `iter_roadworks()`
  filters on 7 real, evidenced roadworks worktypes instead.
- **A real Works-umbrella grouping, the same shape as NYC's** -
  `applicationnumber` genuinely groups multiple real rows (one real
  application had 64 real rows across 64 genuinely different street
  locations).
- No stated join to a street register (confirmed by direct schema
  inspection); licence unconfirmed, the same honest-gap tier as NYC.
- Registry entry (`chicagodot`, territories `USA` + `Chicago`, matching
  nycdot's own city-territory pattern - a real Chicago map centroid
  added to `examples/roadworks_world_map.py`), `scripts/smoke_test.py`
  check, README section, and 14 new tests against a real 6-row fixture
  covering the multi-row grouping, native Point geometry, a missing-
  geometry row, and a real `BlockParty` (non-roadworks) row.

### Confirmed — Florida DOT and Austin, TX join the WZDx keyless population (2026-08-03)

No code changes needed - the registry-driven WZDx design already covers
any registered feed. Live-confirmed and documented: `fldot` (17,932 real
events, 3,386 work-zones) and `austin` (2,791 real events, 100%
work-zone, CC0-licensed - the cleanest feed found anywhere in this SDK).
Also corrects a population-target assumption: no statewide California
WZDx feed is registered at all (only the keyed Bay Area `mtc`), and
Texas's own statewide feed (`txdot_v4_2`) needs a key too - Austin is
the real keyless Texas win.

### Added — MapRoad Roadworks Licensing (Ireland), a documented-unavailable scaffold (2026-08-03)

`streetworks.maproad` - Ireland is now registered (`verified=False`)
rather than left off the board, following an investigation that first
ruled out TII's own DATEX II feed and then settled the real MapRoad
Roadworks Licensing system's read-vs-write question.

- **TII's DATEX II feed (`data.tii.ie`) ruled out first, not assumed.**
  Its real dataset catalogue (verified against its data.gov.ie mirror -
  all 20 real dataset titles enumerated) carries travel times, weather,
  VMS/VDS, collision rates, and traffic counts - no roadworks/Situation
  publication at all.
- **MapRoad Roadworks Licensing is the real roadworks source - a
  genuine national permit register covering both national and local
  roads** - but Ireland's own PSB Data Catalogue metadata (`API
  Available: Yes`, `Open Data: No`, `Data Sharing: Yes`, `Personal Data:
  Yes`, read together) describes a formal, GDPR-gated data-sharing
  arrangement, not a self-service developer key. Registration for
  MapRoad itself is a real, formal applicant process (a registration
  pack emailed to `contact@rmo.ie`), aimed at licence submitters, not
  read-only consumers. No endpoint/schema/auth mechanism for a read path
  was found published anywhere.
- **A distinct tier from every other unverified provider** - not blocked
  on a key (Trafikverket/Vejdirektoratet/SA/LINZ Roads), and not "no
  interface at all" the way Road Report NT is - a real, catalogued API
  exists, just for a different consumer class. `MapRoadClient()` always
  raises the existing `ProviderUnavailableError` immediately, no network
  call, mirroring NT's own documented-scaffold shape exactly.
- Registry entry (`maproad`, `verified=False`, `source_grade=register` -
  the real classification if it were reachable), import-time
  `UserWarning`, a drafted GitHub issue in
  `docs/credentials-wanted-issues.md` (`help wanted` only, not
  `credentials-wanted`), a new README section, and 7 new tests covering
  the informative raise and registry consistency.

### Added — NYC DOT Street Construction Permits, a genuine US permit register (2026-08-02)

`streetworks.nycdot` / `streetworks.common.from_nycdot` - the local
follow-on the WZDx feed-registry harvest deliberately scoped out. 511NY
covers New York *State* highways over WZDx; NYC's five boroughs are a
separate authority (NYC DOT) publishing an entirely separate shape -
NYC Open Data (Socrata), not WZDx at all.

- **A genuine permit register - this SDK's second `source_grade=register`
  source (after England's Street Manager) and the first in the US.**
  Confirmed live 2026-08-02, credential-free, 3,798,494 real rows total.
  A real Works-umbrella grouping matches Street Manager's own shape:
  `applicationtrackingid` genuinely groups multiple real permits (one
  real application had 226 permits under it) - `from_nycdot` groups by
  it the same way `from_wzdx` groups by `works_ref`.
- **No stated join to a street register** - the real 39-column schema
  has no LION `segmentid` or any other street identifier, only free-text
  cross-streets - `WorksSite.street_ref` is never populated, settling
  a genuinely open question honestly. Real geometry
  exists anyway: a real `wkt` column populated on 80.5% of all rows
  (`LINESTRING`/`POINT`/a real, confirmed-live `MULTIPOINT` shape - added
  support for the latter to the shared `_wkt` helper, previously
  unhandled), native CRS EPSG:2263 (NAD83/New York Long Island),
  inferred from coordinate-value evidence, never reprojected.
- **Permit-type filtering needed real evidence** - `iter_roadworks()`
  filters to two confirmed roadworks series (`STREET OPENING PERMIT`,
  `DOT IN-HOUSE PAVING AND MILLING`); `BUILDING OPERATION PERMIT` is
  genuinely mixed at the finer `permittypedesc` level and deliberately
  excluded rather than guessed at, the SA-`REC_TYPE` discipline.
- **New `streetworks.socrata`** - a generic Socrata (SODA) client,
  factored out of `streetworks.wzdx.registry` (refactored to use it,
  behaviour unchanged, 7 existing tests still pass unmodified) when
  this provider needed the identical shape - real `$limit`/`$offset`
  pagination, optional app token.
- Registry entry (`nycdot`, `source_grade=register`, `network_scope=
  COMPREHENSIVE`, licence unconfirmed - NYC Open Data states no formal
  reuse licence), `scripts/smoke_test.py` check, README section, 20 new
  tests (5 `test_socrata.py`, 15 `test_nycdot.py`) against a real
  6-permit fixture covering the multi-permit grouping, all three real
  WKT geometry shapes, and a real no-geometry permit.

### Added — WZDx feed-registry harvest: CWZ/version filtering, auth tiers, 511NY verified end-to-end (2026-08-02)

`streetworks.wzdx.registry` extended, not rebuilt - the existing
`WZDxClient.fetch()` (version-tolerant v3.1-v4.2 parser) and
`list_feeds()` already matched the intended "registry-driven, not
per-state adapter" shape; what was missing was CWZ/version
awareness and auth-tier modelling on `RegistryEntry` itself.

- **A real correction to an early CWZ-filter assumption.**
  Confirmed live (2026-08-02, 41 real registry rows): the `format`
  column never distinguishes WZDx from CWZ (Connected Work Zone, a
  different ITE schema) - it's always just `"geojson"`/`"json"`. The
  real discriminator is `version == "CWZ 1.0"` (4/41 rows). `list_feeds()`
  now defaults to `wzdx_only=True`, filtering on the real field via the
  new `RegistryEntry.is_supported_wzdx` property - a documented skip
  (also catching a real missing-version row and enforcing a 3.1 floor),
  never a silent CWZ mis-parse.
- `RegistryEntry` gained `needapikey`/`apikeyurl` fields - real shape
  confirmed live: `needapikey` is `true` on 13/41 rows, explicit `false`
  on 1, and simply **absent** (not `false`) on the other 27, now parsed
  as "no key needed" rather than left unmodelled.
- **511NY (NYSDOT) confirmed live end-to-end** - the first concrete
  verified US feed via the actual registry pipeline: `list_feeds()` ->
  real NY row -> real fetch (`https://511ny.org/api/wzdx`, no key) ->
  real parse, 6,895+ real events. A real correction to the initial
  geometry assumption: 100% `MultiPoint`, not `LineString` - both are
  legitimate WZDx shapes, this just wasn't the one guessed.
- **A real, live, active Quebec City (Canada) feed is registered too** -
  `streetworks.common.from_wzdx`'s own docstring corrected from "USA
  true for every feed observed" to reflect this; territory/
  administrative_area were already per-feed parameters (not hardcoded),
  now documented as load-bearing rather than incidental.
- NYC DOT (local-street works, a separate Socrata feed, not in this
  registry) recorded as the deliberate, not-yet-built follow-on.
- `scripts/smoke_test.py` gained a dedicated registry-pipeline check
  (list feeds -> find 511NY -> fetch -> parse, plus the real needs-key
  count), the main registry's `wzdx` entry `scope_note` updated, README's
  WZDx section rewritten to show the registry-driven pattern, 6 new
  tests in `test_wzdx_registry.py` against an extended real fixture
  (added a real Colorado `needapikey=true` WZDx row and its real CWZ
  sibling).

### Added — G-NAF & National Roads (Australia), this SDK's first AU gazetteer coverage (2026-08-02)

`streetworks.gnaf` / `streetworks.common.from_gnaf_address`/
`from_gnaf_road` - both confirmed live, credential-free, over the
**Digital Atlas of Australia** (`digital.atlas.gov.au`), a whole-of-
government ArcGIS Online platform, not Geoscape's own commercial API.

- **A real correction to the source investigation.** It was initially
  assumed Australia has no clean national *open* road-centreline register,
  because Geoscape's own **Roads** product is commercial. True of
  Geoscape's direct API - but the Digital Atlas re-publishes an open
  derivative of both G-NAF and Geoscape Roads anyway, under CC BY 4.0,
  found by resolving each dataset's Digital Atlas item to its real
  underlying ArcGIS `FeatureServer` URL (not documented on the JS-
  rendered dataset landing pages themselves). This supersedes the
  earlier fallback plan (SA's CRRS / Tasmania's State Roads as
  state-scoped consolation prizes).
- **National Address Points (G-NAF derivative)** - 15,901,249 real
  addresses, native SR EPSG:7844 (GDA2020), `outSR=4326` confirmed
  honoured live. Real stated identifier `ADDRESS_DETAIL_PID`; no
  separate street/locality PID on this derivative (street identity is
  text only, the same "no street table of its own" shape as `bag`). A
  real `unit`/flat concept (`FLAT_TYPE`/`FLAT_NUMBER`) confirmed as the
  *second* built source with this gap, after `linz` -
  `gazetteer.Address`'s own docstring updated to reflect both. Licence
  CC BY 4.0 plus a genuine mandatory restriction on generating
  mail-address lists without independent verification.
- **National Roads (Geoscape Roads derivative)** - 4,346,217 real
  segments, genuinely comprehensive: real `hierarchy` values reach
  `LOCAL ROAD` (the largest single value), `FOOTPATH` and `CYCLEPATH` -
  beyond even TIGERweb's own local-road layer. `road_id` is real but
  segment-scoped, not an aggregated named-street id, and no separate
  named-street layer exists - emits `Segment` only, never `Street`, the
  same discipline `from_nwb` already established. Real `status` values
  include both `OPERATIONAL` and `PROPOSED` (not-yet-built) roads -
  `iter_roads()` is the raw network, unfiltered by default. Licence CC
  BY 4.0, no extra restriction.
- **No stated join between addresses and roads** - resolves the source
  investigation's own join question, on better evidence than it had:
  neither layer states a reference to the other, and a name match
  (`STREET_NAME` against `full_street_name`) is forbidden by this SDK's
  stated-identifiers-only rule.
- Registry entries `gnaf` (addresses, verified) and `gnaf_roads`
  (streets, verified) - both fully live-verified from day one, no
  Credentials-wanted scaffold needed. `scripts/smoke_test.py` checks for
  both, README provider table row and a new `## G-NAF & National Roads
  (Australia)` section.
- 16 new tests (`test_gnaf.py`) covering client wiring and converter
  behaviour against real ACT-scoped fixtures, including the real
  unnamed-local-road gap, the `PROPOSED` status value, and a hand-built
  `MultiLineString` case (no real sample pulled so far happens to be
  multi-part).

### Added — NZTA & LINZ (New Zealand), this SDK's first NZ coverage (2026-08-02)

`streetworks.nzta` / `streetworks.common.from_nzta` and
`streetworks.linz` / `streetworks.common.from_linz_address`/
`from_linz_road`/`from_linz_road_section` - two new top-level packages,
not a combined `nz` package (same reasoning as Norway's
`kartverket`/`nvdb`/`vegvesen` split: different agencies, different
technologies, sharing a country only incidentally).

- **NZTA (Waka Kotahi) Highway Information - Road Events** - confirmed
  live 2026-08-02 (104 real records), credential-free, shipped
  live-verified with a real fixture from day one. A real correction to
  the source investigation: this is the ArcGIS open-data portal service,
  not the bespoke `trafficnz.info` REST/SOAP API also considered -
  reuses the existing `ArcGISFeatureClient`. Two real layers share an
  identical field schema but never overlap on `eventId`: layer 0 ("Road
  Events", point) is roadworks-relevant; layer 1 ("Road Area Events",
  polyline) is always `eventType=="Area Warning"`, not roadworks at all -
  confirmed live, ruling out a Victoria/QLD-style corridor trap. Real
  `status`/`eventType` correlate perfectly, giving the richest real
  VERIFIED/ESTIMATED `DateConfidence` signal confirmed anywhere in this
  SDK so far. No structured road/route identifier anywhere in the real
  schema (free text only) - settles the works-to-LINZ join question
  directly: `from_nzta` never populates `WorksSite.street_ref`, the same
  SA-`ROAD_NO` discipline. Licensed NZTA 4.0 BY CC (a CC BY 4.0 variant).
- **LINZ (Toitū Te Whenua) NZ Addresses** - confirmed live 2026-08-02
  (2,421,642 real addresses, per the layer's own `feature_count`), a
  public ArcGIS Online mirror needing no LINZ Data Service key at all, CC
  BY 4.0. A real, newly-discovered `unit`/flat-number concept (e.g. `"2"`
  in `"2/49 Pigeon Mountain Road"`) that `Address`'s own docstring already
  flagged as absent from every source built so far - no canonical field
  yet, stays on `.raw` only, alongside `is_land` (a real boolean concept
  the live layer states as `esriFieldTypeString` length 2, so real values
  are the truncated `"tr"`/`"fa"`).
- **LINZ NZ Addresses: Roads/Road Sections** - registered as a Phase 1
  scaffold (`linz_roads`, `verified=False`), the same tier as
  Trafikverket/Vejdirektoratet: schema and a real attribute sample (not
  geometry) confirmed live from LINZ's own public, keyless Koordinates
  metadata API, but the actual WFS pull has never been exercised - needs
  a genuine LINZ Data Service (LDS) API key this build doesn't have. The
  real WFS URL shape is documented and implemented (API key embedded in
  the URL **path**, Koordinates' own convention, confirmed live from the
  layer's own `/services/` listing). Open question, flagged not guessed:
  whether `road_id` (the same field name across all three layers'
  schemas) genuinely cross-references between Addresses and Roads/Road
  Sections - the real samples pulled so far just happen not to overlap.
- Registry entries `nzta` (roadworks, verified), `linz` (addresses,
  verified), `linz_roads` (streets, `verified=False`) - `linz_roads`
  joins the "Credentials wanted" unverified tier alongside
  `trafikverket`/`vejdirektoratet`/`sa`/`nt`. `scripts/smoke_test.py`
  checks for all three (`LINZ_API_KEY` gates the roads/sections check),
  a drafted GitHub issue in `docs/credentials-wanted-issues.md`, and a
  new README section (`## NZTA & LINZ (New Zealand)`).
- 23 new tests (9 `test_nzta.py`, 14 `test_linz.py`) covering client
  wiring (including the real `;key=` WFS URL shape and `startIndex`/
  `count` pagination, unexercised against a real response) and converter
  behaviour against real/real-attribute fixtures.

### Added — Road Report NT (Australia), a documented-unavailable scaffold (2026-08-01)

`streetworks.au.nt` - the Northern Territory is now registered
(`verified=False`) rather than left off the board entirely, formalising
the finding from the AU-tail investigation: Road Report NT has **no
published REST/GeoJSON API at all**, so `RoadReportNtClient()` always
raises the new `streetworks.exceptions.ProviderUnavailableError`
immediately, with no network call, no parser, and no synthetic fixture.

- **A distinct tier from every other unverified provider.** Trafikverket/
  Vejdirektoratet/Traffic SA are all blocked on *access* to a real,
  published interface (a key, a token, a region) - they have a documented
  or at least self-describing contract to build against, just can't
  currently reach it. NT is different in kind: its only real backend is
  an undocumented SignalR real-time hub (`roadsReportingHub`, invoking
  hub methods like `GetAllMajorRoadObstructions`), reverse-engineered
  from the site's own minified Angular bundle, not a published spec.
  Building a client against that inference would present private-app
  implementation detail as a stable contract - the opposite of how every
  other provider here is built - so this ships as an honest, documented
  refusal instead.
- New `streetworks.exceptions.ProviderUnavailableError`, exported from
  the package root - distinct from `ProviderNotFoundError` (a registry
  lookup failure): NT is real and registered, its client class exists,
  but every entry point raises this rather than pretending to work.
- Registry entry (`nt`, `verified=False`, in the same honest-scaffold
  spirit as `sa`/`trafikverket`/`vejdirektoratet` but with its own
  distinct `scope_note` explaining the different blocker), import-time
  `UserWarning`, a drafted GitHub issue in
  `docs/credentials-wanted-issues.md` (labelled `help wanted` only, not
  `credentials-wanted` - no credential would fix this), and 7 new tests
  covering the informative raise and registry consistency.
- `au/__init__.py`, README, and this file all now agree: NT is
  investigated and honestly unavailable, not silently absent.

### Added — ACT & Tasmania (Australia), closing out the AU tail (2026-08-01)

`streetworks.au.act` / `streetworks.common.from_au_act_ttm` and
`streetworks.au.tas` / `streetworks.common.from_au_tas_roadworks` - the
sixth and seventh Australian providers, both confirmed live 2026-08-01
against real, unauthenticated pulls, credential-free, shipped with real
fixtures from day one.

- **ACT (Temporary Traffic Management, Roads ACT)** - the only AU
  provider with genuine municipal/local-street coverage (the ACT has no
  separate local-government tier, so this feed IS the whole real
  network). **A real correction to the source investigation**: this is
  ArcGIS underneath, not a new Socrata client shape - dataACT's own
  catalogue entry is a plain link/pointer (confirmed live:
  `viewType`/`displayType` both `"href"`, its SODA endpoint 400s for
  "non-tabular dataset") to a real ArcGIS Online FeatureServer. The "live
  vs. historical" gating question is resolved live: despite the
  underlying service being literally named
  `Road_Closures_public_view_HISTORICAL`, a real pull returns genuinely
  current 2026-dated closures. Real `type` values confirmed directly
  (34/98 real records are `roadWorks`) - `iter_roadworks()` filters
  server-side on evidenced criteria, unlike SA's still-unconfirmed
  `REC_TYPE`. Licensed CC BY-SA 4.0 (Share-Alike) - the only such licence
  in this AU cluster.
- **Tasmania (Roadworks - State Roads, Dept of State Growth)** - the only
  AU provider with real line geometry (every other member is points-only)
  and the smallest by far (10 real total records, confirmed via
  `returnCountOnly`). Native CRS is GDA94/MGA zone 55, genuinely different
  from WA/SA's Web Mercator - `outSR=4326` is confirmed honoured live, but
  this module deliberately does **not** reuse WA/SA's closed-form Web
  Mercator reprojection guard (the wrong formula would silently produce
  *wrong* coordinates, not just imprecise ones, if `outSR` ever stopped
  being honoured) - `scripts/smoke_test.py` carries a plausible-range
  check instead. **Licence genuinely unconfirmed**, checked directly (the
  ArcGIS item's own `licenseInfo`/`accessInformation` are both `null`,
  and this service isn't even hosted on the LIST portal the licence was
  first guessed from) - shipped anyway on the same openly-queryable
  basis as `streetworks.arcgis.jersey`, distinct from being blocked the
  way SA is.
- **The Northern Territory was investigated and found to have no
  published REST/GeoJSON API at all** - its real backend is a SignalR
  real-time hub (`roadsReportingHub`, confirmed live by reverse-
  engineering the site's own minified Angular bundle), a materially
  different, undocumented client protocol this SDK has never needed
  elsewhere, on top of already-flagged concerns
  (thin roadworks content, unspecified licence). Registered as a
  documented scaffold rather than silently omitted - see "Road Report NT"
  below for the follow-up that formalised this.
- Added `tests/fixtures/act_ttm_live_pull.json` (five real trimmed
  features) and `tests/fixtures/tas_roadworks_live_pull.json` (four real
  trimmed features), 15 new tests, registry entries (`act`, `tas`),
  credential-free `scripts/smoke_test.py` checks, and README/CHANGELOG
  updates.

### Added — Traffic SA / DIT Roadworks (Australia), a Phase 1 scaffold (2026-08-01)

`streetworks.au.sa` / `streetworks.common.from_au_sa_trafficsa` - the
fifth Australian provider, over an ArcGIS **MapServer** (not WA's
FeatureServer), and the least verified provider in this SDK. Genuinely
blocked on **two independent access gates**, not one: the query endpoint
returns HTTP 400 without an ArcGIS token from
`location.sa.gov.au/arcgis/tokens/` (whether that's self-service or
gated by DIT is itself unresolved - the token host has never been
reached), and `maps.sa.gov.au` separately CloudFront-blocks some
countries' network egress outright. **No real feature has ever been
retrieved** - the schema is ground truth from a real, successfully-pulled
layer *metadata* request, but every field-population/join question stays
open, the same "schema confirmed, data not" position
`streetworks.datex2.trafikverket`/`streetworks.datex2.vejdirektoratet` are
in.

- `iter_roadworks()` deliberately returns the layer's full, unfiltered
  `REC_TYPE` mix (roadworks + incidents together) rather than fabricate a
  filter value with zero real evidence behind it - a caller who has
  confirmed the real value can pass `where="REC_TYPE='...'"` themselves.
- `ROAD_NO`/`GIS_LINK_ID` - candidate stated-identifier road-register join
  keys, a potential first for this AU cluster (every other provider is
  name-only) - deliberately do **not** populate `WorksSite.street_ref`,
  since population and real join semantics are unconfirmed; both values
  stay reachable on `.raw` only.
- `streetworks.arcgis.client.ArcGISFeatureClient.iter_features()` gained
  an `extra_params` parameter, threaded through every `/query` call but
  never `layer_info` (which stays public even when the query operation is
  gated) - the escape hatch this provider's ArcGIS token needs, reusable
  by any future token-gated ArcGIS provider.
- Extracted `streetworks.common._web_mercator` (the closed-form EPSG:3857
  inverse first built for WA) as a shared helper, now used by both WA's
  and SA's converters rather than duplicated - WA's own module and tests
  updated to import from it.
- Registered `verified=False` (joining Trafikverket/Vejdirektoratet in the
  registry's "Credentials wanted" tier); `scripts/smoke_test.py` check
  added; a synthetic fixture (built from the real, live-pulled layer
  schema, not invented) since no real record has ever been retrieved;
  README/`docs/credentials-wanted-issues.md`/`.env.example` updated.

### Added — QLDTraffic Events (Australia), a fourth `streetworks.au` shape (2026-08-01)

`streetworks.au.qld` / `streetworks.common.from_au_qld_qldtraffic` - the
fourth Australian provider, and the first with **no credential wait at
all**: a real, globally-shared public API key is published in plaintext by
TMR's own API specification, intended for exactly this use (rate-limited
100 req/min, shared across every anonymous consumer of the API worldwide -
`QldTrafficClient` defaults to it). Confirmed live 2026-08-01 against a
real pull (458 real events, 244 real `Roadworks`) - never a
Credentials-wanted scaffold.

- **One adapter, parameterised over `event_type`** - the NSW pattern, not
  Victoria's - but with no server-side type filter at all (a single
  endpoint returns every event type mixed); `iter_roadworks()` filters the
  real feed client-side. No pagination - confirmed live, a single pull
  returns the whole current feed.
- **Two real doc-vs-reality mismatches, found by checking, not assumed**:
  the source API specification claims `geometry.type` is always
  `GeometryCollection` - real data says only 2.2% of features actually
  are (the rest are a bare top-level `MultiLineString` or `MultiPoint`,
  both now handled); the spec's own `source_name` enum lists exactly three
  values - real data has five, including two genuinely undocumented ones
  (`Asignit`, `MBRC`), both real Queensland local-government republishing
  routes.
- **Real coordinates are `EPSG:7844` (GDA2020), not WGS84** - confirmed
  live on every single feature via its own embedded GeoJSON `crs` member,
  never assumed or silently relabelled `EPSG:4326` the way the initial
  "WGS84" framing would have.
- **A deliberate, evidence-based departure from Victoria's own "prefer the
  Point, drop the LineString" precedent**: 88.5% of real Roadworks events
  have no Point at all, only a LineString - dropping it the way Victoria's
  converter does would leave most Queensland roadworks with no geometry
  whatsoever, not a safe simplification. A real span check found the
  truth is genuinely mixed (median ~1.07 km, worksite-scale; a real ~9%
  tail runs 20-133 km, corridor-scale) - the LineString(s) are now carried
  through honestly as the source's own stated "affected road extent" via
  `Coordinate.points`/`parts`, rather than dropped or given a false
  precision claim. The one real `area_alert=true` event confirms the
  documented exclusion mechanism (the last geometry in the collection is
  the alert polygon) works exactly as specified.
- **`administrative_area` is per-record from `source.provided_by`, not a
  hardcoded operator name** - a deliberate departure from every other AU
  converter in this SDK. Confirmed live: 100% populated across 244 real
  Roadworks records, 17 distinct real values (TMR the plurality, but also
  a private tollway operator and 15 different Queensland local
  government/disaster-management authorities) - richer and more accurate
  than one fixed string. `promoter` carries `source.source_name` instead.
  `Works.reference` is the bare `id`, confirmed globally unique across the
  whole real feed (not just within Roadworks), so no composite key is
  needed the way NSW's per-layer id required.
- Added `tests/fixtures/qld_qldtraffic_live_pull.json` (seven real trimmed
  events covering every real geometry shape found, a non-TMR/council-
  sourced record, and the one real `area_alert=true` event) and 20 new
  tests. Registered in the registry (`qld`), `scripts/smoke_test.py`
  (`check_qld_qldtraffic`, credential-free by default), `.env.example`
  (an entirely optional private-key override), and README.

### Added — Main Roads WA (Australia), a third `streetworks.au` shape (2026-07-31)

`streetworks.au.wa` / `streetworks.common.from_au_wa_mainroads` - the third
Australian provider, and the third genuinely distinct AU client shape (NSW:
one feed, many layers, one schema; Victoria: two independent systems; WA: a
single ArcGIS `FeatureServer` layer). **Credential-free, shipped
live-verified with a real fixture from day one** - unlike NSW/Victoria,
never a Credentials-wanted scaffold.

- **A thin wrapper over the existing, generic `ArcGISFeatureClient`**
  (`streetworks.arcgis.client`), not a new pagination implementation -
  `WaMainRoadsClient` supplies this service's own `base_url`/`layer_id`,
  the same shape `streetworks.arcgis.jersey` already established. The
  real layer states genuine `supportsPagination: true` and its real total
  (227 records, one live pull) sits well under its own `maxRecordCount`
  (2000), so a single unpaged query already returns everything today -
  but pagination is still wired through properly rather than assuming
  that stays true as the dataset grows.
- **Gating check 1, verified live: `outSR=4326` is honoured** by this
  service (real WGS84-range coordinates confirmed) - but since GeoJSON
  strips any per-feature CRS statement, a runtime coordinate guard is
  built anyway: any point outside plausible WGS84 degree range is treated
  as unreprojected Web Mercator metres and reprojected explicitly. **A
  deliberate deviation from the original plan**: uses a small closed-form
  spherical-Mercator inverse formula instead of `pyproj` (the initial
  suggestion) - the exact algebraic inverse of EPSG:3857's own spherical
  definition, not an approximation, chosen to avoid adding a heavy
  geospatial dependency this SDK has explicitly avoided everywhere else
  (see `ArcGISFeatureClient`'s own module docstring for the same
  reasoning applied when it was first built).
- **Gating check 2, pinned from real data, not guessed**: `DateStarte`/
  `EstimatedC`/`EntryDate` are plain strings; a full live pull (227 real
  records, 681 date values) confirms `DD/MM/YYYY HH:MM:SS` unambiguously
  (397 real values have a day > 12, zero have a month > 12).
- **Real findings from that same live pull, not anticipated beforehand**:
  `Road` states the literal sentinel `"LOCAL ROAD"` (not a real road name)
  on 28/227 (~12.3%) records - `LocalRoadName` carries the real name in
  exactly those, confirmed perfectly mutually exclusive across every real
  record checked; resolved before it could leak into
  `location_description`. `WorkStatus` is a real field, confirmed
  **always empty** (0/227) - so every site this module builds grades
  `DateConfidence.ESTIMATED`, never `VERIFIED`, there being no live signal
  to justify promoting. `WorkType` carries a real fifth value, `"PTA
  Works"`, beyond the four the source's own ArcGIS item catalogue
  documents. `SeeMoreName` is confirmed always `null`; `SeeMoreUrl` is
  real but not always a well-formed absolute URL (one real value has no
  `https://` scheme at all) - carried through exactly as stated.
- `network_scope` stays `NetworkScope.UNKNOWN`, not promoted - the real
  local-road minority (~12.3%) is far larger than NSW's own (~1.7%, which
  was judged small enough to promote to `STRATEGIC`), so honest-unknown
  was chosen over a confident guess, per the original instruction.
- **Reference is keyed on `GlobalID`** (a genuine, confirmed-unique GUID),
  **never `FID`** - this is a real `isView: true` ArcGIS view, so its own
  object ids are reassignable view artefacts, not stable identity.
- Licensed **CC BY 4.0**, confirmed live from the ArcGIS item's own
  catalogue metadata (`licenseInfo`) - the layer's own `copyrightText` is
  empty, so attribution genuinely doesn't ride on the layer itself, as
  first expected. `administrative_area="Main Roads Western
  Australia"`, the operator-as-authority rule already applied to Autobahn
  GmbH/TfNSW/DTP.
- Added `tests/fixtures/wa_mainroads_live_pull.json` (five real trimmed
  features from a real, unauthenticated pull) and 16 new tests covering
  the coordinate guard both ways, the DD/MM date lock, the `LOCAL ROAD`
  sentinel resolution, and the full field mapping.
- Registered in the registry (`wa`), `scripts/smoke_test.py`
  (`check_wa_mainroads`, credential-free), and README.

### Fixed / Confirmed — real credential verification (2026-07-30)

A tester ran `scripts/smoke_test.py` against three Credentials-wanted
scaffolds with their own real credentials - Statens vegvesen (Norway),
TfNSW Live Traffic (NSW), and DTP Planned Disruptions (Victoria) - the
exact contribution the Credentials-wanted section has been asking for.
All three graduated to `verified=True` and out of the README's
Credentials-wanted section (now just Sweden/Denmark). Real data found
and fixed two real bugs, found one real unresolved limitation worth
shipping with a loud caveat rather than silently guessing around, and
confirmed most of what Phase 1 had only guessed at for all three.

- **NSW: a real bug, found and fixed** - the correct endpoint paths are
  `roadwork/open`-style, not `roadwork-open.json`-style. Phase 1 had
  read TfNSW's own Developer Guide Table 1 literally and trusted it over
  an earlier paraphrase, reasoning the primary document was more
  authoritative - a live pull proved this backwards:
  `roadwork-open.json` returns a genuine `404` even with a valid key,
  while `roadwork/open` returns real data (363 roadwork + 19 majorevent
  features in one pull). A humbling, generalisable lesson: reading a
  primary source directly doesn't always beat a live probe. Also
  confirmed: `apikey <key>` auth was correct on the first real attempt;
  the main `roadwork` layer genuinely includes a small real local-road
  minority (6/363, ~1.7%) and a small real ferry-hazard impurity (5/363,
  `mainCategory: "FERRY OUT OF SERVICE"`) - both documented, neither
  filtered out. `network_scope` promoted from `UNKNOWN` to `STRATEGIC`
  (with the local-road minority noted). Real `id` values are sometimes
  JSON floats (e.g. `281450.0`) - normalised to `int` before building
  the composite `layerName:id` reference so it never renders a spurious
  `.0`. Added `tests/fixtures/nsw_livetraffic_live_pull.json` (three real
  trimmed features: state-road, local-road, and ferry) alongside the
  existing Developer-Guide-sourced fixture.
  **A second real bug, found the same day via a follow-up check prompted
  by the Victoria lesson below**: the raw `layerName` a real response
  states is not status-independent - `roadwork/open` returns
  `layerName: "Roadwork-Open"`, `roadwork/closed` returns
  `"Roadwork-Closed"`, and `roadwork/all` returns bare `"Roadwork"`
  (`majorevent/*` mirrors this exactly) - three different strings for
  the *same* layer, varying only by which status endpoint was queried.
  Building `Works.reference` from the raw value meant the same real
  hazard got a *different* reference depending on whether a caller used
  `status="open"` or `status="all"` - silently breaking any
  deduplication/tracking keyed on it. Fixed: `parse_features` now also
  computes a normalised `layer` field (`_normalize_layer` strips a real,
  confirmed `-Open`/`-Closed` suffix, case-insensitively), and
  `from_nsw_livetraffic` builds the composite reference from `layer`,
  not `layerName` - the raw value stays available verbatim alongside it.
  Also extended the `encodedPolylines` documentation with the same
  caution Victoria's real LineString-spans-an-entire-route finding
  raises: whether a real NSW polyline (never seen populated yet) is
  worksite linework or a broader affected-corridor/diversion extent is
  unconfirmed, and should not be assumed precise without checking.

- **Victoria: a real design mistake in this SDK's own converter, found
  and fixed** - `from_vic_disruptions._coordinate` preferred a
  GeometryCollection's LineString over its Point, assuming they were
  coarse-vs-precise views of the same site (the DATEX/WZDx shape). A
  real feature disproved this: its LineString spanned ~150km end to end
  (matching `srns: "M31,B400"` - the entire Hume Freeway corridor), while
  its Point sat at the actual disruption site within that span. Promoting
  the LineString to `Coordinate.points` would have silently replaced one
  worksite with an entire highway - now the Point is always preferred and
  the LineString is never used. Also confirmed: coordinate order is
  genuinely `[lon, lat]`; `duration.start`/`end` are naive ISO-8601 with
  **no UTC offset at all** (genuinely ambiguous local-vs-UTC, carried
  through as a timezone-naive `datetime` rather than guessed);
  `recurrences[].duration` is a real ISO-8601 duration string (e.g.
  `"PT6H"`); `impact.delay` holds real free-text ranges (e.g. `"0 to 5
  min"`), confirming Phase 1's choice never to coerce impact fields to a
  number; `endIntersectionRoadName`/`endIntersectionLocality` (not in the
  OpenAPI spec's own schema, only found in a real response) are genuinely
  common (92% populated) and now included in `location_description`; and
  the `KeyID` auth header finding from Phase 1's gateway probe was
  independently reconfirmed by a real key succeeding via that exact
  header. Replaced the synthetic fixture with one real trimmed feature
  (its LineString trimmed to 16 of 2,115 real vertices to keep the file a
  reasonable size).

- **Norway: real coordinates are mixed CRS within the same feed** -
  roughly 76% UTM zone 33N (`EPSG:25833`, confirmed via a real
  `srsName="25833"` attribute) and roughly 24% genuine WGS84, checked
  directly across 844 real roadworks records - not the Belgium/Lithuania
  shape (one CRS override for the whole feed via `from_datex2(crs=...)`),
  since no single `crs=` value is correct here. Initially shipped as a
  loudly-documented open limitation; **now resolved** - see "Norway
  mixed-CRS resolution + shared CRS helper" below. Everything else
  confirmed cleanly: genuine DATEX II **v3** (`modelBaseVersion="3"`,
  resolving the v3.1-vs-v2.0 catalogue discrepancy), a **bare**
  `<messageContainer>` response (not the SOAP envelope Iceland's
  precedent fixture arrives in), real Norwegian-language comments, real
  road numbers, HTTP Basic auth, no IP allow-listing needed, and a
  ~24 MB real response size (confirming the streaming-parser trade-off is
  genuinely warranted, not overcautious). A previously-undocumented real
  location wrapper, `LocationGroupByList`, and real NVDB
  `externalReferencing` values (confirmed present, still not resolved
  into geometry) were also found. Added `tests/fixtures/vegvesen_real_pull.xml`
  (two real trimmed Norwegian situations - one WGS84, one UTM33N - kept
  as a pair specifically to regression-test the mixed-CRS finding)
  alongside the existing Iceland precedent fixture.

- All three modules' import-time `UserWarning` removed (no longer
  Credentials-wanted). `docs/credentials-wanted-issues.md` trimmed to
  the two providers still genuinely blocked (Sweden, Denmark) - the
  three resolved drafts removed rather than left stale.

### Fixed — Norway mixed-CRS resolution + shared CRS helper (2026-07-30)

Norway's mixed-CRS finding (above) is now fixed, not just documented. A
diagnostic pass (a raw regex scan of a real pull, independent of this
SDK's own parser) pinned the mechanism precisely before writing any
resolution code: of 2,636 real coordinate elements, all 2,133
`gmlLineString`-sourced ones carry `srsName="25833"` with zero exceptions,
and all 503 `pointCoordinates`-sourced ones sit in genuine WGS84 range
with zero `srsName` ever present - two clean, non-overlapping encodings,
not a mislabelling problem to arbitrate around.

- **New shared helper**: `streetworks.common._crs.resolve_coordinate_crs`
  resolves one point's real CRS and axis order from a declared `srsName`
  (if any) plus the point's own coordinate value range against a list of
  candidate `CrsProfile`s - declared-and-consistent stays declared;
  declared-but-contradicted is corrected by value range and logged loudly
  (never silently trusted); undeclared-but-fits-the-default is inferred;
  undeclared-and-fits-a-different-candidate is corrected (the Belgium
  shape); nothing fitting is `unresolved`, falling back to the caller's
  stated default rather than a silent guess. Axis order is decided by
  magnitude (`CrsProfile.order`), never by declared/positional order -
  confirmed necessary live, since Norway's own `posList` states raw
  easting-then-northing, the opposite convention from `pointCoordinates`'
  explicit lat-then-lon. Resolution status
  (declared/inferred/corrected/unresolved) is deliberately **not** added
  to the `Coordinate` model - real, useful information, but kept as
  telemetry only (logs, `scope_note`, `smoke_test.py` output), never
  persisted on canon; a downstream consumer can't later query which
  points were corrected, an accepted trade-off, not an oversight. Ships
  with `WGS84`, `WGS84_NORWAY`, `UTM33N_NORWAY`, and `LAMBERT72_BELGIUM`
  candidate profiles (Belgium's is a profile only - migrating Belgium's
  own converter onto this helper is noted as a follow-up, not done here)
  and 11 unit tests in `tests/test_crs.py`.
- **A second, independent bug found and fixed while building this**:
  8/842 real Norwegian roadworks records in one pull had *both* a precise
  `gmlLineString` line and a redundant `pointCoordinates` convenience
  point in the same location group - the parser concatenated them into
  one `Location.points` tuple, silently mixing UTM and WGS84 values as if
  they were adjacent line vertices. `streetworks.datex2.parser` now
  treats the two as mutually exclusive, the line winning when both are
  present. `Location` gained a `srs_name` field capturing the raw
  declared CRS from whichever element sourced `points` (`None` when
  absent, which is the DATEX-spec-correct case for `pointCoordinates`).
- **`from_datex2` gained an opt-in `crs_candidates` parameter**
  (default `None` - zero behaviour change for every adapter that doesn't
  pass it, including Belgium's own `crs="EPSG:31370"` call site). When
  supplied, each record's own `srs_name` plus its first point's values
  are resolved via the shared helper and the winning CRS/axis order is
  applied to every vertex in that record.
- **New `streetworks.common.from_vegvesen`** wraps `from_datex2` with
  Norway's real candidate list (`WGS84_NORWAY`, `UTM33N_NORWAY`)
  pre-supplied, `territory="Norway"` always passed - so a caller doesn't
  have to remember `crs_candidates=` themselves. `VegvesenClient`'s own
  usage example now uses it in place of calling `from_datex2` directly.
- `streetworks.datex2.vegvesen`'s module docstring and the `vegvesen`
  registry `scope_note` both updated from "serious, unresolved finding"
  to "resolved" - the registry note points to `scripts/smoke_test.py` for
  this run's real declared/inferred/corrected split rather than
  hardcoding a percentage that could go stale.
- `scripts/smoke_test.py`'s `check_vegvesen` now classifies every real
  roadworks record's resolution status for the run and reports the actual
  split (e.g. "1 declared, 1 inferred, 0 corrected, 0 unresolved") -
  derived from live classification each run, not a canned string - and
  fails loudly if any record needed `corrected` beyond the expected
  near-zero threshold (0, since the diagnostic pass above found zero
  contradictions ever), since that would mean the feed's `srsName`
  declaration stopped being trustworthy.
- No reprojection anywhere, still - resolving CRS/axis order is not the
  same as converting between them; that stays an explicit consumer step,
  per this SDK's standing CRS policy.

### Added — Credentials wanted (scaffolds, as originally shipped)

*(Norway/NSW/Victoria were confirmed against real data on 2026-07-30 -
see "Fixed / Confirmed" above for what changed. Entries below describe
each scaffold as originally built, kept for history rather than rewritten.)*

- **Australia: New South Wales (TfNSW Live Traffic Hazards) roadworks and
  major-events scaffold** (`streetworks.au.nsw`,
  `streetworks.common.from_nsw_livetraffic`) - this SDK's first Australian
  provider, opening a new `streetworks.au` cluster (the same
  per-country-file shape as `streetworks.datex2`/`streetworks.ogc`, since
  Australia has no national statutory works register like the UK's Street
  Manager - each state publishes its own traffic-disruption feed
  instead). A Phase 1 scaffold, grouped with Norway/Sweden/Denmark under
  **Credentials wanted** - not DATEX-family like those three, TfNSW's own
  GeoJSON hazards schema.
  Built from dedicated investigation, then independently
  re-verified this session by reading TfNSW's own 42-page "Live Traffic
  NSW Developer Guide" (v1.9) directly rather than trusting an earlier
  paraphrase, plus a live, credential-free probe of the real endpoint.
  - **One adapter, parameterised over layer - not one per layer.** All
    six of TfNSW's hazard types (plus the differently-shaped
    `regional-lga-*` composites) share one real schema, confirmed from
    the guide's own tables, differing only in `layerName` and endpoint
    filename. `NswLiveTrafficClient.get_features`/`iter_features` are
    the general primitives; `get_roadworks`/`iter_roadworks` and the new
    `get_major_events`/`iter_major_events` are convenience wrappers over
    the two **planned** (works-relevant) layers this module covers - the
    four unplanned layers (incident/fire/flood/alpine) and the
    `regional-lga-*` composites are deliberately out of scope for a works
    SDK. `majorevent` has no real sample seen anywhere (unlike
    `roadwork` - see below), so its methods are flagged more speculative
    in the module docstring.
  - **`id` is unique only within a layer, confirmed from the guide's own
    property table** - a real roadwork `82681` and a real major-event
    `82681` are not guaranteed distinct. Every parsed feature now carries
    `layerName` alongside `id` (`parse_features` copies it down from the
    `FeatureCollection`), and `from_nsw_livetraffic` builds
    `Works.reference` as the composite `f"{layerName}:{id}"`, never the
    bare `id` - regression-tested by converting synthetic same-`id`
    roadwork/major-event features together and asserting distinct
    references.
  - **Confirmed live**: a bare request against
    `api.transport.nsw.gov.au/v1/live/hazards/roadwork-open.json` returns
    a genuine structured `401` from a real API gateway
    (`Layer7-API-Gateway`), not a generic error page - confirming the
    endpoint independent of any documentation's own claims. The CC-BY
    licence was independently re-confirmed via the TfNSW Open Data Hub's
    own catalogue page.
  - **A correction to the source investigation**: it initially
    described the roadwork endpoints as `roadwork/open`/`roadwork/closed`/
    `roadwork/all`; reading the guide's own Table 1 directly gives
    different literal filenames - `roadwork-open.json`/
    `roadwork-closed.json`/`roadwork.json`. Both path shapes return an
    identical generic 401 from the gateway, so this couldn't be settled
    by a live probe alone - the guide's own literal text is followed here
    as the more authoritative source, flagged as worth re-checking once
    real credentials are available.
  - **The exact `Authorization` header format is genuinely unconfirmed** -
    searched the full 42-page guide directly for "Authorization"/
    "apikey"/"Bearer": zero matches. Defaults to `apikey <key>` (the
    convention documented for other TfNSW Open Data APIs, not
    independently confirmed for this one), overridable via
    `NswLiveTrafficClient(header_format=...)` with no code change needed -
    the same "don't guess, make it correctable" discipline as Norway's
    Basic-vs-Bearer uncertainty.
  - **Test fixture is one real feature, not synthetic** - transcribed
    verbatim from the Developer Guide's own embedded worked example (id
    `82681`, "Nelligen Bridge replacement project"), CC-BY licensed, read
    directly from the PDF rather than trusted from a secondary summary
    (which, checked against the primary text, had hallucinated an
    `Authorization: Bearer <apikey>` claim the guide never actually
    states - caught and discarded before it could be shipped as fact).
  - **A real, previously-unflagged footgun found in that sample**: the
    real `subCategoryA` field holds the *literal string* `"null"`, not
    the JSON value `null` - `_clean_properties` (the guide's own
    documented "disregard empty/null properties" rule) deliberately does
    not treat the string as empty, only genuine `None`/`""`/whitespace/`[]`.
  - **No gazetteer join key exists anywhere in this feed** - `roads[]` is
    free text only (`mainStreet`/`crossStreet`/`suburb`/`region`/...),
    weaker than NWB's `bag_orl` gap (which at least carries an id) - there
    is nothing to join on at all, documented as a hard gap rather than
    worked around.
  - Coordinates are GeoJSON-native `[lon, lat]` (confirmed from the real
    sample - `[150.14, -35.65]` is genuine coastal NSW), never flipped to
    DATEX's `(lat, lon)` convention. Point geometry is a centroid;
    `encodedPolylines` (Google's Encoded Polyline Algorithm Format,
    decoded via a small new local decoder - no new dependency) grades
    higher when present, though the one real fixture record has none.
  - `start`/`end` map to `proposed_start`/`proposed_end` with `ESTIMATED`
    confidence throughout, never `actual_*` - the guide's own field
    description calls `end` the date a hazard "is **scheduled** to end,"
    true even once a record is closed, since nothing distinguishes a
    confirmed completion time from the last-known schedule.
  - Registered in `streetworks.registry` as `nsw`
    (`kind="roadworks"`, `territories={"Australia"}`,
    `network_scope=NetworkScope.UNKNOWN` - honest default, since it's
    unconfirmed whether the main layer includes council roads or only
    state roads), wired into `scripts/smoke_test.py`
    (`check_nsw_livetraffic` - checks both layers, but a `majorevent`
    failure doesn't fail the whole check given how speculative that layer
    is, skip-guarded on missing credentials) and `.env.example`. Ships
    the same import-time `UserWarning` mechanism as the other three
    Credentials-wanted providers.
  - Drafted (not opened) `help wanted` GitHub issue text in
    `docs/credentials-wanted-issues.md`, alongside the existing three.

- **Australia: Victoria (DTP Planned Disruptions - Road) scaffold**
  (`streetworks.au.vic`, `streetworks.common.from_vic_disruptions`) - the
  second `streetworks.au` cluster member, and the **weakest-confirmed**
  Credentials-wanted provider yet: no real payload has ever been obtained
  anywhere (the OpenAPI spec's own Swagger UI can't preview one due to
  response size, and the linked technical documentation PDF returns
  `PublicAccessNotPermitted` from its blob storage - confirmed live this
  session, not just "not yet fetched"). Built from the real,
  machine-readable OpenAPI 3.0.1 spec - fetched and parsed directly this
  session, not trusted from a summary - plus a live gateway probe.
  - **A separate module from NSW, deliberately not one adapter per
    country.** NSW's "one adapter, parameterised over layer" pattern
    relies on every layer sharing one schema; Victoria publishes two
    independent APIs (planned vs. unplanned disruptions) on different
    version tracks with different schemas, so this module covers planned
    only - unplanned (v3, backed by a different system, the Road
    Incident Database) is out of scope, matching the source
    investigation's own explicit warning not to over-apply the NSW
    precedent here.
  - **A decisive, live-verified correction to the source investigation's
    own bet on a real docs-vs-docs conflict**: the investigation flagged
    that the human-facing dataset page names the auth header `KeyID`
    while the OpenAPI spec's own `securitySchemes` name
    `Ocp-Apim-Subscription-Key`/`subscription-key` (the standard Azure
    APIM names), and bet on the APIM names being right at the real
    gateway. A live probe settles it the other way: the gateway's own
    `WWW-Authenticate` error message reads `"Failed to find key field:
    KeyId"` for every header tried except `KeyID` itself, which instead
    gets `"API Key not authorized: <value>"` - proof the gateway
    recognises the field name and is rejecting the value, not failing to
    find it. The OpenAPI spec is simply wrong about its own gateway here
    - this module sends `KeyID`, not the spec's advertised scheme. The
    same live probe also resolved the investigation's other three
    docs-vs-docs conflicts (rate limit 10/min not 20, token-based
    pagination not page/limit, 10-minute cache not 30), all independently
    confirmed straight from the real spec text.
  - **A correction to the initial design**: `administrative_area =
    localGovernmentArea` was initially proposed. Checked against
    `Works.administrative_area`'s own documented semantics (data
    *ownership*, not geography) - an LGA is where a disruption sits, not
    who owns the data, so `administrative_area` is set to "Department of
    Transport and Planning" instead (the real publishing authority, per
    the spec's own description), with `localGovernmentArea` folded into
    `WorksSite.location_description` alongside the road-name fields
    instead, where it belongs as a geography detail.
  - Real, richer-typed schema than NSW's, confirmed field-by-field from
    the spec's own `components.schemas`: a `duration.recurrences[]` with
    a genuine `daysDuration` integer and `allDay` boolean (versus NSW's
    free-text `periods[]`), a structured `impact` object - though its
    `delay`/`numberLanesImpacted`/`speedLimitOnSite` fields are **all
    typed `string` even where the names look numeric**, carried through
    unconverted rather than coerced to a number that might silently
    misparse a shape never seen live. `source.sourceName`/`sourceId`
    maps to `Works.promoter` - a do-not-deduplicate signal, the same
    multi-source-provenance lesson DGT/Consell de Mallorca's real
    republication case already established.
  - Geometry is a `GeometryCollection` wrapping Point/LineString entries
    (confirmed from the real schema, not NSW's bare-Point shape) -
    parsed preferring the first LineString for `Coordinate.points`, else
    the first Point. Coordinate order presumed GeoJSON `[lon, lat]`, and
    `duration.start`/`end`'s timestamp format presumed ISO-8601 via the
    SDK's existing tolerant parser - both genuinely unconfirmed, the
    parser fails to `None` rather than guess epoch-millis (NSW's format)
    if that assumption is wrong, the safer failure mode since a
    genuine-format date run through the wrong parser produces an
    obviously-implausible result rather than a plausible-looking wrong
    one.
  - Test fixture is **synthetic** (structurally correct per the real
    spec, invented values) - the first Credentials-wanted scaffold in
    this SDK with no real sample basis at all, unlike NSW's transcribed
    real example.
  - Registered in `streetworks.registry` as `vic` (`kind="roadworks"`,
    `territories={"Australia"}`, `network_scope=NetworkScope.UNKNOWN`),
    wired into `scripts/smoke_test.py` (`check_vic_disruptions`,
    skip-guarded on missing credentials) and `.env.example`. Ships the
    same import-time `UserWarning` mechanism as every other
    Credentials-wanted provider.
  - Drafted (not opened) `help wanted` GitHub issue text in
    `docs/credentials-wanted-issues.md`, alongside the existing four.

## [0.8.0] - 2026-07-28

### Changed

- **Breaking: `DTROClient.validate_payload()`'s default `version` changed
  from `"v3_5_1"` to `"v4_0_0"`**, matching DfT's production D-TRO schema
  since 2026-06-01 (see D-TRO `v4.0.0` below). Production still accepts
  v3.5.1 payloads, so this isn't simply a correction - pass
  `version="v3_5_1"` explicitly if that's genuinely what you're validating;
  calling `validate_payload()` with no `version` on a v3.5.1-shaped payload
  (`regulation` as a 1-item array) now fails, the mirror image of the
  previous default's trap against v4.0.0 payloads. The raised
  `pydantic.ValidationError` now also names the schema version directly in
  its message (`"...for v4_0_0 Model"`) - both versions' generated classes
  share the name `Model`, so a bare traceback couldn't otherwise say which
  schema actually rejected a payload.

- **`streetworks.registry`'s `Kind.GAZETTEER` split into `Kind.ADDRESSES` and
  `Kind.STREETS`** - a categorisation fix, not a cosmetic rename: with only
  BAN, BAG and Kartverket as examples of `"gazetteer"`, `providers()`
  supported the false conclusion "European gazetteers have no street
  geometry." They do - it lives in a *street* register, published
  separately by a different body, in every territory checked so far except
  the UK (which uniquely unifies both under the NSG). Reassigned: `datavia`
  and `openusrn` to `kind="streets"`; `ban`, `bag` and `kartverket` to
  `kind="addresses"`. Judgement call recorded, not agonised over: Kartverket
  also wraps SSR (Norway's official place-names register - settlements,
  natural features), which is neither addresses nor streets; kept under
  `addresses` rather than minting a third category for one member, noted in
  its own registry entry and this changelog. `ProviderEntry.capabilities()`
  now reports `"address lookup"`/`"street lookup"` in place of the old
  `"gazetteer/street lookup"`. This is purely additive to behaviour (no
  client, import path, or method signature changed) but **is** a breaking
  change to any code matching on `kind="gazetteer"` directly - there was no
  deprecation path available for an enum value rename, so this ships as a
  clean break, flagged here rather than silently.
  With the split, `providers()` is now a real coverage map, not just a
  filter: the UK has two `streets` providers (`datavia`, `openusrn`) and
  **zero** `addresses` - a genuine gap, not an oversight, since AddressBase
  is an OS Premium product, not open data (noted in the README's roadmap,
  not solved here - it may be the one territory where the address layer is
  genuinely blocked, the inverse of the European picture). France and
  Norway have `addresses` only, zero `streets`, until their own street
  registers are investigated; the Netherlands had the same gap until NWB
  (below) gave it the first territory with both layers.

### Added — Canonical gazetteer model

- **Canonical gazetteer model: `Street`, `Segment`, `Address`**
  (`streetworks.common.gazetteer`) - the gazetteer equivalent of what
  `Works`/`WorksSite` did for roadworks at 0.5.0, designed after the eight
  native street/address adapters (`datavia`, `openusrn`, `bdtopo`, `nvdb`,
  `nwb`, `ban`, `bag`, `kartverket`), from their real shapes, closing the
  international-gazetteers strand's design-session exit condition. Additive
  only - native interfaces unchanged. New converters:
  `from_datavia`/`from_openusrn`/`from_bdtopo`/`from_nvdb`/`from_nwb`/
  `from_ban`/`from_bag`/`from_kartverket`.
  **Three types, not two**: `Segment` is independent of `Street`, not a
  child of it - real data proves street/segment is many-to-many, not
  one-to-many (a real DataVIA ESU, `esuid` `4276210541888`, belongs to two
  distinct designated streets at once - Church Street and Church Street
  Villas, Durham; NVDB's real "Dalveien" address spans two
  topologically-unrelated `veglenkesekvenser`).
  **No synthetic streets**: `from_nwb` emits no `Street` at all - NWB
  states segments with a `bag_orl` reference, but this SDK's only built BAG
  route has no street row to be a `Street`, so Dutch street names arrive
  only via `Address.street_name`, a real gap flagged rather than worked
  around.
  **`Coordinate` gained two additive fields**: every point may now be a
  2-tuple or 3-tuple (Z survives, e.g. NVDB's real `LINESTRING Z` under
  EPSG:5973, never defaulted to 0), and a new `parts` field holds a real
  `MultiLineString`'s other lines (DataVIA's `StreetLines`) - existing
  2-tuple-only converters are unaffected.
  **`WorksSite` gained `street_ref: Identifier | None`** - populated from
  Street Manager's per-permit USRN; investigated and deliberately left
  `None` for SRWR, which states street identity only at the activity
  level (record type `004`) with no phase/site join, so populating it
  would have fabricated a link the source doesn't make.
  **Two early assumptions corrected against real data**: `Segment.names`
  was expected to be BD-TOPO-only, but NWB's real `stt_naam`
  (even purely-numbered roads carry one, e.g. a real A79 motorway segment)
  populates it too; and DataVIA's real ESU schema (confirmed via WFS
  `DescribeFeatureType`, live, mid-session) has *no name field at all*,
  closing a genuinely open question about whether a real named
  sub-street ("Anchorage Terrace", part of Church Street, Durham) is
  recoverable from DataVIA at any level - it isn't, structurally, not just
  unpopulated.
  **Native promotions**: `nwb.Wegvak` gained `wvk_begdat` and six real
  house-number-range fields (`hnrstrlnks`/`hnrstrrhts`/`e_hnr_lnks`/
  `e_hnr_rhts`/`l_hnr_lnks`/`l_hnr_rhts`), previously only in `.raw`;
  `nvdb.Veglenke` gained `type_veg`/`type_veg_sosi` (the real `typeVeg`/
  `typeVeg_sosi` road-classification fields), likewise promoted from
  `.raw`.
  **New real fixtures**: two real DataVIA `StreetLines` payloads (Carr
  Street USRN 33909869, Church Street USRN 11713561) and a real
  `ESUStreets` payload, captured live this session with Durham-scoped
  credentials (field shapes are national, confirmed via
  `DescribeFeatureType`; field values are local to Durham) - DataVIA had no
  fixture of any kind before this. A synthetic, clearly-labelled bilingual
  fixture (Durham has no Welsh street names) exercises the `_eng`/`_cym`
  name-pair path.
  See `docs/gazetteer-field-dump.md` for the full field-by-field survey
  this model was built from.

### Added — Gazetteer providers

- **France: BAN (Base Adresse Nationale)** (`streetworks.ban`) - the first
  non-UK gazetteer, native only (no canonical gazetteer type, no
  `streetworks.common` converter - deliberate, same as how the works side
  shipped natively across 0.3.0-0.4.0 before `Works`/`WorksSite` existed).
  Wraps both the credential-free geocoding API (`search`/`reverse`) and the
  bulk per-département/national `csv-bal` files (streamed, never loaded
  whole - the national file is ~1.4 GB gzipped). Verified live, not
  assumed: the documented API endpoint (`api-adresse.data.gouv.fr`) is past
  its stated 2026-01-31 sunset, so this client targets its confirmed-live
  replacement, `data.geopf.fr/geocodage`; an earlier claim that
  the new endpoint returned HTTP 400 did not reproduce - a plain
  `q=`/`lon=`&`lat=` request succeeds. Of the four bulk CSV format variants
  originally identified, only two (`csv`, `csv-bal`) exist as real downloadable
  files today - `csv-with-ids` and `csv-bal-with-lang` do not.
  **BAN is an address base, not a street register**: there is no
  `id_ban_toponyme` field under any format checked, but a street's identity
  is recoverable - every real address `id` is exactly
  `{street prefix}_{numero}`, and stripping the numero reproduces the same
  prefix for every address on the same street within one commune (verified:
  6/6 real addresses on one real street share it). This SDK exposes that
  as a derived `toponyme_id`, explicitly documented as not a literal BAN
  field. Also confirmed live: the API's `banId` and the bulk `csv-bal`
  format's `uid_adresse` are the *same* permanent UUID for the same real
  address, not just similarly-shaped identifiers; the plain `csv` bulk
  format carries neither, only the compact `id`.
  A user-supplied addendum mid-build corrected an earlier claim that
  street naming belongs to FANTOIR: FANTOIR was replaced by DGFiP's
  **TOPO** register in July 2023 and is now archived. Investigated live in
  response: BAN's plain `csv` format's `id_fantoir` column is, despite its
  name, already populated with post-2023 TOPO-length codes (9 characters,
  never the old 10-character FANTOIR form, across every département
  sampled) - and a real BAN `id_fantoir` value was confirmed, live, to
  join cleanly to DGFiP's TOPO API and return the matching street name.
  TOPO itself has no geometry column at all, so even a perfect join only
  recovers a street's name/history, never a centreline - France
  genuinely splits street *identity* (TOPO, DGFiP) from street *position*
  (BAN, IGN/communes), unlike the UK's unified USRN. TOPO is not wrapped by
  this SDK yet - investigated and documented, not built, per the addendum's
  own scope. Coordinates are WGS84 (`lon`/`lat`) throughout - confirmed
  consistent across the API and both bulk formats, and across mainland
  France and five sampled overseas départements; the bulk files' `x`/`y`
  columns are preserved in `.raw` but not modelled as a coordinate, since
  each overseas département uses its own local projection the file itself
  never states. Licence Ouverte / Open Licence 2.0 (Etalab). Registered in
  `streetworks.registry` as `ban` (`kind="gazetteer"`) - France now has two
  providers, so the `"france"` alias was removed from both `ban` and the
  existing `bisonfute` roadworks provider, and `get_provider("france")`
  now raises `AmbiguousProviderError` naming both, the same as `"germany"`.

- **Netherlands: BAG (Basisregistratie Adressen en Gebouwen)**
  (`streetworks.bag`) - the third gazetteer, and the last before the
  canonical-model design session, native only. Wraps the
  credential-free PDOK Locatieserver (`search`/
  `suggest`/`reverse`/`lookup`) and the bulk GeoPackage (`bag-light.gpkg`,
  current status only, no history), whose download URL is discovered from
  an Atom feed every call rather than hardcoded - PDOK republishes monthly
  and the filename can change, the same NDW lesson.
  **THE critical first check - is `openbare ruimte` (street) its own
  object? - was answered against the real, full, 7.8 GB national
  GeoPackage, downloaded in full over this session (~26 minutes), not
  sampled or assumed from documentation**: no, it isn't - `gpkg_contents`
  lists exactly five tables (`woonplaats`, `pand`, `verblijfsobject`,
  `standplaats`, `ligplaats`), all five carrying real geometry, and street
  name/id survive only as `openbare_ruimte_naam`/
  `openbare_ruimte_identificatie` flattened onto every address. Verified
  at full national scale via direct SQL, not sampled: grouping all
  ~10.04M addressable objects (`verblijfsobject`/`standplaats`/`ligplaats`)
  by that id gives 245,893 / 2,980 / 1,546 distinct real street ids
  respectively, zero of which map to more than one distinct street name in
  any table, and zero rows with a null street id anywhere.
  The fuller picture needed checking the *other* real product too: the
  full-history XML extract (investigated via HTTP range requests against
  the real 3.6 GB zip - a nested zip-of-zips, one member per BAG object
  type - without downloading it whole; not parsed, per the original
  scope) confirms `openbare ruimte` genuinely *is* a first-class,
  separately-versioned BAG object there, with its own identity and a real
  `status` lifecycle - but still carries no geometry of its own in either
  product (confirmed: zero of 36 real national `OpenbareRuimte` XML member
  files contain a geometry element, for any of its real `type` values,
  while `Woonplaats`/`Standplaats`/`Ligplaats` all do). So the honest
  answer has three parts, not two: a street is a genuine registered
  object, with a real lifecycle; it never carries geometry, in any
  product; and *which* product you pull from changes whether you can see
  it directly as a row at all - a three-part shape distinct from both the
  UK (street = geometry) and France (street has neither a row nor
  geometry, and only one product exists to check).
  Also confirmed live in the XML extract: a bitemporal `voorkomen`
  versioning model (validity period *and* registration period tracked
  separately) - documented, not parsed, the same "investigate, don't
  build" scope drawn around this product.
  A correction to the initial understanding: "Gemeente" (municipality) is
  not part of the BAG at all, per Kadaster's own disclaimer in the (explicitly
  unofficial) `GEM-WPL-RELATIE` helper file - `Woonplaats` (settlement) is
  BAG's real administrative concept. Also corrected: the live Atom feed's
  own `<rights>` element names **CC0 1.0 Universal**, not the "Public
  Domain Mark 1.0" first assumed - a different (if similarly permissive)
  legal instrument. A `"weg"` (street) Locatieserver result can carry a
  real `MULTILINESTRING` geometry with `fl=*`, but its `bron` field says
  `"BAG/NWB"` - that line comes from NWB (a separate national roads
  dataset), not BAG itself, so it's kept reachable via `.raw` rather than
  promoted to a field that would misattribute it. Registered in
  `streetworks.registry` as `bag` (`kind="gazetteer"`) - the Netherlands
  now has two providers, so the `"netherlands"` alias was removed from
  both `bag` and the existing `ndw` roadworks provider, matching how
  `"france"` was handled for BAN.

- **Norway: Kartverket (Matrikkelen Adresse + SSR stedsnavn)**
  (`streetworks.kartverket`) - the fourth gazetteer, and the last before
  the canonical-model design session, native only. Wraps the
  credential-free address REST API (`search`/`search_nearby`), the SSR
  place-names REST API (`search_places`/`search_names`/`nearby_places`/
  `object_types`/`languages`), and bulk CSV downloads discovered via an
  Atom feed - genuinely not GML-only, unlike Spain: Kartverket publishes
  CSV, FGDB, GML, PostGIS and SOSI side by side for the same dataset,
  confirmed live via the Geonorge catalogue, so CSV was picked
  deliberately for the same standard-library-only reason every other bulk
  provider in this SDK was.
  **Multilingual naming - the finding flagged early on as most
  likely to change the canonical model - lives on the SSR *place*, not the
  address, confirmed live, not assumed**: a real place
  (Karasjok/Kárášjohka/Kaarasjoki, `stedsnummer` 868181) carries three
  parallel official names (Norwegian, Northern Sámi, Kven) in one
  `stedsnavn` array, each independently statused (two `"godkjent og
  prioritert"` - approved and prioritised; the Kven one only `"foreslått
  og prioritert"` - proposed, not yet approved). But a real address in the
  same Sámi-majority municipality ("Čalbmebealskáidi 1") carries exactly
  one `adressenavn`, in Northern Sámi, with no parallel Norwegian name
  anywhere on the record - even though SSR does have a real, dedicated
  `"Adressenavn"` object type (one of 291 real legal types confirmed live),
  that street's own entry there is single-language too. So multilingual
  officialdom turned out to be a property of some SSR places, not a
  systematic property of Norwegian street addressing - `PlaceName.names`
  is modelled as a list for exactly this reason.
  `adressekode` (a street key carried *inside* the address dataset itself
  - between the UK's separate street register and France's separate tax
  register) is real, clean and municipality-scoped: verified at full
  scale, not sampled, via the same over-merge check BAN's `toponyme_id`
  and BAG's `openbare_ruimte_identificatie` both got - two whole real
  municipalities' bulk files (Karasjok, 1,896 addresses/139 codes; Oslo,
  106,154 addresses/2,535 codes), zero codes mapping to more than one
  street name in either. The same live search that surfaced this also
  confirmed the municipality-scoping directly: "Karl Johans gate 1"
  resolves to three different real addresses in three different
  municipalities, each with its own `adressekode`.
  No product checked gives a street geometry of its own - a separate
  Kartverket/Statens vegvesen product, NVDB Vegnett, does hold real
  road-network line geometry, noted but not built, the same treatment
  France's TOPO and the Netherlands' NWB got. That makes three of the four
  European gazetteers built in this SDK with no street centreline of their
  own.
  Two early corrections, both live-verified: SSR's default output
  CRS is the *same* `EPSG:4258` as the address API (a difference was
  suspected; only the query's *input* flexibility differs,
  accepting `25833` alongside `4258` via `koordsys`) - and the "requires an
  agreement with Kartverket" note some catalogues attach turned out to
  name a completely different, SOAP-based, access-restricted service
  (`MatrikkelAPI`), not the open REST APIs this module wraps. Also found:
  the bulk Atom feed mislabels every entry's `type` attribute as
  `application/gml+xml` even for real CSV entries (this module reads the
  URL's filename, never the `type`), and per-entry `<rights>` isn't always
  `"Kartverket"` - some municipalities (confirmed: Karasjok) name the real
  local data steward instead.
  Registered in `streetworks.registry` as `kartverket` (`kind="gazetteer"`)
  - Norway now has two providers, so the `"norway"` alias was removed from
  both `kartverket` and the existing `vegvesen` roadworks provider (a
  different Norwegian agency, with the opposite access story - see
  Credentials wanted, below), and `get_provider("norway")` now raises
  `AmbiguousProviderError` naming both, matching `"france"`/`"netherlands"`.

- **Netherlands: NWB (Nationaal Wegenbestand)** (`streetworks.nwb`) - the
  first non-UK street-geometry provider, native only, the `kind="streets"`
  counterpart to `bag`'s `kind="addresses"`. Wraps the credential-free WFS
  (`query`/`count`, real `CQL_FILTER` support) and a two-hop Atom feed
  (bulk GeoPackage discovery + streamed download - unlike every other Atom
  feed in this SDK, NWB's index feed points to a second per-dataset feed,
  which only then lists the real download).
  **A real, stated join to BAG exists, confirmed live**: `bag_orl`
  (carried on every wegvak/road-segment) is literally BAG's own
  `openbare_ruimte_identificatie` - same format, same commune-code prefix,
  verified by matching a real wegvak's `bag_orl` against BAG's own id
  space - making the Netherlands the first territory in this SDK where an
  address register and a street-geometry register can be joined by a
  stated identifier, not a name match. Verified at real municipality
  scale (Harlingen, 1,886 wegvakken), not sampled: grouping by `bag_orl`
  gives 378 clean groups, zero mapping to more than one street name - but
  the join isn't universal (96 of 1,886 real wegvakken, ~5%, carry no
  `bag_orl` at all), and name-based grouping alone is measurably less
  reliable (7 of 385 real (municipality, name) groups span two different
  real `bag_orl` values - e.g. "Sédyk" is one display name covering two
  genuinely different BAG street objects). `Wegvak.toponyme_id()` returns
  `bag_orl` where present and `None` otherwise, never falling back to the
  name, which would silently over-merge in exactly these real cases.
  Corrected an earlier WFS paging warning, live: `count`
  paging works fine - two earlier failed attempts almost certainly
  hit an unencoded `+` in `outputFormat=application/geopackage+sqlite3`,
  which decodes server-side as a literal space (confirmed: that exact
  rejection message reproduces the failure). But a real bug of the same
  shape was found in its place: **PDOK's WFS silently ignores
  `CQL_FILTER` entirely** - a query filtered to one real municipality
  returned wegvakken from 280+ different municipalities, unfiltered, both
  for actual features and for `resultType=hits` counts - while
  Rijkswaterstaat's own WFS filters correctly on the identical query
  (confirmed: exactly the requested municipality, matching the bulk-file
  count exactly). Since filtering is the entire point of a live-query
  route, `NWBClient.query()`/`count()` target Rijkswaterstaat directly;
  the bulk GeoPackage download stays on PDOK's Atom feed, which is
  unaffected (a static file, not a filtered query) and matches this SDK's
  existing convention for other Dutch open data. Also confirmed live:
  geometry is route-dependent (the WFS's GeoJSON reports plain
  `LineString`; the bulk GeoPackage encodes every real wegvak as a
  `MULTILINESTRING` wrapping exactly one line part, a GeoPackage/FME
  export convention, not genuinely multi-part segments - carried through
  unconverted, never silently unwrapped); CRS is EPSG:28992, matching
  BAG; licence is CC0 1.0 Universal, matching BAG too, confirmed from the
  Atom feed's own `<rights>` element rather than a portal page (the same
  correction BAG's own licence needed). Registered in
  `streetworks.registry` as `nwb` (`kind="streets"`) - the Netherlands
  now has three providers (`ndw` roadworks, `bag` addresses, `nwb`
  streets), so `get_provider("netherlands")` raises
  `AmbiguousProviderError` naming all three.

- **France: BD TOPO (IGN)** (`streetworks.bdtopo`) - the third non-UK
  street-geometry provider, native only, the `kind="streets"` counterpart
  to `ban`'s `kind="addresses"`. Wraps the credential-free Géoplateforme
  WFS (`query_troncons`/`query_voies_nommees`/`count_troncons`, real
  `CQL_FILTER` support confirmed live, including for `resultType=hits`
  counts).
  **`voie_nommee` (named street) is real, confirmed live, and gives
  France a genuine two-level spine** - the strongest structural finding
  this design strand has had: every real `voie_nommee` carries its own
  stable `cleabs` and a real `liens_vers_supports` link down to a
  `troncon_de_route` segment, confirmed live end to end (a real
  `voie_nommee`'s link resolved to the expected segment, with matching
  name and BAN fields). Neither NWB nor the UK's USRN has this two-level
  structure.
  **The join to BAN is real, stated, and richer than NWB's `bag_orl`**:
  both `voie_nommee` and every `troncon_de_route` carry
  `identifiant_voie_ban` in exactly BAN's own compact toponyme-id format,
  *and* a second, independent identifier, `id_ban_odonyme` (a street-level
  BAN UUID that BAN's own API/bulk files never expose directly).
  Verified at real commune scale, not sampled, on two whole communes
  (Ambérieu-en-Bugey, mainland; Basse-Terre, Guadeloupe, overseas):
  grouping by `identifiant_voie_ban` and checking against `nom_voie_ban`
  (BAN's own name) gives zero over-merged groups in either. A real, minor
  nuance surfaced along the way: BD TOPO's own crowd-sourced name field
  (`nom_collaboratif`) had one abbreviation variant under the same BAN id
  in Basse-Terre ("R SALVADOR ALLENDE" vs "Rue du Président Salvador
  Allende") - not a genuine identity conflict, and gone entirely once
  checked against `nom_voie_ban` instead, which is why both name fields
  are kept rather than one being treated as noise.
  **Left/right structure is real**, confirmed live: `troncon_de_route`
  carries independent `_gauche`/`_droite` names, BAN ids, and even INSEE
  commune codes (a segment on a commune boundary can genuinely have two
  different communes, one per side) - a real structural difference from
  both NWB and the UK's USRN.
  **No automated bulk GeoPackage download route was found**, a genuine,
  thoroughly-investigated gap, not an oversight: IGN's documented download
  portal (`geoservices.ign.fr/telechargement`) now redirects to
  `cartes.gouv.fr`, a JavaScript single-page app with no discoverable
  static resource list; `data.gouv.fr`'s own BD TOPO dataset lists 149
  resources, none an actual GeoPackage file; the legacy `wxs.ign.fr` host
  no longer resolves; and the WFS itself does not offer GeoPackage as an
  output format (confirmed live via its own `GetCapabilities` - only GML,
  GeoJSON, KML and CSV). Only the WFS is built as an access route. A
  `BDTopoDatabase` GeoPackage reader is still provided, for a file
  obtained manually from `cartes.gouv.fr`, but - flagged plainly, not
  hidden - it was never verified against a real downloaded file, only
  against the WFS's own confirmed-live table/column naming, which IGN
  documents as generated from the same underlying data model.
  CRS is also route-specific here: the WFS declares WGS84 (EPSG:4326) on
  every real response checked, mainland and overseas alike; IGN's
  documentation states the (unreachable) bulk GeoPackage uses RGF93 /
  Lambert-93 (EPSG:2154) instead - plausible and consistent with every
  other IGN product, but not independently re-confirmed here. Real 3D
  coordinates (a genuine altitude third value) are confirmed present on
  `troncon_de_route`. Licence Ouverte / Open Licence ETALAB 2.0, confirmed
  via data.gouv.fr's dataset metadata - the same licence as `ban` and
  `bisonfute`.
  A note on naming, worth stating plainly: this is unrelated to DGFiP's
  **TOPO** register (`ban`'s FANTOIR successor, see above) despite the
  near-identical name - different agency, different product.
  Registered in `streetworks.registry` as `bdtopo` (`kind="streets"`) -
  France now has three providers (`bisonfute` roadworks, `ban` addresses,
  `bdtopo` streets), so `get_provider("france")` raises
  `AmbiguousProviderError` naming all three.

- **Norway: NVDB (Nasjonal vegdatabank)** (`streetworks.nvdb`) - the
  fourth non-UK street-geometry provider, native only, the
  `kind="streets"` counterpart to `kartverket`'s `kind="addresses"`, and
  the last planned provider in the international-gazetteers strand.
  **Task one, checked first, per the original plan**: no
  credentials required for reads - confirmed live (only a required
  `X-Client` self-identifying header, not an API key; a bare request
  without it returns HTTP 400) and confirmed in NVDB's own API
  documentation ("Det er ikke nødvendig å registrere en bruker..." - "It
  is not necessary to register a user..."). This is the striking
  asymmetry originally flagged: Statens vegvesen's own DATEX roadworks
  feed (`streetworks.datex2.vegvesen`) remains one of this SDK's
  credential-blocked, unverified providers (see Credentials wanted,
  below), while NVDB, from the same agency, is wide open.
  **`veglenkesekvens` (road link sequence) is purely topological -
  confirmed live, it carries no name of its own**, only `lengde`,
  `porter` (network junctions) and `veglenker` (its own geometry-bearing
  sub-links with linear-referencing ranges). Naming and addressing live
  in a separate object type (`Adresse`, NVDB type 538), whose
  `adressekode` is confirmed live to be the *same* identifier
  `streetworks.kartverket` already models - a real, stated join to
  Matrikkelen addresses, never a name match.
  **The genuinely important structural finding, confirmed live**: one
  real address (`adressekode` 1140, "Dalveien") is placed on *two
  different, topologically-unrelated* link sequences (384 and 2399262) -
  so Norway's naming layer and topological layer are not nested the way
  France's `voie_nommee`/`troncon_de_route` are (one aggregating its own
  clean set of segments via a direct link field). Two "two-level
  spines," two different organising principles - exactly the disagreement
  this design strand needed. A third identifier system exists too,
  `vegsystemreferanser` (administrative road-numbering, e.g. the real
  `"KV1140 S1D1 m0-65"`), preserved in `.raw`, not modelled as a
  first-class field.
  **CRS corrected live: EPSG:5973, not the initially expected
  EPSG:25833** - a compound 3D CRS ("ETRS89-NOR [EUREF89] / UTM zone 33N
  + NN2000 height"), not a plain 2D UTM33 one; every real geometry
  checked is a genuine `LINESTRING Z` with real altitude values, matching
  exactly. **Licence corrected too: NLOD 1.0 (Norsk lisens for offentlige
  data), not Elveg's CC BY 4.0** - confirmed from the NVDB API's own
  documentation (`nvdb-vegdata/apidokumentasjon` on GitHub, the real
  source behind `api.vegdata.no`) rather than assumed from Kartverket's
  Elveg distribution metadata, per the original instruction. Same
  underlying road network, two different publishers, two different
  licences.
  REST is this module's only access route - both endpoints paginate with
  a real cursor and accept a `kommune` filter, confirmed live at real
  scale, so the CSV export service (`nvdb-eksport`) was evaluated and not
  built, per the "don't build two routes for the same job" principle.
  Registered in `streetworks.registry` as `nvdb` (`kind="streets"`) -
  Norway now has three providers (`vegvesen` roadworks, `kartverket`
  addresses, `nvdb` streets), so `get_provider("norway")` raises
  `AmbiguousProviderError` naming all three.

- **USA: TIGERweb** (`streetworks.arcgis.tigerweb`, `kind="streets"`,
  `territories={"USA"}`) - the fifth non-UK street-geometry provider, and
  the first outside Europe, built on the new `ArcGISFeatureClient` (see
  Client infrastructure, below). Layers 0-9 are a real cartographic scale
  pyramid, not distinct road classes - confirmed live by comparing feature
  counts (layers 1/2 both 17,612 nationally, 4/5/6 all 248,106, 7/8 both
  16,150,491 - the same data at different generalisation tiers, a real
  correction to the initial framing). Produces `Segment`
  only, never a `Street` - checked live, not assumed: no layer anywhere in
  the service aggregates segments under a named-street entity, the same
  shape as the Netherlands. No Address Ranges layer exists over this REST
  service either (checked across all 35 real `TIGERweb/` services) -
  `Segment.address_ranges` stays on its NWB-only footing. MTFCC carried
  undecoded (`S1100`/`S1200`/`S1400`/others observed live e.g. `S1630`), no
  lookup table bundled. Public domain (17 U.S.C. Sec. 105) - real fixtures
  committed.

### Added — Roadworks providers

- **Sweden (Trafikverket) and Denmark (Vejdirektoratet) DATEX-family
  roadworks scaffolds** (`streetworks.datex2.trafikverket`,
  `streetworks.datex2.vejdirektoratet`) - see Credentials wanted, below.

- **Belgium (Verkeerscentrum Vlaanderen) and Luxembourg (Ponts et
  Chaussées/CITA) DATEX adapters** (`streetworks.datex2.belgium`,
  `streetworks.datex2.luxembourg`) - DATEX II v3 and v2.3 respectively,
  both credential-free, reused through the existing shared parser/model.
  Live-verified: Belgium ~100 situations/86 roadworks records, Luxembourg
  ~110 situations/161 roadworks records. Two real findings surfaced by
  Belgium's data changed *shared* code, not just this adapter:
  - A second, differently-shaped discriminator gap from Spain/DGT's:
    67/86 real roadworks-relevant records use the generic
    `RoadOrCarriagewayOrLaneManagement` xsi:type, discriminated only by
    `roadOrCarriagewayOrLaneManagementType=newRoadworksLayout` (a real
    DATEX II v3 standard value). Added to
    `SituationRecord.is_roadworks` additively - confirmed this doesn't
    over-match the 61 real same-xsi:type records with genuinely different
    values (`narrowLanes`, `roadClosed`, `contraflow`,
    `singleAlternateLineTraffic`), which can arise from accidents/events,
    not just works.
  - Real coordinates are stated in **Belgian Lambert 72 (`EPSG:31370`)**,
    not WGS84 - confirmed from the feed's own `srsName` attribute and the
    coordinate values themselves (the source XML still calls the fields
    `<latitude>`/`<longitude>`, which is genuinely misleading taken at
    face value). `streetworks.common.from_datex2()` gained a `crs`
    keyword parameter (default `EPSG:4326`, unchanged behaviour for every
    other DATEX adapter) so this is stated explicitly, never silently
    reprojected, per this SDK's standing CRS policy - the same choice
    already made for Saxony's UTM33N and the UK's British National Grid
    providers.

  Belgium's coverage is **Flanders only**, not all-Belgium - confirmed
  live via `supplierIdentification/nationalIdentifier` (`"BETICV"`,
  Belgium Traffic Information Centre Vlaanderen) and the dataset's own
  name; Wallonia publishes a separate feed, not wrapped here. Belgium's
  real licence (transportdata.be's own terms of use) prohibits
  distributing the data to third parties for commercial purposes, so -
  since this SDK is itself redistributed openly - its test fixture is
  **synthetic** (real confirmed shape, invented values), the same call
  already made for Autobahn GmbH's unconfirmed licence; Luxembourg's
  fixture is real, trimmed from a live pull, under **CC0 1.0 Universal**.
  Both registered in `streetworks.registry` (`kind="roadworks"`) and
  wired into `scripts/smoke_test.py`.

- **Bulgaria (Road Infrastructure Agency/LIMA) DATEX adapter**
  (`streetworks.datex2.bulgaria`) - DATEX II v2.3, credential-free, reused
  through the existing shared parser/model. Live-verified: 150 real
  roadworks records. Two real findings, one adapter-local, one shared:
  - The NAP-listed host (`lima.api.bg`) is unreachable (connection
    refused); the real, working host is `datasheet.api.bg`, which serves
    roadworks at a date-stamped URL rather than a fixed one, so
    `BulgariaClient.get_situations()` is a two-step fetch (resolve today's
    file link from the catalogue page, then fetch it). LIMA's roadworks
    catalogue also splits into three datasets ("Closed Roads"/r01, 14
    records; "Closed Roadways"/r02, 46 records; "Short-term Road
    Construction"/r03, 150 records) - checking real record IDs across all
    three confirmed r03 is a strict superset of the other two, so this
    adapter fetches r03 alone rather than merging and de-duplicating
    three files. The real file's own XML declaration also claims
    `encoding="UTF-16"` while the actual bytes are UTF-8 - a genuine
    mislabelling a strict parser rejects outright; corrected before
    parsing, kept local to this adapter since no other feed in this SDK
    has shown the same issue.
  - A third, distinct discriminator type: every real record uses the bare
    `Roadworks` xsi:type directly - not schema-typical (`Roadworks` is
    normally DATEX II's abstract base, not a concrete `xsi:type`), but
    real, live data, and distinct in shape from both Spain's cause-based
    check and Belgium's generic-value case. Added to
    `streetworks.datex2.models.ROADWORKS_TYPES` - confirmed zero drift via
    a live before/after roadworks-count regression across France, Spain
    and Belgium.

  Real WGS84 coordinates throughout, but every location states three
  points, of which the shared parser captures only the first - same
  behaviour as every other point-kind location in this SDK, documented
  rather than changed. **Licence unconfirmed**: no licence text exists on
  the reachable host, and the real terms page sits behind the unreachable
  `lima.api.bg`, so - per the Autobahn GmbH/Belgium precedent - the test
  fixture is **synthetic** (real confirmed shape, invented values).
  Registered in `streetworks.registry` (`kind="roadworks"`) and wired into
  `scripts/smoke_test.py`.

- **Lithuania (Via Lietuva) roadworks adapter** (`streetworks.vialietuva`,
  `streetworks.common.from_vialietuva`) - the **open data.gov.lt CSV
  route**, not the RTTI NAP NAPCORE lists (that listed NAP is
  agreement-gated and 403s without one); CSV, not DATEX, so it has its own
  small parser, the same shape of choice already made for Autobahn/WZDx.
  Live-verified: 9,762 real `Remontas` (road repairs) rows, 100%
  coordinate coverage.
  - Checked all four of the dataset's tables, not just the one modelled.
    `Kliutis` (obstacles - real road-condition hazards, e.g. "weakened by
    spring thaw") and `Renginys` (events - real car-rally-stage closures)
    are genuinely not roadworks, not forced into `Works` - the same call
    already made for UK Police. `KelioAtkarpa` (road sections) is
    gazetteer-shaped reference data (road number/name/km-range, no
    restriction content); confirmed live every real `road_id` joins to it
    (886/886), exposed as `ViaLietuvaClient.road_sections()`, the same
    auxiliary-lookup role `dir_regions()`/`provinces()` play for Bison
    Futé/DGT.
  - **Real coordinates are Lithuanian LKS-94 (`EPSG:3346`)**, not WGS84 -
    the third non-WGS84 roadworks provider in this SDK, after Belgium's
    Lambert 72. **The source's own WKT axis order is also reversed** -
    `POINT (northing easting)`, not the usual `(easting, northing)`,
    confirmed from real value ranges (first number always in Lithuania's
    real northing band, second always in its real easting band). Carried
    through unconverted, both facts stated explicitly via
    `from_vialietuva`'s `crs` parameter and its own docstring, not
    assumed.
  - A repair's full path (a real `MULTILINESTRING`) is preferred when
    stated (6,984/9,762 real rows, 71.6%); the rest are point-only - 100%
    coordinate coverage either way.
  - Real, honest data-quality finding: 25/9,762 real rows (~0.26%) are
    plainly unfiltered test data (`aprasymas` literally `"test"`/
    `"testuojam;"` or similar), structurally identical to a genuine row
    otherwise.

  Real trimmed fixtures used throughout (CC BY 4.0 confirmed via the
  dataset's own licence field on data.gov.lt). Registered in
  `streetworks.registry` (`kind="roadworks"`) and wired into
  `scripts/smoke_test.py`.

- **Consell de Mallorca (island roadworks) adapter**
  (`streetworks.ogc.mallorca`, `streetworks.common.from_mallorca`) - built
  from a dedicated recon pass (`docs/idemallorca-investigation.md`), then
  live-verified again during the build. Genuinely additive to DGT (Spain),
  not a duplicate: DGT's national DATEX feed doesn't carry Consell-managed
  island roads at all (confirmed live - a DGT query around Alcúdia
  returned only ~5 works island-wide). Reuses `OGCFeaturesClient` directly,
  no new client shape.
  - **A real, masked-failure format gotcha**: this GeoServer rejects the
    client's own `output_format="application/geo+json"` default, but with
    HTTP 200 wrapping an XML error body, not an error status. Every call
    here passes `output_format="application/json"` explicitly at the call
    site (not a change to the shared client's default), plus an explicit
    `FeatureCollection` shape check as a second guard against this exact
    kind of quiet failure.
  - **A two-layer join, verified not total**: `incidencies_icon` (points,
    all real content) and `incidencies_tram` (affected-segment
    `MultiLineString`s - one real record genuinely has 2 parts) are joined
    by a shared `codi`. 16/17 real incidents in one live pull had a
    matching tram; one is point-only, handled honestly (a real
    `Coordinate`, `parts` left `None`, never a fabricated line).
  - Real CRS is ETRS89/UTM31N (`EPSG:25831`), labelled and carried through
    unconverted, despite the server offering a genuinely correct
    server-side WGS84 reprojection - not used, per this SDK's standing CRS
    policy (the same choice already made for Belgium/Lithuania).
  - Discriminator (`tipoinc`) is clean: `"Obres"`/`"Manteniment"` are
    fetched as roadworks; `"Altres"` is excluded after checking its one
    real example read as a DGT-imposed restriction, not Consell's own
    works.
  - `territory="Spain"`, `administrative_area="Consell de Mallorca"` - as
    a second Spain roadworks provider, DGT's `"spain"` alias is removed
    (`get_provider("spain")` now resolves through the territory-ambiguity
    path, same as `"france"`/`"norway"`/`"germany"`).

  **Licence unconfirmed** (checked the WFS capabilities, the IDEmallorca
  geoportal, and the Consell's general legal notice - no explicit reuse
  terms found anywhere), so the test fixture is synthetic, same precedent
  as Autobahn GmbH/Belgium/Bulgaria. **Mallorca only, not a Balearic
  cluster** - Menorca and Eivissa were checked and don't publish the same
  way. Registered in `streetworks.registry` (`kind="roadworks"`) and wired
  into `scripts/smoke_test.py`.

- **Servei Català de Trànsit (Catalonia) roadworks adapter**
  (`streetworks.sct`, `streetworks.common.from_sct`) - built from a
  dedicated recon pass (`docs/catalonia-sct-investigation.md`), filling
  the larger of DGT's two documented exclusions (DGT explicitly omits
  Catalonia and the Basque Country). Live-verified: 165 real current
  incidents, 136 typed `descripcio_tipus` `"Obres"` (roadworks).
  - The real feed (`incidenciesGML.xml`) is genuine WFS/GML - a
    `wfs:FeatureCollection` with real `gml:Point` geometry - but flat and
    simple (one geometry plus a dozen scalar fields per record, no
    nesting), so it gets its own small, contained parser (plain
    `ElementTree`, no new dependency), the same shape of choice already
    made for Autobahn GmbH. **Deliberately does not touch or depend on**
    this SDK's parked general INSPIRE-GML-reader decision.
  - Discriminator (`descripcio_tipus`) is clean: checked, not assumed,
    that the two non-`"Obres"` real values (`"Retenció"`/congestion,
    `"Cons"`/temporary lane measures) genuinely aren't roadworks -
    including one real edge case (a `"Retenció"` record whose free-text
    `causa` says `"Obres"`), deliberately not reclassified, since the
    dedicated type field is trusted over a secondary free-text hint.
  - **No start/end validity window exists anywhere in this feed** - a
    genuinely real-time, continuously-refreshed current-state feed, not
    a works schedule (confirmed via the dataset's own metadata and by
    watching `Last-Modified` change between live pulls). `date_confidence`
    is always `unknown` and no proposed/actual dates are populated -
    the one real timestamp this feed states reads as "when this record
    was last reported," not "when the works start," so it's never
    promoted into a date field it would misrepresent.
  - CRS is WGS84, confirmed live - the simplest CRS story of any Spanish
    adapter in this SDK, no reprojection question at all.
  - `network_scope=multi_authority_interurban`, the same shape as DGT's
    own real data - real road-number prefixes span the Generalitat's own
    network plus all four provincial councils' networks plus some state
    roads within Catalan territory.
  - Licence is Catalonia's own "Llicència oberta d'ús d'informació" -
    confirmed genuinely open (reuse, distribution and derivative works
    permitted worldwide, attribution required), so the test fixture is
    real, trimmed from a live pull - the cleanest licence of any Spanish
    source checked this session.
  - As a third Spain roadworks provider, `get_provider("spain")` now
    names all three (`dgt`, `mallorca`, `sct`) via the territory-
    ambiguity path.
  - **The Basque Country (DGT's other exclusion) was investigated
    alongside this, not built** - a genuinely promising finding: a real,
    live DATEX II v1.0 feed (`infocar.dgt.es/datex2/dt-gv/...`) that this
    SDK's existing shared parser already reads successfully with zero
    code changes (120 situations, 96 with roadworks, a clean
    `MaintenanceWorks`/`ConstructionWorks` discriminator) - flagged for
    its own dedicated future investigation (licence there is genuinely
    unresolved), not folded into this build.

- **Basque Country (Euskadi) roadworks adapter**
  (`streetworks.datex2.euskadi`) - fills the other of DGT's two
  documented exclusions, via the existing shared `from_datex2` converter
  (no bespoke converter needed). Genuine DATEX II **v1.0** - the oldest
  schema version in this SDK. Live-verified: 96/119 real situations carry
  a roadworks record (101 records total). **Also surfaced a real, additive
  shared-parser bug, fixed alongside this adapter - see Fixed, below.**
  - **Coordinate coverage is genuinely partial - the only Spanish/DATEX
    adapter in this SDK below 100%**: of 101 real roadworks records, 36
    have a real 2+-point line, 6 a single point, and 59 state location
    purely via Alert-C plus a road number and distance along it (no
    coordinates at all).
  - A real per-record province field (`administrativeArea`, nested three
    levels deep) is exposed via its own `provinces()` helper, the same
    shape as DGT's own - all three Basque provinces confirmed live,
    genuinely inconsistent casing kept as stated, not normalised; a real
    `"Desconocida"` (unknown) placeholder is excluded, not treated as a
    name.
  - `network_scope=multi_authority_interurban`, the same shape as DGT's
    and SCT's own real data (state roads plus all three Diputación Foral
    networks). CRS is WGS84, confirmed live from real point values.
  - **Licence: the publisher states "No licence - No contract" -
    literally, not "unconfirmed."** Genuinely more restrictive than an
    unconfirmed licence, not less - absence of a licence grants no
    permission, since copyright is automatic and default-restrictive; a
    licence is what *adds* permissions. Never documented as "assumed
    open" anywhere. Calling the public endpoint needs no licence, so the
    client is built freely, but the test fixture is **synthetic** (real
    confirmed shape, invented content) - committing real records here
    would be redistribution, which nothing here permits.
  - As the fourth Spain roadworks provider, `get_provider("spain")` now
    names all four (`dgt`, `euskadi`, `mallorca`, `sct`) via the
    territory-ambiguity path.

- **Jersey RoadWorkx** (`streetworks.arcgis.jersey`, `kind="roadworks"`,
  `territories={"Jersey"}`) - this SDK's first Channel Islands coverage,
  built on the new `ArcGISFeatureClient` (see Client infrastructure,
  below), and the client's proving ground for a real pagination trap: its
  `RoadWorks` layer states `supportsPagination: false`, and it's true in
  an unusually literal way - `resultOffset` returns HTTP 200 with a
  plausible page every time, but it's silently the *same* first page
  regardless of offset (confirmed at offsets 0/500/1000/2000/21000); the
  real total is 22,105 records behind a `maxRecordCount` of 1,000, so a
  naive query silently returns under 5% of the data with no error.
  Live-verified this session to retrieve all 22,105 real Jersey records
  with zero duplicates via `ArcGISFeatureClient`'s object-id-range
  fallback.
  Real `RoadWorks` features group by `PROJID` into one `Works` per
  project (confirmed the same real shape as Street Manager's
  `work_reference_number`/`permit_reference_number`); the real `STATUS`
  field (`"In Progress"`/`"Finished"`/`"Pending"`) *is* the planned/future
  dimension, no separate layer needed. CRS confirmed live to be EPSG:3109
  ("ETRS89 / Jersey Transverse Mercator") via a sibling service on the same
  deployment stating the `wkid` directly, cross-checked byte-for-byte
  against EPSG:3109's own published WKT - `outSR` is not honoured by this
  service (also confirmed live). **No explicit licence document found** (no
  `copyrightText` anywhere, not catalogued on Jersey's own open-data
  portal, and the public-facing site gates behind a login the REST API
  itself doesn't need) - but the data is confirmed intended for open
  public consumption, so real, live-captured records are committed as test
  fixtures, the same basis Autobahn GmbH's roadworks shipped on.

### Added — Registry & discovery

- **Network-scope audit + `network_scope` registry field**
  (`docs/network-scope-audit.md`) - audited every roadworks provider for
  what tier of the road network its *real* data actually reaches, not its
  stated remit, and wired the result into `streetworks.registry`: a new
  `NetworkScope` enum (`comprehensive` / `multi_authority_interurban` /
  `strategic` / `motorway` / `regional` / `varies_by_feed` /
  `not_applicable` / `unknown`) and a `network_scope` field on every
  `ProviderEntry`, surfaced directly in `providers()`'s own rendering -
  additive, no client behaviour changes.
  - **Corrects an already-shipped claim, stated plainly rather than
    quietly edited.** The Consell de Mallorca adapter above shipped
    describing DGT and Consell de Mallorca as "genuinely additive, not a
    duplicate." A live check found this wrong: DGT's own real data
    reaches Mallorca (`Ma-`/`Me-` prefixed records, confirmed via real
    road-number prefixes, not assumed from DGT's "national" description),
    and 2 of DGT's Balearic records were checked directly against Consell
    de Mallorca's own feed and matched almost exactly on road, km-range
    and end-date - republication of the same real works, not two
    authorities' records for adjacent land (no independent reference
    field exists on DGT's side to attribute it otherwise, and the matched
    geometry sits within, not beside, the same work-zone span). Corrected
    everywhere the original claim appeared: this changelog's own history
    is left as-is (a record of what was believed at the time), but the
    README, `docs/idemallorca-investigation.md`, both modules' own
    docstrings, and `examples/compare_active_works.py` are all updated.
  - DGT itself turned out broader than "national roads" implies: real
    road-number prefixes reach ~10 regional/provincial/insular
    authorities too (`CV-`/Comunidad Valenciana, `M-`/Madrid, and the
    Balearic ones above), never municipal streets - reclassified
    `multi_authority_interurban`, a new enum value the original 5-value
    proposal didn't anticipate.
  - Two providers turned out genuinely two-tier depending on which part
    of their own feed is queried - TrafficWatchNI (NI-wide strategic,
    all-roads within Belfast) and Saxony (broader than its Hamburg/
    Brandenburg siblings, aggregating district and municipal roadworks
    alongside state roads). Kept in the existing free-text `scope_note`
    rather than growing the enum per-provider, per the audit's own
    restraint.
  - New standing principle, added to the README:
    [never deduplicate near-identical works across providers](#never-deduplicate-across-providers) -
    a permit is issued per authority, not per physical worksite, so two
    providers' records for what looks like the same location can both be
    genuinely correct; the same lesson `examples/collaboration_finder.py`
    already applies one level down (never merging a Street Manager permit
    with its own amendment), one level up.
  - `tests/test_registry.py` extended: every `kind="roadworks"` entry must
    set `network_scope` explicitly (never the bare `None` default, which
    now means "this concept doesn't apply" - reserved for non-roadworks
    kinds), the same "can't ship without it" discipline the registry's
    own package-coverage test already applies.

- **Provider discovery** (`streetworks.registry`, exposed as
  `streetworks.providers()`/`get_provider()`) - purely additive: no existing
  import path, class, or behaviour changed. Answers "what covers X" and
  "give me Y's client" without needing to already know which technology a
  country publishes over - `providers(territory="Wales")`,
  `providers(kind="gazetteer")`, `providers(credentials=False)`,
  `get_provider("spain")`. One registry entry per provider, each carrying
  territory, credentials, licence, source grade, and the exact working
  import line.
  Capabilities (`entry.capabilities()`) are **derived by inspecting the
  real client class**, never a hand-maintained dict - including one level
  into known sub-API objects (Street Manager's `.work`/`.reporting`
  attributes, discovered by reading `__init__`'s own source, not
  hardcoded), which is what lets `streetmanager`'s write/publish and
  planning-artifact capabilities show up correctly despite living on
  nested classes rather than flat methods.
  Ambiguous lookups (`get_provider("germany")` → four providers,
  `"england"` → seven) raise naming every real candidate rather than
  guessing; an unknown territory passed to `providers()` warns and returns
  empty rather than raising or silently returning nothing.
  A genuine performance bug was caught and fixed before shipping, not
  after: the first working version imported `SourceGrade` from
  `streetworks.common.models`, which (via `streetworks.common`'s package
  `__init__`) transitively imported every `from_<provider>` converter and
  therefore every provider's client module, including httpx - pulling in
  24 heavy modules just to import the registry, exactly the cost this
  module's own design was supposed to rule out. Fixed by storing
  `source_grade` as a plain string (a `str` `Enum`'s members compare equal
  to their string values either way) instead of importing the real enum
  type; confirmed live that `import streetworks.registry` and
  `import streetworks` now pull in zero httpx/pydantic modules, and that
  `get_provider()` still imports the target client lazily, only on call.
  Two real, previously-undocumented gaps surfaced while verifying every
  territory/licence claim against actual module docstrings rather than
  taking earlier notes on trust: Street Manager and DataVIA never
  state their territory anywhere in code or README prose (England+Wales
  here is inferred by elimination against SRWR/TrafficWatchNI covering the
  other nations separately, not an explicit statement); NDW and
  Digitraffic state no licence anywhere either, and a live check of both
  portals found nothing (`licence_confirmed=False`, the same honest-gap
  convention Autobahn's module already established).

### Added — Client infrastructure

- **`streetworks.arcgis` - a generic ArcGIS REST (MapServer/FeatureServer)
  client**, the third client shape in this SDK after the DATEX/JSON
  adapters and `OGCFeaturesClient`. Built fresh, not a generalisation of
  `OGCFeaturesClient`/`DataViaClient` - they share almost nothing but
  "fetches geodata over HTTP." Verified against two genuinely different
  real consumers - Jersey RoadWorkx and TIGERweb (see Roadworks providers
  and Gazetteer providers, above).
  **The real pagination trap this client exists to handle**: some ArcGIS
  services report `supportsPagination` metadata that doesn't match their
  real behaviour (Jersey's `RoadWorks` layer claims `false`, and
  `resultOffset` silently returns the same first page at every offset,
  confirmed live at 0/500/1000/2000/21000 - a naive query would return
  under 5% of the data with no error). `ArcGISFeatureClient.iter_features`
  verifies live rather than trusting either metadata claim, falling back
  to object-id-range paging the moment offset-paging fails to advance
  (confirmed live to work for Jersey; TIGERweb's own layers state, and
  genuinely honour, real offset pagination), and raises the new
  `TruncatedResultError` if neither strategy is usable - never silently
  returns a partial result.
  New exception: `streetworks.exceptions.TruncatedResultError`.

### Added — UK Police: worker-safety context

- **`streetworks.police` bulk CSV download**:
  `PoliceClient.bulk_download_csv(forces, *, date_from, date_to, ...)` drives
  data.police.uk's custom CSV download (https://data.police.uk/data/) - a
  CSRF-protected HTML form plus an async job, not a JSON endpoint like every
  other method on this client, but fully scriptable with a plain cookie jar
  and no browser. Verified live end-to-end for 1-, 3-, and 12-month
  single-force requests (all ready within seconds; 12 months of Durham is a
  3.5MB zip). Adds a small local retry (fresh CSRF token each attempt) for a
  transient 403 observed live under repeated use - not one of the shared
  transport's retryable statuses, since 403 correctly means "no" everywhere
  else in this SDK. Returns every row keyed by the CSV's own real column
  names; the CSV's `Crime type` ("Violence and sexual offences") maps to the
  JSON API's slug (`violent-crime`) via `crime_categories()`'s existing
  `name`/`url` pairs, confirmed live to match exactly - no separate mapping
  file needed, despite there being a published one
  (`police-uk-category-mappings.csv`) that maps something else entirely.
  Also documents a real, live-verified caveat: a per-force export can carry
  a small amount of geographic cross-force contamination (~0.4% of rows for
  one real Durham check) that `Falls within` cannot be used to filter
  (confirmed live: every row, including the contaminating ones, carries
  that force's own name in that column).
  **New example**: `examples/crime_context_lsoa/` - LSOA-level (not
  neighbourhood-team-level) crime context keyed to a specific worksite
  (point + radius, live-tested; or a USRN against an already-downloaded OS
  Open USRN GeoPackage, implemented but not live-tested end-to-end - see its
  own README), with a real 2021 Census population denominator instead of
  area. Population and boundary geometry both come from one ONS ArcGIS
  FeatureServer query (via the existing `streetworks.arcgis.ArcGISFeatureClient`),
  which structurally removes the 2011/2021 LSOA-vintage-mixing risk at the
  source rather than just checking for it downstream. Defaults to a 12-month
  window (versus the neighbourhood example's 3) now that ingestion is a
  single bulk download rather than hundreds of live polygon queries -
  shrinkage, quintile/tercile/refuse-to-band tiers, and suppression for
  too-few-crimes areas all carry over from the neighbourhood example's
  design. Live-verified against Durham Constabulary, worksite centred on
  Newton Aycliffe town centre. See its own README for the full method,
  the architectural split (police ingestion in `streetworks.police`; ONS
  population/boundary and worksite geometry kept example-local, not
  promoted into the library), and what it deliberately does not attempt.

- **`streetworks.police` neighbourhood support**: `PoliceClient.neighbourhoods(force)`,
  `.neighbourhood(force, id)`, and `.neighbourhood_boundary(force, id)`
  (`GET /{force}/neighbourhoods`, `/{force}/{id}`, `/{force}/{id}/boundary`).
  Verified live, not from the docs: boundary coordinates are stated as
  **strings** (coerced to `float` here); a boundary is always a single,
  closed ring - no multipolygon, no holes; and real rings aren't guaranteed
  simple (a real ring, Leicestershire's `NC04`, has near-duplicate
  consecutive vertices and at least one spike) - returned exactly as
  received, never silently repaired. `neighbourhood_boundary()` returns
  `(lat, lng)` pairs in the same order `street_level_crimes_in_area`
  already expects.
  **`street_level_crimes_in_area` now survives large polygons** (a real
  neighbourhood boundary can be hundreds of vertices - Leicestershire's
  `NA41` is 2,972 points, confirmed live) - public signature unchanged.
  Coordinates are written to 5 decimal places (~1m, far finer than the
  source data's own anonymisation), and the request switches from `GET` to
  a form-encoded `POST` automatically once the query would exceed a safe
  URL length - live-verified against a real 2,972-point boundary (`GET` for
  the small boundary fetch, `POST` for the resulting crimes query). A `503`
  (the API's real response when a polygon is too complex, even over `POST`)
  now raises `streetworks.exceptions.ServerError` naming the problem
  instead of the shared transport's generic message - silently returning
  `[]` here would make an unqueried area look crime-free. A response at
  exactly the API's 10,000-result cap now emits a `UserWarning`, since that
  count may be a truncation, not the true total.
  **New example**: `examples/crime_context/` - a neighbourhood-banded
  recorded-crime context map for a whole force (rolling 3-month window,
  ending at the most recent month `street_level_availability()` itself
  reports data for rather than a fixed guess back from today, rates
  shrunk toward the force mean and banded into quintiles - falling back to
  terciles, or refusing to band at all below a minimum area count - *within*
  the force only, a sequential single-hue ramp rather than red/amber/green,
  and a method/limitations panel embedded in the page itself rather than a
  footnote) - built entirely on the two additions above plus the existing
  `SAFETY_RELEVANT_CATEGORIES`. Live-verified against Durham Constabulary's
  71 real neighbourhoods. See its own README for the full method and what it
  deliberately does not attempt (no per-street scoring, no cross-force
  comparison, not a risk assessment).
  **Also corrected**: the README's "sync and async clients" claim was
  inaccurate for several modules, not just this one - checked directly
  against the source rather than assumed. `streetworks.police` has no
  `AsyncPoliceClient` (nor do `bag`, DATEX II, `autobahn`, `ogc`, `wzdx`,
  `trafficwatchni`, `trafficwales`, or the ArcGIS-based providers) - the
  README now names which modules do and don't, rather than claiming async
  everywhere.

### Added — D-TRO v4.0.0

- **D-TRO `v4.0.0` publish models** (`streetworks.dtro.models.v4_0_0`),
  generated from DfT's real schema with the existing
  `scripts/generate_dtro_models.py` tooling - additive, `v3.5.1` models
  untouched. v4.0.0 became the production schema on 2026-06-01 (confirmed
  directly from the DfT repo's own release announcements); production
  continues to accept v3.5.0/v3.5.1 payloads too, so this is additive
  coverage, not a cut-over.
  **A real, non-cosmetic payload-shape migration**, not a drop-in schema
  swap - see `docs/DTRO_SCHEMAS.md` for the full diff, verified against
  both DfT's own written release notes and the two schemas' real `$defs`
  directly: `regulation` moved from a 1-item array to a plain object;
  `condition`/`conditions`/`conditionSet` were restructured (`conditionSet`
  is now a single object, not an array; `condition` gained its own nested
  `conditionSet` property; a new `permitCondition` type exists with no
  v3.5.1 equivalent - found in the schema diff, not mentioned by name in
  DfT's own notes); `regulation.timeZone` is now fixed
  (`"const": "Europe/London"`); 8 real `vehicleType` values
  (`policeVehicle`, `schoolBus`, and 6 others) moved to `vehicleUsageType`;
  `sourceActionType` gained `"fullRevoke"`. Tests validate a real DfT
  v4.0.0 example payload and exercise three of these changes directly
  (`tests/test_dtro_models_v4_0_0.py`).
  **`DTROClient.validate_payload()`'s default is now `v4_0_0`** (was
  `v3_5_1`) - see the Changed section above for this as its own flagged
  behaviour change. Its "no models for this version" error message now
  lists both shipped versions, and a raised `ValidationError` now names
  which schema version it validated against, since both versions' generated
  classes share the name `Model`.
  Checked and found unchanged: client endpoints, headers, auth, payload
  limits. Two real v4.0.0-era changes are **not** schema concerns and are
  reported, not built here: a new polygon-based spatial search capability
  on `POST /search` (Integration only as of the DfT announcement checked),
  and new service-generated response metadata (creation/update/up-version
  timestamps) that isn't part of the publish schema this SDK validates
  against.
  D-TRO `v5.0.0` (in development, not yet built) was checked against this
  namespacing pattern: it scales cleanly (purely parametrised on the
  version string) except for that one hardcoded error-message string,
  which needs a one-line update whenever a version is added - noted in
  DTRO_SCHEMAS.md so it isn't forgotten next time.

### Added — Credentials wanted (scaffolds, unverified)

- **Sweden (Trafikverket) and Denmark (Vejdirektoratet) DATEX-family
  roadworks scaffolds** (`streetworks.datex2.trafikverket`,
  `streetworks.datex2.vejdirektoratet`) - Phase 1 scaffolds, **not verified
  builds**, grouped with Norway (`vegvesen`, shipped 0.7.0) under a new
  **"Credentials wanted"** README section, since all three share the same
  shape of gap: implemented to a confirmed API/schema shape, covered by
  mocked tests against synthetic fixtures, but never run against a real
  authenticated response - genuinely blocked on credentials this project
  doesn't have, not on unfinished code.
  - **Sweden**: Trafikverket's own bespoke XML-request/JSON-response
    envelope, not DATEX II - like Digitraffic wraps Finland, needs its own
    request/parse path onto the shared `Situation`/`SituationRecord`
    models rather than the streaming DATEX parser. Confirmed live via a
    deliberate invalid-key probe: the endpoint, the `Situation` object
    name, and schema version `1.5` (a genuine structured `401`, not a
    generic error page). The real `MessageType`/`MessageCode` value that
    means roadworks specifically is genuinely unconfirmed after checking
    several sources - rather than guess, `record_type` preserves
    `MessageType` verbatim, so `iter_roadworks()` honestly returns nothing
    until a credentialed pull confirms the real discriminator value;
    `iter_situations()` is the way to see everything in the meantime.
    Licence: CC0 1.0 Universal.
  - **Denmark**: genuine DATEX II 3.2, confirmed directly from
    Vejdirektoratet's own protocol specification (`sit:ConstructionWorks`/
    `sit:MaintenanceWorks` and their full `constructionWorkType`/
    `roadMaintenanceType` enumerations stated explicitly, not inferred),
    so it reuses the existing shared streaming parser unchanged, the same
    shape of solution as `vegvesen`. The open metadata catalogue
    (196 datasets, no auth) was re-verified live; the specific roadworks
    dataset confirmed road-work-themed and **CC BY 4.0**-licensed
    per-dataset, not assumed from the catalogue in general. No public data
    URL exists - the real per-dataset pull address and HTTP Basic Auth
    credentials are both issued together at registration, so
    `VejdirektoratetClient` takes `base_url` as a required argument rather
    than a module constant, unlike every other DATEX adapter here.
  - Both ship an import-time `UserWarning` pointing at the "help wanted"
    issue tracker - a genuinely new mechanism, added here and retrofitted
    onto `vegvesen` too for consistency (previously signalled only via a
    docstring admonition and `ProviderEntry(verified=False, ...)`, which
    still remain the source of truth for tooling).
  - Both registered in `streetworks.registry` (`kind="roadworks"`,
    `network_scope=NetworkScope.UNKNOWN` - honest default, not a guess,
    same as `vegvesen`), wired into `scripts/smoke_test.py`
    (`check_trafikverket`/`check_vejdirektoratet`, skip-guarded on missing
    credentials) and `.env.example`. Test fixtures are **synthetic**
    (structurally real shapes, invented values) since neither adapter has
    ever seen real data - `tests/test_trafikverket.py` deliberately
    asserts `iter_roadworks()` stays empty even for a deviation a human
    would recognise as roadworks (`MessageType: "Vägarbete"`), to keep
    that honesty regression-tested.
  - Drafted (not opened) `help wanted` GitHub issue text for both, plus
    Norway's, in `docs/credentials-wanted-issues.md`.

### Fixed

- **DATEX v1.0 linear locations silently degraded to a single point.**
  Found by reading the "pleasant surprise" of Euskadi's zero-code-change
  parse more carefully, per this project's own standing habit: the shared
  parser only recognised `tpegLinearLocation` (the v2/v3 spelling), not
  v1.0's own `tpeglinearLocation` (lower-case `l`) - confirmed by direct
  byte search of the real Basque feed (74/74 real linear-location records
  use the lower-case v1.0 spelling, 0 use the v2/v3 one). Before the fix,
  the shared parser's two-point `from`/`to` extraction never matched it,
  silently degrading a real 2-point line into a single point via the
  generic fallback. Fixed as a second, fallback lookup in
  `streetworks/datex2/parser.py` (v2/v3 spelling tried first) - confirmed
  via a live before/after regression across France, Spain, Belgium,
  Luxembourg and Bulgaria: identical roadworks counts and multi-point-
  location counts, zero drift.

## [0.7.0] - 2026-07-19

### Added

- **Finland: Digitraffic** (`streetworks.datex2.digitraffic`) - the first
  provider of the European DATEX expansion, and the first adapter to prove
  the National-Highways pattern (a source that isn't DATEX-shaped itself
  can still produce the same shared `Situation`/`SituationRecord` models)
  a second time. Verified against the live feed (574-575 real features,
  not assumed): Digitraffic's Simple-JSON is its own schema, not a JSON
  serialisation of DATEX II. Every field mapping decision is documented in
  the module rather than glossed over - `record_type` is a hardcoded
  compromise (Digitraffic has no maintenance/construction discriminator),
  `road_maintenance_type` takes the single most specific work-type entry
  rather than a joined composite, `validity.status` stays `None` always
  (no lifecycle field exists in the feed, checked exhaustively - so
  `date_confidence` honestly comes out `UNKNOWN` throughout), and location
  geometry is documented as area-level (the situation's, shared across
  every phase-derived record - confirmed on a live 3-phase situation with
  three different road numbers under one geometry), not phase-precise -
  `road_number`/`alert_c_location` are the precise per-phase locators.
  `administrative_area` comes from a new `provinces()` helper (province,
  confirmed *not* an ELY-centre - that field doesn't exist in this feed),
  verified safe to reuse one value per situation across all 610 phases in
  the live feed, zero exceptions. Credential-free; no Alert-C location-code
  decoding (only the human-readable name is preserved, same as elsewhere).
- **`SituationRecord`/`Situation` gained a `.raw` field**, for all three
  DATEX sources, matching the `.raw` pattern already used elsewhere in this
  SDK (WZDx's `RoadEvent`, SRWR's `Record`) - a real, pre-existing gap
  surfaced while reviewing Finland's field mapping, not new to Finland.
  Populated for National Highways and Digitraffic (free - their payloads
  are already fully in memory). Left `None` for the streaming XML parser
  (NDW and raw DATEX v2/v3) deliberately, not by oversight: each XML
  element is cleared after yielding to keep the verified ~170 MB feed /
  ~35 MB memory characteristic, and a stored reference would go stale
  under the caller.
- **Iceland: IRCA/Vegagerðin** (`streetworks.datex2.irca`) - genuine DATEX
  II v3 XML (not a bespoke JSON schema like Finland/National Highways),
  reused through the existing shared parser's field-extraction logic.
  Credential-free, confirmed reliably reachable across multiple independent
  live fetches (no API key, no IP allow-listing) - unlike Norway (see
  below), this one ships complete. Verified field-by-field against real
  data: `record_type` is a genuine `xsi:type` discriminator
  (`MaintenanceWorks`, not a hardcoded compromise), location is always
  `PointLocation`/`pointByCoordinates` (checked across every situation on
  two independent fetches - zero `LinearLocation`, zero Alert-C),
  `road_maintenance_type` is a real, low-cardinality (`"roadworks"`) field,
  and `administrative_area` has no genuinely-stated source field anywhere in
  the feed (checked exhaustively - every unique element name across a full
  live fetch), so it's left unset rather than inferred. Licence confirmed to
  permit free reuse, redistribution, and commercial exploitation, with
  mandatory attribution ("Based on information provided by the Icelandic
  Road and Coastal Administration (IRCA)"), baked into the module
  docstring. Shares SOAP request-construction plumbing
  (`streetworks.datex2._snapshotpull`) with the (pending) Norway adapter,
  since both expose the identical `snapshotPull/2020` WSDL interface.
- **`streetworks.datex2.parser` gained `iter_situations_full`/
  `iter_roadworks_full`** - the same field extraction as
  `iter_situations`/`iter_roadworks`, but parsing the whole document into
  memory at once instead of streaming, so `Situation.raw`/
  `SituationRecord.raw` get populated with their source XML `Element`.
  `iter_situations` (streaming, clears elements) exists specifically for
  huge feeds like NDW's ~170 MB dump, where that memory bound is worth
  losing `.raw` for; Iceland's response is ~250 KB, nowhere near that scale,
  so `streetworks.datex2.irca` uses the `_full` variant and gets `.raw`
  fidelity for free. Norway's `VegvesenClient` still uses the streaming
  form pending Phase 2 confirming its real response size.
- **Norway: Statens vegvesen** (`streetworks.datex2.vegvesen`) - **Phase 1
  scaffold, pending live verification.** Built against Statens vegvesen's
  own WSDL/service catalogue (probed live) and a real snapshotPull document
  from Iceland's sibling implementation (used to validate that the shared
  parser handles a real SOAP-wrapped response unchanged, not as a claim
  about Norway's own feed shape). Blocked on credentials for Phase 2 live
  verification - not usable against real Norwegian data yet; see the module
  docstring for the three explicitly open questions.
- **France: Bison Futé/the DIRs** (`streetworks.datex2.bisonfute`) - genuine
  DATEX II **v2** XML for the non-concessionary national road network,
  reused through the existing shared parser (the `_full` variant, like
  Iceland - `.raw` populated). Credential-free, verified against the live
  feed (256 situations, 170 roadworks: 150 `MaintenanceWorks`, 20
  `ConstructionWorks`). Every single roadworks record (170/170) carries
  WGS84 coordinates alongside an Alert-C reference - coordinates taken,
  Alert-C preserved not decoded. `administrative_area` (the DIR region,
  e.g. `"Direction interdépartementale des routes/DIR Sud-Ouest"`) is
  genuinely stated on 170/170 roadworks records but on a different, coarser
  field than the shared model's `source_name` (a fine sub-office); a new
  `dir_regions()` helper reads it from each record's `.raw` XML directly,
  the same shape of solution as Digitraffic's `provinces()`. Published
  under the Licence Ouverte / Open Licence 2.0 (Etalab), confirmed via the
  official data.gouv.fr dataset page. France's real data (TPEG linear
  locations, Alert-C names) is what surfaced two genuine, pre-existing gaps
  in the *shared* DATEX parser - see Fixed, below.
- **`Coordinate` gained a `points` field.** Every converter with real
  multi-vertex line geometry available (WZDx's `LineString`, Street
  Manager's `LineString`, DATEX's `LinearLocation`/TPEG segments) used to
  collapse it to a single point when building the common model - a real,
  confirmed loss (not a documented convention, despite one docstring
  framing it that way), not just a France-specific gap. `value` stays one
  representative point (the first vertex) for every existing point-only
  consumer; `points` now carries the whole line when one genuinely exists
  (`None` for a real point location), with `points[0] == value` always.
  Fixed in `from_wzdx`, `from_streetmanager`, and `from_datex2` together,
  once, rather than per-provider.
- **Spain: DGT** (`streetworks.datex2.dgt`) - the DGT (Dirección General de
  Tráfico) National Access Point's SituationPublication, genuine DATEX II
  v3 (Level C, Spanish-extended profile), credential-free. Reused through
  the existing shared parser unchanged - no bespoke parsing path, same as
  NDW/Iceland/France. Verified against the live feed (2026-07): 656
  situations, 391 roadworks records, 100% coordinate coverage. Coverage is
  national except Catalonia and the Basque Country, which run their own
  regional traffic authorities and publish separately.
  Surfaced and fixed a genuine *discriminator* gap in the shared
  parser/model, not just a field-mapping one - DGT has zero
  `MaintenanceWorks`/`ConstructionWorks` records anywhere in the feed; it
  publishes roadworks as a generic record type
  (`RoadOrCarriagewayOrLaneManagement`, mostly, but also `SpeedManagement`
  and `AbnormalTraffic`) discriminated only by
  `cause/causeType=roadMaintenance` + `roadMaintenanceType=roadworks`.
  `SituationRecord.is_roadworks` now checks that pair additively when the
  xsi:type isn't one of the two dedicated types (confirmed not to change
  any other adapter's real fixture), and `road_maintenance_type` itself
  gained a matching deep-path fallback since Spain nests it under
  `cause/detailedCauseType` rather than as the record's direct child. The
  road identifier is stated as `roadName` (e.g. `"N-400"`), not
  `roadNumber` like NDW/France, so `_parse_location` gained a fallback for
  that too. `administrative_area` comes from a new `provinces()` helper -
  the real per-record province (e.g. `"Toledo"`), genuinely stated on
  391/391 real roadworks records but nested in a Spanish location
  extension, not on the shared model - same shape of solution as France's
  `dir_regions()`. Published under Creative Commons Attribution (CC BY),
  confirmed via the DGT NAP's own CKAN dataset metadata.
- **`streetworks.datex2.parser` gained an optional `provider` keyword** on
  all four public entry points (`iter_situations`/`iter_roadworks` and
  their `_full` variants), threaded through parsing - a public,
  backwards-compatible API addition, independent of any one country.
  Field-mapping fallbacks (the Spain-motivated ones above, and any future
  ones) now log at DEBUG level naming the provider, field, record id and
  the value used, so a future source doing something a third way is
  visible rather than silent. IRCA, Bison Fute and DGT pass their own
  label automatically; NDW's documented usage calls the parser directly,
  so the README example now passes `provider="NDW"` explicitly.
- **Germany: Autobahn GmbH** (`streetworks.autobahn`) - national motorway
  roadworks via Autobahn GmbH's own open JSON REST API, credential-free.
  Not DATEX II and not OGC/WFS, so it has its own small parser rather than
  routing through `streetworks.datex2` - the same shape of choice as WZDx
  for the US. Verified against a live fetch of all 113 real roads (2026-07,
  zero failures): 2,873 roadworks records grouping into 997 works via a
  genuine two-level identifier-prefix spine (599 multi-record groups, 599/599
  agreeing on their overall end date, zero disagreements) - including
  cross-road grouping, since 50/997 real prefixes span more than one road
  (a junction works gets listed under every connecting road's own
  response). Every real record carries `LineString` geometry (2-767
  vertices), kept whole, not collapsed to a point; native axis order is
  genuinely reversed within one record (`coordinate` is lat/long,
  `geometry.coordinates` is GeoJSON lon/lat) and flipped explicitly in
  `from_autobahn`, same as WZDx. Two real road-list traps confirmed live:
  lowercase route suffixes (`A64a`/`A99a`), and `"A60 "` (trailing space) -
  not a formatting quirk on the one real A60, but a genuinely separate,
  always-empty duplicate entry that must not be stripped (stripping it
  would silently refetch the real `"A60"` entry's 20 records under the
  wrong id). Dates are a deliberate, documented exception to "never infer,
  only take what's stated" (in the same register as Digitraffic's
  `validity.status` caveat): no end-date field exists anywhere in the API,
  and no start-date field at all for `SHORT_TERM_ROADWORKS` records
  (0/1,184 real ones carry it) - dates for those come from parsing
  `description[]` free text, five real shapes handled (long-term
  Beginn/Ende, the overall-measure end, and three short-term shapes -
  single-day, overnight/multi-day, and a recurring-weekly pattern
  collapsed to its outer bounding window), reaching 100%
  (`ROADWORKS`)/99.7% (`SHORT_TERM_ROADWORKS`) coverage; `Roadworks.is_start_verified`
  distinguishes a real `startTimestamp` from a text-derived one.
  Timezone is Europe/Berlin via `zoneinfo`, not a fixed offset - DST is
  genuinely observed in the data. **Licence unconfirmed** despite checking
  four independent sources (govdata.de's CKAN catalogue, the MDM portal,
  the community `bundesAPI/autobahn-api` docs, and the official autobahn.de
  app page - none state reuse/redistribution terms) - shipped deliberately
  with this caveat, flagged prominently in the module docstring and
  README rather than silently assumed open; test fixtures are
  structurally-real synthetic data, not committed real records, for the
  same reason.
- **Germany: state roadworks** (`streetworks.ogc`) - a new, reusable
  generic OGC WFS/OGC API Features GeoJSON client (`OGCFeaturesClient`,
  deliberately not roadworks-specific - built gazetteer-ready for future
  work, since German gazetteers are commonly published the same way),
  plus a declarative per-state field-map registry
  (`streetworks.ogc.germany`) that one shared converter
  (`streetworks.common.from_ogc_features`) reads generically - adding a
  state means a new field-map entry, not a new converter. Two states
  shipped, both verified against real data (2026-07): Hamburg (130
  features, `Point` geometry, dates `DD.MM.YYYY`) and Brandenburg (487
  features, `LineString` geometry, dates ISO, 100% coordinate coverage,
  0 out-of-bounds on the mandatory axis-order sanity check both states'
  tests run). Both publish under Datenlizenz Deutschland - Namensnennung -
  Version 2.0 (dl-de/by-2-0), confirmed directly from each WFS's own
  `GetCapabilities` document. Hamburg's access mode (WFS vs. a "direct
  GeoJSON download") was genuinely ambiguous before checking - confirmed
  live the download is a ZIP wrapper around the same WFS, not a separate
  source; the direct `GetFeature` call is canonical. One real field name
  differs from what was documented before checking: Brandenburg's road
  field is `Straßenummner` (double "n", a typo in the source schema
  itself). Mecklenburg-Vorpommern was checked and **parked**: confirmed
  live GML-only (its WFS explicitly rejects `application/geo+json`) and
  its licence is only vaguely stated, two independent reasons. Ships one
  `Works` per feature (1:1, no grouping) - Brandenburg's `ID` field showed
  a real but imperfect (~81-88% agreement, no corroborating field) grouping
  signal, raised rather than acted on unilaterally, consistent with the
  project's record-identity discipline.
- **Germany: Saxony (Sachsen)** added to `streetworks.ogc` - 1,531 real
  closures + 813 diversions, `LineString` geometry, via a direct GeoJSON
  ZIP download (Saxony has no queryable WFS/Features service at all -
  confirmed exhaustively via the GDI-DE catalogue's own metadata, 5 real
  records checked, none link a working WFS despite an operator news item
  once referencing one). Genuinely has no WGS84 source anywhere (checked
  its WMS, its download, and its "planned works" dataset's own ISO
  metadata) - ships in its real CRS, `EPSG:25833` (UTM33N), carried
  through and labelled explicitly on `Coordinate.crs` rather than parked
  or silently reprojected, the same policy this SDK already applies to
  its British National Grid providers (OS Open USRN, DataVIA, Street
  Manager) - `StateFieldMap` gained a `crs` field and
  `OGCFeaturesClient`/`from_ogc_features` are now CRS-aware throughout,
  not hardcoded to EPSG:4326. Dates are mostly `DD.MM.YYYY` but 639 of
  3,062 real date fields (21%) carry a real hour suffix
  (`"16.08.2026  08 Uhr"`) - parsed rather than dropped, preserving a
  genuinely-stated time instead of collapsing to midnight. Saxony's `ID`
  field shows the same shape of grouping signal Brandenburg's does (1,531
  features, only 1,133 distinct values) - raised in the module docstring,
  not acted on, consistent with the existing 1:1 policy.

  Also investigated and **parked**: Saxony-Anhalt (GML-only, confirmed by
  testing `OUTPUTFORMAT=application/json` directly against the real WFS;
  its licence is also explicitly "non-commercial use only," not merely
  unconfirmed), Mecklenburg-Vorpommern (unchanged from before - GML-only,
  vague licence), NRW (publishes road network data, not roadworks - a
  gazetteer concern; actual roadworks route to the gated Mobilithek/DATEX
  path), and Bavaria (BAYSIS has no Baustellen/roadworks layer at all).

### Fixed

- **DATEX `alert_c_location` returned a raw numeric location-table code
  instead of the human-readable name.** The shared XML parser read
  `specificLocation` (e.g. `"17855"`), ignoring the sibling
  `alertCLocationName` (e.g. `"Fos"`) that actually states the name -
  confirmed on France's live feed, 787/787 real Alert-C blocks carry both.
  A linear location can state two points (primary/secondary); if the first
  name found is an empty placeholder, later ones are tried before falling
  back to the raw code - the same "skip empty, take the first real one"
  discipline as the multilingual-comments fix, one level up. Not a
  France-specific bug: it had simply never been exercised by real Alert-C
  data before (Digitraffic has its own, different, already-correct code
  path).
- **DATEX TPEG linear locations only kept one endpoint's coordinates.** A
  segment's `from`/`to` endpoints (each with their own `pointCoordinates`)
  used to collapse to whichever one the parser's generic "first
  `pointCoordinates` found anywhere" search happened to hit first (`to`,
  on France's real feed) - silently dropping the other, genuinely-present
  endpoint. Now captured as a real 2-point line (`from` then `to`).

- **Multilingual DATEX fields could silently return an empty string.** The
  shared XML parser's `_multilingual()` helper took the *first* `<value>`
  in a `values/value[lang]` structure regardless of whether it was empty -
  some real feeds (confirmed on Iceland's IRCA feed) list an empty
  placeholder value (e.g. `lang="en"`) before the real text in another
  language. This silently dropped real comment text (and any other field
  routed through `_multilingual`) on every DATEX provider with this value
  ordering. Now skips empty entries and returns the first non-empty value.
  Verified against NDW, National Highways, and Digitraffic fixtures
  (unaffected - they don't have this ordering) and confirmed it now
  correctly surfaces real text on the Iceland/Norway fixtures.

## [0.6.1] - 2026-07-11

### Added

- **Location provenance on `Works`**: `territory` (country-level - UK
  nations count as countries, plus `"USA"`, `"Netherlands"`, etc.) and
  `administrative_area` (the sub-national body that *owns* the data one
  level down - a UK highway authority, a US state DOT, a Dutch province,
  or a national operator's own name where the operator IS the authority),
  so a consumer can filter a mixed cross-provider `list[Works]` by where
  the data comes from. `administrative_area` is populated only where a
  provider genuinely states it, never inferred from a coordinate, and is
  consistent *within* a territory but not size-comparable *across* them.
  `WorksSite` gained read-only `territory`/`administrative_area`
  properties that delegate to the parent `Works` (single source of truth,
  convenient access from a site alone).
  - `from_srwr` gained an optional `districts` parameter: District (099)
    records are excluded from `Activity` bundles by the reader (they're
    file-section reference data, not activity data), so decoding
    `notifiable_district_id` to a name needs it passed in explicitly;
    without one, the bare district ID is used.
  - `from_datex2` gained explicit `territory`/`administrative_area`
    keyword parameters - it's one shared converter for NDW and National
    Highways precisely because they produce the same model, but
    Netherlands vs England can't be told apart from a `Situation` alone,
    and National Highways' `source_name` is a generic `"roadworks"`
    label, not an authority name.
  - `from_wzdx` gained the same two parameters, `territory` defaulting to
    `"USA"` - WZDx's publishing state lives on the registry entry, not
    the road event, so it can't be derived from events alone either.
  - `from_streetmanager`, `from_trafficwatchni` and `from_trafficwales`
    populate them directly from existing provider data (or a hardcoded
    territory where the feed is nation-wide with nothing sub-national to
    report).

## [0.6.0] - 2026-07-10

### Added

- **US work zones: WZDx** (`streetworks.wzdx`): a parser-first provider for
  the US Work Zone Data Exchange standard - one schema-level GeoJSON parser
  plus a generic client that fetches any agency's feed URL (WZDx is
  published independently by ~40+ agencies, not one central API), and a
  registry helper against the USDOT feed registry. Built and verified
  against 12 live feeds spanning WZDx v3.1-v4.2 (Hawaii, Maryland, Indiana,
  NY/TRANSCOM, Missouri, Louisiana, Kentucky, Washington, Minnesota,
  Delaware, Idaho, Québec), not a single sample - caught real cross-agency
  variation a narrower check would have missed: `core_details` nesting is
  v4-only (v3.1 feeds are flat), the feed-info key isn't cleanly
  version-gated (`feed_info` vs the older `road_event_feed_info`, one v4.2
  feed emits both), geometry varies (LineString/MultiPoint, sometimes both
  in one feed), and two genuinely different cross-reference mechanisms
  exist in the wild (`relationship.parents`/`.children` vs
  `core_details.related_road_events`). Confirmed real placeholder/garbage
  dates at scale (one live feed's "current" records span years 2019-2040).
  Every field read is defensive - nothing raises on a malformed record.
- **Common models**: `streetworks.common.from_wzdx` converter, mapping
  `event_type == "work-zone"` records to `WorksSite` (detour/device/
  restriction events are WZDx's analogue of DATEX measures and stay
  native-only). `source_grade` is `operator`; `date_confidence` prefers
  WZDx's accuracy-enum fields over its boolean verified flags, per the two
  different encodings observed live. Coordinate axis order is verified
  against `from_datex2`'s actual behaviour (not assumed) and explicitly
  flipped from WZDx's native GeoJSON `(lon, lat)` to this SDK's
  `(lat, lon)` convention for `EPSG:4326`, with a dedicated cross-converter
  test asserting the two can't silently drift apart.
- `streetworks._dt`: the fractional-second-tolerant ISO-8601 parser
  (previously local to `streetworks.datex2`) is now shared - WZDx feeds hit
  the exact same problem (`datetime.fromisoformat` only accepts 0/3/6-digit
  fractional seconds on Python < 3.11) with even worse precision (7 digits
  on a Washington State feed) than the case that broke `datex2` on 3.10.

## [0.5.0] - 2026-07-09

### Added

- **Common models** (`streetworks.common`): canonical cross-provider types -
  `Works` (the umbrella: reference, location, promoter/source), `WorksSite`
  (the dated, actionable unit - Street Manager permits, SRWR phases, DATEX
  roadworks records), `WorksPlanning` (planning artifacts - PAAs, Forward
  Plans - kept a distinct type so a record never migrates canonical type as
  its lifecycle status changes), `Coordinate` (value plus an explicit CRS
  label, never silently reprojected) and `Notice`. `SourceGrade` and
  `DateConfidence` let consumers filter by trustworthiness without
  provider-specific knowledge. Converters (`from_srwr`, `from_streetmanager`,
  `from_datex2`, `from_trafficwatchni`, `from_trafficwales`) sit alongside
  each provider's native, full-fidelity interface - every canonical object
  keeps `.raw` pointing back at its source record(s).
  - SRWR: joins Phase (007) to Undertaker-Phase (008) by `phase_number` -
    no such join existed before.
  - Street Manager: groups permits by `work_reference_number`; a PAA and the
    permit that later supersedes it share one reference, confirmed live -
    the PAA becomes `WorksPlanning`, not a site. New
    `reporting.forward_plans()`/`iter_forward_plans()` (sync + async) feed
    Forward Plans in; real sandbox data showed these already carry their
    eventual work reference (the design spec assumed they're free-floating
    until converted), so `Works` gained a `plannings` field.
  - DATEX (NDW + National Highways): one converter serves both adapters,
    since they already share the same `Situation` model. `date_confidence`
    is computed from real `validityStatus` values observed in the National
    Highways fixture (`active`/`suspended` -> verified, `planned` ->
    estimated).
  - TrafficWatchNI / Traffic Wales: thin converters (RSS items have no
    umbrella reference); `date_confidence` is always `unknown`.
- **Traffic Wales parser upgrade** (`streetworks.trafficwales`): rebuilt
  against a live fetch of the real feed rather than a synthetic sample.
  `FeedItem` now carries `coordinate` (WGS84, from `georss:point`),
  `road`/`direction`/`location_from_to`/`work_type`/`restriction` (parsed
  positionally from both ends of the colon-delimited title - segment count
  and order both vary across real items), `severity` (free text - the feed
  mixes closure-type and genuine severity wording), `start`/`end`/
  `last_updated` (from labelled description fields, 4-digit years,
  preferred over the title's 2-digit dates), `operating_window` and
  `source`. Prerequisite for the Traffic Wales common-model converter.

## [0.4.0] - 2026-07-08

### Fixed

- Reporting auto-pagination now recognises the live API's `has_next_page`
  key (snake_case); previously only the camelCase `hasNextPage` implied by
  the swagger reference was checked, so iteration stopped after one page
  against the real service. Both spellings are now accepted.
  Live-verified and reported by Chris Carlon.
- DATEX II timestamp parsing (`streetworks.datex2.parser._dt`) now tolerates
  non-standard fractional-second precision - National Highways' live API
  emits 2-digit fractions (e.g. `"2026-05-18T08:22:29.29Z"`), which
  `datetime.fromisoformat` silently fails to parse on Python < 3.11 (only
  0/3/6-digit fractions are accepted there). Caught by CI running the matrix
  down to 3.10, not by local testing on a newer interpreter.

### Added

- **National Highways provider** (`streetworks.datex2.nationalhighways`):
  a DATEX II v3.4 adapter for England's Strategic Road Network Road and
  Lane Closures service. Unlike NDW, National Highways returns its closures
  as JSON, not XML, so it gets its own parsing path onto the shared
  `Situation`/`SituationRecord` models; handles both single- and
  multi-location records and cursor pagination via the `x-next` header.
  Live-verified, including the undocumented-as-mandatory
  `X-Response-MediaType: application/json` header the real API requires.
- **UK Police provider** (`streetworks.police`): a thin adapter over
  `data.police.uk`'s street-level crime endpoints (no credentials), plus a
  `safety_signal()` helper that aggregates crime near a point into a
  worker-safety signal for lone working / unfamiliar sites, filtered to the
  categories that actually bear on personal risk. Not a street-works
  dataset in its own right - documented caveats for historical-not-live and
  area-level-not-site-level data. Live-verified.
- `examples/quickstart.py` is now resilient: every provider demo runs
  inside a try/except so one unreachable or misconfigured feed no longer
  aborts the rest of the tour, and it now includes National Highways and
  UK Police alongside the existing providers.

## [0.3.0] - 2026-07-06


### Added

- **Northern Ireland provider: TrafficWatchNI** (`streetworks.trafficwatchni`)
  and **Wales provider: Traffic Wales** (`streetworks.trafficwales`): open,
  credential-free roadworks/incidents RSS feeds (5-minute refresh) with
  best-effort typed extraction and raw text always preserved. Honest
  caveat: traveller-information feeds, not works registers. With these,
  all four UK nations have coverage. Attribution requirements (DfI TICC /
  Traffic Wales) are documented and baked into module docstrings.
- **DATEX II support** (`streetworks.datex2`): streaming, namespace-tolerant
  parser for SituationPublication roadworks (DATEX II v3 and v2) with typed
  situations, records, validity and normalised locations, plus an `NDWClient`
  adapter for the Netherlands' credential-free national open data. Verified
  against the real 172 MB Dutch planned-works feed (14,577 situations parsed
  in ~7 s at ~35 MB memory).
- **Street Manager Section 58 support** (`reporting.section_58s()` and the
  `active_section_58()` derived view, sync + async), the documented
  "derived view" convention, committed v6 generated models, and a swagger
  URL fix in the model generator. Contributed by Chris Carlon (#1).
- **DataVIA WMS support**: `wms_capabilities()`, `get_map()` (rendered NSG
  map images) and `get_feature_info()` ("what's at this pixel?") on both
  sync and async clients. Handles the WMS 1.3.0/1.1.1 dialect differences
  (CRS vs SRS, I/J vs X/Y) and surfaces the classic
  exception-XML-with-HTTP-200 failure as a proper error. WMS layer names
  are unprefixed (unlike the WFS's `ms:` feature types - live-verified);
  the `Layer` enum works for both, and WMS-only aggregate layers such as
  `"Streets"` can be passed as strings.
- `examples/quickstart.py` + `.env.example`: a one-file tour that loads
  credentials from `.env` and retrieves a little real data from every
  configured provider (see above for the 0.4.0 resilience update).

## [0.2.0] - 2026-07-05


### Added

- **New provider: OS Open USRN** (`streetworks.openusrn`) - GB-wide USRN
  lookup with street geometry via the OS Downloads API (OpenData, no key).
  Streamed ~300 MB GeoPackage download and a stdlib-only reader (sqlite3 +
  minimal WKB-to-WKT decoding), so no GDAL or geospatial dependencies.
- **New provider: SRWR Open Data** (`streetworks.srwr`) - Scotland's
  national road works register via its credential-free Open Data CSV
  extracts (OGL v3). Streaming parser for the multi-record-type format
  (spec v2.02), typed records for every SRWR record type, Activity
  grouping, latest-occurrence dedup for monthly/yearly archives, coded-
  value lookup, and a download client with the spec-recommended retry
  logic. Verified against real published daily (45k records) and monthly
  (4M records) extracts.
- Auto-pagination for the Street Manager Reporting API: `iter_permits()`,
  `iter_inspections()`, `iter_fixed_penalty_notices()`, `iter_reinstatements()`
  and `iter_alterations()` on both sync and async clients follow the API's
  `offset`/`hasNextPage` contract so callers never page by hand.
- Generated Pydantic models for the D-TRO v3.5.1 data specification
  (`streetworks.dtro.models.v3_5_1`), plus `DTROClient.validate_payload()`
  to check publish payloads locally before submission. Generation pipeline
  in `scripts/generate_dtro_models.py` with the schema stored under
  `specs/dtro/v3_5_1/`.

## 0.1.0 2026-07-04

Initial release.

- `streetworks.streetmanager`: sync + async clients for all nine Street
  Manager APIs (V6/V7, sandbox/production) with automatic auth, token
  refresh, retries and rate-limit handling. Explicit `authenticate()` method
  for fail-fast credential/connectivity checks.
- Connectivity smoke test (`scripts/smoke_test.py`) and skip-guarded
  integration test suite (`pytest -m integration`) for verifying against the
  real test/sandbox systems.
- `streetworks.opendata`: SNS receiver toolkit — parsing, signature
  verification, subscription auto-confirmation, event extraction.
- `streetworks.datavia`: OGC WFS client for Geoplace DataVIA - Basic and
  OAuth2 client-credentials auth, full NSG layer catalogue, composable
  OGC filters (USRN, DWithin, Intersects, BBOX, attribute equality),
  documentation-faithful POST GetFeature bodies, KVP GET, paging iterator,
  and all documented output formats.
- `streetworks.dtro`: DfT Digital Traffic Regulation Orders client -
  OAuth2 client credentials with token caching, integration/production
  environments, publish (body/file/gzip), retrieve, delete, events search,
  signed-URL full CSV export, provisions (create/update/delete, with the
  distinct `App-Id` header), schemas, and search. Token metadata exposed via
  `token_info`. Verified against the official OpenAPI spec and Postman
  collection.
