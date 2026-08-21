# Canada

> New content, not a migration — Canada wasn't a built provider at the
> time of the phase-one docs migration (see `docs/providers/pending.md`,
> which this section now supersedes for DriveBC specifically — Quebec
> City's WZDx coverage and the rest of the Canadian landscape remain
> pending as described there).

## DriveBC (British Columbia, Open511)

British Columbia's own implementation of Open511, a Canadian-origin
multi-jurisdiction road-events standard — this SDK's first dedicated
Canadian roadworks provider:

```python
from streetworks.drivebc import DriveBCClient
from streetworks.common import from_drivebc

with DriveBCClient() as drivebc:
    events = list(drivebc.iter_roadworks())  # event_type == "CONSTRUCTION" only
works = from_drivebc(events)
```

**Bespoke, not a general `streetworks.open511` parser.** The
initial reasoning for a shared parser was sound in principle — Open511 is a real multi-jurisdiction
standard, the same shape that made a shared WZDx parser worthwhile — but
checked live before committing: DriveBC is the only real, confirmed
roadworks-events Open511 implementation found. San Francisco Bay Area
511's own Open511 use is *transit* data, a different resource entirely,
not a second roadworks-events consumer. Per this SDK's own "extract
shared code only on the second real consumer" pattern — the same
reasoning that kept Paris Chantiers bespoke rather than forcing a
premature `streetworks.opendatasoft` — this ships as
`streetworks.drivebc`. It's genuinely Open511-shaped internally, so a
real second jurisdiction could still prompt extracting a shared parser
later, but nothing was pre-abstracted from one data point.

**Endpoint and pagination**: keyless `GET` on
`https://api.open511.gov.bc.ca/events`, confirmed live (246 real events
at investigation time). `limit`/`offset` pagination, max `limit=500`
(confirmed via the API's own structured error on an over-large request),
no `next_url` — `DriveBCClient.iter_events()` loops `offset` until a
short page, per the API's own documented pattern.

**Roadworks filter: `event_type == "CONSTRUCTION"`** — confirmed live,
194/246 real events. `INCIDENT` (38), `ROAD_CONDITION` (12) and
`WEATHER_CONDITION` (2) are excluded.

**Two real, mutually-exclusive schedule shapes — a genuine finding
beyond the original plan.** 222/246 real events state
`schedule.intervals` (ISO-8601 time-interval strings, closed
`"2026-05-07T04:00/2026-11-25T21:00"` or open-ended
`"2022-12-07T20:19/"`); the other 24 state `schedule.recurring_schedules`
instead — a day-of-week list plus a daily start/end time plus an overall
date range, a weekday work-window shape `intervals` can't express. No
event carries both or neither. `from_drivebc` reconciles both into one
`WorksSite` window each — see `streetworks/common/from_drivebc.py`'s own
docstring for exactly how.

**Interval date-times carry no UTC offset** (unlike the top-level
`created`/`updated` fields, which do). The jurisdiction resource states
`"timezone": "America/Vancouver"`, so these are almost certainly local BC
time — but that's an inference, not something the interval strings
themselves state, so they're parsed naive rather than a timezone being
silently attached.

**Geometry: real GeoJSON, `Point` or `LineString`, WGS84** — 160
`LineString` / 86 `Point` confirmed live, no reprojection question.

**`roads[]` is free-text — no join key.** `name`/`from`/`to`/`direction`,
confirmed no road-network identifier anywhere; `street_ref` stays
unpopulated, the same discipline as every other name-only provider in
this SDK.

**Network scope: `strategic`** — every real event's `areas[]` names one
of BC MoTI's own internal administrative Districts (Lower Mainland,
Vancouver Island, Cariboo, ...), never a municipality, and the
jurisdiction resource itself self-describes as "highways managed by the
Government of British Columbia." One real nuance flagged rather than
smoothed over: `roads[].name` is `"Other Roads"` on 67/246 real events,
including real unnumbered local-sounding names (`"Main Street"`,
`"Horse Lake Road"`) — still organised entirely under BC MoTI's own
Districts in every case checked, not confirmed to ever cross into
municipal territory, but the road names alone don't rule it out either.

