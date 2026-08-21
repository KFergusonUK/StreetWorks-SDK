# United States

> Migrated verbatim from README.md's `## WZDx (US Work Zone Data
> Exchange)`, `## NYC DOT Street Construction Permits (New York City)`,
> and `## Chicago CDOT Street Closures` sections (phase one, lossless
> restructure — see `docs/migration-mapping.md`). TIGERweb (US Census
> Bureau road segments) is documented in
> [`docs/providers/uk.md`](uk.md#jersey-roadworkx-and-tigerweb-arcgis-rest)
> alongside Jersey RoadWorkx, since the README covers both together
> under one section/client shape.

## WZDx (US Work Zone Data Exchange)

WZDx is the US standard for work zone data — GeoJSON-based, distinct from
DATEX II, so `streetworks.wzdx` is its own parser rather than a `datex2`
adapter. It's a schema published independently by ~40+ agencies (state
DOTs, MPOs, tolling authorities...), not one central API, so
`WZDxClient.fetch()` takes any feed URL directly — credential-free:

```python
from streetworks.wzdx import WZDxClient

with WZDxClient() as wzdx:
    feed = wzdx.fetch("https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed")
    print(feed.version, feed.publisher, len(feed.road_events))
    for event in feed.road_events:
        if event.is_work_zone:
            print(event.road_names, event.vehicle_impact, event.geometry.point)
```

Convert to the shared cross-provider model:

```python
from streetworks.common import from_wzdx

works = from_wzdx(feed.road_events, territory="Washington")  # non-work-zone events skipped
```

