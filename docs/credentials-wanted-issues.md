# "Credentials wanted" GitHub issues — drafted text

Draft text for nine `help wanted` issues: six in the
[Credentials wanted section](providers/index.md#credentials-wanted)
(Trafikverket, Vejdirektoratet, Traffic SA, LINZ NZ Addresses: Roads/Road
Sections, Stockholm, ASFINAG — all blocked on *access* to a real,
published interface), plus three genuinely different cases (Road Report
NT, MapRoad Roadworks Licensing, and Greece — none access-blocked in the
usual sense; NT and Greece have no roadworks interface at all (Greece's
own NAP carries POI/sensor data only, and is currently unreachable
besides), MapRoad has a real API but no published read path for a data
consumer, only a formal data-sharing gate). Norway/NSW/Victoria were
confirmed on 2026-07-30 by a real credentialed pull and no longer need
this - their drafted issue text has been removed. None of these have
been opened yet — this file is the text to paste in when opening them
(or to point someone at ahead of time). Every module's import-time
`UserWarning` (or, for LINZ's per-method gate, its own docstring/
`ValueError`) and the README table link to
`https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22`,
which will surface these once opened with the `help wanted` label.

Suggested labels for the first six: `help wanted`, `credentials-wanted`.
For NT, MapRoad, and Greece: `help wanted` only — `credentials-wanted`
would misdescribe the blocker, since no credential fixes any of them.

---

## Issue: Trafikverket (Sweden) — confirm the adapter against real data

**Title:** `Credentials wanted: verify streetworks.datex2.trafikverket against real Swedish data`

**Body:**

`streetworks.datex2.trafikverket` is a Phase 1 scaffold: built against
Trafikverket's own confirmed-live API shape (not vanilla DATEX II — its own
XML-request/JSON-response envelope) — but no real authenticated response
has ever been seen.

**Confirmed, live, credential-free:** a deliberate invalid-key probe
against the real endpoint returns a genuine structured `401` — this
confirms the endpoint, the request envelope shape, the `Situation` object
name, and schema version `1.5`, independent of any documentation page's own
claims.

**Pending:**
1. Whether the response JSON nests exactly as the dotted `INCLUDE` field
   paths suggest.
2. **The real value of `MessageType`/`MessageCode` that means roadworks
   specifically** — searched several third-party sources, none state it.
   Until this is confirmed, `iter_roadworks()` deliberately returns nothing
   rather than guess — see the module docstring.
3. Whether `Deviation` carries a genuine unique `Id` field.
4. Real coordinate coverage for `Geometry.WGS84`.

