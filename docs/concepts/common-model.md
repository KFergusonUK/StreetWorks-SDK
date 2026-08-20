# Using the common model

Every provider in this SDK has its own native, full-fidelity client — see
[`docs/providers/`](../providers/index.md) for each one, with a worked
example. This page is the companion piece: how to convert what a native
client returns into the shared cross-provider types, and when that's the
right tool for the job.

For the full type reference (field-by-field design, why there are two
levels not three, the record-identity rules) see
[`docs/concepts/data-model.md`](data-model.md). This page stays practical —
patterns and a converter-by-converter index.

## The pattern

Every converter is a plain function named `from_<provider>`, importable
from `streetworks.common`. It takes whatever the native client already
returns — a raw feature, a parsed object, a list of them — and returns
canonical type(s). Nothing about the native client changes; the converter
sits alongside it:

```python
from streetworks.srwr import SRWRClient, iter_activities
from streetworks.common import from_srwr

with SRWRClient() as srwr:
    archive = srwr.download_daily("srwr-daily.zip")
    for activity in iter_activities(archive):
        works = from_srwr(activity)          # -> Works, with .sites: list[WorksSite]
        for site in works.sites:
            print(site.reference, site.works_type, site.date_confidence)
```

Two converter families exist, matching the two canonical models:

- **Works-model converters** — return `Works` (or `list[Works]`), each
  carrying `.sites: list[WorksSite]`. This is the roadworks/street-works
  side: what's happening, where, under what confidence.
- **Gazetteer converters** — return `Street`, `Segment`, or `Address`
  (never a list — one native record in, one canonical record out). This is
  the street/address-identity side: what a street or address *is*, not
  what's happening on it.

A converter never replaces the native client's own return values — `.raw`
on every canonical object always points back at the exact source record(s),
so nothing is lost by converting.

## Works-model converters

Most take a list of raw/native records and return `list[Works]`; a few take
one record and return one `Works` (noted below). Two — `from_datex2` and
`from_wzdx` — need `territory`/`administrative_area` passed explicitly,
since neither can be read off the source record alone.

