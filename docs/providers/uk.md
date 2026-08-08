# UK & Crown Dependencies

> Migrated verbatim from README.md's `## Street Manager`, `## Street
> Manager Open Data (SNS push)`, `## Geoplace DataVIA`, `## DfT D-TRO`,
> `## Scottish Road Works Register (SRWR) Open Data`, `## OS Open USRN`,
> `## Jersey RoadWorkx and TIGERweb (ArcGIS REST)`, `## Northern Ireland &
> Wales (traveller-information RSS)`, and `## UK Police` sections (phase
> one, lossless restructure — see `docs/migration-mapping.md`). See
> [`docs/concepts/write-path.md`](../concepts/write-path.md) for the
> Section 50 write-path connector content that was also part of the
> Street Manager section.

## Street Manager

Authentication, token caching, and refresh (via the Party API, with automatic
fall-back to re-authentication) are handled for you — following the DfT
integration guidance: one token, reused, never re-authenticating per call.

```python
from streetworks.streetmanager import StreetManagerClient, Environment, ApiVersion

with StreetManagerClient(
    "api-user@example.com",
    "password",                      # store securely, e.g. environment variable
    environment=Environment.SANDBOX, # or Environment.PRODUCTION
    version=ApiVersion.V6,           # or ApiVersion.V7 / ApiVersion.LATEST
) as sm:
    # Typed convenience methods for common workflows...
    work = sm.work.get_work("TSR1591199404915")
    submitted = sm.reporting.permits(status="submitted")

    # Or let the SDK walk every page for you:
    for permit in sm.reporting.iter_permits(status="submitted"):
        ...
    sm.work.assess_permit("TSR1591199404915", "TSR1591199404915-01",
                          {"assessment_status": "granted", ...})

    # ...and a generic escape hatch for every endpoint we haven't wrapped yet:
    s58 = sm.work.post("section-58s", json={...})
    updates = sm.event.works_updates()
```

Async is a mirror image:

```python
from streetworks.streetmanager import AsyncStreetManagerClient

async with AsyncStreetManagerClient("api-user@example.com", "password") as sm:
    permits = await sm.reporting.permits(status="submitted")
```

> **Environments.** `Environment.SANDBOX` and `Environment.PRODUCTION` are
> isolated systems with separate credentials. Develop and test against
> SANDBOX; only point at PRODUCTION once your workflows are proven. The smoke
> test and integration suite refuse to touch production without an explicit
> opt-in, so a stray setting can't send you at live data by accident.

### Typed models

Pydantic v2 models generated from the official DfT swagger specifications
live under `streetworks.streetmanager.models.<version>` and validate any
client payload:

```python
from streetworks.streetmanager.models.v6.work import WorkResponse

work = WorkResponse.model_validate(sm.work.get_work("TSR1591199404915"))
```

To regenerate after a DfT release, run the **Regenerate Street Manager
models** workflow from the Actions tab (it opens a PR), or locally:

```bash
pip install -e ".[gen]"
python scripts/generate_models.py --version v6 --from-dir specs/streetmanager/v6
```

