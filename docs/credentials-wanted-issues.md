# "Credentials wanted" GitHub issues — drafted text

Draft text for four `help wanted` issues, one per provider in the
[README's Credentials wanted section](../README.md#credentials-wanted).
None of these have been opened yet — this file is the text to paste in when
opening them (or to point someone at ahead of time). All four modules'
import-time `UserWarning` and the README table link to
`https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22`,
which will surface these once opened with the `help wanted` label.

Suggested labels for all four: `help wanted`, `credentials-wanted`.

---

## Issue: Statens vegvesen (Norway) — confirm the DATEX adapter against real data

**Title:** `Credentials wanted: verify streetworks.datex2.vegvesen against real Norwegian data`

**Body:**

`streetworks.datex2.vegvesen` is a Phase 1 scaffold: built against Statens
vegvesen's own WSDL/service catalogue (confirmed live, credential-free) and
validated on a structurally-identical real DATEX II v3 snapshotPull
response from Iceland's IRCA service — but no real Norwegian
`GetSituation` response has ever been seen.

**Confirmed:**
- Endpoint (`datex-server-get-v3-1.atlas.vegvesen.no`), the `GetSituation`
  operation, both SOAP and REST-style paths.
- Auth challenge shape (`401` with both Basic and Bearer `WWW-Authenticate`
  headers).
- The parser-reuse hypothesis works on a real, structurally-identical
  document (Iceland's).

**Pending:**
1. Which DATEX version your credentials actually serve — the WSDL says
   v3.1, but data.norge.no's own catalogue still lists Statens vegvesen's
   DATEX offering as v2.0 with legacy services in parallel.
2. Whether the shared parser handles a real Norwegian response unchanged.
3. What location-referencing method real Norwegian records use
   (`pointCoordinates`, NVDB linear refs, Alert-C, or a mix).

**Credential needed:** username + password (HTTP Basic) or a Bearer token —
unconfirmed which Statens vegvesen actually issues. Free; [request
access](https://www.vegvesen.no/en/fag/technology/open-data/a-selection-of-open-data/what-is-datex/get-access/)
to the "Road traffic information" publication.

**What to report back:** run `python scripts/smoke_test.py` with
`VEGVESEN_USERNAME`/`VEGVESEN_PASSWORD` (or `VEGVESEN_TOKEN`) set, paste the
result line, and — ideally — one real trimmed `situation`/`situationRecord`
(with anything sensitive stripped) so the fixture can be swapped for real
data and the three open questions above closed out.

See `src/streetworks/datex2/vegvesen.py`'s module docstring for the full
detail behind each claim above.

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

## Issue: TfNSW Live Traffic (New South Wales) — confirm the adapter against real data

**Title:** `Credentials wanted: verify streetworks.au.nsw against real NSW data`

**Body:**

`streetworks.au.nsw` is a Phase 1 scaffold: built directly from Transport
for NSW's own "Live Traffic NSW Developer Guide" (read in full, not
summarised) plus a live, credential-free probe of the real endpoint — but
no authenticated response has ever been seen. This SDK's first Australian
provider — there is no national statutory works register in Australia
(unlike the UK's Street Manager), so this is a state traffic-disruption
feed, roadworks alongside incidents/fires/floods/other hazards.

**Confirmed:**
- The endpoint, live: a bare request returns a genuine structured `401`
  from a real API gateway (`Layer7-API-Gateway`), not a generic error page.
- The full GeoJSON schema, directly from the guide's own tables (not
  inferred): `FeatureCollection` → `Feature` → `properties`, the semantic
  0/-1 "no data" sentinel on `expectedDelay`, and the guide's own
  "disregard empty/null properties" rule.
- The test fixture is **one real feature**, transcribed verbatim from the
  guide itself (id `82681`, "Nelligen Bridge replacement project") — not
  synthetic.

**Pending:**
1. **The exact `Authorization` header format** — the 42-page guide never
   states it anywhere (searched the full text directly). This scaffold
   defaults to `apikey <key>` (the convention used by other TfNSW Open
   Data APIs, not confirmed for this one) — override via
   `NswLiveTrafficClient(header_format="Bearer {key}")` if that's wrong.
2. Whether the real endpoint filenames are `roadwork-open.json`-style
   (this scaffold's choice, per the guide's own Table 1) or
   `roadwork/open`-style (an earlier investigation's paraphrase) — a 404
   vs real data will settle it immediately.
3. Whether the main `roadwork` layer includes council/local-road works,
   or whether those are siloed in the separate `regional-lga-*` layers
   this scaffold doesn't fetch.
4. Real coverage of `encodedPolylines` (the one real sample has none) —
   the polyline decoder is written to the standard published algorithm
   but has never decoded a real TfNSW value.

**Credential needed:** an API key from free self-service registration on
the [TfNSW API Gateway](https://opendata.transport.nsw.gov.au/).

**What to report back:** run `python scripts/smoke_test.py` with
`NSW_LIVETRAFFIC_API_KEY` set, paste the result line, confirm which
`Authorization` header format actually worked, and — ideally — one real
trimmed feature (anything sensitive stripped) so the open questions above
can be closed out.

See `src/streetworks/au/nsw.py`'s module docstring for the full detail
behind each claim above.
