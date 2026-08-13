# Europe

> Migrated verbatim from README.md's `## DATEX II (European roadworks)`,
> `## Autobahn GmbH`, `## Via Lietuva (Lithuania)`, `## German state
> roadworks (OGC WFS)`, `## Berlin (VIZ)`, `## Consell de Mallorca (island
> roadworks)`, `## Servei Català de Trànsit (Catalonia)`, `## Basque
> Country (Euskadi)`, `## Base Adresse Nationale (BAN)`, `## Basisregistratie
> Adressen en Gebouwen (BAG)`, `## Kartverket (Norway)`, `## NVDB (Norway)`,
> `## NWB (Netherlands)`, `## BD TOPO (France)`, `## Paris Chantiers
> (Ville de Paris)`, `## Ireland — MapRoad Roadworks Licensing
> (documented, unavailable)`, and `## Greece (documented, unavailable)`
> sections, plus the
> `### European & Crown Dependency roadworks — separate strand` and
> `### International gazetteers — separate strand` roadmap subsections
> (phase one, lossless restructure — see `docs/migration-mapping.md`).
> Italy (CCISS) is documented separately in
> [`docs/providers/italy.md`](italy.md) per the proposed docs tree.

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
used by the UK providers.

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
way to `Coordinate.points` (see [`docs/concepts/data-model.md`](../concepts/data-model.md)).
`administrative_area` (the DIR region, e.g. `"DIR Sud-Ouest"`) is genuinely
stated but on a different, coarser field than the shared model's
`source_name` — `dir_regions()` reads it from each record's `.raw` XML
directly. Published under the **Licence Ouverte / Open Licence 2.0
(Etalab)** — see `streetworks/datex2/bisonfute.py`'s module docstring for
the attribution wording and full field-by-field mapping.

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
scope.