**Licence: Open Government Licence — British Columbia (OGL-BC),
confirmed live from the API's own `/help` page** — *"Use of the
Information provided by this API is governed by the [OGL-BC]"* — a
worldwide, royalty-free, perpetual, non-exclusive licence, commercial use
permitted, attribution required (default text: *"Contains information
licensed under the Open Government Licence – British Columbia."*). The
jurisdiction resource's own `license_url` field (a `data.gov.bc.ca` PDF
path) is dead — confirmed to 404-redirect to a generic catalogue landing
page — so this cites the real, live OGL-BC text instead, not that stale
pointer.

## Québec (MTQ Travaux routiers)

This SDK's first Canadian **provincial** roadworks provider — the
Ministère des Transports et de la Mobilité durable's (MTQ) own "Travaux
routiers" feed, found via Données Québec (the provincial open-data
portal), over a plain WFS 2.0.0 (MapServer) deployment:

```python
from streetworks.quebec import QuebecClient
from streetworks.common import from_quebec

with QuebecClient() as quebec:
    works_list = from_quebec(list(quebec.iter_roadworks()))
```

**Not the same thing as Quebec City's own separate WZDx feed** — that's
a distinct real municipal authority/platform, already covered via
`streetworks.wzdx`'s registry-driven discovery, never deduplicated
against this provincial one. Both are real, both stay separate.

**Built over the exact same generic `streetworks.ogc.client.OGCFeaturesClient`
this SDK's German state cluster and `streetworks.lyon` already use** — no
new fetch/pagination code needed. **526 real features**, confirmed live
via the WFS's own `numberMatched`. `identifiantChantier` genuinely groups
multiple real entraves (obstructions) into one project — 391 distinct
chantiers across the 526 records, 71 with 2–5 real entraves each — the
same shape Jersey's own `PROJID`/`JOBID` gives; `from_quebec` groups
into one `Works` per chantier, one `WorksSite` per entrave.

**A genuinely bilingual official source** — `descriptionFrancais` and
`descriptionAnglais` are both real, separately MTQ-published fields, not
one derived from the other. French is used as the canonical
`location_description`/`traffic_management` text; the English pair stays
on `.raw` only, not dropped.

**No independent verified/status flag exists**, so `date_confidence` is
uniformly `ESTIMATED` — the same reasoning `streetworks.drivebc` already
documents for its own comparable live "currently causing disruption"
feed. `works_type`/`status` come from `identificationDesTravaux` (the
real work title, e.g. *"Construction pont temporaire"*) and `entraveType`
(a real, clean 6-value severity/schedule enum) respectively — the same
role split `from_lyon` gives its own `nomchantier`/`typeperturbation`
pair.

**Geometry is real `LineString`, genuine WGS84** — the client's default
WFS request shape (`TYPENAMES`/`OUTPUTFORMAT=application/geo+json`)
works unchanged against this service, even though the dataset's own
published example URL uses the older `outputformat=geojson` bare-name
form instead.

**Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)**,
confirmed live via Données Québec's own dataset metadata.

## North American 511 platform (Ontario, Alberta, Saskatchewan, New Brunswick, Newfoundland and Labrador, Nova Scotia, Yukon)

One commercial REST API shape, confirmed live to be reused
byte-for-byte identically by **seven** independent government agencies —
Ontario 511, 511 Alberta, Saskatchewan's Highway Hotline, New Brunswick
511, 511 Newfoundland and Labrador, Nova Scotia 511 and 511 Yukon all
publish the exact same `/api/v2/get/event` endpoint (every one answers
the identical URL path with either real data or the identical structured
"Invalid Key" rejection), same field names, same `EventType` enum.
Nevada's own US 511 API shares the identical `/developers/doc`
documentation URL convention too (see [`docs/providers/us.md`](us.md)),
though it wasn't independently confirmed to be the same platform.
Manitoba, Prince Edward Island, the Northwest Territories and Nunavut
were checked and found to have no matching site.