**Credential needed:** an API key (not Basic Auth). Free, self-service:
[data.trafikverket.se](https://data.trafikverket.se/) or via
[Trafiklab](https://www.trafiklab.se/api/other-apis/trafikverket/) — fill a
form, accept the licence, verify email, key issued immediately. The
lightest-weight registration of any Credentials-wanted provider here.

**What to report back:** run `python scripts/smoke_test.py` with
`TRAFIKVERKET_API_KEY` set, paste the result line (it lists the real
`MessageType` values seen), and — most usefully — **the real
`MessageType`/`MessageCode` value on a deviation you know to be
roadworks**, so `ROADWORKS_MESSAGE_TYPES`-equivalent filtering can finally
be implemented correctly. One real trimmed `Situation`/`Deviation` record
(anything sensitive stripped) would also let the synthetic fixture be
replaced.

See `src/streetworks/datex2/trafikverket.py`'s module docstring for the
full detail behind each claim above.

---

## Issue: Vejdirektoratet (Denmark) — confirm the adapter against real data

**Title:** `Credentials wanted: verify streetworks.datex2.vejdirektoratet against real Danish data`

**Body:**

`streetworks.datex2.vejdirektoratet` is a Phase 1 scaffold: built against
genuine DATEX II 3.2, confirmed directly from Vejdirektoratet's own
protocol specification — but the credential-gated data pull itself has
never been exercised.

**Confirmed:**
- `sit:ConstructionWorks`/`sit:MaintenanceWorks` record types and their
  full `constructionWorkType`/`roadMaintenanceType` enumerations, stated
  explicitly in Vejdirektoratet's own protocol PDF (not inferred).
- The open metadata catalogue, live (196 datasets, no auth) — the specific
  roadworks dataset ("OOV2 Trafikmeldinger", id 222) confirmed
  road-work-themed, DATEX-II-standard, and CC BY 4.0-licensed.
- HTTP Basic Auth as the documented scheme (quoted verbatim from the
  protocol doc).

**Pending:**
1. Whether `trafikmeldinger` really is a list of independent DATEX XML
   strings, as documented, or a single wrapping document.
2. Whether the REST response is unmodified DATEX II 3.2 or carries a
   Vejdirektoratet-specific profile the shared parser doesn't expect.
3. Real location-referencing coverage.

**Credential needed:** HTTP Basic Auth username/password **and** the
actual per-dataset pull URL — both issued together at registration; there
is no public data URL to hardcode. Free; register via
[Dataudveksleren](https://du-portal-ui.dataudveksler.app.vd.dk/).

**What to report back:** run `python scripts/smoke_test.py` with
`VEJDIREKTORATET_URL`/`VEJDIREKTORATET_USERNAME`/`VEJDIREKTORATET_PASSWORD`
set, paste the result line, and — ideally — one real trimmed
`sit:situation` (with anything sensitive stripped) so the synthetic fixture
can be swapped for real data and the open questions above closed out.

See `src/streetworks/datex2/vejdirektoratet.py`'s module docstring for the
full detail behind each claim above.

---

## Issue: ASFINAG (Austria) — confirm the pull URL, auth mechanism, and real data

**Title:** `Credentials wanted: verify streetworks.datex2.austria against real Austrian data`

**Body:**

`streetworks.datex2.austria` is a Phase 0 scaffold — one phase earlier
than Vejdirektoratet: built against ASFINAG's own confirmed dataset
description, but neither the real pull URL nor the auth mechanism
(not just the credential value) is known.

**Confirmed, live, credential-free:** ASFINAG's own official dataset
page (`mobilitaetsdaten.gv.at/daten/verkehrsmeldungen-zu-geplanten-ereignissen-asfinag`)
states the dataset covers real event types `Baustellen`
(roadworks)/`Instandhaltungsarbeiten` (maintenance)/`Sanierungen`
(renovations)/pre-planned events, genuinely **DATEX II Situations with
SituationRecords**, XML format, HTTP/HTTPS pull, 1-minute update rate.
The investigation brief's own "check the open RSS first" question is
resolved, negatively: the real public RSS/ATOM feed on the same NAP is
confirmed live to cover only "unplanned and safety-related traffic
events" — not roadworks, filed under a different category entirely. The
licence page confirms genuine CC-BY-4.0 plus real supplementary
conditions (must disclose your own downstream services to ASFINAG; they
may publicly reference you as a licensee).

**Pending — more than Vejdirektoratet had left:**
1. **The real pull URL** — no public data endpoint exists to probe; an
   older, separately-documented API host (`services2.asfinag.at`) is
   unreachable from this build environment.
2. **The auth mechanism itself** — API key? Basic Auth? Bearer token? —
   checked the dataset page, the licence page, and the registration
   portal's (`contentportal.asfinag.at`) own JS bundle; nothing found.
3. Whether the response body is a bare DATEX XML document (assumed here,
   the simplest shape) or wrapped in some envelope.
4. Whether real Austrian data uses the standard DATEX
   `ConstructionWorks`/`MaintenanceWorks` vocabulary this SDK's shared
   `ROADWORKS_TYPES` already recognises, or needs its own discriminator.
5. Real coordinate/location-referencing coverage and CRS.

**Credential needed:** unknown mechanism, issued at registration via the
[ASFINAG Content Portal](https://contentportal.asfinag.at/) (`Anmelden`/
`Registrieren` — reachable, registration flow not walked through; the
dataset page states "Lizenz mit kostenloser Nutzung," consistent with
self-service, but this is unconfirmed).

**What to report back:** whether registration is genuinely self-service,
the real pull URL, the real auth mechanism, and — ideally — one real
trimmed `SituationRecord` (anything sensitive stripped) so the synthetic
fixture can be swapped for real data.

See `src/streetworks/datex2/austria.py`'s module docstring for the full
detail behind each claim above.

---

## Issue: Traffic SA / DIT Roadworks (South Australia) — confirm the adapter against real data

**Title:** `Credentials wanted: verify streetworks.au.sa against real South Australian data`

**Body:**

`streetworks.au.sa` is a Phase 1 scaffold, and the worst-off of this SDK's
three Credentials-wanted providers: it's blocked on **two independent
access gates**, not just a credential wait.

1. **A token-gated query endpoint.** The ArcGIS layer's own *metadata*
   (`?f=json`) is public and was pulled live — the schema in the module
   docstring is ground truth, not documentation. But `/query` itself
   returned a genuine HTTP 400 ("Failed to execute query") on every one of
   four clean attempts (three different `where` clauses, two response
   formats, including ArcGIS's own form-built request UI) — an ArcGIS
   token is required.
2. **A geo-restricted host.** `maps.sa.gov.au` returns a CloudFront 403
   with the literal body *"configured to block access from your
   country"* from more than one tested network egress — independent of
   the token gate above.

**Whether an ArcGIS token is even self-service is unresolved** — the
token-issuing host (`location.sa.gov.au/arcgis/tokens/`) itself returned a
CloudFront 403 from the one egress that could reach the layer metadata, so
it has never been reached to check. If it turns out to require a data
agreement with DIT rather than free registration, this may not be a
"credentials wanted" story at all.

**Confirmed, from the live layer *metadata* only:** the real field list
(`ROADWORKS_AND_INCIDENTS_ID`, `REC_TYPE`, `ROAD_NO`, `GIS_LINK_ID`,
`START_DATE`/`END_DATE` as proper Esri date fields, `LATITUDE`/
`LONGITUDE`, `TRAFFIC_DIR`/`NO_LANES_CLOSED`/`SPEED_LIMIT`), native SR
102100/EPSG:3857, `maxRecordCount` 1000, genuine
`advancedQueryCapabilities.supportsPagination: true`.

**Pending (everything below needs a real query response):**
1. **Whether `ROAD_NO`/`GIS_LINK_ID` are populated and genuinely join to a
   road register** (South Australia's Common Road Referencing System) —
   the single most interesting open question in this SDK's whole
   Australia cluster, since every other AU provider is name-only.
2. Whether `LATITUDE`/`LONGITUDE` are genuinely WGS84 and agree with the
   reprojected `SHAPE` geometry.
3. Real coverage — metropolitan Adelaide only, or all of South Australia
   (the dataset's own description and its "Geospatial Coverage" metadata
   field disagree).
4. The real `REC_TYPE` value(s) that mean roadworks specifically (vs.
   incidents) — `iter_roadworks()` deliberately returns the full,
   unfiltered layer-0 mix until this is confirmed, rather than guess at a
   filter string with zero evidence behind it.
5. The canonical endpoint name — `TrafficSAOpenData2` (what the live
   service resolves under) vs. `TrafficSAOpenData` (what data.sa.gov.au's
   own catalogue links to).
6. Whether `resultOffset` pagination on this MapServer layer behaves like
   WA's FeatureServer does under the shared `ArcGISFeatureClient`.

**Credential needed:** an ArcGIS token from
`location.sa.gov.au/arcgis/tokens/`. Self-service vs. gated: unconfirmed.

**What to report back:** run `python scripts/smoke_test.py` with
`SA_TRAFFICSA_TOKEN` set (from a network egress that isn't blocked by the
CloudFront restriction above), paste the result line, and — most
usefully — **one real trimmed feature showing whether `ROAD_NO` is
populated**, plus the real `REC_TYPE` values you see, so the synthetic
fixture can be swapped for real data and the join-key question finally
answered.

See `src/streetworks/au/sa.py`'s module docstring for the full detail
behind each claim above.

---

## Issue: LINZ NZ Addresses: Roads/Road Sections (New Zealand) — confirm the adapter against real data

**Title:** `Credentials wanted: verify streetworks.linz's Roads/Road Sections against a real LDS response`

**Body:**

`streetworks.linz.client`'s `iter_roads()`/`iter_road_sections()` are a
Phase 1 scaffold — the sibling `iter_addresses()` in the same client is
already confirmed live, no key needed at all, so this is a narrower gap
than the other Credentials-wanted providers here: one client, one real
capability blocked, not the whole module.

**Confirmed, live, credential-free:** the real field lists and one real
sample of attribute values (not geometry) for both layers, pulled from
LINZ's own public Koordinates metadata API
(`data.linz.govt.nz/services/api/v1.x/layers/{id}/versions/{v}/data/sample/`)
— genuine `road_id`/name/territorial-authority values, not fabricated.
Real totals (Roads 82,221, Road Sections 250,409) from each layer's own
`feature_count`. The real WFS URL shape too — Koordinates embeds the API
key in the URL **path** (`services;key={api_key}/wfs/`), confirmed from
the layer's own `/services/` listing, not guessed.

**Pending (everything below needs a real authenticated WFS response):**
1. Whether `startIndex`/`count` pagination (implemented to the WFS 2.0
   spec) is genuinely honoured by Koordinates' WFS the way the spec says.
2. **Whether `road_id` genuinely cross-references between NZ Addresses
   (already confirmed live) and Roads/Road Sections** — the field name is
   identical across all three layers' schemas, but the real samples
   pulled so far happen not to overlap, so value-level joining is
   unconfirmed. This is the single most interesting open question in this
   SDK's whole New Zealand cluster.
3. Real geometry shape in practice — whether `MultiLineString` genuinely
   appears on the aggregated Roads layer (documented as possible, never
   seen in a real sample, since the sample endpoint carries attributes
   only, no geometry).
4. Whether absent/null fields in a real WFS `GetFeature` response are
   genuine JSON `null` (assumed, matching every other GeoJSON provider in
   this SDK) or something else — the Koordinates *sample* endpoint used
   for fixtures renders them as the literal string `"None"`, which this
   build could not resolve without a real key.

**Credential needed:** a LINZ Data Service (LDS) API key. Free,
self-service: register at [data.linz.govt.nz](https://data.linz.govt.nz/)
and create a "Data access only" key.

**What to report back:** run `python scripts/smoke_test.py` with
`LINZ_API_KEY` set, paste the result line, and — most usefully — one real
trimmed feature from each of `iter_roads()`/`iter_road_sections()`
(anything sensitive stripped) showing a real `road_id` value, ideally one
that also appears in a real NZ Addresses feature, so the cross-reference
question above can finally be settled.

See `src/streetworks/linz/client.py`'s module docstring for the full
detail behind each claim above.

---

## Issue: Stockholm (Trafikkontoret) — confirm any real dataset exists

**Title:** `Credentials wanted: does streetworks.stockholm have a real roadworks dataset at all?`

**Body:**

`streetworks.stockholm` is a Phase 0 scaffold — one phase earlier than
every other Credentials-wanted provider here. It resolves
`nordic-capitals-investigation.md`'s "Rome-risk" flag on Stockholm by
**confirming it, not disproving it**.

**Confirmed, live, credential-free:**
1. `dataportalen.stockholm.se` (Stockholm's open-data catalogue) has a
   non-functional full-text search — a nonsense search term returns the
   identical 311 records as no filter at all, so no dataset could be
   located by keyword.
2. Trafikkontoret's real geodata service
   (`openstreetgs.stockholm.se/geoservice/api/wfs`) requires an API key
   for `GetCapabilities` itself — a genuine `HTTP 401`
   (`"You must provide a valid key to consume this API."`), confirmed on
   both WFS and WMS. **No layer name, field, or schema of any kind has
   ever been seen.**
3. A "regional roadworks coordination map" lead traces back to the
   already credential-parked *national* Trafikverket system, not a
   separate Stockholm dataset.
4. The one real documented example query on Trafikkontoret's own guide is
   for motorcycle parking places, not roadworks.

**Pending — everything:**
1. **Whether a roadworks (`vägarbete`) dataset exists on this platform at
   all.** Not confirmed present, not confirmed absent.
2. The real API-key parameter name/placement for the WFS/OGC endpoints —
   `apiKey=` (the one real example, documented for the Parking API) is
   used in this scaffold but unconfirmed for WFS specifically.
3. Every real layer/collection name — `StockholmClient.get_wfs_capabilities()`
   is the one call this scaffold can make without guessing; it hasn't
   been run with a real key.

**Credential needed:** a Trafikkontoret API key. **Registration path
unconfirmed** — the one guessed URL 404'd; try
`api.it.tk@stockholm.se` (the technical/access contact stated on the
platform's own getting-started guide) or navigate the portal's own menu
from [openstreetgs.stockholm.se/home/](https://openstreetgs.stockholm.se/home/).

**What to report back:** whether you can even get a key at all (and how),
then the output of `StockholmClient.get_wfs_capabilities()` — specifically,
does the real layer list include anything roadworks/excavation-shaped
(`vägarbete`, `grävning`, or similar)? If a 401 persists with a real key,
that confirms the parameter name/placement is wrong, not the key.

See `src/streetworks/stockholm/client.py`'s module docstring for the full
detail behind each claim above.

---

## Issue: Road Report NT (Northern Territory) — is there a published REST API?

**Title:** `Help wanted: is there a documented REST/GeoJSON API behind Road Report NT?`

**Body:**

`streetworks.au.nt` is a **documented, honestly-unavailable scaffold**,
not a Credentials-wanted one — the difference matters. Every other
unverified provider in this SDK (Trafikverket, Vejdirektoratet, Traffic
SA) has a real, published interface it's merely blocked from reaching
(a key, a token, a region). Road Report NT is different in kind: as far
as this investigation could tell, **no published REST/GeoJSON API exists
at all**.

**What was found, and how:** the public frontend
(`roadreport.nt.gov.au/road-map`) is a minified Angular single-page app.
Reading its bundled JavaScript directly (not documentation — there is
none) found a real reference to the Microsoft SignalR client library
(`aka.ms/signalr-core-differences` appears verbatim) and a real hub
connection literally named `"roadsReportingHub"`, invoking hub methods by
name over a persistent connection — one such method,
`"GetAllMajorRoadObstructions"`, was found as a literal string in the
bundle. **This is inferred from minified JS, not a published
specification** — stated explicitly so nobody mistakes a reverse-engineered
hub method name for a documented contract.

**Why this isn't built as a client, even though the hub name and one
method are known:** encoding SignalR hub internals (the method names, the
negotiate handshake, the message framing) as a working adapter would
present private-app implementation detail as if it were a stable public
contract — the opposite of how every other provider in this SDK is built.
It would also commit this SDK to an entirely new persistent-connection
transport for its single weakest real works-fit provider (Road Report
NT's real content is dominated by road *conditions* — closures, flooding,
weight restrictions — roadworks is at best a minor subset).

**What would change this:** a genuinely documented REST/GeoJSON endpoint
for Road Report NT, published by DIPL/DLI (the agency's own name is
currently in flux) — either found directly, or via NT opening one. Until
then, `RoadReportNtClient()` always raises
`streetworks.exceptions.ProviderUnavailableError` with this same
explanation, rather than silently doing nothing or guessing.

**A possible alternative worth checking, not yet verified:** the National
Freight Data Hub's harmonised aggregate feed — for once, plausibly the
*right* source rather than the usual lossier re-serve, precisely because
no direct NT API exists to prefer over it. Whether it actually carries
real NT records (rather than a catalogue pointer back to this same
unreachable interface) is unconfirmed.

**What to report back:** if you know of a documented REST/GeoJSON
endpoint for NT road data (official or otherwise), or can confirm whether
the National Freight Data Hub's aggregate genuinely includes NT records,
please share it — either would let this scaffold graduate into a real
adapter.

See `src/streetworks/au/nt.py`'s module docstring for the full detail
behind each claim above.

---

## Issue: MapRoad Roadworks Licensing (Ireland) — is there a public read API?

**Title:** `Help wanted: can MapRoad Roadworks Licensing data be read, not just written to?`

**Body:**

`streetworks.maproad` is a **documented, honestly-unavailable scaffold**,
not a Credentials-wanted one — the difference matters, the same way it
does for Road Report NT (Australia). Trafikverket/Vejdirektoratet/
Traffic SA all have a real, published interface merely blocked from
reaching (a key, a token, a region). MapRoad is different: it has a
real, government-catalogued API, but nothing published describes how a
data *consumer* (as opposed to a licence applicant) would reach it.

**What was found, and how:** Ireland's own PSB Data Catalogue entry for
[MapRoad Roadworks Licensing System](https://datacatalogue.gov.ie/dataset/maproad-roadworks-licensing-system)
states, together: `API Available: Yes`, `Open Data: No`, `Data Sharing:
Yes`, `Personal Data: Yes`. Read as a whole, this describes a formal,
GDPR-gated data-sharing arrangement — not a self-service developer key.
Registration for MapRoad itself (`rmo.ie`) is a real, formal process
(download a registration pack, complete it, email it to
`contact@rmo.ie`) aimed at applicants (utilities/contractors)
*submitting* licence applications, not at read-only consumers. TII's own
DATEX II feed (`data.tii.ie`) was checked first and ruled out — its real
dataset catalogue (verified directly, every real title enumerated)
carries no roadworks/Situation publication at all.

**Why this isn't built as a client, even though a real API is known to
exist:** no endpoint, schema, or authentication mechanism for a read
path has been published anywhere found. Building a client against an
unpublished, GDPR-relevant private contract would mean guessing at
something with real personal-data implications — the same "don't encode
a private implementation detail as a stable public contract" discipline
Road Report NT already established, just for a different underlying
reason (a data-sharing gate, not a total absence of any interface).

**What would change this:** confirmation from the RMO that a read-only
data-sharing route exists for a party without a genuine licensing-system
role (a research/open-data use case, not a road authority or applicant),
plus the real technical shape of that route if so.

**What to report back:** if you have (or can get) a formal MapRoad
data-sharing agreement, or know of any published technical documentation
for a read path (endpoint, schema, auth), please share it — either would
let this scaffold graduate into a real adapter, and would make MapRoad
this SDK's first Irish roadworks source, richer than most (national
*and* local road coverage in one register).

See `src/streetworks/maproad/client.py`'s module docstring for the full
detail behind each claim above.

---

## Issue: Greece — is there a documented roadworks source anywhere?

**Title:** `Help wanted: does any Greek source (national or toll-operator) publish roadworks data?`

**Body:**

`streetworks.greece` is a **documented, honestly-unavailable scaffold**,
the same tier as Road Report NT (Australia) — not a real interface
merely blocked, but investigated and found to have no roadworks source
at all.

**What was found, and how:** Greece's real National Access Point
([nap.gov.gr](https://data.nap.gov.gr/), confirmed as the official
MMTIS/RTTI/SRTI/SSTP NAP for Greece per the European Commission's own
October 2025 [National Access Points list](https://transport.ec.europa.eu/document/download/963c997d-efd9-40ae-a38b-5d4b935bdfcf_en?filename=its-national-access-points.pdf))
is a decentralised metadata catalogue (CKAN, run by CERTH/HIT), not a
centralised DATEX II feed. Its own real dataset titles were checked
directly (not assumed): truck parking, refuelling points, KTEL bus/
ferry timetables, Thessaloniki floating car data, and toll-operator
sensor feeds — real Vehicle Detection Sensor data from Attiki Odos, Road
Weather Information System locations for Egnatia Odos, and real-time
Variable Message Sign data from the Hellastron network. **No roadworks
or DATEX II Situation Publication dataset anywhere.**

**A second, independent reason nothing can be built right now: the
portal itself is genuinely down.** Confirmed live (2026-08-03) via
direct probing: `data.nap.gov.gr` returns a real `502 Bad Gateway` from
its own CKAN backend (reproduced on both the dataset-list page and the
`/api/3/action/package_list` endpoint); its mirror, `data.nap.imet.gr`,
hangs at the TLS handshake stage and never completes a connection.

**Why this isn't built as a client:** there is nothing published to
build against — no roadworks dataset exists in the one place Greece's
own EU-recognised data offering would carry it. Even a best-case future
(a toll operator publishing its own roadworks feed) would only ever be
motorway-concession-only, fragmented per operator — not a genuine
national source.

**What would change this:** a genuinely documented roadworks or DATEX II
Situation dataset appearing on the Greek NAP once it's reachable again,
or a toll operator (Attiki Odos, Egnatia Odos, or the wider Hellastron
network) publishing its own roadworks/closures feed independently of the
NAP.

**What to report back:** if you know of a documented roadworks source
for Greece (national or toll-operator, current or once the NAP is back
up), please share it — that would let this scaffold graduate into a
real adapter, and would make Greece this SDK's first Greek coverage.

See `src/streetworks/greece/client.py`'s module docstring for the full
detail behind each claim above.