See [`examples/collaboration_finder.py`](../../examples/collaboration_finder.py)
for a worked example of finding same-street, close-in-time works worth
coordinating (the reusable matching logic is commented separately from the
fetch/print code, since that's the bit worth lifting into your own script).

See [`docs/concepts/write-path.md`](../concepts/write-path.md) for the
Section 50 licence connector — the first write-path example in this SDK.

## Street Manager Open Data (SNS push)

Open Data is a *push* model: Street Manager POSTs event notifications to an
HTTPS endpoint you host. **The receiver needs no credentials** — messages are
authenticated with AWS's public signing certificate (fetched over HTTPS), not
a shared secret, so there's nothing to configure on the SDK side for parsing,
verifying, or confirming. `streetworks.opendata` handles all of that,
framework-agnostic:

```python
from streetworks.opendata import handle

# inside your web handler, with the raw request body:
event = handle(request_body, expected_topic_arn="arn:aws:sns:eu-west-2:...:...")
if event is not None:               # None => subscription handshake, auto-confirmed
    print(event["event_type"], event["object_reference"])
```

See [`examples/opendata_fastapi.py`](../../examples/opendata_fastapi.py) for a
complete FastAPI receiver.

> **Credentials nuance.** *Receiving* Open Data needs no credentials. But note
> there are two distinct feeds: the fully public **Open Data** feed (this
> module), and a separate per-organisation **API Notifications** feed whose
> *subscription* is set up by calling an authenticated Street Manager endpoint
> (`POST api-notifications/subscribe`) — that setup step needs Street Manager
> credentials, though the messages, once flowing, are received the same
> credential-free way. This module handles the receiving side of both.

## Geoplace DataVIA

Basic auth or OAuth2 client credentials (server-to-server), the full NSG layer
catalogue (`Layer.STREET_LINES`, `ESU_STREETS`, `ESU_ONE_WAY_EXEMPTIONS`, and
the Interest / Construction / Special Designation layers in all three geometry
flavours), composable OGC filters, and transparent paging:

```python
from streetworks.datavia import DataViaClient, Layer, filters

with DataViaClient(username="user", password="pass") as dv:      # or client_id=/client_secret=
    street = dv.street_by_usrn(4401245)
    nearby = dv.streets_near_point(-0.138405, 50.825181, 100)    # within 100m

    sed = dv.get_features(
        Layer.SPECIAL_DESIGNATION_LINES,
        filter_fragment=filters.and_(
            filters.intersects_polygon(ring),
            filters.property_equals("special_designation_code", 3),
        ),
    )

    for feature in dv.iter_features(Layer.ESU_STREETS, page_size=500):
        ...
```

POST `GetFeature` bodies match the shapes in the DataVIA documentation
(WFS 1.1.0 + `ogc:Filter`); GET KVP with `startIndex`/`count` is also
available via `get_features_kvp()`. Output formats: GeoJSON (default),
OGRGML, SHAPEZIP, CSV, SPATIALITEZIP.

### WMS (rendered map images)

The same endpoints also serve OGC WMS, so you can pull rendered map images of
NSG layers or ask "what street is at this pixel?":

```python
from pathlib import Path

png = dv.get_map([Layer.STREET_LINES], (424000, 533800, 426000, 535200))
Path("durham-streets.png").write_bytes(png)

info = dv.get_feature_info(Layer.STREET_LINES, (424000, 533800, 426000, 535200),
                           i=384, j=384)      # pixel coords in the image
```

Coordinates default to British National Grid (EPSG:27700), which sidesteps
the WMS 1.3.0 lat/lon axis-order trap that bites with EPSG:4326.

## DfT D-TRO

OAuth2 client credentials (30-minute tokens, cached and renewed
automatically), `x-app-id` and per-request `X-Correlation-ID` headers handled
for you:

```python
from streetworks.dtro import DTROClient, Environment

with DTROClient(client_id, client_secret, app_id=app_id,
                environment=Environment.INTEGRATION) as dtro:
    events = dtro.search_events(since="2026-06-01T00:00:00", pageSize=50)
    record = dtro.get_dtro(events["events"][0]["id"])

    dtro.create_dtro(payload)                          # publisher scope
    dtro.create_dtro_from_file(big_json, gzip=True)    # large D-TROs
    signed = dtro.get_all_dtros_url()                  # full CSV extract

    dtro.schema_versions()                             # available schema versions
    dtro.search({...})                                 # search published D-TROs
    dtro.create_provisions([...], dtro_id="...")       # provisions (App-Id header handled)
```

## Scottish Road Works Register (SRWR) Open Data

Scotland's national road works register publishes its full noticing data as
daily Open Data extracts under the Open Government Licence v3 — **no
credentials required**. `streetworks.srwr` downloads the archives and parses
the multi-record-type CSV format (spec v2.02) into typed records, grouped
into complete Activities:

```python
from streetworks.srwr import SRWRClient, describe

with SRWRClient() as srwr:
    archive = srwr.download_daily("srwr-daily.zip")
    for activity in srwr.iter_activities(archive):
        phase = activity.phases[-1]
        print(activity.activity_id,
              describe("works_type", phase.works_type),
              describe("activity_status", phase.activity_status),
              phase.location)
```

Parsing streams (a 4-million-record monthly archive parses in well under a
minute at ~30 MB memory). Monthly/yearly archives concatenate the daily
extracts; `latest_activities()` applies the spec's most-recent-occurrence
rule. Notices, phases, sites, inspections, FPNs, restrictions and reference
data are all exposed; `describe()` translates the register's coded values.

> The authenticated SRWR (Aurora) web-services API is available only to
> Scottish roads authorities and utilities and is not publicly documented, so
> it isn't covered. The Open Data feed carries the register's noticing data
> and needs no account.

## OS Open USRN

Every Unique Street Reference Number in Great Britain, with street geometry,
as Ordnance Survey OpenData — **no credentials required**. USRNs are the
common key across this SDK: Street Manager works, DataVIA streets, D-TRO
regulated places and SRWR activities all reference them.
`streetworks.openusrn` downloads the GeoPackage via the OS Downloads API and
queries it with the standard library only (no GDAL or geospatial stack):

```python
from streetworks.openusrn import OpenUSRNClient, UsrnDatabase, extract_gpkg

with OpenUSRNClient() as client:
    archive = client.download("osopenusrn.zip")   # ~300 MB, streamed

with UsrnDatabase(extract_gpkg(archive)) as db:
    street = db.get(33909869)
    print(street.geometry)        # WKT, British National Grid (EPSG:27700)
```

## Jersey RoadWorkx and TIGERweb (ArcGIS REST)

> Note: TIGERweb is a US Census Bureau service, included in this section
> (rather than `docs/providers/us.md`) because the README documents it and
> Jersey RoadWorkx together — they share one client shape and one README
> section. See [`docs/providers/us.md`](us.md) for a cross-reference.

The third client shape in this SDK, after the DATEX/JSON adapters and
`OGCFeaturesClient`: `ArcGISFeatureClient` fetches/pages GeoJSON from any
ArcGIS REST `MapServer`/`FeatureServer` layer — no GDAL, no shapefile, no
file geodatabase. Built fresh for this protocol, not a generalisation of
`OGCFeaturesClient` or `DataViaClient` — they share almost nothing but
"fetches geodata over HTTP."

**Pagination is the real trap this client exists to handle — verified live
against two genuinely different real services, not assumed from either
one alone.** Jersey's real `RoadWorks` layer states
`supportsPagination: false`, and it's telling the truth in an unusually
literal way: a live `resultOffset` request returns HTTP 200 with a
plausible page of records, but it's silently the *same* first page every
time, at any offset — confirmed at offsets 0/500/1000/2000/21000. The real
total is 22,105 records behind a `maxRecordCount` of 1,000 — a naive
one-shot query silently returns under 5% of the data with no error.
TIGERweb's layers state (and, verified live, genuinely honour)
`supportsPagination: true`. `ArcGISFeatureClient.iter_features` doesn't
trust the metadata either way — it verifies live, by comparing the first
two pages fetched with different offsets, and falls back to object-id-range
paging (`WHERE {oid_field} > {last} ORDER BY {oid_field}` — confirmed live
to genuinely work for Jersey) the moment offset-paging fails to advance.
If neither strategy is usable, it raises `TruncatedResultError` rather than
silently handing back a partial result.

```python
from streetworks.arcgis.jersey import JerseyRoadworksClient
from streetworks.common import from_jersey

with JerseyRoadworksClient() as jersey:
    works_list = from_jersey(list(jersey.iter_roadworks()))
for works in works_list:
    print(works.reference, len(works.sites), works.administrative_area)
```

Jersey RoadWorkx — this SDK's first Channel Islands coverage — groups real
`RoadWorks` features by `PROJID` into one `Works` per project (confirmed
live: `NAME`/`PROJID` are always identical, and several `JOBID`s share one
`PROJID` — the same real shape as Street Manager's
`work_reference_number`/`permit_reference_number`). The real `STATUS`
field (`"In Progress"`/`"Finished"`/`"Pending"`) *is* the planned/future
dimension — `"Pending"` records land on `proposed_start`/`proposed_end`
with `ESTIMATED` confidence, no separate layer or type needed. Geometry is
real `EPSG:3109` ("ETRS89 / Jersey Transverse Mercator") — confirmed live
via a sibling service on the same deployment that states the `wkid`
directly, cross-checked byte-for-byte against EPSG:3109's own published
WKT parameters; `outSR` is **not** honoured by this service (confirmed
live), so this is carried through exactly as received, never reprojected.
**No explicit licence document found** — no `copyrightText` anywhere on the
service, not catalogued on Jersey's own open-data portal, and the
public-facing site gates behind a login even though the ArcGIS REST API
itself needs none — but the service is openly, unauthenticatedly
queryable by design and Jersey's data is confirmed intended for open
public consumption, so real, live-captured records are committed as this
module's test fixtures, the same basis Autobahn GmbH's roadworks shipped
on; see `streetworks/arcgis/jersey.py`'s module docstring.

```python
from streetworks.arcgis.tigerweb import TIGERwebClient, LOCAL_ROADS_LAYER
from streetworks.common import from_tigerweb

dc_bbox = (-77.05, 38.89, -77.03, 38.91)  # (xmin, ymin, xmax, ymax), WGS84
with TIGERwebClient() as tiger:
    segments = [from_tigerweb(f) for f in tiger.iter_roads(LOCAL_ROADS_LAYER, bbox=dc_bbox)]
```

TIGERweb (US Census Bureau) is a statistical/cartographic product, not a
legal street register — there's no USRN equivalent; real identifiers
(`OID`, a TIGER/Line TLID-shaped string) are dataset-scoped, exactly what
`Identifier.scope` exists for. Layers 0–9 are a real cartographic scale
pyramid, not distinct road classes — confirmed live by comparing feature
counts (layers 1/2 both report 17,612 features nationally, 4/5/6 all
248,106, 7/8 both 16,150,491 — the same underlying data at different
generalisation tiers). `from_tigerweb` queries the three genuinely
non-redundant full-detail layers (Primary `S1100`, Secondary `S1200`,
Local `S1400` — MTFCC carried undecoded, no lookup table bundled) and
produces **`Segment` only, never a `Street`** — checked, not assumed: no
layer anywhere in the service aggregates segments under a named-street
entity, so per the no-synthetic-streets rule this is the same shape as
the Netherlands. No Address Ranges layer exists over this REST service
either (checked across all 35 real `TIGERweb/` services) — `Segment
.address_ranges` stays on its NWB-only footing. Public domain (17 U.S.C.
§ 105, a work of the US federal government) — real fixtures are committed.
Query with a real bounding box; layer 8 alone has 16,150,491 features
nationally, the largest dataset this SDK queries through a REST API.

**Not built here, noted as the obvious follow-on**: USDOT's **National
Address Database (NAD)** — a national address *point* file (last compiled
2026-06-30), distributed as flat text, readable with the standard library
and needing no new client shape — would give the US its first `Address`
provider, the counterpart to TIGERweb's `Segment`. The **USGS National
Transportation Dataset** is readable today (GeoPackage) but is TIGER
supplemented with HERE commercial data — its licence needs care before
building against it. Neither is built in this release.

## Northern Ireland & Wales (traveller-information RSS)

The remaining UK nations are covered by open RSS feeds — credential-free, but
**shallower data**: these are traveller-information services (current and
forthcoming closures as human-readable text), not works registers. Typed
fields are best-effort extractions and the raw text is always preserved.

**Northern Ireland — TrafficWatchNI** (`streetworks.trafficwatchni`): DfI's
Traffic Information & Control Centre feeds for roadworks, incidents and
events; trunk roads and motorways NI-wide plus all roads in Greater Belfast,
refreshed every 5 minutes. *Attribution required: credit DfI TICC and
preserve item URLs.*

**Wales — Traffic Wales** (`streetworks.trafficwales`): Welsh Government
feeds for roadworks, incidents/events and headlines on the motorway and
trunk road network, in English and Welsh, refreshed every 5 minutes.
*Attribution required: credit Traffic Wales.* (Traffic Wales also offers
richer DATEX II feeds — access on application via traffic.wales/developers;
once granted, `streetworks.datex2` can parse them.)

```python
from streetworks.trafficwatchni import TrafficWatchNIClient
from streetworks.trafficwales import TrafficWalesClient, Feed

with TrafficWatchNIClient() as twni:
    for item in twni.fetch():
        print(item.closure_type, item.road, item.town, "-", item.promoter)

with TrafficWalesClient() as tw:
    for item in tw.fetch(Feed.ROADWORKS):
        print(item.roads, item.title)
```

## UK Police (crime data — a worker-safety signal)

There's no API for reporting abuse or aggression towards road workers
directly — it doesn't exist. What does exist is the [UK Police
API](https://data.police.uk/docs/) (`data.police.uk`), which publishes
street-level crime for England, Wales, and Northern Ireland — **no
credentials required**. `streetworks.police` wraps it as a contextual
safety signal for planning lone working or an unfamiliar site, not as a
street-works dataset in its own right.

```python
from streetworks.police import PoliceClient

with PoliceClient() as police:
    signal = police.safety_signal(51.500617, -0.124629)  # lat, lng of the worksite
    print(signal)
    # {'date': None, 'total_crimes': 3420, 'safety_relevant_count': 1623,
    #  'by_category': {'anti-social-behaviour': 1152, 'violent-crime': 344,
    #                  'public-order': 98, 'robbery': 21, 'possession-of-weapons': 8}}
```

`safety_signal()` fetches crime in roughly a one-mile radius of a point and
counts only the categories in `SAFETY_RELEVANT_CATEGORIES` — violence and
sexual offences, public order, anti-social behaviour, robbery, and
possession of weapons. Property crime (vehicle crime, burglary, shoplifting,
bicycle theft, criminal damage) is fetched but excluded from the count,
because it says little about the risk of confrontation to a person on site.
The raw per-point and per-polygon methods (`street_level_crimes`,
`street_level_crimes_in_area`, `crimes_at_location`, `crimes_no_location`,
`forces`, `locate_neighbourhood`, ...) are also available unfiltered.

**Read this as contextual awareness, not prediction** — three things that
would otherwise mislead:

1. **Historical, not live.** The API publishes street-level crime roughly a
   month or two in arrears, aggregated per calendar month — recent past, not
   what's happening at the site today.
2. **Area-level, not site-level.** Police deliberately anonymise each
   crime's location to a snapped map point (often the middle of the street,
   sometimes 100m+ off the true spot) to protect victim privacy. This is a
   signal about the surrounding area, never the exact worksite.