```python
from streetworks.na511 import NA511Client
from streetworks.na511.jurisdictions import ONTARIO
from streetworks.common import from_na511

with NA511Client() as client:
    works_list = from_na511(
        client.fetch("ontario"),
        territory=ONTARIO.territory,
        administrative_area=ONTARIO.administrative_area,
    )
```

**Ontario 511 is real, live, keyless, and fully shipped** — confirmed
live 2026-08-21 (590 real roadwork events of 595 total), despite the
site's own "Sign up for an account" prompt, which turns out to gate only
human-facing My511 personalisation, not the API itself. A plain `GET`
with no `key` parameter at all returns real data.

**Every other jurisdiction confirmed here requires a real developer
key** — confirmed live via each host's own structured rejection
(`{"Error":{"Message":"Invalid Key"}}`) on the identical endpoint with no
key supplied, and Alberta's own docs explicitly state `key: Developer
Key, Required`. This SDK does not register for that key on a caller's
behalf (the same standing rule as Massachusetts's CWZ feed — see
[`docs/providers/us.md`](us.md#wzdx-us-work-zone-data-exchange)) — but
unlike a typical "Credentials wanted" scaffold, the schema itself isn't
a guess: it's proven correct by Ontario's own real, live, unauthenticated
response, cross-checked field-for-field against Alberta's own published
docs. `ab511`/`nb511`/`nl511` have real, working self-service signup
pages confirmed live (`ALBERTA_511_API_KEY`/`NEW_BRUNSWICK_511_API_KEY`/
`NEWFOUNDLAND_511_API_KEY` — see `.env.example`) — set one to confirm
the last open question, that the jurisdiction's own authenticated
response round-trips through the identical parsing unchanged.

**Saskatchewan's and Nova Scotia's own public signup paths have since
been taken down** — confirmed live 2026-08-21 (a few days after the
Saskatchewan endpoint itself was first confirmed key-gated):
`/developers/doc` 404s and `/developers` redirects to `/notfound` on
both sites, with no developer/API link found anywhere else on either.
The real API endpoints themselves are unaffected and still answer the
identical `Invalid Key` rejection, so `sk511`/`ns511` stay wired in
exactly as before — there's just no currently-known self-service route
to a real key for either, a genuine regression worth flagging rather
than leaving stale.

**One shared `NA511Client`, keyed by jurisdiction per call**
(`.fetch("ontario")`/`"alberta"`/`"saskatchewan"`/`"new_brunswick"`/
`"newfoundland_and_labrador"`/`"nova_scotia"`/`"yukon"`) — the same
shape `streetworks.ogc.germany.GermanRoadworksClient` already gives its
own `.fetch(state)`, since the real endpoint is identical across all
seven.

**`EventType == "roadwork"` is the real roadworks filter** (590/595 real
Ontario events; `"closures"` and `"accidentsAndIncidents"` are the other
two documented values). Real **Google Encoded Polyline** geometry is
present on ~50% of real roadwork events — decoded and confirmed correct
by checking a real sample's first/last points against that same record's
own separately-stated `Latitude`/`Longitude`/`LatitudeSecondary`/
`LongitudeSecondary` fields.

## National Road Network (NRN, streets gazetteer)

This SDK's first Canadian streets/gazetteer provider — Statistics
Canada / Natural Resources Canada's real, live, keyless ArcGIS REST
service, found via the same `open.canada.ca` catalogue-entry route that
gave IDEE Transportes its shape for Spain:

```python
from streetworks.arcgis.nrn import NrnClient, LAYER_IDS
from streetworks.common import from_nrn

toronto_bbox = (-79.40, 43.64, -79.38, 43.66)
layer = LAYER_IDS["local_roads"]["ON"]
with NrnClient() as nrn:
    segments = [from_nrn(f) for f in nrn.iter_roads(layer, bbox=toronto_bbox)]