**Not state-roads-only, despite the name** — a later network-scope audit
(`docs/network-scope-audit.md`) found real road-number prefixes reach
several regional/provincial/insular authorities too (`CV-`/Comunidad
Valenciana, `M-`/Madrid, `Ma-`/`Me-`/the Balearic insular councils, ~10
checked live), never municipal streets — a genuine multi-authority
*interurban* aggregator, not a single national road authority's own
network. This also means DGT **overlaps with Consell de Mallorca**
(see below), not the disjoint "genuinely additive" picture first assumed
— see [Never deduplicate across providers](../concepts/data-model.md#never-deduplicate-across-providers).
Published under **Creative Commons Attribution (CC BY)** — see
`streetworks/datex2/dgt.py`'s module docstring for the attribution wording
and full field-by-field mapping.

**Belgium's Verkeerscentrum Vlaanderen** publishes real-time traffic
situations, including roadworks, credential-free as genuine DATEX II **v3**
— reused through the same shared parser, but this feed forced two real
changes to the *shared* code, not just this adapter:

```python
from streetworks.datex2.belgium import BelgiumClient, CRS
from streetworks.common import from_datex2

with BelgiumClient() as be:
    situations = list(be.iter_roadworks())
for situation in situations:
    works = from_datex2(
        situation, territory="Belgium", administrative_area="Flanders", crs=CRS,
    )
```

Verified against the live feed (2026-07, ~100 situations, 86 roadworks
records): a **second, differently-shaped discriminator gap** from Spain's —
of 86 real roadworks-relevant records, only 19 used the dedicated
`MaintenanceWorks` xsi:type; the other 67 were the generic
`RoadOrCarriagewayOrLaneManagement` record, discriminated only by
`roadOrCarriagewayOrLaneManagementType=newRoadworksLayout` (a real DATEX II
v3 standard value, not Belgium-specific) — added to
`SituationRecord.is_roadworks` additively, confirmed not to over-match the
61 other real records of that same xsi:type with genuinely different
values (`narrowLanes`, `roadClosed`, `contraflow`,
`singleAlternateLineTraffic`), which can arise from accidents or events,
not just works. More significantly: **every real coordinate in this feed is
Belgian Lambert 72 (`EPSG:31370`), not WGS84** — confirmed from the feed's
own `srsName` attribute and from the coordinate values themselves (the
source XML still calls the fields `<latitude>`/`<longitude>`, which is
genuinely misleading taken at face value). `from_datex2()` gained a `crs`
parameter (default `EPSG:4326`, true for every DATEX source checked before
this one) so Belgium's real CRS can be stated explicitly rather than
assumed — coordinates are carried through unconverted, per this SDK's
standing CRS policy (see [`docs/concepts/crs-and-datums.md`](../concepts/crs-and-datums.md)).
Coverage is **Flanders only** — confirmed live via
`supplierIdentification/nationalIdentifier` (`"BETICV"`) and the dataset's
own name; Wallonia publishes separately and isn't wrapped here. **No
permissive licence**: transportdata.be's own terms of use prohibit
distributing the data to third parties for commercial purposes — real
fixture data was judged too close to that restriction for this openly
redistributed SDK, so the test fixture is synthetic (real shape, invented
values), the same call already made for Autobahn GmbH's unconfirmed
licence. See `streetworks/datex2/belgium.py`'s module docstring for the
full verbatim licence text (French original + English translation) and
field-by-field mapping.

**Luxembourg's Ponts et Chaussées** (via CITA) publishes current roadworks
on the national road network credential-free, as genuine DATEX II **v2.3**
— the same version France uses:

```python
from streetworks.datex2.luxembourg import LuxembourgClient
from streetworks.common import from_datex2

with LuxembourgClient() as lu:
    situations = list(lu.iter_roadworks())
for situation in situations:
    works = from_datex2(situation, territory="Luxembourg")
```

Verified against the live feed (2026-07, ~110 situations, 161 roadworks
records): a clean result — every roadworks record uses the dedicated
`MaintenanceWorks` xsi:type (no `ConstructionWorks`, no discriminator
issue), 100% genuine WGS84 coordinate coverage, `source_name` always the
real `"PCH"` (Ponts et Chaussées's own initials), so `administrative_area`
needs no override. Two honest, real gaps confirmed against the live feed:
every record's comment is the identical placeholder text
`"Titre:Nouvelle tape"` (not a real per-site description), and
`validity.status` is always the literal `"definedByValidityTimeSpec"`,
never `"active"`/`"planned"`/`"suspended"` — so `date_confidence` comes out
`UNKNOWN` for every Luxembourg site even though the dates themselves are
real. Published under **CC0 1.0 Universal (Public Domain Dedication)** —
the least restricted licence of any DATEX adapter in this SDK; real
trimmed fixture data is used directly. See
`streetworks/datex2/luxembourg.py`'s module docstring for the full
field-by-field mapping.

**Bulgaria's Road Infrastructure Agency (LIMA)** publishes current roadworks
on the republican road network credential-free, as genuine DATEX II **v2.3**:

```python
from streetworks.datex2.bulgaria import BulgariaClient
from streetworks.common import from_datex2

with BulgariaClient() as bg:
    situations = list(bg.iter_roadworks())
for situation in situations:
    works = from_datex2(situation, territory="Bulgaria")
```

The NAP-listed host (`lima.api.bg`) is **unreachable** — connection refused,
consistently. The real working host is `datasheet.api.bg`, a separate public
download front for the same LIMA platform. That host doesn't serve roadworks
at a fixed URL either: each dataset's catalogue page links a same-day file
(`/files/YYYYMMDD_roadworks_r03.xml`), so `BulgariaClient.get_situations()` is
a two-step fetch — resolve today's real file link from the catalogue page,
then fetch it. LIMA's roadworks catalogue also splits into three separate
datasets ("Closed Roads"/r01, "Closed Roadways"/r02, "Short-term Road
Construction"/r03); checking real record IDs across all three confirmed r03
is a strict superset of the other two, so this adapter fetches r03 alone.
Verified against the live feed (2026-07, 150 real roadworks records, all
three categories): every record uses the bare `Roadworks` xsi:type directly
— a **third dedicated discriminator type**, distinct from both
`MaintenanceWorks`/`ConstructionWorks` and Belgium's generic-value case,
added to `ROADWORKS_TYPES` (confirmed zero drift across every other
adapter's real fixture data — see the live-regression check in
`streetworks/datex2/models.py`). The real file's own XML declaration claims
`encoding="UTF-16"`, but the actual bytes are UTF-8 — a genuine mislabelling
that a strict XML parser rejects outright; `get_situations()` corrects the
declaration before parsing. Every location states three real WGS84 points
per record (not one), of which the shared parser captures only the first, as
it does for every other point-kind location in this SDK. **Licence
unconfirmed**: no licence text exists on the reachable host, and the real
terms page sits behind the unreachable `lima.api.bg` — so, per the Autobahn
GmbH/Belgium precedent, the test fixture is synthetic (real confirmed shape,
invented values) rather than trimmed from a live pull. See
`streetworks/datex2/bulgaria.py`'s module docstring for the full
field-by-field mapping.

## Basque Country (Euskadi)

The Basque Country's road incidents, credential-free, fill the *other*
of DGT's two documented exclusions:

```python
from streetworks.datex2.euskadi import EuskadiClient, provinces
from streetworks.common import from_datex2

with EuskadiClient() as euskadi:
    situations = list(euskadi.iter_roadworks())
basque_provinces = provinces(situations)
for situation in situations:
    works = from_datex2(
        situation, territory="Spain",
        administrative_area=basque_provinces.get(situation.id),
    )
```

Published by the Basque Government's own traffic directorate on Spain's
national NAP, as genuine **DATEX II v1.0** — the oldest schema version in
this SDK (every other adapter targets v2.x/v3.x). Reusing the shared
parser worked out of the box for the roadworks classification itself
(`MaintenanceWorks`/`ConstructionWorks`, already in `ROADWORKS_TYPES`) —
but reading it carefully, per this SDK's "a pleasant surprise deserves a
second look" habit, surfaced one real, additive parser fix:

**`tpeglinearLocation` (lower-case), not `tpegLinearLocation`** — confirmed
by direct byte search of the real feed (74/74 real linear-location
records use the lower-case v1.0 spelling; zero use the v2/v3 PascalCase
one). Before the fix, the shared parser's two-point `from`/`to`
extraction never matched it, silently degrading a real 2-point line into
a single point via the generic fallback. Fixed as a second, fallback
lookup in `streetworks/datex2/parser.py` (v2/v3 spelling tried first, so
nothing else changes) — confirmed via a live before/after regression
across France, Spain, Belgium, Luxembourg and Bulgaria: identical
roadworks counts and multi-point-location counts, zero drift.

**Coordinate coverage is genuinely partial — the only Spanish/DATEX
adapter in this SDK where it isn't 100%.** Of 101 real roadworks records
checked live, 36 have a real 2+-point line, 6 a single point, and 59
state their location purely via Alert-C codes plus a road number and
distance along it (captured as `road_number`; the distance itself has no
canonical slot and stays in `.raw`) — no coordinates at all. Reported
honestly, not padded.

**`administrativeArea` — a real per-record province field**, exposed via
its own `provinces()` helper, the same pattern DGT's own uses. Real values
confirmed across all three Basque provinces (`GIPUZKOA`/`BIZKAIA`/`ARABA`,
genuinely inconsistent casing across records, kept as stated) plus a real
literal `"Desconocida"` ("unknown") placeholder — treated as unstated, not
a real province name. **Network scope: `multi_authority_interurban`**,
the same shape as DGT's and SCT's own real data (state roads plus all
three Diputación Foral networks). **CRS: WGS84, confirmed live** from
real point values.

**Licence: the publisher states "No licence - No contract" — literally,
not "unconfirmed."** This is more restrictive than an unconfirmed
licence, not less: absence of a licence means no permission has been
granted, since copyright is automatic and default-restrictive — a licence
is what *adds* permissions. **Never read this as "assumed open."**
Calling the public endpoint needs no licence, so the client is built
freely, but the test fixture is **synthetic** (real confirmed shape,
invented content) — committing real records into this openly-
redistributed, MIT-licensed repository would be redistribution, which
nothing here permits. This is Spanish public-sector information, and
Spain's own transposition of the EU PSI/open-data directive creates a
general presumption that public-sector information is reusable unless
stated otherwise, so it is *probably* reusable in practice — but
"probably, under PSI law" is not the same as "the publisher granted a
licence," and only the honest version belongs here. **Confirm your own
rights before relying on this commercially.** See
`streetworks/datex2/euskadi.py`'s module docstring for the full
field-by-field mapping.

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

## Via Lietuva (Lithuania)

Lithuania's national roadworks, via **the open data.gov.lt route, not the
RTTI NAP NAPCORE lists** — that listed NAP is agreement-gated and returns
403 without one. The open dataset ("Eismo ribojimai valstybinės reikšmės
keliuose" — traffic restrictions on state roads, provider Via Lietuva) is
published separately as CSV/JSON, licensed **CC BY 4.0**, credential-free.
It's CSV, not DATEX, so `streetworks.vialietuva` has its own small parser,
same shape of choice as Autobahn/WZDx:

```python
from streetworks.vialietuva import ViaLietuvaClient
from streetworks.common import from_vialietuva

with ViaLietuvaClient() as lt:
    repairs = lt.road_repairs()
works = from_vialietuva(repairs)
```

The dataset has **four** tables; only one is roadworks. Verified against
the live feed (2026-07): `Remontas` (road repairs, 9,762 real rows) is the
roadworks core, modelled here. `Kliutis` (obstacles) and `Renginys`
(events) were checked and are genuinely **not** roadworks — `Kliutis` is
real road-condition hazards ("Silpna, nelygi kelio danga" — weak, uneven
road surface), closer to an incident register than planned works;
`Renginys` is closures for organised events (car rally stages), not
construction/maintenance at all — neither is forced into `Works`, the
same call already made for UK Police. `KelioAtkarpa` (road sections) is
real reference data (road number, name, km range) with no
restriction/date/coordinate content — gazetteer-shaped, not roadworks;
confirmed live that every `RoadRepair.road_id` joins to a real
`KelioAtkarpa` row (886/886), exposed as `ViaLietuvaClient.road_sections()`
for callers who want it, the same auxiliary-lookup role `dir_regions()`/
`provinces()` play for Bison Futé/DGT.

**CRS — the important finding.** Coordinates are real Lithuanian national
grid, **LKS-94 (`EPSG:3346`)**, not WGS84 — the third non-WGS84 roadworks
provider in this SDK, after Belgium's Lambert 72. **The WKT axis order is
also reversed from the usual convention** — `POINT (6061836 567621)`
states `(Northing, Easting)`, not `(Easting, Northing)`, confirmed from
real value ranges (the first number is always in Lithuania's real northing
band, ~5,990,000–6,265,000; the second always in its real easting band,
~300,000–720,000). Carried through unconverted, both the CRS and the axis
order stated explicitly rather than assumed — see
`streetworks/common/from_vialietuva.py`'s module docstring.

A repair's full path (a real `MULTILINESTRING`, present on 6,984/9,762
real rows, 71.6%) is preferred when stated; the rest are point-only —
100% coordinate coverage either way. Two other honest findings confirmed
against the real feed: `koord_validacija` (coordinate-validated) is
`True` on every single row checked (9,762/9,762) — a real field, but not a
useful discriminator in practice — and 25/9,762 real rows (~0.26%) are
plainly test data (`aprasymas` literally `"test"`/`"testuojam;"` or
similar), structurally identical to a real row otherwise and not filtered
by the source. See `streetworks/vialietuva/models.py`'s module docstring
for the full field-by-field mapping.

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
open geodata is road *network* data (a `streets`-kind concern, the same
category as NWB below), not roadworks — its actual roadworks route is the
gated Mobilithek/DATEX path already out of scope elsewhere; Bavaria's
BAYSIS portal has no Baustellen (roadworks) layer at all.

**CRS is stated per state, never assumed — and Saxony breaks the
"always WGS84" pattern deliberately.** See
[`docs/concepts/crs-and-datums.md`](../concepts/crs-and-datums.md) for the
full detail.

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

## Berlin (VIZ)

The largest remaining German gap this cluster had — Berlin is a
city-state Land in its own right, entirely surrounded by the
already-covered Brandenburg. A genuinely different platform from the
Hamburg/Brandenburg/Saxony WFS/GeoJSON-download cluster above: two
public, keyless GeoJSON feeds published hourly by VIZ
(Verkehrsinformationszentrale), each its own plain static file, no
query language at all — the simplest client shape in this SDK. Its own
top-level module, `streetworks.berlin`, not a `streetworks.ogc.germany`
field-map entry.

```python
from streetworks.berlin import BerlinClient
from streetworks.common import from_berlin

with BerlinClient() as berlin:
    works_list = from_berlin(list(berlin.iter_roadworks()))
```

**Two feeds, and the source brief's assumption about them turned out
wrong once checked live.** The dataset's own official description says
Verkehrsredaktion (`daten/baustellen_sperrungen_viz.json`) is "a subset
of Landesmeldestelle (`tic3/baustellen_sperrungen_tic.json`) with extra
detail." Live data disagrees: using the real, verified join key (every
Verkehrsredaktion record's `lms_id` matches a Landesmeldestelle record's
own `id` when present — 199/205 confirmed live) and restricting both to
real roadworks `subtype` values (`Baustelle`/`Sperrung`/`Bauarbeiten`),
Landesmeldestelle has 215 such records, Verkehrsredaktion has 202, and
only **104 overlap**. Landesmeldestelle carries 111 real roadworks
records Verkehrsredaktion lacks entirely; Verkehrsredaktion carries 98
Landesmeldestelle lacks (35 of those with no `lms_id` at all — genuine
Verkehrsredaktion-only editorial entries, not just richer detail on
shared records). Neither feed alone is complete, so
`iter_roadworks()` **merges both via the verified join key** rather than
picking one as primary or duplicating the confirmed overlaps — for a
matched pair it prefers Verkehrsredaktion's richer fields (`severity`,
`direction`, lane counts, ISO dates) while keeping Landesmeldestelle's
own `id` as the canonical reference. Every merged record carries an
explicit `sources` list — never silently blended without provenance.

**Roadworks filter, evidenced not the source brief's assumed upstream
values.** The brief named `TrafficMessage_RoadWorks`/
`TrafficMessage_Incidents` as the upstream OCIT object types, but those
don't survive the OCIT→GeoJSON conversion — the real field on the
published output is `subtype`, with exactly three roadworks-relevant
values plus `Gefahr` (hazard/danger warning, excluded — a warning
notice, not a worksite, even though some `Gefahr` records' free text
happens to mention nearby construction).

**Two date formats depending on feed** — Verkehrsredaktion's are
near-ISO; Landesmeldestelle's are German `DD.MM.YYYY HH:MM` (sometimes
blank for the start date — a real, common case, not an edge case
invented for testing). Geometry is `Point`, or a real `GeometryCollection`
pairing a `Point` with one or more `LineString` entries — the first
`LineString`'s vertices map to `Coordinate.points`, the same contract
line-geometry sources elsewhere in this SDK already use, unlike Paris's
polygon-ring case which didn't fit it.