| Provider | Converter | Notes |
|---|---|---|
| Street Manager (England) | `from_streetmanager` | Groups by `work_reference_number` |
| SRWR (Scotland) | `from_srwr` | One `Activity` in, one `Works` out; optional `districts` map |
| WZDx (USA, multi-agency) | `from_wzdx` | Takes `territory`/`administrative_area` as keywords |
| NYC DOT | `from_nycdot` | Groups by `applicationtrackingid` |
| Chicago CDOT | `from_chicagodot` | Groups by `applicationnumber` |
| DriveBC (British Columbia) | `from_drivebc` | Reconciles two mutually-exclusive schedule shapes |
| DATEX II (NDW, National Highways, Digitraffic, IRCA, Bison Futé, DGT, Belgium/Flanders, Luxembourg, Bulgaria, Euskadi, Statens vegvesen, ASFINAG) | `from_datex2` | One shared converter for the whole DATEX cluster; takes `territory`/`administrative_area`/`crs` as keywords — see [DATEX II](../providers/europe.md#datex-ii-european-roadworks) |
| Statens vegvesen (Norway, DATEX) | `from_vegvesen` | One `Situation` in, one `Works` out |
| Autobahn GmbH (Germany) | `from_autobahn` | |
| German state roadworks (Hamburg, Brandenburg, Saxony) | `from_ogc_features` | One shared converter, takes a `field_map` per state |
| Berlin (VIZ) | `from_berlin` | Merges two feeds via a verified join key |
| Consell de Mallorca | `from_mallorca` | Joins two layers (icons + tram) |
| Servei Català de Trànsit (Catalonia) | `from_sct` | No dates in the source; `date_confidence` always unknown |
| Ayuntamiento de Madrid (INFORMO) | `from_madrid` | |
| Via Lietuva (Lithuania) | `from_vialietuva` | Own CRS (`EPSG:3346`) and reversed WKT axis order |
| Paris (Chantiers) | `from_paris` | |
| Copenhagen (Gravetilladelser) | `from_copenhagen` | Dedupes by `sagsnr`, prefers LineString over Point |
| Oslo (SøkSys) | `from_oslo` | Dedupes by row id, then groups by `activity_id` |
| Helsinki (Kaivuilmoitus) | `from_helsinki` | Groups by `hakemustunnus` |
| Vienna (verkehrswirksame Baustellen) | `from_vienna` | Combines two disjoint layers (Point + LineString) |
| Kanton Zürich | `from_canton_zurich` | `reference` stays `None` — no unique id field exists |
| Stadt Zürich | `from_zurich` | `reference = baunr`, 100% unique |
| Lisboa (Condicionamentos) | `from_lisboa` | Evidence-based `motivo` filter |
| Roma (Roma si trasforma) | `from_roma` | No dates in the schema |
| Milano (Avvisi di manomissione) | `from_milano` | One `Works` per feature, no grouping |
| CCISS (Italy) | `from_cciss` | One `BulletinItem` in, one `Works` out; no geometry |
| TrafficWatchNI (Northern Ireland) | `from_trafficwatchni` | One `RoadworksItem` in, one `Works` out |
| Traffic Wales | `from_trafficwales` | One `FeedItem` in, one `Works` out |
| Transport for London (Road Disruption) | `from_tfl` | `corridorIds` never promoted to `street_ref` — too incomplete |
| Jersey RoadWorkx | `from_jersey` | |
| NZTA (Waka Kotahi) | `from_nzta` | Point-only; excludes the `Road Area Events` hazard layer |
| Transport for NSW (Live Traffic) | `from_nsw_livetraffic` | |
| DTP Planned Disruptions (Victoria) | `from_vic_disruptions` | |
| Main Roads WA (WebEOC Roadworks) | `from_au_wa_mainroads` | Runtime coordinate guard against unreprojected Web Mercator |
| Traffic SA / DIT Roadworks | `from_au_sa_trafficsa` | |
| QLDTraffic Events (Queensland) | `from_au_qld_qldtraffic` | |
| ACT Temporary Traffic Management | `from_au_act_ttm` | |
| Tasmania Roadworks (State Roads) | `from_au_tas_roadworks` | Only AU provider with real line geometry |

`streetworks.police` (UK Police) deliberately has **no** `from_police`
converter — it's a worker-safety context signal (area-level crime), not a
works feed, and forcing it into `WorksSite` would misrepresent what it is.
`streetworks.dtro` and `streetworks.opendata` (Street Manager Open Data)
are similarly out of the works hierarchy for their own stated reasons — see
their own module docstrings.

## Gazetteer converters (`Street` / `Segment` / `Address`)

One record in, one canonical record out — never a list. Designed for three
use cases only: plotting streets on a map, linking streets to roadworks via
`WorksSite.street_ref`, and pulling street names out of address gazetteers.

| Provider | Converter | Returns |
|---|---|---|
| BAN (France) | `from_ban` | `Address` |
| BD TOPO (France) | `from_bdtopo` | `Segment` or `Street`, depending on the input object |
| BAG (Netherlands) | `from_bag` | `Address` |
| NWB (Netherlands) | `from_nwb` | `Segment` (no `Street` — see below) |
| Kartverket (Norway) | `from_kartverket` | `Address` |
| NVDB (Norway) | `from_nvdb` | `Segment` (real `LINESTRING Z`, compound 3D CRS) |
| Geoplace DataVIA (GB) | `from_datavia` | `Street` or `Segment` |
| OS Open USRN (GB) | `from_openusrn` | `Street` |
| TIGERweb (US Census) | `from_tigerweb` | `Segment` |
| LINZ (New Zealand) | `from_linz_address` / `from_linz_road` / `from_linz_road_section` | `Address` / `Street` / `Segment` |
| G-NAF & National Roads (Australia) | `from_gnaf_address` / `from_gnaf_road` | `Address` / `Segment` |

`from_nwb` is the one deliberate gap worth calling out: NWB publishes
segments with a `bag_orl` reference, but this SDK's built BAG route has no
street row of its own to emit as a `Street` — so Dutch street names only
reach this model via `Address.street_name`, never a Dutch `Street`. Not a
bug, a documented, real gap — see `from_nwb`'s own docstring.

## Comparing across providers

The point of converting is code that treats works data from several
providers the same way without caring which one it came from — filtering
by `source_grade` or `date_confidence`, or printing two providers side by
side:

```python
from streetworks.streetmanager import StreetManagerClient, Environment
from streetworks.common import from_streetmanager, from_paris
from streetworks.paris import ParisClient

with StreetManagerClient(user, password, environment=Environment.SANDBOX) as sm:
    sm.authenticate()
    permits = list(sm.reporting.iter_permits(status="submitted"))
    sm_works = from_streetmanager(permits)

with ParisClient() as paris:
    paris_works = from_paris(list(paris.iter_roadworks()))

for works in [*sm_works, *paris_works]:
    for site in works.sites:
        if site.date_confidence != "unknown":
            print(works.territory, site.reference, site.works_type, site.date_confidence)
```

See [`examples/compare_active_works.py`](../../examples/compare_active_works.py)
for this pattern working end-to-end against two genuinely different
provider shapes (Street Manager states an explicit lifecycle status field;
Paris states none, so "active" is inferred from its own date window
instead) — the same few lines of caller code handle both unmodified.

**Never deduplicate across providers on this basis.** Two providers'
records can legitimately describe overlapping ground truth (a national
DATEX feed and a municipal register both covering the same stretch of
road) without being the same permit — this SDK never merges near-identical
works across providers without a shared, verified reference id, and
neither should code built on top of it. See
[`docs/concepts/data-model.md`](data-model.md#never-deduplicate-across-providers)
for the full reasoning and a real case where two feeds turned out to
genuinely overlap.

For a mixed list of those `Works` near a WGS84 point or UK USRN, see
[`examples/works_near/`](../../examples/works_near/) — a documented
UK-first join over a four-provider subset (Traffic Wales, National
Highways, Street Manager, SRWR), not a uniform `search()` facade. This
is deliberately example code, not a `streetworks` package export: a
top-level `streetworks.works_near(lat, lon)` would sit next to
`providers()`/`get_provider()`, which genuinely do span every
registered provider, and a caller would have no signal at the call site
that this one is a curated UK-only subset — a point in, say, Zürich or
Amsterdam would just silently come back empty. Keeping it under
`examples/` (not shipped in the installed package — see `pyproject.toml`'s
`packages = ["src/streetworks"]`) makes that scope obvious from where
the code lives, not just from a docstring caveat. Distance is haversine
on `EPSG:4326` only; records whose only geometry is in another CRS are
skipped, never silently reprojected.