3. **Category matters more than the total.** "High crime" as a lump figure
   is close to meaningless for personal safety — an area heavy in vehicle
   crime or shoplifting says little about risk to a road crew. That's why
   `safety_signal()` filters to the categories that actually bear on it
   rather than reporting the raw total.

### Neighbourhood policing teams

```python
with PoliceClient() as police:
    teams = police.neighbourhoods("leicestershire")
    boundary = police.neighbourhood_boundary("leicestershire", teams[0]["id"])
    crimes = police.street_level_crimes_in_area(boundary, date="2026-05")
```

`neighbourhoods(force)` lists every neighbourhood policing team;
`neighbourhood(force, id)` gets one team's details (centre point, contact
details, links); `neighbourhood_boundary(force, id)` returns the team's
boundary as `(lat, lng)` pairs, in the same order `street_level_crimes_in_area`
already expects — feed one straight into the other with no reordering.
Verified live, not from the docs: the API states each boundary coordinate as
a **string**, coerced to `float` here; it's always a **single, closed ring**
(no multipolygon, no holes — a physically disjoint neighbourhood can't be
represented); and real rings aren't guaranteed simple (near-duplicate
consecutive vertices and the odd spike, confirmed on a real ring — returned
as-is, never silently repaired).

A neighbourhood boundary can be hundreds of vertices — too long for a GET
query string. `street_level_crimes_in_area` handles this itself: coordinates
are written to 5 decimal places (~1m, far finer than the source data's own
anonymisation), and if the query would still exceed a safe URL length, it's
sent as a form-encoded `POST` to the same endpoint automatically — same
public signature either way. A `503` (the API's own response when a polygon
is too complex to process, even over `POST`) raises
`streetworks.exceptions.ServerError` naming the problem, never silently
returns `[]` — an empty result and an unqueried polygon must not look the
same. A response landing at exactly the API's 10,000-result cap emits a
`UserWarning`, since that count may be a truncation.