**No grouping** — unlike NYC/Chicago/Paris, no umbrella-application field
exists in either real feed, so `from_berlin` ships one `Works` with
exactly one `WorksSite` per record, the same 1:1 shape this SDK's own
Brandenburg entry uses for the same reason (a real but uncorroborated
grouping signal, not acted on without stronger evidence). `street_ref`
is never populated — no segment identifier field exists on either feed.
`source_grade="traveller_info"` — VIZ is a traffic-information/editorial
source, not a statutory register, distinct from this cluster's
`streetmanager`/`nycdot`/`chicagodot`/`paris` register-grade tier.
Licence: **Datenlizenz Deutschland — Namensnennung — Version 2.0**
(dl-de/by-2-0), the same licence Hamburg/Brandenburg already publish
under, confirmed from the real dataset page. Attribution: "Digitale
Plattform Stadtverkehr Berlin / [dataset title]".

## Consell de Mallorca (island roadworks)

Mallorca island-road works via the IDEmallorca GeoServer WFS — credential
-free, no citizen registration, reusing the same `OGCFeaturesClient` the
German states use. This is the *insular* layer beneath DGT — but
**overlapping, not disjoint, corrected from an earlier "genuinely
additive, not a duplicate" claim** (see
[`docs/network-scope-audit.md`](../network-scope-audit.md), the audit
that found this): DGT's own real data does reach Mallorca (`Ma-`/`Me-`
prefixed records, confirmed via a live road-number check, not assumed),
and 2 of DGT's Balearic records were checked directly against Consell de
Mallorca's own feed and matched almost exactly on road, km-range, and end
-date — republication of the same real works, not two authorities'
records for adjacent land (no independent reference field exists on
DGT's side to attribute it otherwise, and the matched geometry sits
within, not beside, the same work-zone span). Consell de Mallorca is
still by far the richer, more detailed, and larger source for the island
(16-17 current records vs. DGT's ~4-5), and DGT itself turns out to carry
real works for several other Spanish regional/provincial/insular
authorities too, not just its own state network (see DGT's own section
above) — so this remains a genuinely useful additional source, just not
a clean disjoint layer the way Germany's state-vs-national split is.
**Never deduplicate matches across the two** (or any two providers) — see
[Never deduplicate across providers](../concepts/data-model.md#never-deduplicate-across-providers):

```python
from streetworks.ogc.mallorca import MallorcaClient
from streetworks.common import from_mallorca

with MallorcaClient() as mallorca:
    icons = mallorca.fetch_roadworks_icons()  # tipoinc filtered - Obres/Manteniment
    trams = mallorca.fetch_trams()            # affected-segment lines, joined by codi
works = from_mallorca(icons, trams)
```

Built from a dedicated recon pass (`docs/idemallorca-investigation.md`),
then verified again while building. Two layers, joined by a shared `codi`:
`incidencies_icon` (one point per incident — type, dates, description,
road, direction) is the spine; `incidencies_tram` supplies the affected
road segment(s) as a real `MultiLineString` (one real record genuinely has
2 parts, not always a single-part wrapper). **The join isn't total** —
16/17 real icons in one live pull had a matching tram; one (a lane closure
on Ma-13) is point-only, handled honestly (a real `Coordinate`, `parts`
left `None`, never a fabricated line).

**A real, masked-failure format gotcha**, not a documentation gap: this
GeoServer genuinely rejects `OGCFeaturesClient`'s own default
`output_format="application/geo+json"` — but with **HTTP 200**, wrapping
an XML `InvalidParameterValue` exception body, not an error status. Every
call here passes `output_format="application/json"` explicitly instead
(a call-site override, not a change to the client's default), and
`MallorcaClient` validates the decoded payload really is a
`FeatureCollection` before returning it, as a second guard against exactly
this kind of quiet failure.

**CRS: ETRS89/UTM31N (`EPSG:25831`), confirmed live, not reprojected** —
the server *can* reproject to WGS84 server-side on request (tested,
genuinely correct), but per this SDK's standing CRS policy the native CRS
is requested and labelled instead, the same choice already made for
Belgium's Lambert 72 and Lithuania's LKS-94.

**Discriminator: `tipoinc`**, clean and explicit (`"Obres"`/
`"Manteniment"`/`"Altres"` — three real values in one live 17-incident
pull) — not the free-text-inference problem some sources have.
`fetch_roadworks_icons()` filters to the first two; the one real `Altres`
record checked reads as a DGT-imposed restriction on a Consell road
(`"Restriccions de la DGT..."`), not Consell's own works programme, so
it's excluded rather than assumed roadworks. `territory="Spain"`,
`administrative_area="Consell de Mallorca"` — the island authority is the
data-owning operator, the same rule already applied to Autobahn GmbH/
National Highways/Via Lietuva.

**Licence unconfirmed** — checked the WFS capabilities
(`Fees`/`AccessConstraints` both blank, GeoServer's own unconfigured
defaults, not a deliberate statement), the IDEmallorca geoportal, and the
Consell's general legal notice; no explicit reuse terms found anywhere.
Per the Autobahn GmbH/Belgium/Bulgaria precedent, the test fixture is
synthetic (real confirmed shape, invented values) — **verify your own
reuse rights before relying on this commercially.**

**Mallorca only, not a Balearic cluster** — the investigation checked
Menorca (its own separate IDE, no incidents layer located) and Eivissa (a
differently-shaped open-data portal with a broken TLS certificate, nothing
roadworks-related found); the pattern doesn't uniformly generalise, so
this ships as one additive provider, not the head of a committed cluster.
See `streetworks/ogc/mallorca.py`'s module docstring for the full
field-by-field mapping.

## Servei Català de Trànsit (Catalonia)

Catalonia's real-time road incidents, credential-free, filling the larger
of DGT's two documented exclusions (DGT explicitly omits Catalonia and
the Basque Country — see DGT's own section above):

```python
from streetworks.sct import SCTClient
from streetworks.common import from_sct

with SCTClient() as sct:
    incidents = list(sct.iter_roadworks())  # descripcio_tipus == "Obres" only
works = from_sct(incidents)
```

Built from a dedicated recon pass (`docs/catalonia-sct-investigation.md`),
then verified again while building. The real feed
(`incidenciesGML.xml`) is genuine WFS/GML — a `wfs:FeatureCollection`
with real `gml:Point` geometry — but flat and simple (one geometry plus a
dozen scalar sibling fields per record, no nesting), so it gets its own
small, contained parser (`streetworks.sct`, plain `ElementTree`, no new
dependency), the same shape of choice already made for Autobahn GmbH —
**this does not touch or depend on the general INSPIRE-GML-reader
decision parked elsewhere in this SDK.**

**Discriminator: `descripcio_tipus`, clean and explicit** — confirmed
live, 136 of 165 real current records typed `"Obres"` (works); the other
two real values, `"Retenció"` (congestion) and `"Cons"` (temporary cone/
lane measures), are excluded — checked, not assumed: one real `"Retenció"`
record does carry a free-text `causa` of `"Obres"` (congestion whose
*cause* is roadworks), but the dedicated `descripcio_tipus` field is
trusted over that secondary hint, the same way this SDK avoids promoting
free text into a primary classification elsewhere.

**No start/end validity window exists anywhere in this feed** — a
genuinely real-time, continuously-refreshed current-state feed (confirmed
via the dataset's own metadata and by watching `Last-Modified` change
between live pulls), not a works schedule. `date_confidence` is always
`UNKNOWN` and no proposed/actual dates are populated — the one real
timestamp this feed states (`data`) reads as "when this record was last
reported," not "when the works start," so it's kept on `.raw` rather than
promoted into a date field it would misrepresent.

**CRS: WGS84 (`EPSG:4326`), confirmed live** — the simplest CRS story of
any Spanish adapter in this SDK, no reprojection question at all. 100%
coordinate coverage confirmed (165/165 real records checked).

**Network scope: `multi_authority_interurban`**, the same shape as DGT's
own real data (see `docs/network-scope-audit.md`) — real road-number
prefixes span the Generalitat's own network (`C-`) and all four
provincial councils' networks (`B-`/`GI-`/`T-`/`L-` and their variants)
and some state roads within Catalan territory, never confirmed to reach
municipal streets.

**Licence: confirmed genuinely open** — Catalonia's own "Llicència oberta
d'ús d'informació" (reuse, distribution and derivative works permitted
worldwide, attribution required: *"Generalitat de Catalunya. Departament
d'Interior"*) — the cleanest licence of any Spanish source checked this
session, so the test fixture is real, trimmed from a live pull, not
synthetic. See `streetworks/sct/models.py`'s module docstring for the
full field-by-field mapping.

## Ayuntamiento de Madrid (INFORMO)

Madrid's own municipal traffic-incidents feed — the capital and largest
Spanish city (~3.3M), and the gap DGT's national coverage explicitly
doesn't reach (DGT never touches municipal streets, even where its own
`M-`-prefixed interurban roads run through the wider Madrid region — see
DGT's own section above):

```python
from streetworks.madrid import MadridClient
from streetworks.common import from_madrid

with MadridClient() as madrid:
    incidents = list(madrid.iter_roadworks())  # es_obras == "S" only
works = from_madrid(incidents)
```

**The investigation brief's stated URL is dead — checked live before
writing any code, not assumed working.** `informo.munimadrid.es` (the
brief's URL, and the host still named in the open-data portal's own
October-2023 PDF schema document) returns `NXDOMAIN` on two independent
resolvers, including a public DNS-over-HTTPS lookup used specifically to
rule out a local network quirk rather than a genuinely dead host. Madrid
relaunched its entire open-data portal on a new CKAN platform in February
2026 (confirmed via the portal's own news coverage); the new
`datos.madrid.es` dataset page's own "download" link now redirects to the
real current host, **`informo.madrid.es`** (`munimadrid.es` →
`madrid.es`, not just a path change). `MadridClient` targets that
confirmed-live URL directly, not the CKAN redirect hop.

**The live wire date format also doesn't match the portal's own
documentation.** The PDF states `yyyy-mm-ddTHH:mm:ss+dd:00` (a UTC
offset); every one of 217 real records checked live instead uses no
offset and **seven** fractional-second digits — one more than Python's
`%f` accepts. `streetworks.common.from_madrid` truncates rather than
failing.

**Roadworks filter: the source's own `es_obras` flag, not a free-text
type guess** — settling two questions the brief left open, with real
evidence: `cortes de carriles` (lane closures, 7/217 live) and
`operación asfalto` (asphalt resurfacing, 2/217) are both real and
common, but neither is flagged `es_obras` by Madrid's own system —
excluded. The asphalt-operations exclusion is a genuine surprise (it
reads like roadworks to a human) but the source's own classification is
trusted over what the label sounds like, the same discipline Chicago's
`worktype` filter and Berlin's `subtype` filter already apply.

**`source_grade="operator"`, not the `traveller_info` the brief
guessed** — Madrid's own field dictionary states its incident-type codes
follow "la normativa DATEX 2," and the feed is published directly by the
city's own traffic-circulation management directorate, not a separate
information-relay body (unlike Berlin's VIZ, genuinely an editorial
centre — see Berlin's own section above). Matches DGT/SCT/Mallorca's own
classification.

**Coordinates: geographic pair given directly, labelled `EPSG:4258`
(ETRS89), never silently WGS84** — the source states its UTM pair
(`utm_x`/`utm_y`) is `EPSG:25830` (ETRS89 / UTM Zone 30N) explicitly; the
`longitud`/`latitud` pair comes from the same reference frame, so it's
used directly rather than reprojected, and labelled honestly rather than
assumed `EPSG:4326` — the same standing policy already applied to
Consell de Mallorca and Jersey RoadWorkx.

**`id_incidencia` is the reliable reference, not `codigo`** (the
documented "año/número" field) — `codigo` is unique on 212/217 real
records checked live, but 6 genuinely share the literal placeholder
`"2025/0"`, a real data-quality gap in the source. `id_incidencia` is
unique on all 217.

**Network scope: `comprehensive`** — real records span everything from
named residential streets (`Antonio Leyva`) to motorway sections
(`A-3`/`A-5`), spread across the whole municipality, not one road tier —
the same reasoning behind Berlin's own `comprehensive` classification for
a city traffic-management feed, not DGT's `multi_authority_interurban`.

**Licence: CC BY, confirmed live** at `nap.dgt.es/dataset/trafico-
incidencias-en-via-publica` (organization `ayuntamiento-de-madrid`,
license field `cc-by`, "Creative Commons Attribution" stated on the page
itself) — not just carried over from the investigation brief. The exact
attribution string on `datos.madrid.es`'s own new portal wasn't
separately re-verified.

## Base Adresse Nationale (BAN)

French national address base — ~25M addresses, no credentials. **This is
an address base, not a street register** — unlike OS Open USRN, a UK
reader's first assumption (a downloadable street with its own key) is
wrong here: BAN publishes addresses as its primary entity, and a street
("voie") or hamlet ("lieu-dit") only exists as an implicit grouping under
the addresses that sit on it. `streetworks.ban` wraps both the credential-
free geocoding API and the bulk per-département/national files (streamed,
never loaded whole — the national file is ~1 GB+ gzipped):

```python
from streetworks.ban import BANClient

with BANClient() as ban:
    hits = ban.search("8 rue des halles paris")     # geocoding API
    print(hits[0].street, hits[0].commune_nom, hits[0].toponyme_id)

    path = ban.download_departement("48", "dept48.csv.gz")   # bulk file
    for address in ban.iter_addresses(path):
        print(address.id, address.lon, address.lat)          # WGS84
```

`toponyme_id` is **derived by this SDK**, not a literal BAN field — BAN
carries no `id_ban_toponyme` column under any format currently served, but
every real address `id` is exactly `{street prefix}_{numero}`, so stripping
the numero recovers a stable per-street grouping key (verified: 6/6 real
addresses on one real street share it). Because a street's identifier
starts with its commune's INSEE code, a street crossing a commune boundary
gets a different `toponyme_id` on each side, by construction. See
`streetworks.ban.models`'s module docstring for the full finding, including
a confirmed-live join from BAN's own data to DGFiP's **TOPO** register
(FANTOIR's July-2023 replacement) — investigated, not built into this SDK
yet.

The documented API endpoint (`api-adresse.data.gouv.fr`) is past its
2026-01-31 sunset; this client targets its confirmed-live replacement,
`data.geopf.fr/geocodage`. Licence Ouverte / Open Licence 2.0 (Etalab).

## Basisregistratie Adressen en Gebouwen (BAG)

Dutch national addresses and buildings register — no credentials. Two
routes, both wrapped by `streetworks.bag.BAGClient`: the PDOK
**Locatieserver** (live search/suggest/reverse/lookup — a geocoding
service, not the reference dataset) and the bulk **GeoPackage**
(`bag-light.gpkg`, current status only, no history — confirmed live at
~7.8 GB, ~21.4M rows across 5 tables), discovered from an Atom feed rather
than a hardcoded URL:

```python
from streetworks.bag import BAGClient, BAGDatabase

with BAGClient() as bag:
    hits = bag.search("Dam 1 Amsterdam")           # Locatieserver
    print(hits[0].straatnaam, hits[0].lon, hits[0].lat)   # WGS84

    path = bag.download_geopackage("bag-light.gpkg")     # ~7.8 GB, streamed

with BAGDatabase(path) as db:
    for table in db.tables():
        print(table.table, table.geometry_type)           # 5 real tables
    for address in db.iter_features("verblijfsobject", limit=5):
        print(address.raw["openbare_ruimte_naam"], address.geometry)
```

**The critical shape question — is a street its own object? — has a
three-part answer, confirmed against the real national file, not a
sample.** Yes, `openbare ruimte` (street/public-space) is a genuine
first-class BAG object with its own id and a real registered lifecycle —
but confirmed only by checking the *other* real product, the full-history
XML extract (investigated, not parsed — see below), because the
GeoPackage this SDK actually reads has no `openbareruimte` table at all:
only `woonplaats`, `pand`, `verblijfsobject`, `standplaats` and
`ligplaats`, all five of them carrying real geometry. Street name and id
survive there only as `openbare_ruimte_naam`/`openbare_ruimte_identificatie`,
flattened onto every address — verified at full national scale (~10.04M
addressable objects, zero of the resulting 250K+ street ids map to more
than one street name). And in neither product does a street carry geometry
of its own. Which shape you see — first-class object, or flattened
attribute — turns out to depend on *which real product you pull from*, not
on a fixed property of the data: that's the Netherlands' own contribution
to the canonical-gazetteer design session. Full detail, including the
bitemporal history model (`voorkomen` versioning) found in the
not-built XML extract, is in `streetworks.bag.models`'s module docstring.

Licence: **CC0 1.0 Universal** — confirmed from the Atom feed's own
`<rights>` element, a correction to what was originally documented
(Public Domain Mark 1.0 — a different, if similarly permissive, legal
instrument).

## Kartverket (Norway)

Norwegian national address register + official place names — no
credentials, no registration. **Worth saying plainly: this is the
opposite access story to Norway's *roadworks* provider** —
`streetworks.datex2.vegvesen` needed real Statens vegvesen credentials to
confirm (done 2026-07-30, see
[Recently confirmed](index.md#recently-confirmed)),
while Kartverket (a different agency) is wide open and always was.
`streetworks.kartverket.KartverketClient` wraps the
address REST API, the SSR (Sentralt stedsnavnregister) place-names API,
and bulk CSV downloads (discovered via an Atom feed, genuinely not
GML-only — CSV, FGDB, GML, PostGIS and SOSI are all published side by
side):

```python
from streetworks.kartverket import KartverketClient

with KartverketClient() as kv:
    hits = kv.search(sok="Karl Johans gate 1")        # address REST API
    print(hits[0].kommunenavn, hits[0].epsg, hits[0].nord, hits[0].ost)

    places = kv.search_places(sok="Karasjok")          # SSR, multilingual
    for name in places[0].names:
        print(name.sprak, name.skrivemate, name.skrivematestatus)
    # -> Norsk Karasjok / Nordsamisk Kárášjohka / Kvensk Kaarasjoki
```

**Multilingual naming lives on the place, not the address — confirmed
live, not assumed.** A real SSR place (Karasjok/Kárášjohka/Kaarasjoki)
carries three parallel official names, Norwegian/Northern Sámi/Kven, each
independently statused (two approved, the Kven one only proposed) — which
is why `PlaceName.names` is a list, never a single field. But a real
address in the same Sámi-majority municipality ("Čalbmebealskáidi 1") has
exactly *one* name, in Sámi, with no parallel Norwegian name anywhere on
the record — multilingual officialdom is a property of some SSR places,
not a systematic property of Norwegian street addressing.

`adressekode` (the street key carried *inside* the address dataset itself
— unlike the UK's separate register or France's separate tax register) is
real, clean, and municipality-scoped: verified at full scale, not
sampled, across two whole municipalities' bulk files (Karasjok, 1,896
addresses/139 codes; Oslo, 106,154 addresses/2,535 codes), zero codes
mapped to more than one street name in either. No product checked gives a
street its own geometry through this client — a separate Statens
vegvesen product, NVDB, does, and is Norway's own `streets` counterpart —
see below.

Licence: Creative Commons BY 4.0 (confirmed independently for both the
address API and SSR, per the design brief's own instruction not to assume
they matched).

## NVDB (Norway)

Norwegian national road network (Statens vegvesen) — no credentials.
**Worth saying plainly: this is the opposite access story to Norway's
own roadworks provider a second time** — `streetworks.datex2.vegvesen`
(same agency, DATEX) needed real credentials to confirm (done
2026-07-30), while NVDB is wide open, confirmed both live and in the
API's own documentation. The `streets` counterpart to `kartverket`'s
`addresses`:

```python
from streetworks.nvdb import NVDBClient

with NVDBClient(client_name="my-app") as nvdb:
    sequences = nvdb.veglenkesekvenser(kommune=4201)      # link topology
    addresses = nvdb.adresser(kommune=4201)               # naming layer
    print(addresses[0].adressenavn, addresses[0].veglenkesekvens_ids)
```

**`veglenkesekvens` (road link sequence) is purely topological — it has
no name of its own**, confirmed live: a real sequence carries only
`lengde`, `porter` (the network junctions it connects to) and `veglenker`
(its own geometry-bearing sub-links with linear-referencing ranges) —
nothing resembling a name. Naming lives in a separate object type
(`Adresse`, NVDB type 538), and its `adressekode` is confirmed live to be
the *same* identifier `streetworks.kartverket` already models — a real,
stated join to Matrikkelen addresses, never a name match.

**The genuinely important finding: one address can span multiple,
unrelated link sequences** — confirmed live on a real object ("Dalveien",
`adressekode` 1140, placed on sequences 384 *and* 2399262). So Norway's
naming layer and its topological layer are not nested the way France's
`voie_nommee`/`troncon_de_route` are (see below) — two "two-level
spines," two different organising principles, which is exactly the
disagreement this design strand needed. A third identifier system exists
too, `vegsystemreferanser` (administrative road-numbering, e.g. the real
`"KV1140 S1D1 m0-65"`) — independent of both, preserved in `.raw`, not
modelled as a first-class field.

CRS is **EPSG:5973, not the design brief's expected EPSG:25833** — see
[`docs/concepts/crs-and-datums.md`](../concepts/crs-and-datums.md) for
the full finding. Licence is **NLOD 1.0** (Norsk lisens for offentlige
data), confirmed from the NVDB API's own documentation — not
Elveg/Kartverket's CC BY 4.0, which covers a different distribution of
the same underlying network. Elveg / NVDB Vegnett Pluss (Kartverket's own
SOSI/GML-only distribution) is noted, not built, the same treatment as BD
TOPO's unreachable bulk route.

## Oslo (SøkSys)

Oslo kommune's real digging/work-permit case system — this SDK's second
Nordic *roadworks* coverage (after Copenhagen), alongside the separate,
already-verified national Statens vegvesen DATEX II feed above:

```python
from streetworks.oslo import OsloClient
from streetworks.common import from_oslo

with OsloClient() as oslo:
    features = list(oslo.iter_roadworks())  # Containerutsett excluded
works = from_oslo(features)  # id-deduped, activity_id-grouped
```

**Built from `nordic-capitals-investigation.md`'s recommendation to build
Oslo second. Live verification found a different real source than either
brief guess** (an Origo/Bymiljøetaten GeoServer layer, or the national
NVDB above). A web search for Oslo kommune's own page on this system
found **"SøkSys"** — a 2024-introduced permit/case-management system
(replacing older "Kgrav"/"ISYcase") covering crossing/proximity permits
for cable and pipe work, excavation and work permits, and traffic
warning — run on Oslo's behalf by **Geomatikk**, a real Norwegian
utility-location company. The real public map is `pub.soksys.no`
(confirmed Oslo-scoped: 19 distinct real `city_district` values, every
one a genuine Oslo bydel). Its own `map.js` bundle — read directly, the
same technique that found Roma's/Lisboa's/Road Report NT's real
backends — reveals the real internal API:
`https://pub.soksys.no/api/map/soksys-activities`, with `extent`
(a real bounding box) and `filter` (`atimequick=4`, the live site's own
default) query parameters. Keyless — every claim here came from a fully
unauthenticated pull (1354 real features at investigation time).

**The response body double-encodes its own JSON** — the raw HTTP body is
a JSON string literal containing escaped GeoJSON, so it needs
`json.loads` twice to reach the real `FeatureCollection`. Handled inside
`OsloClient.iter_roadworks` so callers never see the intermediate
string.

**CRS confirmed live: `EPSG:25832`** (ETRS89/UTM zone 32N) — a genuinely
projected CRS, not WGS84. Per this SDK's own convention (matching British
National Grid/Jersey/NYC DOT/Via Lietuva), `Coordinate.value` stays
plain `(x, y)` = `(easting, northing)`, never swapped to `(lat, lon)` —
unlike Copenhagen's genuine WGS84 source, built earlier the same
session.

**Real roadworks filter, evidenced not guessed**: `activity_type` has
exactly 3 real values — `Arbeidstillatelse` (work permit, 934/1354),
`Gravearbeid` (excavation work, 412/1354), `Containerutsett` (container
placement, 8/1354). Sampled real `sender` values confirm the split:
`Arbeidstillatelse`/`Gravearbeid` senders are genuine traffic/road-work
companies (VEISKILTING AS — "road signage", TRAFIKKJENTENE AS, SAFEROAD
TRAFFIC AS); `Containerutsett` senders are the city agency itself or
property managers placing skips, not construction work.

**A real, load-bearing geometry/grouping finding, genuinely different
from Copenhagen's own dedupe pattern.** Under the default filter, 1354
raw rows collapse to 631 distinct `activity_id`s (261 multi-row).
Checked every one: 256 multi-row groups are **pure duplicate artifacts**
— identical `id` and identical geometry, appearing twice, a real
tiling/extent artifact of querying a wide bbox (confirmed: only 1338 of
1354 `id` values are distinct). But a real handful of permits genuinely
span several distinct sub-areas — different `id`, different real
coordinates/areas, same `file_number`/`sender`/dates — a real
Jersey/NYC-DOT-style "one project, several real sites" shape, not
Copenhagen's "one site, several geometry representations" shape. So
`from_oslo` dedupes by exact `id` first (drops the tiling artifact), then
groups the survivors by `activity_id` into one `Works` per activity with
one `WorksSite` per distinct surviving geometry row.

**Polygon geometry** (the majority real shape here, unlike Copenhagen
where it was always droppable) uses its own first ring's first vertex as
`Coordinate.value` only — `Coordinate.points`/`.parts` are documented
for line-geometry vertices, not polygon rings, the same discipline
`from_paris`'s own polygon case already established above.

**A separate `/plans` endpoint exists** (`soksys-plans`,
`filter=ptimequick=4`) — confirmed live, 1339 real features, but a
genuinely different schema (`status: "Koordinert"` = Coordinated, no
`activity_type`/`sender`/`case_handler`/`city_district` at all). This is
the earlier, pre-permit planning stage — not built here.

**Licence: genuinely unconfirmed.** Checked both the live
`pub.soksys.no` page and Oslo kommune's own SøkSys explainer page — no
licence/terms statement found on either.

**A real, evidenced "shared platform" lead, not chased this pass**: the
map bundle's own `typenamePrefix` logic switches on
`configSettings['countryCode'] === 'SE'`, meaning SøkSys is
white-labelled per municipality/country — other Norwegian *and Swedish*
municipalities may run their own instance. Left for a future
investigation, the same "verify before building" discipline this whole
Nordic strand is under.

## Helsinki (Kaivuilmoitus)

City of Helsinki's real excavation-notification register — this SDK's
third Nordic *roadworks* coverage (after Copenhagen and Oslo), alongside
the separate, already keyless-built national Digitraffic DATEX II feed
above:

```python
from streetworks.helsinki import HelsinkiClient
from streetworks.common import from_helsinki

with HelsinkiClient() as helsinki:
    features = list(helsinki.iter_roadworks())  # raw, ungrouped
works = from_helsinki(features)  # grouped by hakemustunnus
```

**Resolves the investigation brief's own open question, not assumed.**
`nordic-capitals-investigation.md` flagged Helsinki "least urgent" and
left its own core claim unconfirmed: *"a roadworks
(`katutyöt`/excavation-permits) dataset is not confirmed"* on Helsinki
Region Infoshare. Checked live via HRI's own CKAN `package_search` API:
every excavation/permit-shaped search term (`kaivulupa`, `kaivuilmoitus`,
`työmaa`, `excavation`, `katutyöt`) surfaces one real dataset — **"Land
usage permission system for public areas in the City of Helsinki"** —
backed by a live GeoServer WFS, layer `avoindata:Kaivuilmoitus_alue`
("excavation notification, area"). Keyless — every claim here came from
a fully unauthenticated pull (3,431 real features at investigation time).

**No pagination needed** — a `GetFeature` request with no `count`
parameter returns every real row in one response
(`numberReturned == totalFeatures`), the same single-call shape as this
SDK's Hamburg/Brandenburg sources.

**CRS confirmed live: `EPSG:3879`** (ETRS-GK25FIN) — a genuinely projected
CRS, not WGS84. The WFS *can* reproject to WGS84 on request (tested live,
genuinely correct) — not used here, per this SDK's standing CRS policy of
carrying a source's native CRS through explicitly rather than asking a
server to reproject, the same call Mallorca's own docstring documents
making even though its WFS offers the same capability.
`Coordinate.value` stays plain `(x, y)` = `(easting, northing)`, never
swapped to `(lat, lon)`.

**A real, load-bearing grouping finding, Oslo-shaped not Copenhagen-
shaped.** `id` is genuinely unique across every real row (no tiling-
duplicate problem to dedupe first, unlike Oslo) — but `hakemustunnus`
(application reference) repeats heavily: 803 distinct references across
3,431 rows, up to **164 real rows under one reference**
(`KP2601938`). Checked: this is one excavation notification genuinely
spanning many real geometry sub-areas (segmented dig zones), the same
"one project, several real sites" shape as Oslo's `activity_id`/Jersey/
NYC DOT. `from_helsinki` groups by `hakemustunnus` into one `Works` with
one `WorksSite` per surviving geometry row.

**Two other real layers on this WFS, checked live and deliberately not
used**:
- `Kaivuilmoitus_piste` (point version, 16 real rows) — confirmed to be a
  **redundant subset**, not disjoint data: all 4 of its distinct
  `hakemustunnus` values already appear in the area layer, with identical
  dates/status/address row-for-row — just an alternate point
  representation for a handful of applications, not additional coverage.
- `Tilapainen_liikennejarjestely_alue` ("temporary traffic arrangement",
  342 real rows) — a genuinely different application type and schema.
  Related but structurally distinct — the same "found, not built this
  pass" treatment Oslo gave its own separate `/plans` endpoint.

**`status` is a genuinely informative two-value field, unlike Oslo's
always-"granted" `status`.** `"Käynnissä"` (in progress, 3,223/3,431) and
`"Tuleva"` (upcoming, 208/3,431) — cross-checked live against a
date-based future/past split on `tyo_alkaa` and it matches exactly
(208 = 208). A real "genuinely happening now" vs "not yet" signal, so
`"Käynnissä"` populates `actual_start`/`actual_end` and grades
`DateConfidence.VERIFIED` (the same `actual_start`-present rule
`from_streetmanager` already uses), not always `ESTIMATED` like Oslo.

**`promoter` is never populated — a real, confirmed absence.** `hakija`
(applicant) and `tyon_suorittaja` (contractor) are empty on all 3,431
real rows checked, matching the dataset's own published description
("licensee only to a limited extent").

**Licence: CC-BY-4.0, confirmed live** via the dataset's own CKAN
`package_show` metadata (`license_id: "CC-BY-4.0"`) — clean, no hedging
needed, the same confidence level as Copenhagen's.

## NWB (Netherlands)

Dutch national road network — no credentials. **The `streets` counterpart
to `bag`'s `addresses`**: between them, the Netherlands is the first
territory in this SDK with both layers. A street is a *set* of `wegvakken`
(road segments, e.g. each direction of a dual carriageway is its own
segment) — how they group back into one real street, and whether a
usable join to BAG exists, were this module's key open questions:

```python
from streetworks.nwb import NWBClient, NWBDatabase

with NWBClient() as nwb:
    segments = nwb.query(cql_filter="gme_naam='Harlingen'")   # live WFS
    print(segments[0].stt_naam, segments[0].bag_orl)           # BAG join

    path = nwb.download_geopackage("nwb_wegen.gpkg")           # ~1 GB, streamed

with NWBDatabase(path) as db:
    for wegvak in db.iter_wegvakken(limit=5):
        print(wegvak.stt_naam, wegvak.toponyme_id())            # bag_orl, or None
```

**A real, stated join to BAG exists — `bag_orl`, literally BAG's own
`openbare_ruimte_identificatie`** (confirmed live: format and commune-code
prefix match exactly), not a name match. But it isn't universal (~5% of a
real municipality's wegvakken, Harlingen, carry none) and name-based
grouping alone is measurably less reliable: of 385 real (municipality,
name) groups there, 7 span two different real `bag_orl` values — e.g.
"Sédyk" is one display name covering two genuinely different BAG street
objects. `Wegvak.toponyme_id()` returns `bag_orl` where present and
`None` otherwise — it never falls back to the name, which would silently
over-merge in exactly these real cases.

Two access-route findings worth knowing before you build against this
data yourself: the WFS's own paging **does** work (the design brief's
warning traced to an unencoded `+` in `outputFormat`, decoded server-side
as a space) — but **PDOK's WFS proxy silently ignores `CQL_FILTER`
entirely**, while Rijkswaterstaat's own WFS filters correctly on the
identical query, so this client queries Rijkswaterstaat directly and
only uses PDOK's Atom feed for the (unaffected) bulk GeoPackage download.
CRS is EPSG:28992, matching BAG; licence is CC0 1.0 Universal, matching
BAG too — confirmed from the Atom feed's own `<rights>` element, not a
portal page.

## BD TOPO (France)

French national road network (IGN) — no credentials. **The `streets`
counterpart to `ban`'s `addresses`**: France is now the second territory
(after the Netherlands) with both layers. Two findings settle the
strongest open questions from this strand: does a named-street entity
exist above the segments, and is there a real join to the address
register?

```python
from streetworks.bdtopo import BDTopoClient

with BDTopoClient() as bdtopo:
    segments = bdtopo.query_troncons(cql_filter="insee_commune_gauche='01004'")
    print(segments[0].nom_voie_ban_gauche, segments[0].toponyme_id_gauche())  # BAN join

    streets = bdtopo.query_voies_nommees(cql_filter="insee_commune='01004'")
    print(streets[0].nom_voie_ban, streets[0].liens_vers_supports)  # -> a real troncon cleabs
```

**Both answers are yes, confirmed live, and BD TOPO's are richer than
NWB's.** `voie_nommee` (named street) is a genuine first-class layer with
its own stable id (`cleabs`) and a real link down to `troncon_de_route`
(`liens_vers_supports`, confirmed live to resolve to the matching real
segment) — a true two-level spine, the strongest input this design
strand has had. And every segment carries `identifiant_voie_ban` —
exactly BAN's own compact toponyme-id format — *plus* `id_ban_odonyme`,
a street-level BAN UUID that BAN's own API/bulk files never expose
directly. Verified at real commune scale, not sampled, on two whole
communes (Ambérieu-en-Bugey, mainland; Basse-Terre, Guadeloupe,
overseas): grouping by `identifiant_voie_ban` and checking against
`nom_voie_ban` (BAN's own name) gives **zero** over-merged groups in
either. A real, minor nuance surfaced along the way: BD TOPO's own
crowd-sourced name field (`nom_collaboratif`) had one abbreviation
variant under the same BAN id in Basse-Terre — not a genuine conflict,
and gone entirely once checked against `nom_voie_ban` instead, which is
why both name fields are kept rather than one being treated as noise.

**`id_ban_odonyme` is worth calling out on its own — it isn't just a
cross-reference, it's an identifier BAN itself keeps internal.** Neither
BAN's geocoding API nor its bulk `csv`/`csv-bal` files ever return this
UUID (confirmed across both, see `streetworks.ban`); it only surfaces
here, in IGN's data. That means joining a French street to its BAN
address cloud by a real permanent id — not the derived `toponyme_id`
this SDK has to construct for BAN on its own, and not a name match — is
something this SDK can do by combining two providers that neither
provider makes possible alone. A French developer reaching for BAN or BD
TOPO individually would not expect this; it only becomes visible by
having both native interfaces side by side.

BD TOPO also models something neither NWB nor the UK's USRN does:
**left/right structure is real**, not a documentation artefact — a
segment carries independent `_gauche`/`_droite` names, BAN ids, and even
INSEE commune codes (a segment on a commune boundary can genuinely have
two different communes, one per side).

Only the WFS is built here — **no automated bulk-download route was
found**, a genuine, thoroughly-investigated gap: IGN's documented download
portal now redirects to a JavaScript single-page app with no discoverable
static resource list (checked: `data.gouv.fr`'s 149-resource listing,
`geoservices.ign.fr`, the legacy `wxs.ign.fr`, and the WFS's own output
formats, which don't include GeoPackage). CRS is also route-specific
here — see [`docs/concepts/crs-and-datums.md`](../concepts/crs-and-datums.md).
Licence ouverte / Open Licence ETALAB 2.0, matching `ban`.

## Paris Chantiers (Ville de Paris)

This SDK's third municipal permit register, and the French analogue of
`nycdot`/`chicagodot` (see [`docs/providers/us.md`](us.md)) — same
`source_grade=register` tier, same "one application groups several
sites" shape — but the first provider on **OpenDataSoft**, not Socrata.
No shared `streetworks.opendatasoft` client was extracted for it: built
bespoke inside `streetworks.paris`, the same sequence that produced
`streetworks.socrata`'s `SodaClient` (bespoke first, shared only once a
second same-platform provider needs the identical shape).

```python
from streetworks.paris import ParisClient
from streetworks.common import from_paris

with ParisClient() as paris:
    works_list = from_paris(list(paris.iter_roadworks()))
```

**Municipal, not national — deliberately not deduplicated against
`bisonfute`.** France is already covered nationally (Bison Futé/the
DIRs, interurban), but that coverage doesn't reach Paris city streets.
Paris's own register is a genuinely separate authority publishing a
genuinely separate shape, at a different scope — the same non-dedup
principle `nycdot` already establishes relative to WZDx's state-level
511NY coverage.

**Roadworks-vs-private filter, evidenced not guessed.** The real
`chantier_categorie` field has exactly three live values: `"Ville de
Paris (Tvx sur espace ou édifice public)"` (598 rows) and `"Opérateurs
de réseau (gaz-électricité-RATP-etc)"` (1,191 rows) are genuine
street/public-space works; `"Tiers (travaux sur bâtiment)"` (2,918 rows
— private building works/scaffolding) is not roadworks and is the only
category `iter_roadworks()` excludes.

**Geometry is already WGS84, despite the underlying survey CRS being
Lambert 93.** Both `geo_shape` (a GeoJSON `Polygon` — the worksite
footprint) and `geo_point_2d` (a representative point) are served in
WGS84 degrees — OpenDataSoft reprojects on the way out, so no CRS
transform was needed here, unlike this SDK's British National Grid
providers. The full polygon is preserved in `WorksSite.raw`;
`Coordinate.value` uses the representative point, since
`Coordinate.points`/`.parts` are documented for line-geometry vertices,
not polygon rings (see [`docs/concepts/data-model.md`](../concepts/data-model.md)).

**A real Works-umbrella grouping, the same shape as NYC's own** —
`chantier_cite_id` genuinely groups multiple real emprise rows under one
parent chantier (a real example, `329467`, a 3-emprise green-space
maintenance job spanning 3 genuinely different real polygons).

**No stated join to a street register** — only `cp_arrondissement`
(postcode) and the geometry itself; `street_ref` is never populated, the
same nycdot/chicagodot/Roads-ACT discipline. **Licence: ODbL 1.0 (Open
Database License), confirmed** from the dataset's own metadata — a
share-alike licence, a stronger documentation case than nycdot/
chicagodot's own unconfirmed tier. Share-alike means an adapted/derived
database must itself be released under ODbL (or a compatible licence) —
the same nuance `streetworks.au.act`'s CC BY-SA carries relative to its
plain-CC-BY siblings. Attribution: "Ville de Paris".

## Ireland — MapRoad Roadworks Licensing (documented, unavailable)

Investigated and registered honestly-unavailable, the same treatment
Road Report NT (Australia) already established (see
[`docs/providers/australia.md`](australia.md#act--tasmania--the-au-tail-plus-a-documented-northern-territory))
— not silently skipped, but not a working client either.

**TII's own DATEX II feed (`data.tii.ie`) was checked first and ruled
out as the roadworks source.** Its real, published dataset catalogue
(verified directly against its data.gov.ie mirror — all 20 real dataset
titles enumerated) carries travel times, weather, VMS/VDS, collision
rates, WIM sensor data, and traffic counts — no roadworks or Situation
publication at all.

**MapRoad Roadworks Licensing is the real roadworks source — a genuine
national permit register covering both national and local roads** (TII's
own national-road consents route through it; local authorities' regional/
local consents also do), run by the Road Management Office under the
Local Government Management Agency. If it were reachable, this would be
this SDK's third `source_grade=register` source, and the first genuinely
combined national+local one.

**Why it's a documented scaffold, not a working client.** Ireland's own
[PSB Data Catalogue entry](https://datacatalogue.gov.ie/dataset/maproad-roadworks-licensing-system)
states, together: `API Available: Yes`, `Open Data: No`, `Data Sharing:
Yes`, `Personal Data: Yes`. Read as a whole, this describes a real API
gated behind a formal, GDPR-relevant data-sharing arrangement — not a
self-service developer key the way Trafikverket/LINZ's are. Registration
for MapRoad itself (`rmo.ie`) is a real, formal process (download a
registration pack, complete it, email it to `contact@rmo.ie`) aimed at
licence *applicants*, not read-only consumers. No endpoint, schema, or
authentication mechanism for a read path was found published anywhere.
`MapRoadClient()` always raises `ProviderUnavailableError` immediately,
with no network call, rather than guessing at an unpublished private
contract with real personal-data implications — see
[`docs/providers/index.md#credentials-wanted`](index.md#credentials-wanted)
for the condensed table entry, and revisit if a documented read API, or
a confirmed data-sharing route for non-applicants, ever surfaces.

## Greece (documented, unavailable)

Investigated and registered honestly-unavailable, the same treatment as
Road Report NT and MapRoad — not silently skipped, but no roadworks
source exists at all.

**Greece's real National Access Point** (`nap.gov.gr`, confirmed as the
official MMTIS/RTTI/SRTI/SSTP access point per the European Commission's
own October 2025 National Access Points list) **is a decentralised
metadata catalogue (CKAN), not a centralised DATEX II feed** — the
reason Greece is absent from the pan-EU DATEX aggregators that carry
~24 other live NAPs, Italy among them (see
[`docs/providers/italy.md`](italy.md)). Its own real dataset
titles were checked directly, not assumed: truck parking, refuelling
points, KTEL bus/ferry timetables, Thessaloniki floating car data, and
toll-operator sensor feeds — real Vehicle Detection Sensor data from
Attiki Odos, Road Weather Information System locations for Egnatia
Odos, and real-time Variable Message Sign data from the Hellastron
network. **No roadworks or DATEX II Situation Publication dataset
anywhere.**

**A second, independent reason: the portal itself is currently down.**
Confirmed live (2026-08-03) via direct probing: `data.nap.gov.gr`
returns a real `502 Bad Gateway` from its own CKAN backend, reproduced
on both the dataset-list page and its `/api/3/action/package_list`
endpoint; its mirror, `data.nap.imet.gr`, hangs at the TLS handshake
stage and never completes a connection.

`GreeceClient()` always raises `ProviderUnavailableError` immediately,
with no network call — see
[`docs/providers/index.md#credentials-wanted`](index.md#credentials-wanted)
for the condensed table entry, and revisit if a documented roadworks
source (national or toll-operator) ever surfaces. Even a best-case
future toll-operator feed would only ever be motorway-concession-only,
fragmented per operator — not a genuine national source.

## European & Crown Dependency roadworks — separate strand

Candidate feeds, researched but **not yet verified**. As always, each needs a
real sample feed and a licence/access check *before* building — the first task
per source is "can we get the feed and what do the terms permit," not coding.

Grouped by the client shape they need:

- **DATEX II adapters** (thin fetchers over the existing `streetworks.datex2`
  models, Finland/National-Highways-style where the source isn't DATEX-shaped
  itself). Norway, Iceland, France, and Spain are covered above (Iceland,
  France, and Spain shipped, Norway/Sweden/Denmark Phase 1 — see
  [Credentials wanted](index.md#credentials-wanted)). Access models vary from fully
  open to registration/agreement-gated — confirm per country. Note Alert-C
  location-code decoding (numeric codes → geometry, not yet supported) is
  likely needed for some of these, unlike Finland's coordinate-carrying JSON.
- **ArcGIS REST** — shipped. Jersey RoadWorkx (`streetworks.arcgis.jersey`,
  see [`docs/providers/uk.md`](uk.md)) was this strand's ArcGIS candidate;
  turned out to need a real pagination-truncation fallback strategy, not
  just a quick fetch — see `streetworks.arcgis.client`'s module docstring.
  Guernsey remains open — it still appears to be an HTML site with no
  confirmed structured feed.
- **Dedicated pieces** (each its own project, not a quick adapter): Germany's
  Mobilithek *broker* (subscription access, mixed schemas — D-TRO-scale
  effort; distinct from Autobahn GmbH's own public motorway-roadworks API,
  already covered above).
- **UK local-authority ArcGIS roadworks** — the same `ArcGISFeatureClient`
  shape Jersey uses, but a per-authority cluster like the German states
  (West Berkshire and others each publish their own ArcGIS
  MapServer/FeatureServer roadworks layer). Noted, not built — West
  Berkshire's own service was the real-world reference this session used
  to anticipate the "`Supports Pagination: false`" trap, but wasn't itself
  built into a converter.
- Verify-the-source-first: prefer official government feeds over third-party
  API-marketplace wrappers; a couple of the researched links need their real
  upstream endpoint confirmed.

## International gazetteers — separate strand

The European equivalents of OS Open USRN (address/street reference layers, not
roadworks — keep distinct from the feeds above). **NVDB was this strand's
last planned provider** — four `addresses` registers and three non-UK
`streets` registers are now in hand, and every one disagrees with the
others in a real, load-bearing way:

- the UK pair — street-centric, unified identity and geometry under one register;
- France's BAN — address-centric, street identity lives in a *different
  dataset* (DGFiP's TOPO) with no street geometry anywhere; BD TOPO then
  showed the *street*-geometry side has its own two-level spine
  (`voie_nommee`/`troncon_de_route`), organised by *name*, with a real
  stated join back to BAN;
- the Netherlands' BAG — street *is* a genuine first-class registered
  object with a real lifecycle, but whether you can see it as its own row,
  and whether it has geometry, depends on which real product you pull
  from; NWB's `bag_orl` gave a real, stated join back to it, not universal
  and less reliable by name than by id;
- Norway's Kartverket — a street code (`adressekode`) lives *inside* the
  address dataset itself; NVDB then showed its own two-level spine
  (`veglenkesekvens`/`Adresse`) is organised by *network topology*, not
  name, and — the real disagreement this strand needed — one named
  address can span several topologically-unrelated link sequences, so
  Norway's two spines aren't nested the same way France's are, despite
  both being called "two-level."

That's the exit condition this strand set for itself, and the
canonical-gazetteer design session it called for has now happened — see
[`docs/concepts/data-model.md`](../concepts/data-model.md#canonical-gazetteer-model-street-segment-address).
Further gazetteers (Spain Catastro, Germany Geoportal, Portugal
SNIG, the UK GeoPlace gazetteer SOAP API) now have a settled shape to build
against. Germany's own state
gazetteers are commonly published the same way as the regional roadworks
above (WFS/OGC API Features) — `streetworks.ogc`'s `OGCFeaturesClient` was
deliberately kept generic (GeoJSON in, features out, CRS-aware, nothing
roadworks-specific) so this future work can reuse it rather than needing
its own fetch layer.

**`streetworks.registry`'s `kind` reflects this directly**: what used to be
one `"gazetteer"` value is now `"addresses"` and `"streets"`, because
lumping the two together produced a real, false conclusion — "European
gazetteers have no street geometry" looked true with only address
registers (BAN/BAG/Kartverket) as examples, and it's wrong; the geometry
lives in a *street* register published separately, by a different body,
in every territory checked so far except the UK. Splitting the category
turned `providers()` into an actual coverage map: the UK has two
`streets` providers (`datavia`, `openusrn`) and **zero** `addresses` — a
real gap, not an oversight, since AddressBase is an OS Premium product,
not open data, which may make the UK the one territory where the address
layer is genuinely blocked, the inverse of the European picture. The
Netherlands, France and Norway each had the same `addresses`-only gap
until NWB, BD TOPO and NVDB gave all three both layers, in that order.

Also investigated, not built: France's street *names* now live in DGFiP's
**TOPO** register (which replaced FANTOIR in July 2023 — FANTOIR is
archived), a separate dataset from BAN with no geometry of its own -
**not to be confused with IGN's BD TOPO** (`streetworks.bdtopo`, above),
an unrelated product from a different agency that happens to share the
name almost exactly; worth stating plainly since the two are easy to
conflate. BAN's plain `csv` bulk format carries a real, live-confirmed
join to DGFiP's TOPO (see `streetworks.ban`'s module docstring) — worth
its own module or folding into `streetworks.ban`, a decision for the
canonical-gazetteer design session.
Likewise, BAG's full-history XML extract (its own `openbare ruimte` object
with a bitemporal `voorkomen` versioning model) is investigated, documented
in `streetworks.bag.models`, and not parsed — the same deferral. Norway's
NVDB Vegnett (the real road-network line geometry no Kartverket address
product carries) gets the same treatment: noted, not built.
