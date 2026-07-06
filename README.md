# streetworks

[![CI](https://github.com/KFergusonUK/StreetWorks-SDK/actions/workflows/ci.yml/badge.svg)](https://github.com/KFergusonUK/StreetWorks-SDK/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/streetworks)](https://pypi.org/project/streetworks/)
[![Python](https://img.shields.io/pypi/pyversions/streetworks)](https://pypi.org/project/streetworks/)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)

An open Python SDK for UK street works APIs — one consistent, typed,
well-tested client for the services the sector actually uses.

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
| `streetworks.dtro` | [DfT Digital Traffic Regulation Orders](https://d-tro.dft.gov.uk/api-documentation/) — integration & production | read + write |
| `streetworks.srwr` | [Scottish Road Works Register](https://roadworks.scot/) — national register via Open Data CSV extracts (no credentials) | read |
| `streetworks.openusrn` | [OS Open USRN](https://osdatahub.os.uk/downloads/open/OpenUSRN) — every GB USRN with geometry, via the OS Downloads API (no credentials) | read |
| `streetworks.datex2` | [DATEX II](https://datex2.eu/) — European roadworks parser (v3 + v2), with the NDW (Netherlands) open-data adapter | read |
| `streetworks.trafficwatchni` | [TrafficWatchNI](https://trafficwatchni.com/) — Northern Ireland roadworks/incidents RSS (DfI TICC; no credentials) | read |
| `streetworks.trafficwales` | [Traffic Wales](https://traffic.wales/) — Welsh motorway/trunk roadworks RSS, EN + CY (no credentials) | read |

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
the real systems for all providers:** Street Manager (SANDBOX), Geoplace
DataVIA (live — including a real feature query), D-TRO (production token +
events search), the Open Data SNS parsing/verification pipeline, SRWR
Open Data (parsed against real published daily and monthly extracts), and
OS Open USRN (Downloads API + GeoPackage reader).

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
DATEX II **v3 and v2** — plus source adapters, starting with the Netherlands'
credential-free NDW open data:

```python
from streetworks.datex2 import NDWClient, iter_roadworks

with NDWClient() as ndw:
    feed = ndw.download_planned_works("ndw-planned.xml.gz")

for situation in iter_roadworks(feed):
    works = situation.roadworks[0]
    print(works.source_name, works.road_maintenance_type,
          works.validity.overall_start, works.location.point)
```

The parser streams (the ~170 MB Dutch national feed parses in seconds at
~35 MB memory) and normalises locations across referencing methods.
**Coordinates are WGS84 latitude/longitude** — not the British National Grid
used by the UK providers here. National Highways (England's SRN, DATEX II
v3.4 via its developer portal) is the planned second adapter.

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
- [ ] **Common models**: canonical cross-provider types (`Street`, `WorksNotice`,
      `Coordinate`, ...) with explicit `.to_common()` converters, so the same code
      handles English and Scottish data - native full-fidelity interfaces retained
- [x] OS Open USRN: credential-free GB-wide USRN lookup with geometry (`streetworks.openusrn`)
- [x] Northern Ireland roadworks (TrafficWatchNI RSS) and Wales motorway/trunk
      roadworks (Traffic Wales RSS) — all four UK nations now have coverage
- [ ] Traffic Wales DATEX II feeds (richer than the RSS; access on application)
- [ ] Scottish street gazetteer (OSG portal open data); Northern Ireland gazetteer
      (Wales street gazetteer is already covered by the Geoplace NSG via DataVIA)
- [x] **DATEX II parser** (v3 + v2 SituationPublication roadworks) with the
      NDW (Netherlands) open-data adapter — verified against the real national feed
- [ ] Further DATEX II adapters: National Highways (England SRN, developer-portal
      key), Mobilithek (DE), transport.data.gouv.fr (FR) — per-NAP verification needed
- [ ] Ordnance Survey NGD / Linked Identifiers?

### 0.4.0 — European & Crown Dependency roadworks

Candidate feeds, researched but **not yet verified**. As always, each needs a
real sample feed and a licence/access check *before* building — the first task
per source is "can we get the feed and what do the terms permit," not coding.

Grouped by the client shape they need:

- **DATEX II adapters** (thin fetchers over the existing `streetworks.datex2`
  parser, NDW-style). Candidates: Finland (Digitraffic — open, well-documented,
  the natural next one to prove the pattern), Norway (Statens vegvesen),
  Denmark (Vejdirektoratet), Sweden (Trafikverket — verify its SOAP/XML model
  is DATEX-compatible), Spain (DGT NAP), France (Bison Futé). Access models
  vary from fully open to registration/agreement-gated — confirm per country.
- **ArcGIS REST** (a new client shape — Esri `/query?f=json`). Jersey publishes
  roadworks as an ArcGIS MapServer layer; likely a quick, self-contained win
  and the SDK's first Channel Islands coverage.
- **Dedicated pieces** (each its own project, not a quick adapter): Germany's
  Mobilithek (broker/subscription access, mixed schemas — D-TRO-scale effort);
  Guernsey (appears to be an HTML site — confirm whether any structured feed
  exists before committing, and check licensing for scraping).
- Verify-the-source-first: prefer official government feeds over third-party
  API-marketplace wrappers; a couple of the researched links need their real
  upstream endpoint confirmed.

### US work zones (WZDx) — separate strand, own research session

The US standard for roadworks is **WZDx (Work Zone Data Exchange)**, GeoJSON-
based and distinct from DATEX II — so it needs its own parser, not a `datex2`
adapter. The USDOT [WZDx feed registry](https://datahub.transportation.gov/Roadways-and-Bridges/Work-Zone-Data-Feed-Registry/69qe-yiui/about_data)
is the canonical directory of live publishers and feed URLs — the right
starting point for surveying what exists.

### International gazetteers — separate strand

The European equivalents of OS Open USRN (address/street reference layers, not
roadworks — keep distinct from the feeds above): France BAN, Spain Catastro,
Norway Kartverket, Netherlands PDOK, Germany Geoportal, Portugal SNIG, plus the
UK GeoPlace gazetteer SOAP API. These eventually connect to the **common
models** work; formats differ widely, so each needs its own mapping design.

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Development

```bash
pip install -e ".[dev]"
pytest                    # 35 mocked unit tests - no credentials needed
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