```

**Segment only, same TIGERweb/NWB outcome — no separate named-street
entity exists in this REST service**, checked live, not assumed. **65
real, genuinely non-redundant layers** — 5 road-class tiers (Trans-Canada
Highway, National Highway System, Major Roads, Local Roads, Alleyways) ×
13 provinces/territories, confirmed live by comparing feature counts
(Alberta alone: 2,556 / 7,700 / 55,876 / 443,392 / 443,593 — five
genuinely different totals, not a cartographic-scale pyramid the way
TIGERweb's own layers 0–9 turned out to be). Real street names confirmed
live in downtown Toronto (`"Wellington Street West"`, `"Mccaul Street"`,
`"F G Gardiner Expressway"`) alongside a real `"Unknown"` placeholder
NRN itself uses for genuinely unrecorded names — treated as no name at
all, never carried through literally.

**No genuine per-segment identifier is exposed over this REST
service** (unlike the bulk GeoPackage/Shapefile product's own real `NID`
field) — `Segment.identifiers` stays empty on every real record.
**`administrative_area` uses the same shared-value-only discipline
`from_bdtopo` established** for its own real left/right commune split:
`l_placenam`/`r_placenam` genuinely diverge on segments that sit on a
real administrative boundary (confirmed live, a real Ontario segment
between "Township of MacDonald, Meredith and Aberdeen Additional" and
"Township of Laird") — a single field can't honestly state two
different real values, so this stays `None` rather than an arbitrary
pick.

**CRS**: the service's stated native reference is NAD83(CSRS) (`wkid
4140`/`4617`), but real `f=geojson` output comes back genuinely WGS84-
shaped regardless of `outSR` — confirmed live, the same real behaviour
TIGERweb's own service exhibits. Pagination and bounding-box filtering
both genuinely work (confirmed live against a 644,758-record Ontario
layer). Licence: **Open Government Licence – Canada**, stated directly
on the real `open.canada.ca` catalogue entry.

## The rest of the Canadian landscape

Not built yet — see [`docs/providers/pending.md`](pending.md) for what's
confirmed versus still unchecked:

- **Quebec City** — already covered, not a new build: a real, active
  WZDx feed already flows through `streetworks.wzdx`'s registry-driven
  discovery (`streetworks.common.from_wzdx()` already takes
  `territory`/`administrative_area` per feed rather than assuming
  `"USA"`, specifically because of this entry). See
  [`docs/providers/us.md`](us.md#wzdx-us-work-zone-data-exchange).
- **Ontario, Alberta, Saskatchewan, New Brunswick, Newfoundland and
  Labrador, Nova Scotia, Yukon** — already covered, not a new build: see
  [`streetworks.na511`](#north-american-511-platform-ontario-alberta-saskatchewan-new-brunswick-newfoundland-and-labrador-nova-scotia-yukon)
  above. That's 7 of Canada's 10 provinces plus 1 of 3 territories.
  Ontario is fully shipped and keyless; Alberta/New Brunswick/
  Newfoundland and Labrador are built and ready, waiting only on a real
  developer key someone with an account can supply;
  Saskatchewan/Nova Scotia are also built and ready but have no
  currently-known self-service route to a key at all (their own signup
  pages were taken down).
- **Manitoba** — Manitoba Transportation and Infrastructure's own Road
  Network is open data (ArcGIS REST), but no public real-time
  construction/closure API endpoint was found live this session — only
  an email-notification signup (`roadinfo@gov.mb.ca`). Not on the 511
  platform (no matching site found).
- **Prince Edward Island, Northwest Territories, Nunavut** — checked
  this session, no matching 511-platform site found (no DNS record for
  any plausible domain); PEI has a general open-data portal but nothing
  road-closure-specific confirmed.
- **Municipal portals** (Toronto, Montreal, Vancouver) — not checked
  this session.
