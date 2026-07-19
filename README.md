# streetworks

[![CI](https://github.com/KFergusonUK/StreetWorks-SDK/actions/workflows/ci.yml/badge.svg)](https://github.com/KFergusonUK/StreetWorks-SDK/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/streetworks)](https://pypi.org/project/streetworks/)
[![Python](https://img.shields.io/pypi/pyversions/streetworks)](https://pypi.org/project/streetworks/)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)

An open Python SDK for street works and roadworks data — the UK's
registers, Europe's national roadworks feeds, and the US WZDx standard,
behind one consistent, typed, well-tested client.

> We do this not because it is easy, but because it is hard.

```python
from streetworks.streetmanager import StreetManagerClient, Environment

with StreetManagerClient("api-user@example.com", password, environment=Environment.SANDBOX) as sm:
    sm.authenticate()                                  # verify credentials
    submitted = sm.reporting.permits(status="submitted")
```

| Module | Service | Direction |
|---|---|---|
| `streetworks.streetmanager` | [DfT Street Manager](https://department-for-transport-streetmanager.github.io/street-manager-docs/api-documentation/) — all nine APIs (Work, Reporting, Street Lookup, GeoJSON, Party, Data Export, Event, Sampling, Worklist), V6 & V7, sandbox & production | read + write |
| `streetworks.opendata` | [Street Manager Open Data](https://department-for-transport-streetmanager.github.io/street-manager-docs/open-data/) — AWS SNS push notifications | receive |
| `streetworks.datavia` | [Geoplace DataVIA](https://datavia.geoplace.co.uk/documentation) — full NSG layer catalogue over OGC WFS and WMS (rendered maps + feature info), Basic + OAuth2 | read |
| `streetworks.dtro` | [DfT Digital Traffic Regulation Orders](https://d-tro.dft.gov.uk/api-documentation/) — the legal orders behind speed limits, closures and restrictions; integration & production | read + write |
| `streetworks.srwr` | [Scottish Road Works Register](https://roadworks.scot/) — national register via Open Data CSV extracts (no credentials) | read |
| `streetworks.openusrn` | [OS Open USRN](https://osdatahub.os.uk/downloads/open/OpenUSRN) — every GB USRN with geometry, via the OS Downloads API (no credentials) | read |
| `streetworks.datex2` | [DATEX II](https://datex2.eu/) — European roadworks parser (v3 + v2), with adapters for NDW (Netherlands, XML), National Highways (England SRN, JSON), Digitraffic (Finland, its own JSON schema; no credentials), IRCA/Vegagerðin (Iceland, XML over SOAP; no credentials), Bison Futé (France, XML v2; no credentials), and DGT (Spain, excl. Catalonia & the Basque Country, XML v3; no credentials) | read |
| `streetworks.autobahn` | [Autobahn GmbH](https://verkehr.autobahn.de/) — Germany's national motorway roadworks, its own JSON REST API, not DATEX (no credentials; **licence unconfirmed**, see below) | read |
| `streetworks.ogc` | German *state* roadworks — Hamburg, Brandenburg, Saxony (open geodata over OGC WFS/direct GeoJSON download; no credentials); a reusable OGC-features fetch client underneath, not roadworks-specific. **New in 0.7.0 — interface provisional**, may change as the gazetteer work exercises it | read |
| `streetworks.wzdx` | [WZDx](https://github.com/usdot-jpo-ode/wzdx) — US roadworks ("work zones") via the WZDx standard — parser (v3.1–v4.2), generic feed client, and USDOT registry helper (no credentials) | read |
| `streetworks.trafficwatchni` | [TrafficWatchNI](https://trafficwatchni.com/) — Northern Ireland roadworks/incidents RSS (DfI TICC; no credentials) | read |
| `streetworks.trafficwales` | [Traffic Wales](https://traffic.wales/) — Welsh motorway/trunk roadworks RSS, EN + CY (no credentials) | read |
| `streetworks.police` | [UK Police](https://data.police.uk/docs/) — street-level crime, as a worker-safety signal, not a street-works feed (no credentials) | read |
| `streetworks.common` | Canonical cross-provider works types (`Works`, `WorksSite`, `WorksPlanning`, `Coordinate`, `Notice`) with per-provider converters, alongside every native interface above | — |

Shared across all modules: automatic retries with exponential backoff and
jitter, `Retry-After`-aware 429 handling, a single exception hierarchy, and
both **sync and async** clients built on [httpx](https://www.python-httpx.org/).

## What this is (and isn't)

**It is** a typed client library: it handles authentication, token lifecycles,
retries, rate limiting, pagination, and request/response plumbing for each of
these APIs, so you call Python methods instead of hand-rolling HTTP. Auth and
connectivity are verified against the real systems (see **Status** below).

**It isn't** a replacement for the APIs' own documentation. You still bring
your own credentials (issued by the service operators, not by this SDK) and
you still need each API's domain concepts — what a permit payload contains,
what makes a valid USRN filter, which DataVIA layer holds which data. The SDK
gets you connected and typed; the linked docs tell you what to send.

## Status

Early alpha. **Authentication and read/consume access are verified against
the real systems for all providers except one, noted below:** Street Manager (SANDBOX), Geoplace
DataVIA (live — including a real feature query), D-TRO (production token +
events search), the Open Data SNS parsing/verification pipeline, SRWR
Open Data (parsed against real published daily and monthly extracts),
OS Open USRN (Downloads API + GeoPackage reader), UK Police (live
`safety_signal()` and category queries against `data.police.uk`), WZDx
(parsed against 12 live agency feeds spanning v3.1–v4.2), Digitraffic/
Finland, IRCA/Iceland, Bison Futé/France, DGT/Spain, Autobahn GmbH/Germany,
and the German states Hamburg, Brandenburg and Saxony (all parsed against
real live feeds).

**Autobahn GmbH's licence is unconfirmed** - checked four independent
sources (see the [Autobahn GmbH section below](#autobahn-gmbh-germany-national-motorways)
for what was checked) and none state reuse/redistribution terms. Shipped
anyway, flagged deliberately rather than silently assumed open - confirm
your own rights before redistributing this data.

**The one unverified provider is Norway** (`streetworks.datex2.vegvesen`):
implemented to Statens vegvesen's published specs and covered by mocked
tests, but **never run against real Norwegian data** — the authenticated
pull is blocked pending credentials. It ships as a scaffold and is
excluded from the verified-providers claim above; see the module
docstring for precisely what's confirmed vs. still open. **If you have
Statens vegvesen API credentials, running the smoke test against it and
reporting back would be a genuinely valuable contribution.**

Not yet exercised against live systems — implemented to the published specs
and covered by mocked tests: the **write/publish** paths (Street Manager work
submission and assessment; D-TRO create/update and provisions). These are
publisher-scoped and deliberately excluded from the read-only smoke test.

Known reconciliation items: D-TRO `v4.0.0` schema models to follow when it
lands (production cut-over expected mid-2026; `v3.5.1` models ship now); the
`streetworks.exceptions` API and client method surface may change before
`1.0`. See [docs/INTEGRATION.md](docs/INTEGRATION.md) for how to verify
against the real systems yourself. First-contact reports welcome.

## Install

```bash
pip install streetworks            # core
pip install "streetworks[sns]"     # + SNS signature verification (cryptography)
```

Requires Python 3.10+.

## Quickstart

The fastest way to see everything working: copy the credential template, fill
in what you have, and run the one-file tour — it logs in to each configured
provider and retrieves a little real data (read-only). Providers you leave
blank are skipped, and SRWR / OS Open USRN need no credentials at all.

```bash
cp .env.example .env      # then edit .env
python examples/quickstart.py
```

For connectivity checks without data retrieval, use the smoke test instead:
`python scripts/smoke_test.py`.

## Prerequisites: credentials

Credentials are issued by the service operators. You only need the ones for the
service(s) you'll use. Keep them in environment variables or a secret manager —
never in code.

| Service | How to get access | Environment variables |
|---|---|---|
| Street Manager | Your organisation's Street Manager admin issues API accounts; [start in sandbox](https://department-for-transport-streetmanager.github.io/street-manager-docs/articles/testing-with-street-manager-sandbox-environment.html) | `SM_EMAIL`, `SM_PASSWORD` |
| Street Manager Open Data | Register an HTTPS endpoint with DfT to receive the SNS subscription | *(none — you host the receiver)* |
| DataVIA | A [Geoplace DataVIA](https://datavia.geoplace.co.uk/) account (username/password) or issued OAuth2 client credentials | `DATAVIA_USER` + `DATAVIA_PASSWORD`, or `DATAVIA_CLIENT_ID` + `DATAVIA_CLIENT_SECRET` |
| D-TRO | Register an application via the [D-TRO service](https://d-tro.dft.gov.uk/) for an app id and OAuth2 client credentials (integration first, then production) | `DTRO_CLIENT_ID`, `DTRO_CLIENT_SECRET`, `DTRO_APP_ID` |
| National Highways | Free account at the [developer portal](https://developer.data.nationalhighways.co.uk/) — create a "Subscription" for an API key | `NH_SUBSCRIPTION_KEY` |

Credentials are **per-environment** — sandbox/integration credentials do not
work against production, and vice versa.

## Verify your setup

Before writing any code, confirm your credentials and connectivity with the
included smoke test. It targets the **test** environments by default, is
read-only, and skips any service you haven't configured:

```bash
SM_EMAIL='api-user@example.com' SM_PASSWORD='...' python scripts/smoke_test.py
```

```
================================================================
streetworks connectivity smoke test
TARGET  Street Manager: sandbox
All checks are READ-ONLY.
================================================================

  [PASS] Street Manager - authenticated (sandbox/v6), organisation 1355
  ...
```

A `FAIL` prints the exact exception, so a wrong credential or environment is
obvious immediately. See [docs/INTEGRATION.md](docs/INTEGRATION.md) for the
full variable list and how to (deliberately) target production.

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

See [`examples/opendata_fastapi.py`](examples/opendata_fastapi.py) for a
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

## DATEX II (European roadworks)

DATEX II is the European standard for traffic and roadworks data exchange,
used by the National Access Points across Europe. `streetworks.datex2` is a
streaming, namespace-tolerant parser for SituationPublication roadworks —
DATEX II **v3 and v2** — plus source adapters. The first is the Netherlands'
credential-free NDW open data (XML):

```python
from streetworks.datex2 import NDWClient, iter_roadworks

with NDWClient() as ndw:
    feed = ndw.download_planned_works("ndw-planned.xml.gz")

for situation in iter_roadworks(feed, provider="NDW"):
    works = situation.roadworks[0]
    print(works.source_name, works.road_maintenance_type,
          works.validity.overall_start, works.location.point)
```

The parser streams (the ~170 MB Dutch national feed parses in seconds at
~35 MB memory) and normalises locations across referencing methods.
**Coordinates are WGS84 latitude/longitude** — not the British National Grid
used by the UK providers here.

`iter_situations`/`iter_roadworks` (and their `_full` variants) take an
optional `provider` label, as above, naming the source in the debug-level
log a field-mapping fallback emits when it fires (see Spain below). IRCA,
Bison Futé and DGT pass it automatically since they own their own fetch;
it's stated explicitly here since you're calling the parser directly
(Digitraffic and National Highways parse JSON separately, so it doesn't
apply there).

**National Highways** (England's Strategic Road Network) publishes its
DATEX II v3.4 extended profile as **JSON, not XML**, so it needs its own
parsing path rather than the streaming XML parser above —
`streetworks.datex2.nationalhighways` maps that JSON onto the same
`Situation`/`SituationRecord` models. Needs a free subscription key from the
[developer portal](https://developer.data.nationalhighways.co.uk/); it pages
through results automatically via the `x-next` cursor:

```python
from streetworks.datex2 import ClosureType, NationalHighwaysClient

with NationalHighwaysClient(subscription_key) as nh:
    for situation in nh.iter_roadworks(ClosureType.PLANNED):
        works = situation.roadworks[0]
        print(works.cause_type, works.road_maintenance_type, works.location.point)
```

(Verified against the live API: it returns XML regardless of `Accept`
headers unless you also send `X-Response-MediaType: application/json` — the
client sends this for you.)

**Finland's Digitraffic** (Fintraffic's open data platform) publishes
national roadworks credential-free as its own JSON schema — **not** a DATEX
II serialisation, unlike National Highways — so
`streetworks.datex2.digitraffic` has its own parsing path too, onto the
same shared models:

```python
from streetworks.datex2.digitraffic import DigitrafficClient, provinces

with DigitrafficClient() as digitraffic:
    payload = digitraffic.get_roadworks()
    situations = digitraffic.parse(payload)

situation_provinces = provinces(payload)  # {situation.id: "province name", ...}
for situation in situations:
    works = situation.roadworks[0]
    print(situation_provinces.get(situation.id), works.road_maintenance_type,
          works.location.point)
```

Verified against the live feed (2026-07): `record_type` is a documented
compromise (Digitraffic has no maintenance/construction split, so it's
hardcoded, not read off a field), `validity.status` stays unset always (no
active/planned/suspended-equivalent exists in the feed, so
`date_confidence` honestly comes out `unknown`), and the coordinate given
per record is the *situation's* affected-area geometry, not that record's
exact spot — `road_number`/Alert-C name are the precise per-record
locators. See `streetworks/datex2/digitraffic.py`'s module docstring for
the full field-by-field mapping and why each choice was made.

**Iceland's IRCA/Vegagerðin** publishes national roadworks credential-free
as genuine DATEX II v3 XML over a SOAP `snapshotPull` interface, reused
through the same shared field-extraction logic as NDW — no bespoke parsing
path needed. Its ~250 KB response is small enough to parse fully into
memory (`iter_situations_full`), unlike NDW's ~170 MB feed, so `.raw` is
populated here where NDW's streaming parser leaves it unset:

```python
from streetworks.datex2.irca import IcelandClient

with IcelandClient() as irca:
    for situation in irca.iter_roadworks():
        works = situation.roadworks[0]
        print(works.record_type, works.validity.overall_start, works.location.point)
```

Verified against multiple independent live fetches (2026-07): reliably
reachable with no credentials, no API key, no IP allow-listing;
`record_type` is a genuine `xsi:type` discriminator (not a compromise);
location is always `PointLocation` (checked across every situation on two
separate fetches — no linear geometry, no Alert-C); `administrative_area`
has no genuinely-stated source field anywhere in the feed (checked
exhaustively), so it's left unset rather than inferred. Data is published
under a licence permitting free reuse, redistribution, and commercial use,
with mandatory attribution — see `streetworks/datex2/irca.py`'s module
docstring for the exact required wording and the full field-by-field
mapping.

**France's Bison Futé/the DIRs** publish roadworks for the non-concessionary
national road network (the state-run RRN) credential-free, as genuine
DATEX II **v2** XML — again reused through the same shared parser, no
bespoke path needed:

```python
from streetworks.datex2.bisonfute import BisonFuteClient, dir_regions

with BisonFuteClient() as bf:
    situations = list(bf.iter_roadworks())
regions = dir_regions(situations)  # {situation.id: "DIR region name", ...}
for situation in situations:
    works = situation.roadworks[0]
    print(regions.get(situation.id), works.road_maintenance_type, works.location.point)
```

Verified against the live feed (2026-07, 256 situations, 170 roadworks):
every single roadworks record carries WGS84 coordinates *and* an Alert-C
reference side by side — coordinates are taken, Alert-C is preserved (not
decoded). France's real data is what surfaced two genuine gaps in the
*shared* DATEX parser, now fixed: `alert_c_location` used to return a raw
numeric location-table code instead of the human-readable name sitting
right next to it, and TPEG linear locations (a segment's `from`/`to`
endpoints) used to keep only whichever endpoint came first in document
order, silently dropping the other — both fixed in
`streetworks/datex2/parser.py`, and the 2-point line now survives all the
way to `Coordinate.points` (see below). `administrative_area` (the DIR
region, e.g. `"DIR Sud-Ouest"`) is genuinely stated but on a different,
coarser field than the shared model's `source_name` — `dir_regions()`
reads it from each record's `.raw` XML directly. Published under the
**Licence Ouverte / Open Licence 2.0 (Etalab)** — see
`streetworks/datex2/bisonfute.py`'s module docstring for the attribution
wording and full field-by-field mapping.

**Spain's DGT** (Dirección General de Tráfico) publishes national traffic
incidents, including roadworks, credential-free as genuine DATEX II **v3**
(Level C, with Spanish national extensions alongside the standard elements)
— reused through the same shared parser, no bespoke path needed:

```python
from streetworks.datex2.dgt import DGTClient, provinces

with DGTClient() as dgt:
    situations = list(dgt.iter_roadworks())
spanish_provinces = provinces(situations)  # {situation.id: "province name", ...}
for situation in situations:
    works = situation.roadworks[0]
    print(spanish_provinces.get(situation.id), works.road_maintenance_type, works.location.point)
```

Verified against the live feed (2026-07, 656 situations, 391 roadworks
records, 100% coordinate coverage): Spain's real data is what surfaced the
first genuine *discriminator* gap, not just a field-mapping one — DGT has
**zero** `MaintenanceWorks`/`ConstructionWorks` records anywhere in the
feed. It publishes roadworks as a generic record type
(`RoadOrCarriagewayOrLaneManagement`, mostly, but also `SpeedManagement`
and `AbnormalTraffic`) discriminated only by
`cause/causeType=roadMaintenance` + `roadMaintenanceType=roadworks` —
`SituationRecord.is_roadworks` now checks that pair additively when the
xsi:type isn't one of the two dedicated types, confirmed not to change any
other adapter's real fixture. The road identifier is stated as `roadName`
(e.g. `"N-400"`), not `roadNumber` like NDW/France — added as a fallback,
tried only when `roadNumber` is absent. `administrative_area` comes from a
new `provinces()` helper (the real per-record province, e.g. `"Toledo"` —
genuinely stated on 391/391 real records, nested in a Spanish location
extension, not on the shared model, same shape of solution as France's
`dir_regions()`). Coverage is national **except Catalonia and the Basque
Country**, which run their own regional traffic authorities and publish
separately — documented honestly, like France's non-concessionary-network
scope. Published under **Creative Commons Attribution (CC BY)** — see
`streetworks/datex2/dgt.py`'s module docstring for the attribution wording
and full field-by-field mapping.

## Autobahn GmbH (Germany, national motorways)

Germany's national motorway (Autobahn) network roadworks, via Autobahn
GmbH's own open JSON REST API — credential-free, but **not** DATEX II and
**not** OGC/WFS, so `streetworks.autobahn` has its own small parser rather
than routing through `streetworks.datex2` (the same shape of choice as
WZDx for the US). Covers the national motorway network only; German state
roads are a separate WFS-based source, out of scope here.

> ⚠️ **Licence unconfirmed.** Checked govdata.de's CKAN catalogue entry for
> this API (organisation: Mobilithek — `license_title`/`license_url` both
> blank), the MDM portal link that entry points to (unreachable), the
> community `bundesAPI/autobahn-api` documentation (no licence stated), and
> the official autobahn.de app page (no terms of use found). None confirm
> reuse/redistribution rights. Shipped deliberately with this caveat rather
> than silently assumed open — confirm your own rights before
> redistributing this data.

```python
from streetworks.autobahn import AutobahnClient
from streetworks.common import from_autobahn

with AutobahnClient() as autobahn:
    roads = autobahn.list_roads()               # 113 real road ids, e.g. "A1"
    items = list(autobahn.iter_all_roadworks(roads))   # one request per road

works = from_autobahn(items)                     # grouped into works + phases
for w in works:
    print(w.reference, len(w.sites), w.administrative_area)
```

Verified against a live fetch of all 113 roads (2026-07, zero failures):
2,873 roadworks records, grouping into 997 works. `territory="Germany"`,
`administrative_area="Autobahn GmbH"` — the national motorway operator IS
the data-owning authority, same rule as National Highways for England.

**Two real road-list traps, confirmed live, not just documented**:
`"A64a"`/`"A99a"` use lowercase route suffixes — don't upper-case road
ids. More surprising: `"A60 "` (trailing space) isn't a formatting quirk
on the one real A60 — the list carries *two* separate entries, a plain
`"A60"` and this space-suffixed one, and they behave differently:
`GET .../A60/...` returns 20 real roadworks, `GET .../A60%20/...` (the
listed id, correctly percent-encoded, not stripped) returns zero.
Stripping the space would silently refetch the other entry's 20 records
under the wrong road id — so despite looking like noise, road ids must be
used exactly as listed, never stripped or reformatted.

**Geometry is a real line, not a point** — every one of 2,873 real records
carries `LineString` geometry (2–767 vertices), kept whole on
`Coordinate.points`, same as the France/WZDx line-geometry handling.
Native axis order is genuinely reversed *within one record*: the
`coordinate` field is `(lat, long)`, `geometry.coordinates` is GeoJSON
`(lon, lat)` — both native in `Roadworks`, flipped explicitly in
`from_autobahn`, same as WZDx.

**A genuine two-level spine, confirmed not assumed**: records sharing an
identifier prefix (before its first `--`) are phases of one works — in the
full fetch, 599 multi-record groups, and *every one* agrees on its overall
end date (599/599, zero disagreements). Grouping is **cross-road**: 50 of
997 real prefixes span more than one road, because a works at a junction
gets listed under every connecting road's own response (e.g. one A1/A61
junction project has 3 records under `A1` and 2 under `A61`) — confirmed
safe to merge (no identifier is ever duplicated across roads).

**Dates are a deliberate, documented exception to "never infer, only take
what's stated"**, in the same honest register as Digitraffic's
`validity.status` caveat: there is no end-date field anywhere in this API,
and no start-date field at all for `SHORT_TERM_ROADWORKS` records (0/1,184
real ones carry it, vs. 1,689/1,689 long-term `ROADWORKS` records that
do). Dates for everything else come from parsing `description[]` —
machine-generated, consistently-formatted text, not human prose, so this
is extraction, not inference, but it's still an exception, and
`Roadworks.is_start_verified` exists so callers can tell a verified date
from an estimated one rather than trusting every date equally. Five real
text shapes are handled (long-term Beginn/Ende, the overall-measure end,
and three short-term shapes — single-day, overnight/multi-day, and a
recurring-weekly pattern collapsed to its outer bounding window, the same
trade-off DATEX's `Validity` makes for multi-period validity) — coverage
is 100% for `ROADWORKS` and 99.7% (1,181/1,184) for `SHORT_TERM_ROADWORKS`;
the remaining 3 records use free-form "valid except these days" text that
isn't safely extractable without guessing, and are left with dates unset,
raw text preserved. Timezone is Europe/Berlin via `zoneinfo`, not a fixed
offset — DST is genuinely observed in the data (`+01:00`/`+02:00` both
seen live), and `"24:00"` (also seen live) means end-of-day, handled by
rolling to `00:00` the next day rather than rejected. See
`streetworks/autobahn/parser.py`'s module docstring for the exact shapes
and full field-by-field mapping.

The per-item `details/roadworks/{id}` endpoint was checked and confirmed
to add nothing over the list response (sampled 6 varied real records,
every extra field was `null`) — skipped, avoiding ~2,900 extra requests.

## German state roadworks (OGC WFS)

Germany's individual *states* (Bundesländer) each publish their own
regional-road roadworks as open geodata — separate from, and complementary
to, Autobahn GmbH's national-motorway API above. `streetworks.ogc` is a
generic OGC-features GeoJSON client (`OGCFeaturesClient`), plus a
declarative per-state field-map registry (`streetworks.ogc.germany`) that
one shared converter reads — adding a state is writing a new field-map
entry, not a new converter. (`streetworks.ogc` is new infrastructure in
0.7.0 and its interface is **provisional** — it was deliberately built
generic so the future gazetteer work can reuse it, and that work may
reshape it in 0.8.0.)

```python
from streetworks.common import from_ogc_features
from streetworks.ogc.germany import BRANDENBURG, GermanRoadworksClient

with GermanRoadworksClient() as germany:
    features = germany.fetch("Brandenburg")

works = from_ogc_features(features, BRANDENBURG)
for w in works:
    print(w.administrative_area, w.sites[0].works_type, w.sites[0].location_description)
```

Three states are live, all verified against real data (2026-07):
**Hamburg** (130 features, `Point` geometry, dates `DD.MM.YYYY`, via WFS),
**Brandenburg** (487 features, `LineString`, dates ISO, via WFS), and
**Saxony** (1,531 real closures + 813 diversions, `LineString`, dates
`DD.MM.YYYY` with an occasional real hour suffix, via a direct GeoJSON
download — Saxony has no queryable service at all). Hamburg and
Brandenburg publish under **Datenlizenz Deutschland — Namensnennung —
Version 2.0** (dl-de/by-2-0); Saxony under **Creative Commons Attribution
4.0 International**. All three confirmed directly from each service's
own `GetCapabilities`/catalogue metadata, with exact attribution wording
baked into each state's field-map entry.

**GeoJSON-primary, no GML — but not every state is EPSG:4326.**
`OGCFeaturesClient` always requests `application/geo+json` over WFS,
never trusting a server's default output format (commonly GML). A
GML-only state is out of scope, not a GML-parsing project — confirmed
live for both **Mecklenburg-Vorpommern** (its WFS explicitly rejects
`application/geo+json` with an `InvalidParameterValue` exception) and
**Saxony-Anhalt** (rejects `application/json` too, with an
`msPostGISLayer` exception) — both **parked**. Saxony-Anhalt has a second,
independent reason: its `GetCapabilities` states outright *"This service
is for non-commercial use only"* — an explicit restriction, not merely an
unconfirmed licence, and one that conflicts with this SDK's own MIT
licence. (The state's own web page separately calls the service "free of
charge," which reads as open but answers a different question — cost, not
commercial-use rights. Worth knowing before anyone reopens this one.)
**NRW** and **Bavaria** are parked too, for a different reason each: NRW's
open geodata is road *network* data (a gazetteer concern), not roadworks
— its actual roadworks route is the gated Mobilithek/DATEX path already
out of scope elsewhere; Bavaria's BAYSIS portal has no Baustellen
(roadworks) layer at all.

**CRS is stated per state, never assumed — and Saxony breaks the
"always WGS84" pattern deliberately.** Every request states its CRS
explicitly (`SRSNAME=EPSG:4326` for the WFS states) rather than trusting
a server default (commonly a UTM zone). Saxony's data, checked
exhaustively (its WMS, its direct download, even its "planned works"
dataset's own ISO metadata), genuinely has **no WGS84 source anywhere** —
only `EPSG:25833` (UTM33N). Rather than park a source this rich (district
*and* municipal roadworks, not just state roads — deeper coverage than
Hamburg or Brandenburg) over an axis-order technicality, Saxony ships
with its real CRS carried through and labelled explicitly on
`Coordinate.crs` — the same policy this SDK already uses for its British
National Grid providers (OS Open USRN, DataVIA, Street Manager): a
non-4326 CRS is never silently reprojected, just stated. GeoJSON
coordinates in Saxony's feed are `(easting, northing)`, taken as-is, no
axis flip — exactly how `from_streetmanager` already handles BNG.

**Axis order was checked, not assumed** — WFS 2.0/EPSG:4326 can come back
lat/lon (the reverse of GeoJSON's mandated lon/lat), the same trap the
DataVIA WMS work already documented. Every real coordinate from Hamburg
and Brandenburg falls inside Germany's true lon/lat bounds (~5.6–15.3,
~47.0–55.3); Saxony has its own equivalent UTM bounds check. All three
confirmed in a mandatory test per state, not just eyeballed once.

**Hamburg's access mode was genuinely ambiguous — resolved, not assumed.**
The state's open-data catalogue also lists a "direct GeoJSON download";
confirmed live, it's a ZIP archive wrapping this same WFS's output (the
archive contains `de_hh_up_baustelle_EPSG_4326.json`) — not a separate
source. The direct WFS `GetFeature` call is the canonical path: one HTTP
request, GeoJSON immediately, no archive to unpack. Saxony's own "direct
GeoJSON download" is genuinely the *only* path — confirmed via the GDI-DE
catalogue's own metadata search (5 real records for Saxony's
SPERRINFOSYS) that the "GDI-Baustellen-WFS" once referenced in passing
doesn't exist as a live, queryable endpoint.

**One `Works` per feature, one `WorksSite`, deliberately not grouped** —
no state's data states a genuine works/phase grouping key. Brandenburg's
`ID` property has real prefix/suffix structure (e.g. `"267201193_1"`,
`"_2"`, `"_3"`) and 140 of 164 distinct prefixes are multi-record, but
agreement within a group is only ~81–88% on dates/type/road — far short
of Autobahn's independently-corroborated 100%. Saxony shows the same
shape of pattern through a different field: 1,531 real features, only
1,133 distinct `ID` values — a spot-check confirms a duplicated ID is one
closure split across several line segments, but the full pattern wasn't
checked as thoroughly as Brandenburg's. Both ship 1:1 like every other
provider without a genuine grouping signal, per this SDK's record-identity
rule: raise an observed pattern, never act on it without real evidence.
`territory="Germany"`, `administrative_area` (`"Hamburg"`/`"Brandenburg"`/
`"Sachsen"`) is **endpoint provenance, not a record field** — there is no
`bundesland` property on any state's features; the state is known because
each field map is bound to one state's own endpoint, the same mechanism
National Highways' `administrative_area="National Highways"` uses, not
Spain's `provinces()` reading a real per-record field.

Field names are UTF-8 throughout, umlauts and `ß` included — one real
Brandenburg field name is `Straßenummner` (double "n", a typo in the
source schema itself, confirmed live — not `Straßennummer`). Hamburg has
no road number/name field of any kind (checked all 130 real features) and
no single clean status field either — six independent boolean flags
(`iststoerung`, `istfreigegeben`, `istoepnveingeschraenkt`, ...) instead,
all preserved on `.raw`, none forced into the common model. See
`streetworks/ogc/germany.py`'s module docstring for the full
field-by-field mapping and every state's exact attribution text.

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

Use `streetworks.wzdx.list_feeds()` to discover feed URLs from the [USDOT
feed registry](https://datahub.transportation.gov/Roadways-and-Bridges/Work-Zone-Data-Feed-Registry/69qe-yiui/about_data)
rather than hardcoding one.

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

## Common models

Every provider above has its own native, full-fidelity shape — that's
deliberate, and it never goes away. `streetworks.common` adds canonical
types *alongside* those native interfaces, for code that wants to handle
works data from several providers the same way without caring which one it
came from:

```python
from streetworks.common import from_srwr
from streetworks.srwr import SRWRClient, iter_activities

with SRWRClient() as srwr:
    archive = srwr.download_daily("srwr-daily.zip")
    for activity in iter_activities(archive):
        works = from_srwr(activity)
        for site in works.sites:
            print(site.reference, site.works_type, site.date_confidence, site.raw)
```

A DATEX source needs two more keyword arguments, since a `Situation` can't
state them itself — see below:

```python
from streetworks.common import from_datex2
from streetworks.datex2.dgt import DGTClient, provinces

with DGTClient() as dgt:
    situations = list(dgt.iter_roadworks())
spanish_provinces = provinces(situations)  # {situation.id: "province name", ...}
for situation in situations:
    works = from_datex2(
        situation, territory="Spain",
        administrative_area=spanish_provinces.get(situation.id),
    )
```

`from_datex2` (and `from_wzdx`) take `territory`/`administrative_area` as
keywords rather than deriving them, because neither can be read off a
DATEX `Situation` (or a WZDx `RoadEvent`) alone — the provider sections
above show what each source natively states — a province, a DIR region, or
nothing at all — that you'd pass in.

Two levels, deliberately not three: `Works` is the umbrella (reference,
location, promoter — no committed dates of its own); `WorksSite` is the
dated, actionable unit under it (Street Manager's `-01`/`-02` permits,
SRWR's phases joined to their Undertaker-Phase, DATEX roadworks records all
map here). `WorksPlanning` is a separate type for planning *artifacts* —
PAAs and Street Manager Forward Plans — with indicative rather than
committed dates: a record that is *born* as a planning artifact maps here;
a record that only *transitions* through a planning-ish status (SRWR's
"Advance Planning", DATEX's `validityStatus = planned`) stays a `WorksSite`
with that status exposed, so the same source record never migrates between
canonical types as its lifecycle progresses.

Every canonical object carries a `source_grade` (`register` / `operator` /
`traveller_info`) and `WorksSite` carries a computed `date_confidence`
(`verified` / `estimated` / `unknown`), so consumers can filter by
trustworthiness without provider-specific knowledge — and every one keeps
`.raw` pointing back at its exact source record(s), so converting never
loses anything.

`Coordinate.value` is always one representative point, so every point-only
consumer keeps working unchanged; `Coordinate.points` holds every vertex
when the source geometry is a real line (a WZDx/Street Manager `LineString`,
a DATEX `LinearLocation`/TPEG segment) — `points[0] == value` always. This
used to just collapse to `value` across every converter that had line
geometry available; now it survives.

`Works` also carries location *provenance*, not location *geography*:
`territory` (country-level — UK nations count as countries: `"Scotland"`,
`"England"`, ..., plus `"USA"`, `"Netherlands"`) and `administrative_area`
(the sub-national body that *owns* the data one level down — a UK highway
authority, a US state DOT, a Dutch province, or a national operator's own
name where the operator IS the authority). `administrative_area` is
populated only where a provider genuinely states it, never inferred from a
coordinate, and is consistent *within* one territory but not
size-comparable *across* them — filter by `territory` before aggregating.
`WorksSite.territory`/`.administrative_area` delegate to the parent `Works`,
so a site in hand doesn't need the umbrella held separately. Some
converters (`from_datex2`, `from_wzdx`) can't derive these from the source
record alone — see their docstrings for why — and take them as keyword
arguments instead of guessing.

Converters currently cover SRWR, Street Manager, DATEX II (NDW, National
Highways, Digitraffic/Finland, IRCA/Iceland, Bison Futé/France, and
DGT/Spain via the one shared converter), Autobahn GmbH/Germany, German
state roadworks (Hamburg, Brandenburg, Saxony, via the one shared
`from_ogc_features` converter), WZDx, TrafficWatchNI and Traffic Wales.
UK Police stays outside
the works hierarchy entirely — it's a *context* provider (area-level crime as a
safety signal), not a works
provider, and forcing it into a `WorksSite` would misrepresent what it
actually is.

## Design principles

1. **Never block the user.** Typed methods for confirmed, common endpoints;
   generic `get/post/put/delete` on every API group for everything else.
2. **Be a good API citizen.** Token reuse, refresh-then-reauth, exponential
   backoff, honoured `Retry-After` — per the DfT integration guidance.
3. **Test without credentials, verify with them.** The whole unit suite runs
   against mocked transports (`respx`) so CI needs no secrets; a separate
   smoke test and skip-guarded integration suite verify against the real
   systems when you supply credentials.
4. **Room to grow.** Each provider is a self-contained module over a shared
   transport/exception core — adding a new API is additive.

## Roadmap

- [x] Pydantic model generation pipeline for the Street Manager swagger specs
- [x] Auto-pagination helpers for the Reporting API (`iter_permits()` etc.)
- [x] DataVIA WMS support (`get_map`, `get_feature_info`, `wms_capabilities`)
- [x] D-TRO publish models generated from the DfT JSON schemas, version-namespaced
      (`v3.5.1` to match production, `v4.0.0` to follow) — see [docs/DTRO_SCHEMAS.md](docs/DTRO_SCHEMAS.md)
- [x] Scottish Road Works Register - Open Data provider (`streetworks.srwr`).
      The authenticated SRWR/Aurora web-services API is restricted to Scottish
      authorities and utilities; contributions from SRWR users welcome.
- [x] **Common models** (`streetworks.common`): canonical cross-provider types
      (`Works`, `WorksSite`, `WorksPlanning`, `Coordinate`, `Notice`) with explicit
      per-provider converters (`from_srwr`, `from_streetmanager`, `from_datex2`,
      `from_wzdx`, `from_trafficwatchni`, `from_trafficwales`), so the same code
      handles works data from any provider — native full-fidelity interfaces
      retained, `.raw` always keeps the source record(s); `Works` also carries
      `territory`/`administrative_area` location provenance so a mixed
      cross-provider list can be filtered by where the data comes from
- [x] OS Open USRN: credential-free GB-wide USRN lookup with geometry (`streetworks.openusrn`)
- [x] Northern Ireland roadworks (TrafficWatchNI RSS) and Wales motorway/trunk
      roadworks (Traffic Wales RSS) — all four UK nations now have coverage
- [x] UK Police crime data (`streetworks.police`) as a worker-safety signal —
      no API exists for roadworker abuse directly, so this is the closest
      honest proxy; `safety_signal()` filters to the categories that bear on
      personal safety — verified against the real API
- [ ] Traffic Wales DATEX II feeds (richer than the RSS; access on application)
- [ ] Scottish street gazetteer (OSG portal open data); Northern Ireland gazetteer
      (Wales street gazetteer is already covered by the Geoplace NSG via DataVIA)
- [x] **DATEX II parser** (v3 + v2 SituationPublication roadworks) with the
      NDW (Netherlands, XML) open-data adapter — verified against the real national feed
- [x] National Highways (England SRN) DATEX II v3.4 **JSON** adapter
      (`streetworks.datex2.nationalhighways`), cursor pagination via `x-next` —
      verified against the real API
- [x] Finland (Digitraffic) DATEX adapter (`streetworks.datex2.digitraffic`)
      — its own JSON schema, not a DATEX-II serialisation, mapped onto the
      same shared models; verified against the real feed, no credentials
- [x] Iceland (IRCA/Vegagerðin) DATEX adapter (`streetworks.datex2.irca`) —
      genuine DATEX II v3 XML over a SOAP `snapshotPull` interface, reused
      through the existing shared parser unchanged; verified against
      multiple independent live fetches, no credentials
- [x] France (Bison Futé/the DIRs) DATEX adapter (`streetworks.datex2.bisonfute`)
      — genuine DATEX II v2 XML for the non-concessionary national network,
      reused through the existing shared parser; verified against the real
      feed (256 situations, 170 roadworks, 100% coordinate coverage), no
      credentials. Surfaced and fixed two real gaps in the shared parser
      itself (`alert_c_location` name preference, TPEG linear from/to
      geometry) - not France-specific bugs, just never exercised before
- [x] Spain (DGT) DATEX adapter (`streetworks.datex2.dgt`) — genuine DATEX
      II v3 (Level C, Spanish-extended profile), reused through the existing
      shared parser; verified against the real feed (656 situations, 391
      roadworks, 100% coordinate coverage), no credentials. Coverage excl.
      Catalonia & the Basque Country. Surfaced and fixed a genuine
      *discriminator* gap, not just a field-mapping one — DGT has zero
      `MaintenanceWorks`/`ConstructionWorks` records at all, so
      `SituationRecord.is_roadworks` gained an additive cause-based check
      (`roadMaintenance`/`roadworks`), plus a `roadName` fallback for the
      road identifier (Spain never states `roadNumber`)
- [x] Germany (Autobahn GmbH) national motorway adapter (`streetworks.autobahn`)
      — its own JSON REST API, not DATEX; verified against a live fetch of
      all 113 roads (2,873 roadworks, zero failures), no credentials. A
      genuine two-level spine (works/phases) confirmed live, cross-road
      grouping (a junction project can be split across two roads' API
      responses), and a documented free-text date-parsing exception
      (99.7% coverage on the class with no date field at all). **Licence
      unconfirmed** despite checking four independent sources — shipped
      anyway, flagged prominently, not silently assumed open
- [x] German state (Bundesland) roadworks (`streetworks.ogc`) — a reusable
      generic OGC WFS/Features/direct-download GeoJSON client plus a
      declarative per-state field-map registry, one shared converter
      reading it (adding a state is a field map, not a new converter).
      Hamburg, Brandenburg and Saxony shipped, verified against real data
      (130 + 487 + 1,531 features, 100% coordinate coverage, 0
      out-of-bounds on the mandatory axis-order check each). Saxony has
      no queryable service at all — WMS + a direct GeoJSON ZIP download
      only — and no WGS84 source anywhere, so it ships in its real CRS
      (EPSG:25833/UTM33N), carried through and labelled explicitly, never
      reprojected, the same policy this SDK already applies to its BNG
      providers. Mecklenburg-Vorpommern and Saxony-Anhalt checked and
      **parked** (both GML-only; Saxony-Anhalt's licence also explicitly
      non-commercial); NRW and Bavaria parked too (network-only geodata /
      no Baustellen layer, not GML/CRS issues). Both Brandenburg's and
      Saxony's `ID` fields showed a real but imperfect grouping signal —
      raised, not acted on; ships 1:1 like every other provider without
      corroborated grouping evidence. Client built gazetteer-ready
      (generic GeoJSON fetch, CRS-aware) but no gazetteer features added
      yet — separate design session pending
- [ ] Norway (Statens vegvesen) DATEX adapter (`streetworks.datex2.vegvesen`)
      — **Phase 1 scaffold built, pending live verification.** Blocked on
      credentials for the actual authenticated pull; not usable against
      real Norwegian data yet — see the module docstring for what's confirmed
      vs. still open
- [ ] Further DATEX II adapters: Mobilithek (DE), transport.data.gouv.fr (FR)
      — per-NAP verification needed
- [x] **WZDx (US Work Zone Data Exchange)** parser (`streetworks.wzdx`,
      v3.1–v4.2), a generic feed client, and a USDOT registry helper —
      verified against 12 live agency feeds, not one sample
- [ ] Ordnance Survey NGD / Linked Identifiers?

### European & Crown Dependency roadworks — separate strand

Candidate feeds, researched but **not yet verified**. As always, each needs a
real sample feed and a licence/access check *before* building — the first task
per source is "can we get the feed and what do the terms permit," not coding.

Grouped by the client shape they need:

- **DATEX II adapters** (thin fetchers over the existing `streetworks.datex2`
  models, Finland/National-Highways-style where the source isn't DATEX-shaped
  itself). Norway, Iceland, France, and Spain are covered above (Iceland,
  France, and Spain shipped, Norway Phase 1). Further candidates: Denmark
  (Vejdirektoratet), Sweden (Trafikverket — verify its SOAP/XML model is
  DATEX-compatible). Access models vary from fully open to
  registration/agreement-gated — confirm per country. Note Alert-C
  location-code decoding (numeric codes → geometry, not yet supported) is
  likely needed for some of these, unlike Finland's coordinate-carrying JSON.
- **ArcGIS REST** (a new client shape — Esri `/query?f=json`). Jersey publishes
  roadworks as an ArcGIS MapServer layer; likely a quick, self-contained win
  and the SDK's first Channel Islands coverage.
- **Dedicated pieces** (each its own project, not a quick adapter): Germany's
  Mobilithek *broker* (subscription access, mixed schemas — D-TRO-scale
  effort; distinct from Autobahn GmbH's own public motorway-roadworks API,
  already covered above); Guernsey (appears to be an HTML site — confirm
  whether any structured feed exists before committing, and check
  licensing for scraping).
- Verify-the-source-first: prefer official government feeds over third-party
  API-marketplace wrappers; a couple of the researched links need their real
  upstream endpoint confirmed.

### International gazetteers — separate strand

The European equivalents of OS Open USRN (address/street reference layers, not
roadworks — keep distinct from the feeds above): France BAN, Spain Catastro,
Norway Kartverket, Netherlands PDOK, Germany Geoportal, Portugal SNIG, plus the
UK GeoPlace gazetteer SOAP API. These eventually connect to the **common
models** work; formats differ widely, so each needs its own mapping design.
Germany's own state gazetteers are commonly published the same way as the
regional roadworks above (WFS/OGC API Features) — `streetworks.ogc`'s
`OGCFeaturesClient` was deliberately kept generic (GeoJSON in, features
out, CRS-aware, nothing roadworks-specific) so this future work can reuse
it rather than needing its own fetch layer; no gazetteer-specific code
exists yet, that's still its own design session.

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Development

```bash
pip install -e ".[dev]"
pytest                    # mocked unit tests - no credentials needed
ruff check .
```

The unit tests mock the network so they run offline and without credentials.
To verify the SDK against the **real** test/sandbox systems with your own
credentials, use the smoke test or the integration suite — see
[docs/INTEGRATION.md](docs/INTEGRATION.md):

```bash
python scripts/smoke_test.py     # one read-only call per configured service
pytest -m integration -v         # same checks, in the test suite
```

## Licence

MIT. Not affiliated with or endorsed by the Department for Transport or
Geoplace. Street Manager documentation is © Crown copyright, available under
the Open Government Licence v3.0.
