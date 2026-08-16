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
- **Ontario 511** (`511on.ca`) — a different vendor-511 REST platform,
  not Open511. Checked live against the WZDx feed registry specifically
  to see whether it publishes WZDx (the near-free route, if so) — it
  doesn't appear in the registry at all, so a real WZDx feed for Ontario
  wasn't found. A bespoke build against its own REST API remains
  possible, not attempted this session.
- **Other provinces, and municipal portals** (Toronto, Montreal,
  Vancouver) — not checked this session.