Use `streetworks.wzdx.list_feeds()` to discover feed URLs from the [USDOT
feed registry](https://datahub.transportation.gov/Roadways-and-Bridges/Work-Zone-Data-Feed-Registry/69qe-yiui/about_data)
rather than hardcoding one — **confirmed live 2026-08-02, 41 real
registered feeds.** `list_feeds()` defaults to `active_only=True,
wzdx_only=True`: it drops feeds the registry itself flags inactive, plus
any sub-3.1/unparseable version, a documented skip rather than a
mis-parse — the real version discriminator is `version`, *not* the
`format` column, which is always just `"geojson"`/`"json"` and never
states spec family.

**CWZ (Connected Work Zone, `version == "CWZ 1.0"`) is parsed too** —
a related AASHTO/ITE/NEMA/SAE standard built on WZDx v4.2 as its own
base (4/41 real registry rows: Massachusetts DOT, Colorado DOT, Illinois
DOT, and PurposeBuilt Systems). A real, live, genuinely keyless CWZ feed
(PurposeBuilt Systems) confirmed the standard's own field-naming
convention is identical to WZDx's, needing no changes at all; Massachusetts
DOT's own real implementation instead serializes every key in camelCase
(`coreDetails`, `eventType`...) — a vendor quirk, not the spec's own
convention, confirmed against its live OpenAPI schema — so every feed's
properties are normalized (camelCase → snake_case, a no-op on feeds
already snake_case) before field extraction. Massachusetts DOT, Colorado
DOT and Illinois DOT's own real CWZ feeds all require a credential this
SDK does not obtain on a caller's behalf — `entry.needapikey`/
`entry.apikeyurl` surface the same way as any other keyed WZDx feed (see
below), and `WZDxClient.fetch(url, headers=...)` accepts a caller's own
Bearer token or (for feeds preferring it) a pre-templated query-param key
already in the registry's `url`:

```python
from streetworks.wzdx import WZDxClient
from streetworks.wzdx.registry import list_feeds

for entry in list_feeds():
    if entry.needapikey:
        continue  # ~13/41 real feeds need a caller-supplied key - entry.apikeyurl points at signup
    with WZDxClient() as wzdx:
        feed = wzdx.fetch(entry.url)
        print(entry.state, entry.organization, len(feed.road_events))
```

**511NY (NYSDOT) is the first concrete verified feed** — confirmed live
end-to-end (registry lookup → real fetch → real parse): no key needed,
WZDx v4.1, 6,895+ real road events, 100% `MultiPoint` geometry (not
`LineString` — a real correction to an earlier assumption; WZDx's spec
allows either). NYC's own local-street works are **not in this
registry** — they're NYC DOT's separate Socrata feed (see below), a
deliberate, follow-on build, kept apart from New York *State* coverage.
**Not US-only** — a real, active Quebec City (Canada) feed is registered
too, so `streetworks.common.from_wzdx()` takes `territory`/
`administrative_area` per feed (sourced from `entry.state`/
`entry.organization`) rather than assuming `"USA"`. See
[`docs/providers/canada.md`](canada.md) for the rest of this SDK's
Canadian coverage (DriveBC/British Columbia).

**Two more concrete population wins, confirmed live 2026-08-03** — both
keyless, both zero code changes needed (the registry-driven design
already covers any feed): **Florida DOT** (`fldot`, WZDx v4.2) — 17,932
real events, 3,386 real work-zones cleanly separated from 14,546 real
detours. **Austin, TX** (`austin`, WZDx v4.2, **CC0**-licensed directly
in the feed) — 2,791 real events, **100% work-zone**, no incident/detour
noise at all — the cleanest feed found anywhere in this SDK so far. Two
corrections to an earlier population-target assumption, on real registry
evidence rather than a guess: **no statewide California feed is
registered at all** (the only real California entry, `mtc`/Bay Area
MTC, needs a key), and **Texas's own statewide feed (`txdot_v4_2`) also
needs a key** — Austin is the real keyless Texas win, not TxDOT.

Verified against **12 live agency feeds spanning WZDx v3.1–v4.2** (not one
sample — cross-agency variation a single feed hides is exactly what broke
assumptions during development): `core_details` nesting is a v4-only
convention (v3.1 feeds are flat on `properties`); the feed-info key isn't
cleanly version-gated (`feed_info` vs the older `road_event_feed_info` -
one v4.2 feed emits both); geometry varies (`LineString`/`MultiPoint`,
sometimes both within one feed, always **`(longitude, latitude)`** GeoJSON
order — the reverse of DATEX's `(latitude, longitude)`); and date-firmness
has two independent encodings in the wild (boolean
`is_start_date_verified`/`is_end_date_verified` flags, and accuracy enums
`start_date_accuracy`/`end_date_accuracy`) that don't always agree with
each other and don't always exist together. Real placeholder/garbage dates
are confirmed at scale, not assumed — one live feed's "current" records
spanned years 2019–2040. Every field is read defensively; nothing raises
on a malformed record.

## NYC DOT Street Construction Permits (New York City)

The local follow-on the WZDx feed-registry harvest deliberately scoped
out — 511NY (above) covers New York *State* highways; New York *City*'s
five boroughs are a separate authority (NYC DOT) publishing a separate
shape entirely, not WZDx at all.

```python
from streetworks.nycdot import NycDotClient
from streetworks.common import from_nycdot

with NycDotClient() as nycdot:
    works_list = from_nycdot(list(nycdot.iter_roadworks()))
```

**A genuine permit register — the US cousin of Street Manager.** [Street
Construction Permits (2022-Present)](https://data.cityofnewyork.us/Transportation/Street-Construction-Permits-2022-Present/tqtj-sjs8)
(NYC Open Data/Socrata, real total **3,798,494** rows, confirmed live
2026-08-02, no credentials) records DOT's own issued permits, not
observed conditions — `source_grade=register`, this SDK's second source
at that tier after England's Street Manager, and the first in the US. A
real Works-umbrella grouping matches Street Manager's own shape exactly:
`applicationtrackingid` genuinely groups multiple permits (one real
application had 226 real permits under it, a large paving job spanning
many street segments) — `from_nycdot` groups by it the same way
`from_wzdx` groups by `works_ref`, one `Works` per application, one
`WorksSite` per permit.

**No stated join to a street register — settles a genuinely open
question, honestly, not the hoped-for way.** The full real
39-column schema was checked directly: there is no LION `segmentid` (or
any other street-register identifier) anywhere on this dataset — only
free-text cross-street names, so `WorksSite.street_ref` is never
populated, the same SA-`ROAD_NO`/NZTA discipline this SDK holds
everywhere. A genuine NYC LION gazetteer strand remains a real,
separate, not-yet-built follow-on, but it would join to nothing here
even once built.

**Real geometry exists anyway.** A real `wkt` column is populated on
**80.5%** of all rows (`LINESTRING`/`POINT`/a real, confirmed-live
`MULTIPOINT` shape — support for the latter added to this SDK's shared
`_wkt` helper, previously unhandled). **Coordinates are NAD83 / New York
Long Island, EPSG:2263** — inferred from real coordinate-value-range
evidence and the near-universal NYC city-agency GIS convention, not an
explicitly stated dataset SRID, and never silently reprojected to
WGS84, the same "label honestly" discipline Tasmania's own real
GDA94/MGA zone 55 geometry established for this SDK.

**Permit-type filtering needed real evidence, not the coarser series
field alone.** `iter_roadworks()` filters to two confirmed roadworks
series (`STREET OPENING PERMIT`, 1,717,842 real rows; `DOT IN-HOUSE
PAVING AND MILLING`, 118,656). `BUILDING OPERATION PERMIT` (1,206,251,
the second-largest series) is genuinely mixed at the finer
`permittypedesc` level — real street-occupying sub-types
(`OCCUPANCY OF ROADWAY AS STIPULATED`, `PLACE MATERIAL ON STREET`)
sit alongside clearly non-roadway ones (`OCCUPANCY OF SIDEWALK AS
STIPULATED`, bike-share placement) — no confident allowlist could be
built from the series field alone, so it's excluded from the default
filter rather than guessed at, the same SA-`REC_TYPE` discipline;
`iter_permits()` (unfiltered) is always available for a caller who wants
to build their own finer filter.

**`streetworks.socrata`** is a new shared Socrata (SODA) client,
factored out of `streetworks.wzdx.registry` when this provider needed
the identical GET-with-query-params-and-paginate shape — the same role
`streetworks.arcgis`/`streetworks.ogc` play for their own technologies.
Real `$limit`/`$offset` pagination, an optional app token.

**Licence unconfirmed** — NYC Open Data states no formal reuse licence
on this dataset (`license: None` in its own metadata), only NYC.gov's
general Terms of Use and a no-warranty disclaimer, plus a stated
attribution: "Department of Transportation (DOT)".

## Chicago CDOT Street Closures

This SDK's second US city permit register — reuses `streetworks.socrata`
and the NYC permit-register pattern (permit → `WorksSite`, an
application-id grouping → `Works`, `source_grade=register`) directly.

```python
from streetworks.chicagodot import ChicagoDotClient
from streetworks.common import from_chicagodot

with ChicagoDotClient() as chicago:
    works_list = from_chicagodot(list(chicago.iter_roadworks()))
```

**The obvious primary dataset id turned out to be dead —
found live, not guessed.** `6fd2-pzze` ("CDOT Permits") returns a
genuinely empty schema (`X-SODA2-Fields: []`, confirmed via a real
request) despite 2.3M historical rows and a fresh `Last-Modified` — a
real casualty on Chicago's own portal. The real, current, actively-
updated dataset this module uses is
[`jdis-5sry`](https://data.cityofchicago.org/Transportation/Transportation-Department-Permits-Street-Closures/jdis-5sry)
("Transportation Department Permits - Street Closures", 46 columns,
466,829 real rows, confirmed updated the same day as this build) — a
Chicago-maintained view, already filtered to 3 of the full register's
11 real `applicationtype` values.

**Genuinely cleaner than NYC in two real ways, despite being the second
city.** Geometry is a native Socrata `point` column — real GeoJSON,
straightforward WGS84, no WKT parsing and no State-Plane CRS question
the way NYC's EPSG:2263 needed. Geometry and dates are both populated on
**99.94%** of real rows (466,568/466,829) — richer than NYC's own 80.5%
geometry rate.

**The view's own pre-filter isn't sufficient on its own — a real
correction found live, matching an explicit warning found during
investigation.** Even within the 3 pre-filtered `applicationtype` values, a
finer real field, `worktype`, still mixes in confirmed non-roadworks
activity: `BlockParty` (53,679 real rows — the single largest worktype
after genuine openings), `Festival` (8,938), `Athletic` (3,863),
`Filming` (1,255), `SideSale` (934), `Parade` (86), `Assembly` (33),
`FarmMkt` (6). So `iter_roadworks()` filters on `worktype` itself, to 7
real, evidenced roadworks values (`GenOpening`/"Opening in the Public
Way", `Restorat`, `GenOccupy`, `WorkInAdv`, `SoilNWell`, `StClosure`,
`Driveway`) — the same SA-`REC_TYPE`/NYC-series discipline, just one
level finer than the source's own pre-filter required.

**A real Works-umbrella grouping, the same shape as NYC's own** —
`applicationnumber` genuinely groups multiple real rows (one real
example, `DOT604194`, had 64 real rows across 64 genuinely different
real street locations — a citywide restoration job, not duplicate
records).

**No stated join to a street register** — the real 46-column schema has
no segment/street identifier, only free-text `streetname`/`direction`/
`suffix`/`streetnumberfrom`/`streetnumberto`. **Licence unconfirmed** —
the dataset states only `"See Terms of Use"`, the same honest-gap tier
as NYC.

## Washington DC DDOT Construction Permits

This SDK's third US city permit register, and its first over a plain
ArcGIS REST `MapServer` rather than Socrata — built on the same generic
`streetworks.arcgis.ArcGISFeatureClient` Jersey/TIGERweb already use. Not
in the WZDx/CWZ US registry at all — DC has no row there.

```python
from streetworks.arcgis.dc import DCConstructionPermitsClient
from streetworks.common import from_dc

with DCConstructionPermitsClient() as dc:
    works_list = from_dc(list(dc.iter_roadworks()))
```

**Confirmed to be genuinely street/right-of-way work, not general
building permits, by reading real sample records — not by name matching.**
A generically-named `Construction_Permits` ArcGIS table found first this
session, via DC's own Hub search, turned out on inspection to be
unrelated Boulder, Colorado building-permit data (real addresses in
Boulder, CO, `BOCOPIN`/`COBPIN` Boulder parcel identifiers) — Hub search
can surface content from other organizations. This module instead points
at DDOT's own real service (`maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DDOT/MapServer`),
found via `opendata.dc.gov`'s own dataset metadata, and confirmed with a
real sample: `ISEXCAVATION` true on ~80% of a 1,000-record sample of the
`Construction Permit - Last 30 Days` layer used here.

**Six real boolean work-type flags, confirmed not mutually exclusive** —
`ISEXCAVATION`/`ISPAVING`/`ISLANDSCAPING`/`ISPROJECTIONS`/`ISFIXTURE`/
`ISPSRENTAL` (public-space rental) can be true together (a real sample:
five of six true on one record) or all false at once (60/1,000 real
records sampled) — `from_dc` joins every true flag into `works_type`,
`None` rather than an empty string when none are.

**A related but distinct real layer, Occupancy Permit, on the same
service also covers non-construction public-space use** (a real sampled
record: a music festival, `EVENTTYPESCODEDESC="Other Special Events"`) —
not consumed here, the same "related but distinct, noted not consumed"
treatment Jersey's own `Projects` layer gets.

**Real WGS84 geometry under `f=geojson`, confirmed live** (a real returned
pair, `[-77.09..., 38.95...]`, correct for DC), despite this layer's own
stated native `spatialReference` being EPSG:26985 (NAD83 meters) — the
GeoJSON export can be trusted here, the same "check per-service, don't
assume" discipline TIGERweb's own docs establish. Dates stay real Esri
epoch-millisecond integers even under `f=geojson` — not converted to ISO
8601 by this service's export.

**Licence: Creative Commons Attribution 4.0 International**, confirmed
live via `opendata.dc.gov`'s own dataset `licenseInfo` metadata.

## Nevada 511

Found while surveying the states with no WZDx/CWZ coverage (Nevada has
no row in the WZDx registry at all — confirmed live). Nevada 511 turned
out to be this SDK's first US jurisdiction on the North American 511
platform — the same commercial API shape already built out for Ontario/
Alberta/Saskatchewan/New Brunswick/Newfoundland and Labrador/Nova
Scotia/Yukon, documented in full in
[`docs/providers/canada.md`](canada.md#north-american-511-platform-ontario-alberta-saskatchewan-new-brunswick-newfoundland-and-labrador-nova-scotia-yukon):

```python
from streetworks.na511 import NA511Client
from streetworks.na511.jurisdictions import NEVADA
from streetworks.common import from_na511

with NA511Client(api_key=api_key) as client:  # doctest: +SKIP
    works_list = from_na511(
        client.fetch("nevada"),
        territory=NEVADA.territory,
        administrative_area=NEVADA.administrative_area,
    )
```

**Confirmed live to be the identical platform**, not just a name
coincidence: the same `/api/v2/get/event` endpoint, the same structured
`{"Error":{"Message":"Invalid Key"}}` rejection with no key supplied,
and a real, working `/developers/doc` page whose own field-by-field
documentation matches Ontario's/Alberta's exactly. Requires a real
developer key — not obtained on this SDK's behalf, the same standing
rule as Massachusetts's CWZ feed above. Free self-service registration:
`https://www.nvroads.com/developers/doc`; set `NEVADA_511_API_KEY` (see
`.env.example`) and run `scripts/smoke_test.py` to confirm the last
open question — that Nevada's own authenticated response round-trips
through the identical parsing unchanged.
