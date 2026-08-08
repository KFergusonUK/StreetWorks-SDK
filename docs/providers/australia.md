# Australia

> Migrated verbatim from README.md's `## Main Roads WA (ArcGIS REST)`,
> `## QLDTraffic Events (Queensland)`, `## Traffic SA / DIT Roadworks
> (South Australia) — Credentials wanted`, `## ACT & Tasmania — the AU
> tail, plus a documented Northern Territory`, and `## G-NAF & National
> Roads (Australia)` sections, plus the `streetworks.au` module-table
> entry covering NSW/Victoria (phase one, lossless restructure — see
> `docs/migration-mapping.md`).

`streetworks.au` is a per-state cluster (no national statutory register
exists, unlike Street Manager). Transport for NSW's Live Traffic Hazards
API (New South Wales roadwork + major-event hazards, GeoJSON) and DTP's
Planned Disruptions (Victoria, permit-derived, richer structured impact/
recurrence fields) — both confirmed 2026-07-30, see
[Recently confirmed](index.md#recently-confirmed) — plus Main Roads WA's
WebEOC Roadworks (Western Australia, ArcGIS REST, no credentials, shipped
live-verified with a real fixture), QLDTraffic Events (Queensland, TMR,
no credentials via a real shared public API key, one typed feed over
every `event_type`, confirmed live 2026-08-01), ACT's Temporary Traffic
Management (the only municipal/local-street AU coverage, no credentials,
CC BY-SA 4.0) and Tasmania's Roadworks - State Roads (the only AU
provider with real line geometry, no credentials, licence genuinely
unconfirmed); Traffic SA / DIT Roadworks (South Australia, ArcGIS
MapServer) is a **[Credentials wanted](index.md#credentials-wanted)**
scaffold, blocked on a token-gated query endpoint behind a geo-restricted
host. Road Report NT (Northern Territory) is registered as a documented,
honestly-unavailable scaffold — investigated and found to have no
published REST/GeoJSON API at all (its real backend is an undocumented
SignalR hub), so `RoadReportNtClient()` always raises
`ProviderUnavailableError` rather than pretending to work.

## Main Roads WA (ArcGIS REST)

The third `streetworks.au` member, and the third genuinely distinct AU
shape (NSW: one feed, many layers, one schema; Victoria: two independent
systems; WA: a single ArcGIS `FeatureServer` layer) — a thin wrapper over
the same `ArcGISFeatureClient` Jersey/TIGERweb already use, not a new
pagination implementation. **Credential-free, shipped live-verified with a
real fixture from day one** — unlike NSW/Victoria, this one never went
through a Credentials-wanted phase.

```python
from streetworks.au.wa import WaMainRoadsClient
from streetworks.common import from_au_wa_mainroads

with WaMainRoadsClient() as wa:
    works_list = from_au_wa_mainroads(list(wa.iter_roadworks()))
for works in works_list:
    print(works.reference, works.coordinate.value, works.sites[0].works_type)
```

**Two gating checks, both verified live before writing any mapping code.**
(1) *Is `outSR=4326` honoured?* Layer 2's native CRS is Web Mercator, and a
sibling ArcGIS deployment in this SDK (Jersey's) is confirmed to silently
ignore `outSR` entirely — so this couldn't be assumed. A live query
confirms WA's service **does** honour it (real WGS84-range coordinates
came back), but because GeoJSON strips any per-feature CRS statement, a
runtime coordinate guard is built anyway: any point outside plausible
degree range is treated as unreprojected Web Mercator metres and converted
via a small closed-form spherical-Mercator inverse — **not** `pyproj`
(the source brief's own suggestion), to avoid adding a heavy geospatial
dependency this SDK has deliberately avoided everywhere else (see
`streetworks/au/wa.py`'s own module docstring for the full reasoning). (2)
*Date format* — `DateStarte`/`EstimatedC`/`EntryDate` are plain strings; a
full live pull (227 real records) confirms `DD/MM/YYYY HH:MM:SS`
unambiguously (397 real values have a day > 12; zero have a month > 12).

**Real, undocumented findings from that same live pull**: `Road` states
the literal sentinel `"LOCAL ROAD"` (not a real road name) on 28/227
(~12.3%) records — `LocalRoadName` carries the real name in exactly those,
confirmed perfectly mutually exclusive; `network_scope` stays `UNKNOWN`
rather than promoted, since that minority is far larger than NSW's ~1.7%.
`WorkStatus` is a real field, confirmed **always empty** (0/227) — no live
signal exists to grade a site past `DateConfidence.ESTIMATED`. `WorkType`
carries a real fifth value, `"PTA Works"`, beyond the four the source's own
catalogue documents. Licensed **CC BY 4.0**, confirmed from the ArcGIS
item's own catalogue metadata (the layer's own `copyrightText` is empty —
attribution genuinely doesn't ride on the layer itself); `administrative_area`
is `"Main Roads Western Australia"`, the operator-as-authority rule already
applied to Autobahn GmbH/TfNSW/DTP.

## QLDTraffic Events (Queensland)

The fourth `streetworks.au` member, and the first with **no credential
wait at all** — TMR's own API specification publishes a real, globally-
shared public API key directly in plaintext, intended for exactly this
use (rate-limited 100 req/min, shared across every anonymous consumer of
the API worldwide — `streetworks.au.qld.QldTrafficClient` defaults to it,
so no registration is needed to try this one). **One adapter,
parameterised over `event_type`** — the NSW pattern, not Victoria's — but
with no server-side type filter at all, so `iter_roadworks()` filters the
single mixed feed client-side.

```python
from streetworks.au.qld import QldTrafficClient
from streetworks.common import from_au_qld_qldtraffic

with QldTrafficClient() as qld:
    works_list = from_au_qld_qldtraffic(qld.iter_roadworks())
for works in works_list:
    print(works.reference, works.administrative_area, works.coordinate.crs)
```

**Two real doc-vs-reality mismatches, confirmed live (2026-08-01, 458 real
events, 244 real Roadworks) — not implemented mechanically from the
spec's own text.** (1) The spec claims `geometry.type` is *always*
`GeometryCollection` — real data says otherwise: only 2.2% of features
actually are; the rest are a bare top-level `MultiLineString` or
`MultiPoint`, all three handled. (2) The spec's own `source_name` enum
lists exactly three values — real data has five, including two genuinely
undocumented ones (`Asignit`, `MBRC`), both real Queensland local-
government republishing routes, not interstate at all.

**Real coordinates are `EPSG:7844` (GDA2020), not WGS84** — confirmed live
on every single feature via its own embedded GeoJSON `crs` member, never
assumed or silently relabelled `EPSG:4326`.

**A deliberate, evidence-based departure from Victoria's own "prefer the
Point, drop the LineString" precedent.** 88.5% of real Roadworks events
have *no* Point at all — only a LineString. Dropping it the way Victoria's
converter does would leave the large majority of Queensland roadworks
with no geometry whatsoever, not the safe, lossless simplification it was
for Victoria (which always had a real Point standing in). A real span
check found the truth is genuinely mixed — median ~1.07 km (worksite-
scale) but a real ~9% tail running 20–133 km (Victoria-style corridor
extent) — so this module carries the LineString(s) through honestly as
the source's own stated "affected road extent" via `Coordinate.points`/
`parts`, rather than either fabricating false precision or discarding
real, mostly-precise data. See `streetworks/au/qld.py`'s own module
docstring for the full reasoning.

**`administrative_area` is per-record from `source.provided_by`, not a
single hardcoded operator** — a real, deliberate departure from every
other AU converter in this SDK. Confirmed live: 100% populated across 244
real Roadworks records, 17 distinct real values — the plurality is TMR,
but real, named values also include a private tollway operator
(Transurban) and 15 different Queensland local government/disaster-
management authorities. Genuinely richer and more accurate than one fixed
string, and exactly what `administrative_area` is documented to mean.

## Traffic SA / DIT Roadworks (South Australia) — Credentials wanted

The fifth `streetworks.au` member, over an ArcGIS **MapServer** (not WA's
FeatureServer), and the **least verified provider in this SDK** — see
[Credentials wanted](index.md#credentials-wanted). Blocked on **two
independent access gates**: the query endpoint returns a genuine HTTP 400
without an ArcGIS token (the layer *metadata* is public and was pulled
live — the schema below is ground truth, not documentation), and
`maps.sa.gov.au` separately CloudFront-blocks some countries' network
egress outright. Whether the token itself is self-service or requires a
data agreement with DIT is unresolved — the token-issuing host has never
been reached either. **No real feature has ever been retrieved.**

```python
from streetworks.au.sa import TrafficSaClient
from streetworks.common import from_au_sa_trafficsa

with TrafficSaClient(token=token) as sa:  # requires an ArcGIS token
    works_list = from_au_sa_trafficsa(list(sa.iter_roadworks()))
```

**The headline reason this provider matters, unconfirmed**: SA's real
field list (confirmed from the live layer metadata) states numeric road
identifiers — `ROAD_NO`, `GIS_LINK_ID` — not just names. Every other AU
provider built so far (NSW, Victoria, WA, QLD) is name-only, leaving the
stated-identifier join gap open; if `ROAD_NO` turns out to be South
Australia's Common Road Referencing System number and genuinely joins to
a road register, this would be the first AU provider to close that gap.
Until confirmed, `WorksSite.street_ref` deliberately stays unpopulated
from either field — this SDK doesn't wire unverified candidates into a
gazetteer join, the same discipline as a name-match. `iter_roadworks()`
also deliberately returns the layer's full, unfiltered `REC_TYPE` mix
(roadworks + incidents together) rather than guess at a filter value with
zero real evidence behind it. See `streetworks/au/sa.py`'s own module
docstring for the full detail, including the real (`START_DATE`/
`END_DATE` as proper Esri date fields, not WA's ambiguous strings) and
still-open (coverage: metro-Adelaide vs. statewide; `LATITUDE`/
`LONGITUDE` vs. the reprojected `SHAPE`) parts of the schema.

## ACT & Tasmania — the AU tail, plus a documented Northern Territory

Two more `streetworks.au` members, both confirmed live 2026-08-01,
credential-free, closing out the cluster's smaller jurisdictions.

```python
from streetworks.au.act import ActTtmClient
from streetworks.common import from_au_act_ttm

with ActTtmClient() as act:
    works_list = from_au_act_ttm(list(act.iter_roadworks()))

from streetworks.au.tas import TasRoadworksClient
from streetworks.common import from_au_tas_roadworks

with TasRoadworksClient() as tas:
    works_list = from_au_tas_roadworks(list(tas.iter_roadworks()))
```

**ACT (Temporary Traffic Management, Roads ACT) is the standout** — the
only AU provider with genuine **municipal/local-street** coverage. Every
other provider in this cluster, including the big five, only ever reaches
a state road authority's own network; the ACT has no separate
local-government tier at all, so Roads ACT's own feed *is* the whole real
road network. **A real correction to the source investigation**: this is
ArcGIS underneath, not a new Socrata client shape — dataACT's own Socrata
catalogue entry is confirmed live to be a plain link/pointer (`viewType`/
`displayType` both `"href"`, its SODA endpoint returns a real 400 for
"non-tabular dataset"), reachable to a real ArcGIS Online FeatureServer via
the catalogue item's own metadata. The "live vs. historical" gating
question is resolved live too: despite the underlying service literally
being named `Road_Closures_public_view_HISTORICAL`, a real pull returns
genuinely current 2026-dated closures — the service name isn't evidence,
the query result is. Real `type` values are confirmed directly (34/98
real records are `roadWorks`), so `iter_roadworks()` filters server-side
on real, evidenced criteria, unlike South Australia's still-unconfirmed
`REC_TYPE`. Licensed **CC BY-SA 4.0** — the only Share-Alike licence in
this AU cluster, distinct from everyone else's plain CC-BY.

**Tasmania (Roadworks - State Roads, Department of State Growth) is the
only AU provider with real line geometry** — every other member is
points-only. Genuinely tiny (10 real total records) and confirmed
single-type (`EVENT_TYPE=='Roadworks'` on 10/10, no incident mix). Its
native CRS, **GDA94/MGA zone 55**, is genuinely different from WA/SA's
Web Mercator — `outSR=4326` is confirmed honoured live, but this module
deliberately does **not** reuse WA/SA's closed-form Web Mercator
reprojection guard, since applying that formula to a different projection
would silently produce *wrong*, not just imprecise, coordinates if
`outSR` ever stopped being honoured; `scripts/smoke_test.py` carries a
plausible-range check instead, the same "fail loudly, don't guess"
discipline. **Licence is genuinely unconfirmed** — checked directly on
the ArcGIS item's own portal metadata (`licenseInfo`/`accessInformation`
both `null`), not inferred from Tasmania's LISTdata CC-BY norms the way
the source brief speculated (this service isn't even hosted on the LIST
portal). Shipped anyway on the same openly-queryable basis as
`streetworks.arcgis.jersey` — real data, real fixture, honest licence
caveat, not blocked the way SA is.

**The Northern Territory (Road Report NT) is registered as a documented,
honestly-unavailable scaffold** — `streetworks.au.nt`, `verified=False`,
on the board rather than silently missing, but genuinely not a working
client. Its real backend is not a REST/GeoJSON API at all:
reverse-engineering the site's own minified Angular bundle found a
genuine SignalR real-time hub connection (`roadsReportingHub`, invoking
hub methods like `GetAllMajorRoadObstructions`) — an undocumented,
materially different client protocol this SDK has never needed elsewhere,
on top of the source investigation's own already-flagged concerns
(roadworks is a minor subset of a road-condition system dominated by
closures/flooding, and the licence is unspecified). Rather than encode
that reverse-engineered hub as a stable contract, `RoadReportNtClient()`
always raises `streetworks.exceptions.ProviderUnavailableError`
immediately, with no network call — see
[Credentials wanted](index.md#credentials-wanted) for the fuller writeup,
and revisit if a documented REST equivalent ever surfaces.

## G-NAF & National Roads (Australia)

This SDK's first Australian gazetteer coverage — over the **Digital
Atlas of Australia** (`digital.atlas.gov.au`), a whole-of-government
ArcGIS Online platform, not Geoscape's own commercial G-NAF/Roads API.

```python
from streetworks.gnaf import GnafClient
from streetworks.common import from_gnaf_address, from_gnaf_road

with GnafClient() as gnaf:
    addresses = [from_gnaf_address(a) for a in gnaf.iter_addresses(where="STATE='ACT'")]
    roads = [from_gnaf_road(r) for r in gnaf.iter_roads(where="state='ACT'")]
```

**A real correction to the source investigation.** The brief that
started this build concluded Australia has "no clean national *open*
road-centreline register with identifiers" — true of Geoscape's own
commercial **Roads** API, which is what the brief checked. It missed a
separate, genuinely open publication route: the Digital Atlas
re-publishes both a G-NAF-derived address layer and a Geoscape
Roads-derived road network, both under **CC BY 4.0**, both live,
neither documented on the platform's own JS-rendered dataset pages —
found only by resolving each dataset's Digital Atlas item to its real
underlying `services-ap1.arcgis.com` `FeatureServer` URL. This
supersedes the brief's own fallback plan (SA's CRRS / Tasmania's State
Roads as state-scoped consolation prizes) — Australia now has a genuine
*national* road register, the same tier as New Zealand's LINZ.

**National Address Points (G-NAF derivative), confirmed live 2026-08-02
— 15,901,249 real addresses, credential-free.** Native SR EPSG:7844
(GDA2020), `outSR=4326` confirmed honoured live. The real stated
identifier is `ADDRESS_DETAIL_PID` (G-NAF's own PID) — but there's no
separate street/locality PID on this derivative, only text
(`STREET_NAME`/`STREET_TYPE`), the same "no street table of its own"
shape this SDK's own BAG route already has. A real `unit`/flat concept
(`FLAT_TYPE`+`FLAT_NUMBER`, e.g. `"SHOP"` + `83`) is present — confirmed
as the *second* built source with this gap, after LINZ's own `unit`
field; `Address`'s model docstring now documents both rather than the
single-source "no built source has" claim it carried before. Licence CC
BY 4.0, plus a genuine mandatory restriction: open G-NAF must not be
used to generate an address or address list for sending mail unless
each address is independently verified — irrelevant to gazetteer use,
stated here for completeness.

**National Roads (Geoscape Roads derivative), confirmed live 2026-08-02
— 4,346,217 real segments, credential-free, genuinely comprehensive.**
Real `hierarchy` values span the whole network, from `NATIONAL OR STATE
HIGHWAY` down through `LOCAL ROAD` (the largest single value),
`FOOTPATH` and `CYCLEPATH` — real local-road reach beyond even
TIGERweb's own local-road layer. The real stated identifier `road_id`
is segment-scoped, not an aggregated named-street id, and no separate
named-street layer exists alongside it, so this converter emits
`Segment` only, never `Street` — the same "no synthetic streets"
discipline `from_nwb` already established for the Netherlands. Real
per-segment attributes include `jurisdiction_control` (a genuine
per-record authority, e.g. `"Transport for New South Wales (controlled
roads)"`) and both `OPERATIONAL` and `PROPOSED` (not-yet-built) real
`status` values — `iter_roads()` returns the raw network unfiltered by
default, not a curated "built only" view. Licence CC BY 4.0, no extra
restriction.

**No stated join between addresses and roads — resolves the brief's
join question, on better evidence than it had.** Neither layer states a
reference to the other; the only possible link is a name match
(`STREET_NAME` against `full_street_name`), forbidden by this SDK's
stated-identifiers-only rule. So Australia's addresses and roads stand
alone from each other, the same conclusion already reached about the AU
roadworks cluster (no AU roadworks feed states a G-NAF/road identifier
either) — now settled for the gazetteer side too, on the real open
register rather than the commercial one the brief assumed was the only
option.