See [`examples/crime_context/`](../../examples/crime_context/) for a full worked
example: a neighbourhood-banded recorded-crime context map for a whole
force, built entirely on these methods.

### Bulk CSV download

```python
with PoliceClient() as police:
    rows = police.bulk_download_csv("durham", date_from="2025-06", date_to="2026-05")
    categories = police.crime_categories()  # name/url pairs map the CSV's
                                             # "Crime type" strings to the
                                             # JSON API's slugs, exactly
```

`bulk_download_csv(forces, *, date_from, date_to, ...)` drives
data.police.uk's custom CSV download (https://data.police.uk/data/) — a
CSRF-protected HTML form plus an async job, not a JSON endpoint like every
other method here, but fully scriptable with a plain cookie jar and no
browser. Verified live end-to-end for 1-, 3-, and 12-month single-force
requests, all ready within seconds (a 12-month Durham request: a 3.5MB zip,
one file per month). Returns every row from every requested month's
street-level crime CSV, keyed by the CSV's own real column names (`Crime
ID`, `Month`, `LSOA code`, `Crime type`, …) — the CSV's `Crime type` is a
human string ("Violence and sexual offences"), not the JSON API's slug
("violent-crime"); `crime_categories()`'s `name`/`url` pairs are, confirmed
live character-for-character, the mapping between the two, so no separate
lookup file is needed. A per-force export can carry a small amount of real
geographic cross-force contamination (confirmed live for Durham, ~0.4% of
rows) — `Falls within` isn't a geographic filter (every row, including the
contaminating ones, carries that force's own name in that column); scope by
`LSOA code` against whatever LSOA set matters to your use case instead.

See [`examples/crime_context_lsoa/`](../../examples/crime_context_lsoa/) for a
full worked example: LSOA-level (not neighbourhood-team-level) crime
context, keyed to a specific worksite, with a real population denominator —
the finer-grained successor to `examples/crime_context/` above, and a
demonstration of `streetworks.police`, `streetworks.arcgis`, and (for its
USRN input path) `streetworks.openusrn` working together.
