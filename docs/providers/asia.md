# Asia

Singapore was this SDK's first Asian territory (Credentials wanted); Hong
Kong is its first *confirmed live* one. See
[`docs/providers/index.md`](index.md) for the authoritative
live/verified status table.

- [Hong Kong (Transport Department / Highways Department) — Confirmed live](#hong-kong-transport-department--highways-department--confirmed-live)
- [LTA DataMall (Singapore) — Credentials wanted](#lta-datamall-singapore--credentials-wanted)
- [Korea Expressway Corporation (South Korea) — Credentials wanted](#korea-expressway-corporation-south-korea--credentials-wanted)

## Hong Kong (Transport Department / Highways Department) — Confirmed live

Hong Kong's Transport Department, in cooperation with Highways Department,
publishes a genuinely keyless JSON/GeoJSON feed of real-time roadworks
information — this SDK's first *confirmed live* Asian territory (Singapore
and South Korea are both still Credentials wanted, below). Found while
checking whether more Asian roadworks gaps existed beyond Singapore and
Korea.

```python
from streetworks.hongkong import HongKongClient
from streetworks.common import from_hongkong

with HongKongClient() as client:  # doctest: +SKIP
    works = from_hongkong(list(client.iter_roadworks()))
```

**Confirmed live 2026-08-24** against a real, unauthenticated pull (8 real
records at time of writing), matching the Transport Department's own
published data specification (`roadworks_location_data_specification.pdf`,
version 1.02, May 2026) field-for-field.

**Genuinely keyless — no app key, no registration, nothing.** Unlike most
feeds in this SDK, there isn't even an optional rate-limit-courtesy key
like TfL's or Socrata's — the resource URL is a plain public JSON file:
`https://resource.data.one.gov.hk/td/roadworks-location/get_all_the_roadworks.json`
(a sibling GeoJSON resource carries the identical fields wrapped in `Point`
features).

**Real scope, stated explicitly, not inferred**: Highways Department's own
roadworks "involving lane closure on public roads with a speed limit of
70km/hr or above" — Hong Kong's strategic/expressway-grade network, the
same honestly-narrower-than-comprehensive shape as ASFINAG/TfL in this
SDK. The feed only ever holds roadworks that are genuinely in progress or
"under preparation" (due to start within 12 hours) — not a forward-looking
schedule.

**`worksstatus` has exactly two real documented values** — `"Under
Preparation"` and `"In Progress"` — confirmed by the spec, not just
observed. Every one of the 8 real live records checked was `"In
Progress"`; `"Under Preparation"` is real and documented but wasn't
observed live in this pull, checked explicitly rather than assumed
absent. `"In Progress"` drives real `VERIFIED` date-confidence grading
(`actual_start`/`actual_end` populated); the not-yet-observed
`"Under Preparation"` would grade `ESTIMATED` (`proposed_start`/
`proposed_end` only).

**Every text field is real and trilingual** — English (bare field name),
Traditional Chinese (`_tc`), and Simplified Chinese (`_sc`) variants of
`datasource`/`workstype`/`district`/`roadname`/`locdesc`/`bound`/`lane`/
`remark`/`worksstatus`/`disclaimer` are all populated on every real
record. Only English is promoted by `from_hongkong`; the Chinese variants
stay on `.raw`.

**Geometry**: real WGS84 `latitude`/`longitude` fields directly on each
record (the spec states this explicitly) — no GeoJSON unwrapping or
coordinate-order flip needed, unlike Brussels/TfL.

**Licence: DATA.GOV.HK's portal-wide terms**, confirmed live (no
per-dataset licence is stated on the dataset's own catalogue page) — free
for commercial and non-commercial use, but **attribution is required**:
*"you shall identify clearly the source of the Data and acknowledge the
Government and the Relevant Organisations' ownership of the intellectual
property rights in the Data."*

**What's still open**: whether `"Under Preparation"` ever actually
appears live (worth re-checking); whether `remark` is ever populated in
practice (empty on every real record checked so far); real record volumes
over time (only 8 seen at time of writing, "ad hoc" update frequency
stated in the spec).

## LTA DataMall (Singapore) — Credentials wanted

Singapore's Land Transport Authority runs a real, well-documented national
open-data platform, LTA DataMall. Found while asking whether any more
country-level roadworks gaps existed beyond Europe — see
[`docs/roadmap.md`](../roadmap.md) and
[`docs/findings/europe-gaps.md`](../findings/europe-gaps.md) for the wider
survey this sits alongside.

```python
from streetworks.singapore import SingaporeClient
from streetworks.common import from_singapore

with SingaporeClient(account_key=account_key) as client:  # doctest: +SKIP
    works_list = from_singapore(list(client.iter_roadworks()))
```

**Better-confirmed than most Credentials-wanted scaffolds in this SDK.**
Built entirely from LTA's own current, official documentation — the "LTA
DataMall API User Guide & Documentation", Version 6.9 (3 Aug 2026), fetched
live — and the auth mechanism itself was confirmed live, not just
documented: a `GET` with a placeholder `AccountKey` header returns a real
`401` on both real endpoints (`RoadWorks`, `TrafficIncidents`), not a `404`
— confirming the real paths and the real header name, short of a real
authenticated response.

**Three real, genuinely different-shaped datasets, not one:**

- **`RoadWorks`** ("Approved Road Works") — road works currently
  approved/being carried out. Real fields: `EventID`, `StartDate`,
  `EndDate` (`YYYY-MM-DD`), `SvcDept` (the department or company performing
  the work — a real applicant-style field, the same role Vienna's/NYC
  DOT's own applicant fields already play in this SDK, mapped to
  `Works.promoter`), `RoadName`, `Other` (free text). **No coordinates at
  all** — a real, documented gap. Updated every 24 hours.
- **`RoadOpenings`** ("Planned Road Openings") — the identical real field
  shape, a genuinely separate dataset (new-road-opening events, not
  works-in-progress). Also no coordinates, also 24-hour updates.
- **`TrafficIncidents`** — a live, 2-minute-update feed of current road
  incidents, a genuinely different shape again: `Type` (a real, explicit
  13-value enum — `Accident`, **`Roadwork`**, `Vehicle breakdown`,
  `Weather`, `Obstacle`, `Road Block`, `Heavy Traffic`, `Miscellaneous`,
  `Diversion`, `Unattended Vehicle`, `Fire`, `Plant Failure`, `Reverse
  Flow`), `Latitude`/`Longitude` (real point coordinates, unlike the other
  two datasets), and `Message` (free text). **No id field and no dates at
  all** — a real gap in the opposite direction from `RoadWorks`/
  `RoadOpenings`. `Type == "Roadwork"` is the real, spec-stated roadworks
  filter for this dataset.

`SingaporeClient.iter_roadworks()` combines all three: every real
`RoadWorks`/`RoadOpenings` record, plus `TrafficIncidents` filtered to
`Type == "Roadwork"`.

**Pagination**: real OData envelope, `{"odata.metadata": ..., "value":
[...]}`, capped at 500 records per call — documented explicitly: append
`?$skip=500`/`$skip=1000`/... for subsequent pages. The client loops until
a page comes back short of 500 records.

**Licence: Singapore Open Data Licence v1.0** — confirmed via LTA's own
published licence page: worldwide, perpetual, royalty-free, non-exclusive,
commercial use explicitly permitted. Rate limit 10,000,000 calls/day (LTA's
own stated API Terms of Service figure).

**Credentials**: free self-service registration ("Request for API Access"
on [datamall.lta.gov.sg](https://datamall.lta.gov.sg/content/datamall/en.html))
issues a single `AccountKey` header value — not a formal contract, but not
obtained on the user's behalf either. Env var: `SINGAPORE_LTA_ACCOUNT_KEY`.

**What's still open until a real key is used**: whether the
empty/short-page pagination end-condition is correct in practice; whether
`SvcDept`/`Other`/`Message` ever carry structured data beyond free text;
real record volumes for `RoadWorks`/`RoadOpenings`. Have a key? Running
`scripts/smoke_test.py` and reporting back one real trimmed record from
each dataset would confirm this adapter — see the "help wanted" issues at
<https://github.com/KFergusonUK/StreetWorks-SDK/issues>.

## Korea Expressway Corporation (South Korea) — Credentials wanted

South Korea's national Public Data Portal (data.go.kr, 공공데이터포털) hosts
a real dataset published by Korea Expressway Corporation (한국도로공사):
"고속도로 공사현황" ("Expressway Construction Status"), dataset id
`15076874`. Found the same way as Singapore — checking whether more
country-level roadworks gaps existed in Asia.

```python
from streetworks.korea import KoreaClient

with KoreaClient(  # doctest: +SKIP
    base_url=base_url, service_key=service_key,
) as client:
    records = list(client.iter_items())
```

**At or below ASFINAG's own tier — genuinely less confirmed than most
Credentials-wanted scaffolds in this SDK.** Confirmed live from the
dataset's own public listing page (both the Korean page and its English
mirror) and its embedded schema.org JSON-LD metadata block: real field
descriptions, a real open licence, and a real self-service registration
process. But unlike Croatia (whose real pull URL is public) or even
Vejdirektoratet (whose URL is issued at registration alongside a stated
auth scheme), **data.go.kr's own convention only reveals a dataset's
real request URL once a service key has actually been applied for and
approved** — the listing page confirms the service exists, but not
where to call it. **The real field key names are unconfirmed too** —
the dataset names its fields only in human-readable Korean, not the
actual JSON/XML parameter keys a real response would use — so, unlike
every other scaffold in this SDK, no `from_korea` converter has been
built yet; `KoreaClient.iter_items()` only gets a caller as far as raw
response items.

**Real fields (Korean descriptions, not yet mapped to real API keys)**:
노선명 (route name), 구간명 (section name), 사업 명칭 (project name),
공사연장 (construction extension/length), 공사기간 (construction period),
준공날짜 (completion date), 공사 시작·종점 주소 (construction start/end
point address), 준공 및 시공 구분 (completion/construction classification),
사업단 정보 (project team/business-unit information). Format: JSON+XML
(both stated as supported).

**Licence**: `이용허락범위 제한 없음` ("no restriction on scope of use") —
confirmed identically on both the public listing page and its embedded
schema.org `license` field. Free of charge.

**Registration**: free self-service via data.go.kr's own "Apply for Use"
flow (Project Service Key / Personal Service Key) — the dataset's own
review-type metadata states *"Development Stage: Auto Approval /
Production Stage: Manual Review"*, i.e. a development-tier key is
expected to be near-instant. The real pull URL and a real `serviceKey`
are expected to be issued together once approved — neither was obtained
on the user's behalf. Env vars: `KOREA_BASE_URL`/`KOREA_SERVICE_KEY`.

**What was checked and ruled out while looking for the real URL directly**:
Korea Expressway Corporation's own dedicated documentation portal
(`data.ex.co.kr`), which very likely states the real path, is completely
unreachable from this build environment — DNS resolved fine, but the TCP
connection timed out with no response, a real environment-specific block
rather than a dead site (the same class of miss as Czech Republic's
`dopravniinfo.cz`, see [`docs/findings/europe-gaps.md`](../findings/europe-gaps.md)).
Three plausible paths were also tried directly against the real API
gateway (`apis.data.go.kr`) — `B552061/ConstructionInfo/getConstructionInfo`,
`B552061/ExConstructionInfoService/getConstructionInfo`,
`B552061/rest/construction/list` — each returned a genuine, structured
`NO_OPENAPI_SERVICE_ERROR` XML response, confirming the gateway host and
its `serviceKey` query-parameter convention are real, but none of these
specific guesses were the right path.

**`iter_items()`** reads the standard data.go.kr response envelope
(`response > body > items > item`, `numOfRows`/`pageNo`/`totalCount`
pagination) defensively — this is a platform-wide convention used by
most OpenAPI services on data.go.kr, **not confirmed for this specific
dataset**, since no real response has ever been seen. It yields nothing
rather than raising if a real response doesn't match.

**What's still open until a real key is used**: the real pull URL itself;
the real JSON/XML field key names behind each of the nine fields
described above (needed before `from_korea` can be written); whether the
assumed response envelope is actually correct; whether any real
coordinate field exists beyond the described free-text start/end
addresses. Have a data.go.kr service key for dataset `15076874`
(`한국도로공사_고속도로 공사현황`)? Running `scripts/smoke_test.py` and
reporting back the real pull URL, one real trimmed record, and the real
field key names would be the single most useful contribution — see the
"help wanted" issues at
<https://github.com/KFergusonUK/StreetWorks-SDK/issues>.
