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

Every DATEX-parsed source in this cluster — NDW, National Highways,
Digitraffic, and every other adapter below — converts the same way, onto
the shared cross-provider model:

```python
from streetworks.common import from_datex2

works = from_datex2(situation, territory="Netherlands")  # or England, Finland, ...
```

(`territory`/`administrative_area` can't be derived from a `Situation`
alone, so pass them explicitly — see the module docstring.)

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

## Straatnamenregister (Flanders, Belgium)

Flanders' own street-name register, part of Basisregisters Vlaanderen
(the Flemish Base Registries suite) - no credentials. This SDK's first
Belgian streets/gazetteer coverage, a sibling to the Belgium roadworks
coverage above (Verkeerscentrum Vlaanderen) - both genuinely
Flanders-only, not all-Belgium:

```python
from streetworks.vlaanderen import VlaanderenStreetsClient
from streetworks.common import from_vlaanderen_street

with VlaanderenStreetsClient() as vlaanderen:
    streets = [from_vlaanderen_street(r) for r in vlaanderen.iter_streets()]
```

**Not the layer first checked - a road-segment WFS with embedded names
was tried first, a dedicated name register was found instead.**
Informatie Vlaanderen's own "Wegenregister" WFS
(`geo.api.vlaanderen.be/Wegenregister/wfs`, confirmed live, keyless)
carries a real `Wegsegment` layer with real line geometry, but street
identity there is a genuinely richer shape than this SDK's single-name
`Street` model cleanly supports: each segment states **two**
independent street-name references (`linkerstraatnaam`/
`rechterstraatnaam` - left/right side of the road can genuinely differ,
a real Belgian addressing convention), both frequently blank on
footpaths/cycleways - closer to NWB's own "street is an aggregation of
segments" shape than a queryable named entity. Basisregisters
Vlaanderen's own `Straatnaam` REST resource, found separately, publishes
street identity directly instead.

**Roughly 99,600 real street names, confirmed live 2026-08-20 by
bisecting the `offset` parameter** - the list response states no total
count field directly. **No geometry anywhere in this resource -
`GeometryGrade.ABSENT` on every real `Street`, the same shape ANNCSU
(Italy)/BEV (Austria) already established, not a gap in this build.**
Real coordinates would need a separate join back to the Wegenregister
WFS above - not attempted here, the same "streets built, richer join
left for later" call already made for ANNCSU's own `accessi` sibling.

**A real, confirmed API quirk: the documented municipality filter is
silently ignored.** `gemeenteniscode` (the parameter this API's own
schema suggests for filtering by municipality) makes no difference -
confirmed live: two different real codes and no filter at all all
return byte-identical first pages. An undocumented `gemeentenaam=<name>`
text filter genuinely works (confirmed live: distinctly different,
correctly-scoped results for "Antwerpen"), but using it to resolve every
street's municipality would mean a real ~300-municipality fan-out this
build doesn't attempt - `administrative_area` is therefore left
unresolved, the same honest gap Denmark's DAR leaves for its own raw
kommune code.

**Pagination: real, confirmed live** - `offset`/`limit` parameters
(capped at 500 server-side, confirmed live: a requested `limit=2000`
silently returned only 500), with a real `volgende` ("next") field
carrying the next page's full URL, confirmed live to be absent on the
genuine last page.

**Licence: Flanders' standard government open-data terms**, the
"Modellicentie Gratis Hergebruik" (Model Licence for Free Reuse -
confirmed live and reachable, though its own clause text sits behind a
JS-rendered page this build couldn't extract directly) - the default
licence for Flemish government open data per web search, not this
specific API's own confirmed per-dataset licence field; free reuse for
any purpose with attribution as the only stated condition.

**No credentials required** - every claim above came from a fully
unauthenticated GET request.

## CACLR (Registre national des localités et des rues, Luxembourg)

Luxembourg's national street register, run by ACT (Administration du
Cadastre et de la Topographie) under the law of 25 July 2002 - no
credentials. This SDK's first Luxembourgish streets/gazetteer coverage,
a sibling to the Luxembourg roadworks coverage above (Ponts et
Chaussées):

```python
from streetworks.caclr import CaclrStreetsClient
from streetworks.common import from_caclr_street

with CaclrStreetsClient() as caclr:
    streets = [from_caclr_street(r) for r in caclr.iter_streets()]
```

**Not a modern WFS/REST feed - the live government geoportal WFS was
checked first and ruled out.** `ws.geoportail.lu` (Luxembourg's national
geoportal WFS/WMS host) is real and live, but is MapServer-based with
per-theme "map" identifiers this module never found a working one for;
its GeoNetwork catalogue search API only returned real `400`s on every
query shape tried. The real route instead is CACLR's own bulk export on
`data.public.lu` (Luxembourg's national open-data portal, a udata
instance, the same software family as France's data.gouv.fr).

**A real, stable "current resource" API used instead of the dataset
page's own promoted (dated-snapshot) download link.** The page's UI
links directly to a real but dated URL
(`.../20260817-023002/caclr.zip` - the same no-stable-latest-alias
shape Austria's BEV and Lithuania's Registrų centras registers both
have). udata's own REST API
(`data.public.lu/api/1/datasets/registre-national-des-localites-et-des-rues/`,
confirmed live) always reflects the *current* resource list, so this
client resolves the real `caclr.zip` URL from there first - genuinely
self-updating, unlike the hardcoded-snapshot workaround used for
Austria's BEV.

**A real, fixed-width flat-file format inside the ZIP, confirmed
field-by-field from ACT's own published PostgreSQL import script**
(`import-caclr.sql`, bundled as a sibling resource on the same dataset
page) rather than guessed from column alignment. Three of the 13 real
tables in the ZIP are used: `RUE` (9,946 real streets), `LOCALITE` (590
real localities), and `COMMUALL` (132 real communes). Encoding is
genuine ISO-8859-1 (Latin-1), confirmed live: 1,613/9,946 real street
names contain a real accented character (French and Luxembourgish, e.g.
"Rue Siggy vu Lëtzebuerg"), and UTF-8 decoding fails outright on this
file.

**A real join trap found and worked around before shipping, not
reproduced.** `LOCALITE.FK_COMMU_CODE` and `COMMUALL.CODE` are *not*
globally unique - Luxembourg's real commune codes are only unique
**within their own canton**, confirmed live: joining on `FK_COMMU_CODE`
alone resolves a real Luxembourg-City street to "Burmerange" (a
different, real, but wrong commune roughly 30 km away). The correct
join uses the composite `(FK_CANTO_CODE, FK_COMMU_CODE)` key both
tables actually carry - confirmed live against the same street,
correctly resolving to "Luxembourg".

**No geometry anywhere in the `RUE` table - a real, defining
characteristic of this specific resource, not a gap in this build.**
The same pure name-registry shape ANNCSU (Italy) and BEV (Austria)
already established. Real coordinates would need a join to a separate,
much larger address-point-level resource (`IMMEUBLE`, ~14.6 MB) this
build doesn't fetch.

**Real per-row lifecycle flags kept, never used to filter.**
`DATE_FIN_VALID` (a real end-validity date, populated on 573/9,946
rows) and `INDIC_PROVISOIRE` (a real provisional-street flag, `O` on
145/9,946 rows) are both genuine, live-confirmed states this client
passes through rather than silently dropping.

**Licence: Creative Commons Zero (CC0)**, confirmed live from the
dataset's own page on data.public.lu - the most permissive licence any
provider in this SDK carries, no attribution required at all.

**No credentials required** - every claim above came from a fully
unauthenticated GET request.

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

## Adresų registras (Registrų centras, Lithuania streets)

Lithuania's national street-centerline register, run by Registrų
centras (State Enterprise Centre of Registers) — no credentials. This
SDK's first Lithuanian streets/gazetteer coverage, a sibling to the
roadworks coverage above (Via Lietuva):

```python
from streetworks.registrucentras import RegistruCentrasStreetsClient
from streetworks.common import from_registrucentras_street

with RegistruCentrasStreetsClient() as rc:
    streets = [from_registrucentras_street(r) for r in rc.iter_streets()]
```

**22,547 real national street records, confirmed live 2026-08-20 — 100%
carrying a real name and real geometry, zero duplicate street codes.**
Found via data.gov.lt's own DCAT catalogue; the dataset's own promoted
download link bakes a version number into the URL
(`.../versions/116/dynamic-resource/gragatve/json/download/` — the same
no-stable-latest-alias shape Austria's BEV register has), but a
shorter, undated link on the same page was followed and found to
redirect to a real, stable, version-less route
(`get.data.gov.lt/datasets/gov/rc/ar/gragatve/GraGatve`, confirmed
byte-identical to the versioned URL) — used instead. The whole real
dataset (~15.5 MB) comes back in one response, no pagination needed.

**The same real axis-order quirk this SDK's own Via Lietuva roadworks
provider already documented, confirmed independently here rather than
assumed to carry over.** The `gatves` field's WKT `LINESTRING`/
`MULTILINESTRING` geometry states coordinate pairs as `(Northing,
Easting)`, not the standard WKT/GeoJSON `(X, Y)` order — confirmed the
same way Via Lietuva's own finding was: a real sample point's first
ordinate (~6,107,030) only ever falls inside LKS-94's real Lithuanian
*northing* range (~5,990,000–6,265,000), never its real easting range
(~300,000–720,000), and reprojecting with the ordinates swapped lands
the point inside Lithuania's real extent (~22.7°E, ~55.1°N) while the
literal order lands near Sri Lanka. Unlike Via Lietuva (which carries
LKS-94 through unconverted, since DATEX-style consumers expect a stated
projected CRS), this streets build reprojects client-side to WGS84 via
a new closed-form Transverse Mercator inverse
(`streetworks.common._lks94`, no `pyproj`) — matching the `(lat, lon)`
convention every other streets provider in this SDK uses.

**Genuinely multi-part `MULTILINESTRING` on a real minority of rows**
(21/22,547) — parsed into `Coordinate.parts`, never a first-part-only
shortcut.

**`administrative_area` is left unresolved — a real, disclosed gap.**
Each row's `gyvenamoji_vietove` (settlement) reference is a bare
`{"_id": ...}` pointer; resolving it to a real name would mean fetching
a separate 127 MB national dataset (20,880 real residential areas) just
to label one field — disproportionate next to Austria's BEV register,
whose own municipality lookup was a 51 KB table bundled in the same
download. Kept on `.raw` for any caller who wants to resolve it
themselves.

**Licence: Creative Commons Attribution 4.0 International**, confirmed
live directly from the dataset's own page on data.gov.lt.

**No credentials required** — every claim above came from a fully
unauthenticated GET request.

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

Six states are live, all verified against real data — the first three
2026-07, the last three 2026-08-20: **Hamburg** (130 features, `Point`
geometry, dates `DD.MM.YYYY`, via WFS), **Brandenburg** (487 features,
`LineString`, dates ISO, via WFS), **Saxony** (1,531 real closures + 813
diversions, `LineString`, dates `DD.MM.YYYY` with an occasional real hour
suffix, via a direct GeoJSON download — Saxony has no queryable service
at all), **Baden-Württemberg** (928 features, `LineString`, real
time-of-day ISO 8601 dates with a UTC offset — the one state in this
cluster with a genuine time component — via a real direct GeoJSON
download, MobiData BW), **Schleswig-Holstein** (1,116 features,
`LineString`, via a genuinely GML-only WFS parsed client-side — see
below), and **Rheinland-Pfalz** (999 features, `Point`, via a real WFS
that genuinely aggregates several sources on one shared platform — see
below). Hamburg, Brandenburg and Baden-Württemberg publish under
**Datenlizenz Deutschland — Namensnennung — Version 2.0** (dl-de/by-2-0);
Saxony and Schleswig-Holstein under **Creative Commons Attribution 4.0
International**; Rheinland-Pfalz's licence is genuinely unconfirmed (see
below). Five of six confirmed directly from each service's own
`GetCapabilities`/catalogue metadata, with exact attribution wording
baked into each state's field-map entry.

**Rheinland-Pfalz's real WFS layer is a genuine multi-source
aggregation, not RLP's own data alone — found and scoped, not assumed.**
`maps.mobilitaetsatlas.de`'s `mwvlw:baustelle` layer (run directly by
RLP's own transport ministry, MWVLW) states a real `quelle` (source)
property per feature — live grouping found 999 records genuinely from
`"Verkehrsbehörden in Rheinland-Pfalz"` (RLP's own state/county traffic
authorities, real per-record contact emails down to individual
Kreis/municipal level — comprehensive, not state-network-only), but
also 1,201 from `"Autobahn GmbH"`, 652 from
`"Verkehrsministerium Baden-Württemberg"` and 220 from
`"Stadt Karlsruhe - Tiefbauamt"` — all three already covered by this
SDK's own separate providers. A real `cql_filter` (a new
`StateFieldMap.extra_params`, passed through to
`OGCFeaturesClient.get_wfs_features`) scopes this entry to RLP's own
real contribution only, the same discipline already applied when
Schleswig-Holstein's own shared WFS was found to also carry
Niedersachsen/Mecklenburg-Vorpommern data. This GeoServer also only
registers `application/json` for this layer, not
`OGCFeaturesClient`'s own `application/geo+json` default — a real
`InvalidParameterValue` exception confirmed live, handled via a new
`StateFieldMap.output_format` override (both are structurally identical
GeoJSON here — only the registered MIME type differs). Real `von`/`bis`
dates state a bare `"Z"` UTC suffix (e.g. `"2026-05-25T18:00:00Z"`) —
the same `"iso_datetime"` format Baden-Württemberg's own explicit-offset
dates use, with `Z` rewritten to `+00:00` first for Python 3.10
compatibility (this SDK's own minimum). **Licence genuinely
unconfirmed, not "none exists"** — `govdata.de`, the WFS's own
`GetCapabilities` `AccessConstraints` (empty), and `open.rlp.de`'s own
API (a real `403`, not routed around) were all checked.

**Schleswig-Holstein is genuinely GML-only — parsed anyway, not routed
around.** Its real WFS (`dienste.gdi-sh.de`, run by LBV.SH) rejects
`OUTPUTFORMAT=application/json` outright, the same shape Mecklenburg-
Vorpommern's and Saxony-Anhalt's own dedicated WFS already reject (see
below) — but unlike those two, Schleswig-Holstein has a real, confirmed
open licence, so this SDK parses its real GML directly via the standard
library's own `xml.etree.ElementTree` (`streetworks.ogc.germany`'s own
`_fetch_lbv_sh_gml`/`_parse_lbv_sh_gml`) instead of parking it. Geometry
is real `gml:MultiCurve`/`curveMember`/`LineString` in the service's own
stated native EPSG:25832 (ETRS89/UTM32N), reprojected client-side via
the same standard UTM32N transform already verified for Denmark. Every
real MultiCurve wraps exactly one curveMember (1,114/1,116 real features
carry one; the other 2 carry none). One real field states a combined
start/end range, not two separate fields — `Dauer_der_Bauphase`
(e.g. `"2026-08-03 23:00:00 bis 2026-09-11 22:59:00"`, German "bis" =
"until") — split client-side into synthetic start/end properties before
the shared converter ever sees them. Real road-class prefixes span
`B`/`L`/`K` (federal/state/county) and a bare `"G"` (Gemeindestraße,
municipal — 466/1,116 real records, the largest single group, a real
but low-information value since only the class letter is stated, not an
actual road name) — genuinely comprehensive, reaching down to municipal
roads by classification.

**This same WFS also carries Niedersachsen and Mecklenburg-Vorpommern
feature types — found, checked, deliberately not built.** Both are
genuinely reachable unauthenticated off the identical endpoint (142 and
77 real features respectively), but neither has its own confirmed open
licence: Niedersachsen's own real roadworks dataset traces to a
Mobilithek marketplace "offer" with no stated licence and no
independent open republish found on any Niedersachsen state portal —
the same gated-at-origin shape already parked for NRW's own roadworks
route. Reachability via a neighbouring state's operational mirror
doesn't establish a licence the origin state itself hasn't granted, so
neither is built — Schleswig-Holstein's own real CC BY 4.0 licence
covers only its own state's layer.

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

**Bremen — a real, live, well-shaped feed found, then ruled out on
licence, not access.** `vmz.bremen.de`'s own real "Mapsight" map app
(found by reading its bundled JS config for the real relative path,
`geojson/construction-work.geojson`) is genuinely open and keyless — 241
real features, a real `GeometryCollection` (`Point` + `LineString`, the
same shape `from_berlin` already handles), real ISO 8601 dates with an
explicit UTC offset. But the page's own footer states the licence
directly: **Creative Commons BY-NC-ND** (non-commercial, no-derivatives)
— an explicit restriction, the same conflict-with-this-SDK's-own-MIT-
licence category Saxony-Anhalt's own roadworks feed already sits in, so
this is parked for the same reason, not a technical blocker.

**A real, unstarted next step, not a dead end.** Relicensing this SDK
itself cannot fix this: the SDK's own licence governs its code, not
Bremen's copyright in the data, and NC/ND are two separate problems —
adding an attribution clause wouldn't make the feed NC-compatible (NC
restricts commercial use, unrelated to attribution, and making the
whole package non-commercial to accommodate one provider would regress
every other one), and no downstream licence choice can lift an ND
restriction on the source data itself — only the rights holder can do
that, or the SDK could stop transforming/redistributing it entirely.
The real move, matching the same open-question status Spain's Catastro
already has in this SDK: a direct enquiry to VMZ Bremen asking whether
they'd grant explicit permission for an attributed, open-source SDK to
build a connector — many German public-sector CC BY-NC-ND footers are
generic site-wide defaults, not a bespoke per-dataset decision. Not yet
contacted — the project owner's own next step, to revisit.

**Hesse and Thüringen — real state-wide platforms found, no queryable
endpoint discovered within reasonable effort.** Hesse's
`verkehrsservice.hessen.de` (a real Vue SPA, TraffGo Road-powered) and
Thüringen's `baustellen.tlbv.de/app/Bis/` (a real Novasib/Kendo UI app)
were both found live, but neither states a fetchable data URL in its
own bundled JS the way Bremen's/Saarland's own apps do — genuinely
unresolved, not ruled out, a real next step if picked back up. A real,
separate, *municipal* Frankfurt am Main WFS was found for Hesse
(`geowebdienste.frankfurt.de/Baustellen`, `dl-by-de/2.0`, confirmed via
`opendata.hessen.de`) — city-scoped, not this cluster's state-wide
concern, noted but not built.

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
`"Sachsen"`/`"Baden-Württemberg"`/`"Schleswig-Holstein"`) is **endpoint
provenance, not a record field** — there is no `bundesland` property on
any state's features; the state is known because each field map is
bound to one state's own endpoint, the same mechanism National
Highways' `administrative_area="National Highways"` uses, not Spain's
`provinces()` reading a real per-record field.

**A third real per-feature-identifier shape, Baden-Württemberg's own.**
Neither a meaningful `ID` property (Brandenburg's shape) nor the GeoJSON
feature's own `id` (Hamburg's shape) — Baden-Württemberg's real
identifier lives in a lowercase `id` *property* instead
(`"1487640-1487641-1487644-3508083-sperrung.001"`), handled via a new
`StateFieldMap.id_field` override rather than stretching the existing
two-shape fallback further.

Field names are UTF-8 throughout, umlauts and `ß` included — one real
Brandenburg field name is `Straßenummner` (double "n", a typo in the
source schema itself, confirmed live — not `Straßennummer`). Hamburg has
no road number/name field of any kind (checked all 130 real features) and
no single clean status field either — six independent boolean flags
(`iststoerung`, `istfreigegeben`, `istoepnveingeschraenkt`, ...) instead,
all preserved on `.raw`, none forced into the common model. See
`streetworks/ogc/germany.py`'s module docstring for the full
field-by-field mapping and every state's exact attribution text.

## Saarland (Landesbetrieb für Straßenbau)

Saarland's own roadworks feed, run by LfS (Landesbetrieb für
Straßenbau) — no credentials. A real state that isn't published through
a WFS at all, so unlike its siblings above this doesn't go through
`streetworks.ogc.germany`'s shared field-map architecture — it's a
bespoke `streetworks.saarland` client instead:

```python
from streetworks.saarland import SaarlandClient
from streetworks.common import from_saarland

with SaarlandClient() as saarland:
    works = from_saarland(list(saarland.iter_roadworks()))
```

**Found by reading LfS's own real public map app's bundled JS — the
same technique that found Lisboa's Condicionamentos endpoint.**
`baustellen.saarland` is a real Leaflet-based map, confirmed live, no
login; its `js/map.js` states two real relative data paths —
`data/baustellen/roadworks_line_geojson.geojson` (used here — real
`MultiLineString` geometry, every vertex kept) and the same 38 records
again as `Point`-only (not consumed, a strict subset).

**38 real features at investigation time (2026-08-20) — genuinely
smaller than this SDK's other German states**, consistent with
Saarland's own small size. Real road-class prefixes found in the free-
text `description` field span `L` (Landesstraße) and `B`
(Bundesstraße) only — no `K`/`A` seen live.

**`roadname` is a real field, genuinely blank on 14/38 records at
investigation time — not a data-quality gap.** Where blank, the real
route number is still stated inside `description` as free text; per
this SDK's "never extract structured data from free text" discipline,
it stays there rather than being parsed out.

**Dates are genuinely naive — no UTC offset stated at all**
(`"2022-11-28T00:00"`), unlike Baden-Württemberg's own real
`+02:00`-suffixed dates on the same shared cluster — localised to
Europe/Berlin via `zoneinfo`, the same date-only-state convention this
cluster already uses throughout.

**Licence genuinely unconfirmed, not "none exists" — three real
sources checked, none confirm.** No entry found on `govdata.de`; the
GDI-DE metadata catalogue search API returned a real `403`; `saarland.de`'s
own general pages returned a real `403` too (a site-wide WAF, not this
dataset specifically — confirmed by the same block on unrelated
`saarland.de` pages, not routed around). The same honest tier Autobahn
GmbH's own licence already sits at in this SDK.

## Dortmund (municipal roadworks, NRW)

The City of Dortmund's own roadworks register — no credentials. This
SDK's first German *municipal* roadworks provider, a genuinely
different tier from the state-level cluster above — opened up because
NRW's own state-level route stays gated (Mobilithek/DATEX, already
parked), but this one real city's own feed isn't:

```python
from streetworks.dortmund import DortmundClient
from streetworks.common import from_dortmund

with DortmundClient() as dortmund:
    works = from_dortmund(list(dortmund.iter_roadworks()))
```

**Found via GOVdata, not assumed from NRW's own state-level gating —
and checked against two other real NRW cities first, not generalised
from one example.** Cologne and Aachen were both checked live and
trace only to Mobilithek marketplace "offer" URLs, no independent open
republish found for either — Dortmund is a genuine exception, not
representative of a wider open NRW-municipal pattern. Its own real
`open-data.dortmund.de` — the same **OpenDataSoft** platform family as
`streetworks.paris`'s own "Chantiers à Paris" — publishes two real,
live, keyless datasets directly, harvested onto Open.NRW/GOVdata but
genuinely served from Dortmund's own infrastructure.

**Two real datasets, not one** — "tagesaktuell" (134 real currently-
active records) and "geplant" (38 real planned records) at
investigation time, identical real schema on both.
`DortmundClient.iter_roadworks` fetches and combines both.

**A real per-record identifier exists — but only via the older, nested
`/api/v2/catalog/...` endpoint, not the newer flat
`/api/explore/v2.1/...` Explore API `streetworks.paris` uses.** Checked
live: the v2.1 Explore API's own flattened records (matching Paris's
own shape) carry no id field at all, the same real gap the plain
`exports/geojson` shortcut has — only the v2 endpoint's `record.id` (a
real, stable per-record hash) survives, so this module uses that
endpoint specifically, not for consistency with Paris's own choice.

**Real, specific fields — not placeholders.** `auftraggeber` (a real
promoter — e.g. `"EB70 - Stadtentwässerung"`, the city's own sewage/
drainage utility; `"Dortmunder Netz"`, the local gas/electricity
network operator; `"Stadt Dortmund"`), `stadtbezirk` (a real Dortmund
city district, e.g. `"Hörde"`, mapped to `location_description` — a
coarser-than-street location fact, not endpoint-provenance
`administrative_area`, which stays the constant `"Dortmund"`).
`art_der_baumassnahme` combines street, works type and restriction in
one real free-text field (e.g. `"Stiegenweg 12 - Kanalreparatur //
Vollsperrung"`) — no clean separate street field exists, the same
honest gap NYC/Chicago/Paris's own permit registers already carry.

**Geometry is already WGS84** — `geografische_koordinate` states
`{"lon": ..., "lat": ...}` degrees directly, no reprojection needed.

**Dates are date-only** (`"2026-08-20"`) — localised to Europe/Berlin
via `zoneinfo`, the same convention this SDK's other German date-only
sources already use. `status` carries the real literal source value
(`"tagesaktuell"`/`"geplant"`), used to decide `actual_start` (only
genuinely current, not merely planned, records get one).

**Licence: Datenlizenz Deutschland - Zero - Version 2.0
(dl-zero-de/2.0), confirmed** directly from GOVdata's own harvested
metadata for this exact dataset — effectively public domain, no
attribution even required.

**No credentials required** — every claim above came from a fully
unauthenticated GET request.

## Zentraler AdressService Hamburg (GAGES)

Hamburg's own street gazetteer, run jointly by the Statistisches Amt
für Hamburg und Schleswig-Holstein (StA-Nord) and the Landesbetrieb
Geoinformation und Vermessung (LGV) — no credentials. This SDK's first
German state-level streets/gazetteer coverage, picking up the "state
fan-out" fallback path Germany's own national investigation left open
(see [`docs/germany-streets-investigation.md`](../germany-streets-investigation.md)):

```python
from streetworks.hamburg import HamburgStreetsClient
from streetworks.common import from_hamburg_street

with HamburgStreetsClient() as hamburg:
    streets = [from_hamburg_street(f) for f in hamburg.iter_streets()]
```

**Berlin was checked first — genuinely blocked, not ruled out.**
Berlin's own GDI WFS host (`gdi.berlin.de`, serving every real Berlin
state geodata WFS — addresses, street network, everything) is
confirmed live to be down for maintenance across every real path
tried, no ETA stated — a real, reportable connectivity failure,
confirmed via multiple different service paths and repeated retries,
not routed around. This lines up with a real, separately-confirmed
fact: Berlin's older FIS-Broker system was fully shut down 1 December
2025 in favour of new open-source infrastructure, so this outage
plausibly reflects an active migration rather than a permanent
closure. Two real candidate datasets were found on `daten.berlin.de`
before hitting the wall (`Adressen Berlin`, `Detailnetz
Straßenabschnitte`) — worth a retry once the host is back.

**Not the archived WFS this dataset's own catalogue page still
lists.** Hamburg's catalogue entry (`suche.transparenz.hamburg.de`)
lists two older WFS snapshots (`DOG`/`GAGES` XML, from the shut-down
FIS-Broker era) alongside a real, current OGC API Features landing
page — this module uses the live one, resolved to
`qs-api.hamburg.de/datasets/v1/gages_vereinfacht`, confirmed live with
two real collections (`hauskoordinaten`, `strassen`).

**9,639 real Hamburg street records, confirmed live 2026-08-20 — 100%
carrying a real name.** Real Point geometry, genuinely reprojected
server-side to WGS84 by this API's own default (the collection's own
storage CRS is `EPSG:25832`, confirmed live via its metadata, but a
plain unparametrised request already returns real WGS84 coordinates).

**Pagination: real, standard OGC API Features `links` with `rel:
"next"`**, followed directly rather than reconstructing offsets — the
same "follow the real link until it's genuinely absent" discipline
already applied to Amsterdam's WIOR and Flanders' Straatnamenregister.

**`administrative_area` is a per-provider constant, `"Hamburg"`.** The
real per-feature `geographicidentifier` field states a finer Ortsteil
(district) code inline (e.g. `"(OT 0603)"`), but no separate
code-to-name lookup collection exists on this API — kept `.raw`-only
rather than parsed into a fabricated field.

**Licence: Datenlizenz Deutschland - Namensnennung - 2.0** (Germany's
own standard open-data attribution licence), confirmed live from this
dataset's own CKAN metadata on `suche.transparenz.hamburg.de`.

**No credentials required** — every claim above came from a fully
unauthenticated GET request.

## WFS BB-BE Gazetteer (Brandenburg)

Brandenburg's own street gazetteer, run by LGB (Landesvermessung und
Geobasisinformation Brandenburg) — no credentials. This SDK's second
German state-level streets/gazetteer coverage, continuing the "state
fan-out" fallback path Germany's national streets investigation left
open:

```python
from streetworks.brandenburg import BrandenburgStreetsClient
from streetworks.common import from_brandenburg_street

with BrandenburgStreetsClient() as bb:
    streets = [from_brandenburg_street(r) for r in bb.iter_streets()]
```

**52,902 real street records, confirmed live 2026-08-20 via
`resultType=hits`** — much larger than Hamburg's 9,639, consistent with
Brandenburg's far greater land area. Found via Brandenburg's own
geoportal metadata record for "Deutschland-Online-Gazetteer Brandenburg
mit Berlin (WFS)", resolving to `isk.geobasis-bb.de/ows/gazetteer_wfs`.

**A real, confirmed GML-only WFS — no JSON output format exists,
checked live rather than assumed.** `GetCapabilities` lists only GML
output formats for this feature type; a real
`outputFormat=application/json` request was tried and rejected with a
genuine `400` (`"This WFS is not configured to handle the output/input
format 'application/json'"`). This module doesn't use the shared
`OGCFeaturesClient` (JSON-first) and instead parses the real GML/XML
response directly via the standard library's own `xml.etree.ElementTree`
— no `lxml`, matching this SDK's stdlib-plus-httpx convention.

**Real, comprehensive per-record fields, richer than Hamburg's own
simpler schema.** `strassenname` (the real name), `postleitzahl`
(postal code), `postOrtsteil`/`ortsteilname` (real district names, not
just codes), `land` (the real German state code), and a real
`strassenschluessel` (structured street key). `administrative_area`
reconstructs the real municipality name from two real, independently-
stated fields — `ortsnamePost` + `zusatzOrtsname` (e.g.
`"Brandenburg"` + `"an der Havel"` → `"Brandenburg an der Havel"`) —
confirmed live to match the same record's own
`gemeindename_normalisiert` field, not a guessed concatenation.

**No geometry — the only real geometry this source states is a
`Polygon`** (the street's areal extent, in `geographicExtent`) —
`GeometryGrade.ABSENT` on every real `Street`, the same discipline
`from_marousi_street` already established for its own polygon-only
Greek source; the real polygon GML is preserved unmodified on `.raw`.

**A real, live-confirmed, non-exhaustive Berlin presence.** The
service's own abstract states it directly: data covers both Brandenburg
and Berlin (Berlin's own contribution sourced from Geoportal Berlin's
Amtliche Hauskoordinaten) — confirmed live in a real 500-record sample,
8/500 rows genuinely carry `land=11` (Berlin's real ISO 3166-2:DE
code), the rest `land=12` (Brandenburg's own code). This build is
scoped and documented as Brandenburg's own provider — the real Berlin
content is a genuine bonus, not claimed as exhaustive Berlin coverage
(unlike this SDK's own Hamburg build, which is a complete state
gazetteer). Berlin's own dedicated GDI WFS host remains genuinely
blocked (see the Hamburg section above) — worth a retry once it's back.

**Licence: Datenlizenz Deutschland - Namensnennung - 2.0**, confirmed
live directly from this WFS's own `GetCapabilities` `AccessConstraints`
element, with a real, stated attribution string: *"© GeoBasis-DE/LGB,
dl-de/by-2-0, (Daten geändert)"*.

**No credentials required** — every claim above came from a fully
unauthenticated GET request.

## GeoSN Hauskoordinaten (Saxony)

Saxony's statewide address-point export, published by GeoSN
(Staatsbetrieb Geobasisinformation und Vermessung Sachsen) — no
credentials. This SDK's third German state-level streets/gazetteer
provider, completing the "state fan-out" Germany's national streets
investigation named (Hamburg, Brandenburg, Saxony, Berlin):

```python
from streetworks.geosn import GeoSNStreetsClient
from streetworks.common import from_geosn_street

with GeoSNStreetsClient() as geosn:
    streets = [from_geosn_street(r) for r in geosn.iter_streets()]
```

**Not the shared Deutschland-Online-Gazetteer (DOG) WFS Hamburg and
Brandenburg both use — checked and confirmed Saxony genuinely doesn't
participate in it.** The DOG service's own real member states are
Brandenburg and Berlin only (confirmed live via its own abstract);
Saxony's own ALKIS WFS (`geodienste.sachsen.de/aaa/public_alkis/vereinf/wfs`,
confirmed live) publishes only cadastral parcels, buildings, land use
and administrative boundaries — no street or address feature type at
all. Saxony instead publishes its own address-point data as a real
statewide bulk CSV/text export.

**A genuinely large real file — the largest single download this SDK's
German-state cluster has needed (~206 MB uncompressed, ~51 MB
zipped).** 990,090 real address-point rows, confirmed live, 100%
carrying a real street name. This is address-point data, not a
dedicated street register — one row per real address, not per street —
so the client itself deduplicates by `(gmdschl, strschl)` (municipality
code + street code), keeping the first real row's own coordinate as a
representative point for the whole street, the same "one real,
arbitrarily-chosen-but-genuinely-stated point stands for the whole
entity" discipline `from_oslo`/`from_canton_zurich`/
`from_brandenburg_street` already apply to their own polygon-first-
vertex case. 42,824 real distinct (municipality, street) combinations,
confirmed live.

**CRS: real ETRS89 / UTM zone 33N (`EPSG:25833`), confirmed live —
zone 33, not 32 (unlike Denmark's DAR).** The file's own `zone` column
reads `33` on every row checked; reprojected client-side via a new
closed-form Transverse Mercator inverse (`streetworks.common._utm33n`,
no `pyproj`), cross-checked against a real address in Dolsenhain
(Frohburg, near Leipzig) before shipping — the axis order is the
standard `(Easting, Northing)`, confirmed by the same bounds check,
unlike Lithuania's own UTM-family source, which needed a swap.

**`administrative_area` carries the real `gmd` (municipality name)
field directly** — already a resolved name, no lookup or
reconstruction needed, unlike Brandenburg's own two-field
reconstruction.

**Licence: Datenlizenz Deutschland - Namensnennung - 2.0**, confirmed
live from GeoSN's own open-geodata FAQ page — explicitly stated to
permit commercial reuse.

**No credentials required** — every claim above came from a fully
unauthenticated GET request.

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

**Two feeds, and the initial assumption about them turned out
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

**Roadworks filter, evidenced not the initially assumed upstream
values.** `TrafficMessage_RoadWorks`/
`TrafficMessage_Incidents` were first assumed to be the upstream OCIT object types, but those
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

**The first-tried URL is dead — checked live before
writing any code, not assumed working.** `informo.munimadrid.es` (the
initial URL, and the host still named in the open-data portal's own
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
type guess** — settling two open questions, with real
evidence: `cortes de carriles` (lane closures, 7/217 live) and
`operación asfalto` (asphalt resurfacing, 2/217) are both real and
common, but neither is flagged `es_obras` by Madrid's own system —
excluded. The asphalt-operations exclusion is a genuine surprise (it
reads like roadworks to a human) but the source's own classification is
trusted over what the label sounds like, the same discipline Chicago's
`worktype` filter and Berlin's `subtype` filter already apply.

**`source_grade="operator"`, not the `traveller_info` first
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
itself) — not just carried over from an earlier assumption. The exact
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

Convert a geocoding hit to the shared cross-provider gazetteer model:

```python
from streetworks.common import from_ban

gazetteer_address = from_ban(hits[0])
```

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

Convert a `type="adres"` location to the shared cross-provider gazetteer model:

```python
from streetworks.common import from_bag

gazetteer_address = from_bag(hits[0])
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

Convert an address hit to the shared cross-provider gazetteer model:

```python
from streetworks.common import from_kartverket

gazetteer_address = from_kartverket(hits[0])
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
address API and SSR, rather than assuming they matched just because
they're the same agency).

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

Convert either shape to the shared cross-provider gazetteer model:

```python
from streetworks.common import from_nvdb

segment_or_street = from_nvdb(sequences[0])  # Segment or Street, see module docstring
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

CRS is **EPSG:5973, not the initially expected EPSG:25833** — see
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

**Built second among the Nordic capitals. Live verification found a
different real source than either early
guess** (an Origo/Bymiljøetaten GeoServer layer, or the national
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

**Resolves an open question from earlier investigation, not assumed.**
Helsinki was flagged "least urgent" among the Nordic capitals, and
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
data yourself: the WFS's own paging **does** work (an earlier report of
broken paging traced to an unencoded `+` in `outputFormat`, decoded
server-side as a space) — but **PDOK's WFS proxy silently ignores `CQL_FILTER`
entirely**, while Rijkswaterstaat's own WFS filters correctly on the
identical query, so this client queries Rijkswaterstaat directly and
only uses PDOK's Atom feed for the (unaffected) bulk GeoPackage download.
CRS is EPSG:28992, matching BAG; licence is CC0 1.0 Universal, matching
BAG too — confirmed from the Atom feed's own `<rights>` element, not a
portal page.

Convert a road segment to the shared cross-provider gazetteer model:

```python
from streetworks.common import from_nwb

gazetteer_segment = from_nwb(segments[0])
```

## Amsterdam (WIOR)

Gemeente Amsterdam's own public-space-works coordination register —
**WIOR** (Werken in de Openbare Ruimte, "Works in the Public Space") —
no credentials. This SDK's first Dutch *municipal* roadworks provider,
a sibling to the existing national coverage (NDW's DATEX II feed, NWB's
road network, BAG's addresses) at city scale — the same national-plus-
one-city shape Denmark (Vejdirektoratet + Copenhagen), Norway (Vegvesen
+ Oslo) and Switzerland (Kanton Zürich + Stadt Zürich) already have:

```python
from streetworks.amsterdam import AmsterdamClient
from streetworks.common import from_amsterdam

with AmsterdamClient() as amsterdam:
    works = from_amsterdam(list(amsterdam.iter_roadworks()))
```

**Real, live, genuinely keyless REST API on `api.data.amsterdam.nl`**
(Amsterdam's own DSO-API open-data platform, 120+ real datasets) —
confirmed live with a plain unauthenticated `GET`; the dataset's own
catalogue metadata states `"api_authentication": ["OPENBAAR"]` ("public").
**A real path quirk found and worked around**: the dataset's own
published OpenAPI path is `/wior`, relative to its own sub-router, not
the API root — the real, live data endpoint is the doubled
`https://api.data.amsterdam.nl/v1/wior/wior/` (confirmed live: the
undoubled path 404s).

**10,063 real works records, confirmed live 2026-08-18** — real project
names (`"Noordzeeweg (tussen Luvernes en Hornweg) T-stukken vervangen"`),
100% carrying real start/end dates. A real, live-confirmed data-quality
quirk kept rather than normalised away: one real record carries
`hoofdstatus: "Yes"` instead of a genuine Dutch status value —
`from_amsterdam` treats `hoofdstatus` as an open string, never validated
against a closed enum.

**Geometry is real `Polygon`/`MultiPolygon` only** — genuinely no
Point/LineString rows found live (a live 1000-record sample: 867
Polygon, 133 MultiPolygon). The first ring's first vertex is used as a
representative `Coordinate.value`, the same discipline `from_oslo`/
`from_canton_zurich` already apply to their own polygon case; the full
raw geometry stays in `WorksSite.raw`. **Unlike Denmark's DAR, this
endpoint genuinely honours server-side reprojection to WGS84** — a real
`Accept-Crs: EPSG:4326` request header is confirmed live to be honoured
(the response's own `Content-Crs` header echoes it back, and real
Amsterdam coordinates come back), so no client-side reprojection is
needed here.

**`date_confidence` is `VERIFIED` (with `actual_start`/`actual_end`
populated) only when `hoofdstatus == "Uitvoering"`** ("execution" — the
dominant real value, 774/1000 in a live sample) — every other value
falls back to `ESTIMATED`, the same "only a confirmed-active status
earns VERIFIED" discipline this SDK applies everywhere else.
`location_description` carries the real `projectnaam` (project name),
confirmed live to usually embed real street/location context in its own
text — the closest real fit to an address field on a schema that has
none. `promoter` and `street_ref` are never populated — no
organisation/contractor or street-identifier field exists anywhere in
this schema.

**Licence: Gemeente Amsterdam's own general open-data terms, checked
live rather than assumed CC0.** The dataset's own catalogue metadata
states `"license": "public"`; Gemeente Amsterdam's general geodata terms
page (`maps.amsterdam.nl/open_geodata/terms.php`, confirmed live) grants
free use and reuse "voor elk wettig doel" ("for any lawful purpose"),
commercial and non-commercial, with attribution appreciated but
explicitly not required — functionally CC0-equivalent in permissiveness,
but not stated under that specific label anywhere checked, so this SDK
doesn't assert one.

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

Convert either shape to the shared cross-provider gazetteer model:

```python
from streetworks.common import from_bdtopo

segment_or_street = from_bdtopo(segments[0])  # Segment or Street, see module docstring
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

## French département roadworks (Routes Départementales)

Individual French *départements* each publish their own Routes
Départementales (RD) roadworks — the majority of the French road
network by length, and genuinely separate from Bison Futé's own
non-concessionary national network. `streetworks.opendatasoft` is a
generic OpenDataSoft Explore API v2.1 client, plus a declarative
per-département field-map registry
(`streetworks.opendatasoft.france_departements`) — the same shape
`streetworks.ogc.germany` already established for German state
roadworks, adding a département is writing a new field-map entry, not
a new converter.

```python
from streetworks.common import from_departement_roadworks
from streetworks.opendatasoft.france_departements import SARTHE, DepartementRoadworksClient

with DepartementRoadworksClient() as france:
    records = france.fetch("Sarthe")

works = from_departement_roadworks(records, SARTHE)
```

**Extracted now, not from day one — the same sequence that produced
`SodaClient`.** `streetworks.paris`'s own module docstring already
named the threshold: "bespoke first, extracted only when a second
OpenDataSoft-backed provider needs the identical shape." That threshold
is now real — Sarthe, Loire-Atlantique and Hauts-de-Seine's own real
département feeds all independently turned out to be genuine
`/api/explore/v2.1/catalog/datasets/{dataset}/records` deployments,
confirmed live to share byte-for-byte the same pagination shape
(`results`/`total_count`, `limit`/`offset`) and even the same real
geometry field-naming convention (`geo_shape`/`geo_point_2d`) Paris's
own dataset uses. Paris's own `ParisClient` is left exactly as it was —
not retrofitted, since it already works and retrofitting it would
carry real regression risk for no functional gain.

Three départements are live, all verified against real data
(2026-08-20): **Sarthe** (9 real features, `LineString`, structured ISO
datetimes with an explicit UTC offset — the only département checked
so far with real structured dates), **Loire-Atlantique** (21 real
features, `Point` only, described by its own publisher as real-time),
and **Hauts-de-Seine** (122 real features, `LineString`/
`MultiLineString`).

**A real fourth département was found and set aside, not built.**
Corrèze's own WFS (`ogc.geo-ide.developpement-durable.gouv.fr`, a real
national DREAL geo-infrastructure) is genuinely GML-only — its
`GetCapabilities` states only GML output formats, the same real shape
already handled for Schleswig-Holstein in `streetworks.ogc.germany` —
not out of scope in principle, just not built this round. **Côtes
d'Armor is real, live, and by far the richest département found (5,292
real features) but doesn't fit this OpenDataSoft-specific field map at
all** — a genuine REST API over the Koumoul/`data-fair` platform
(`datarmor.cotesdarmor.fr/data-fair/api/v1/datasets/...`), with its own
real rich fields (`ROUTE`, `PRDEBUT`/`PRFIN`/`ABSCISSEDEBUT`/
`ABSCISSEFIN` — real French *Point de Repère* kilometre-marker
referencing, `CIRCULATION`, `COMMUNE`, `NUMDOSSIER` — a real per-record
case reference) — tracked separately, a real next step, not built this
round.

**No structured dates on two of three départements — a genuine finding,
not a converter gap.** Loire-Atlantique's real date range is French
free text only (`ligne4`, e.g. `"Du 18/08/2026 au 20/08/2026"`);
Hauts-de-Seine's own `date_travaux` is similarly free text, often
spanning years (e.g. `"Travaux d'assainissement début 2026 et travaux
concessionnaires jusqu'à fin 2029"`) or `None` outright — Hauts-de-
Seine's real register turns out to be a capital-works/infrastructure-
project index (tramway extensions, cycle-lane programmes; its own real
`avancement` field states a project phase — `"Travaux en
cours"`/`"Travaux programmés"`/`"Projet à l'étude"`), not a day-to-day
closures feed. Per this SDK's "never extract structured data from free
text" discipline, both carry `DateConfidence.UNKNOWN` throughout —
honest, not a bug.

**`value`/`points` are two independently real, stated facts, not one
derived from the other** — the same shape `from_berlin`'s own real
`GeometryCollection` (`Point` + `LineString`) handling already
establishes: `Coordinate.value` is the département's own real
representative point field (`geo_point_2d` for Sarthe/Hauts-de-Seine;
`localisation` for Loire-Atlantique — a real per-dataset name, not an
OpenDataSoft platform standard, confirmed live), and `.points` (when a
real `geo_shape` line exists) is the separately real line geometry —
`points[0]` is never asserted to equal `value`.

**Licence: Licence Ouverte / Open Licence 2.0 (Etalab), confirmed for
all three** — France's own standard open licence, the same one already
confirmed for Bison Futé, directly from each dataset's own catalogue
metadata on `data.gouv.fr`.

## Trafikverket (Sweden roadworks) — Credentials wanted

Sweden's national roadworks source — the Swedish Transport
Administration's own `Situation`/`Deviation` API. **Not a DATEX II
serialisation** — Trafikverket's own request/response envelope (XML in,
JSON out), so this parses onto the shared `Situation`/`SituationRecord`
models directly rather than reusing the streaming DATEX XML parser.

```python
from streetworks.datex2.trafikverket import TrafikverketClient
from streetworks.common import from_datex2

with TrafikverketClient(api_key=api_key) as trafikverket:  # requires an API key
    for situation in trafikverket.iter_situations():
        works = from_datex2(situation, territory="Sweden")
```

**Confirmed live, credential-free, without ever pulling real data.** A
deliberately invalid key against the real endpoint
(`api.trafikinfo.trafikverket.se/v2/data.json`) returns a genuine,
structured rejection, not a generic error page — confirming the
endpoint, the request envelope shape, the `Situation` object name, and
schema version `1.5` all live, independent of any documentation page's
own claims. Better-confirmed than most Credentials-wanted scaffolds at
this stage for exactly that reason.

**Field names are documented, not verified** — cross-referenced across
Trafikverket's own API console description, a real published example
query, and independent third-party client libraries (C#, R) that all
agree on the same field set (`Header`, `Message`, `MessageType`,
`MessageCode`, `RoadNumber`, `Geometry.WGS84`, ...). Trafikverket's own
description of `Situation` states it covers "traffic messages, road work
(vägarbeten), accidents, restrictions" — so roadworks are genuinely in
scope — but **no confirmed value distinguishes a roadworks `Deviation`
from any other kind** yet. Rather than guess, `MessageType` is preserved
verbatim and `iter_roadworks()` honestly returns an empty list against
real data until a real credentialed pull confirms the discriminator —
use `iter_situations()` and inspect `record_type` directly in the
meantime.

**Licence: CC0 1.0 Universal (Public Domain Dedication)**, confirmed via
the catalogue's own per-dataset licence facet — the least restricted
tier in this SDK, no attribution required. Credentials: free,
self-service registration at
[data.trafikverket.se](https://data.trafikverket.se/) or via
[Trafiklab](https://www.trafiklab.se/api/other-apis/trafikverket/),
issuing an API key (not Basic Auth). See
[`docs/providers/index.md#credentials-wanted`](index.md#credentials-wanted)
for the condensed table entry.

## Stockholm (Trafikkontoret) — Credentials wanted

Stockholm's own city geodata service — the least-confirmed
Credentials-wanted scaffold in this SDK, one phase earlier than
Trafikverket above.

```python
from streetworks.stockholm import StockholmClient

with StockholmClient(api_key=api_key) as stockholm:  # requires an API key
    capabilities = stockholm.get_wfs_capabilities()  # nothing more is confirmed yet
```

**Every real data-fetching surface tested returns a genuine `HTTP 401`
before any dataset name, layer, or field is ever revealed** — unlike
South Australia (whose layer definition is public) or Trafikverket
(whose object type and fields are confirmed via documentation), no real
schema of any kind has been seen for Stockholm. Both WFS `GetCapabilities`
and WMS `GetCapabilities` (metadata only, no data) return a structured
401 (`text/plain`, *"You must provide a valid key to consume this API."*)
from Trafikkontoret's own geodata service
(`openstreetgs.stockholm.se`) — confirmed live, not assumed.

**A real, promising-sounding lead traced back to a dead end, not left
unchecked.** Stockholm's open-data catalogue (`dataportalen.stockholm.se`)
has a non-functional full-text search — a nonsense search term returns
the identical record count as no filter at all, so no dataset could be
located that way. A lead about "a map that coordinates roadworks to
minimise regional traffic impact" traces back to the Regionala
Trafikgruppen, which resolves to the already credential-parked
**national** Trafikverket system above, not a separate Stockholm
dataset — so it doesn't add new disjoint coverage. **Whether a roadworks
(`vägarbete`) dataset exists on this platform at all is genuinely
unresolved** — not confirmed present, and not confirmed absent either.

**Auth mechanism partially evidenced, not fully confirmed.** The one
real documented example on Trafikkontoret's own getting-started guide
(a working Parking-API query) uses `apiKey=<key>` as a query parameter —
used here on the WFS endpoint since it's the only real evidence
available, but unconfirmed for WFS/OGC API specifically. Licence:
unconfirmed — no dataset has ever been reached to check one against.
Credentials: an API key: registration path found via the site's own
navigation, but the exact self-service page returned a 404 — contact
`api.it.tk@stockholm.se` or navigate the portal's own menu from
[openstreetgs.stockholm.se/home/](https://openstreetgs.stockholm.se/home/).
See [`docs/providers/index.md#credentials-wanted`](index.md#credentials-wanted)
for the condensed table entry.

> Ireland — MapRoad Roadworks Licensing (documented, unavailable) moved
> to its own page, [`docs/providers/ireland.md`](ireland.md), once
> Ireland got a real, live provider (Monaghan) alongside it.

> Greece (documented, unavailable) moved to its own page,
> [`docs/providers/greece.md`](greece.md), once Greece got a real,
> live provider (Marousi) alongside it.

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

## IDEE Transportes (Spain national road network)

Spain's national road-transport network, published by **IGN (Instituto
Geográfico Nacional)** over IDEE's INSPIRE WFS — this SDK's first
`streets` gazetteer coverage for Spain, added after the international
gazetteers strand above had already been declared closed. A different
agency and data class from this SDK's existing Spanish roadworks
coverage (DGT, Consell de Mallorca, SCT) — do not conflate.

```python
from streetworks.idee import IdeeTransportesClient

with IdeeTransportesClient() as idee:
    roads = list(idee.iter_roads())
    print(roads[0].name, roads[0].national_road_code, roads[0].unresolved_links)
```

Convert to the shared cross-provider gazetteer model:

```python
from streetworks.common import from_idee

street = from_idee(roads[0])
```

**Built directly from a prior, dedicated investigation
(`docs/inspire-gml-investigation.md`) that had found the real shape but
never shipped it — re-verified live before writing any new code, and
everything it found still held.** That investigation's real, decisive
finding: `RoadLink` — the feature type carrying real geometry — states
no name at all. Checked at the schema level (`RoadLinkType` extends the
shared transport-link base type with an empty `<sequence/>`) and live
(the one schema-legal inline name field is absent on every real
`RoadLink` sampled). The name, road codes, and the list of constituent
`RoadLink`s all live one hop up, on `Road` — this build fetches `Road`
first, then batch-resolves its `RoadLink`s.

**`RESOLVE` doesn't work — confirmed dead both ways by the original
investigation, still true.** Neither the default (no resolve parameter)
nor an explicit `RESOLVE=local` (matching this service's own declared
`ResolveLocalScope=*`) inlines the referenced feature — both leave a
bare `xlink:href`. So `IdeeTransportesClient` never asks for resolve; it
follows the href's own URL fragment (the real `gml:id` after `#`)
directly.

**But WFS 2.0's `RESOURCEID` parameter genuinely accepts a batch —
re-confirmed live for this build.** One
`GetFeature&RESOURCEID=id1,id2,...` request returns every requested
`RoadLink`, geometry included, in a single round trip — **same-type
batching only**: a mixed `RoadLink`+`RoadNode` batch was tried live and
returned a real `HTTP 500`, so this client never mixes feature types in
one `RESOURCEID` call. The real shape per page of `Road`s is therefore
two requests total, not one per `Road`: a paged `GetFeature` for `Road`
(following the server's own stated `next` link, never computed
`STARTINDEX` math), then one batched `RESOURCEID` call covering every
distinct `RoadLink` id that whole page's `Road`s reference.

**A broken cross-reference is confirmed real and non-fatal, not assumed
impossible.** The original investigation found 1 of 3 real
`RoadName→Road` hrefs it followed returned a genuine
`403 OperationProcessingFailed: feature not found` — a stale reference
the service itself generated. `IdeeTransportesClient` treats an
unresolved `net:link` the same way: skipped, and counted on
`Road.unresolved_links`, never raised — `Road.geometry` is `None` only
when every real link on that Road failed to resolve.

**Geometry aggregation follows the same multi-line shape DataVIA's
`StreetLines` already established** — a `Road` genuinely spans several
`RoadLink`s (up to 40 seen live in this build's own sampling), each its
own real `LineString`; `from_idee` puts one part per successfully-
resolved `RoadLink`, in the `Road`'s own stated order, into
`Coordinate.parts`. `streetworks.idee` does not emit a `Segment` per
`RoadLink` — a real classification layer
(`FunctionalRoadClass`/`FormOfWay`/`NumberOfLanes`) does exist one hop
further, confirmed live by the original investigation, but building it
would mean per-attribute-type round trips beyond this bounded two-hop
shape, for data none of this canonical model's three use cases need.

**CRS confirmed live: `EPSG:4258` (ETRS89), genuine lat/lon axis
order** — every real `srsName` is the OGC "http URI" form
(`http://www.opengis.net/def/crs/EPSG/0/4258`); a real vertex
`41.613948 2.291140` places the road in Barcelona, not the
Mediterranean, confirming no swap is needed. No credentials. Licence CC
BY 4.0.

**Coverage confirmed live to include the Balearic Islands (Mallorca) —
but the service's own declared bounding box does not.** `GetCapabilities`
states an `ows:WGS84BoundingBox` reaching only to `3.20°E` for both
`Road` and `RoadLink` — which would exclude part of Mallorca. A real
spatial query proved this metadata wrong: a `fes:BBOX` filter over
Mallorca's own extent (against `RoadLink`, since `Road` itself has no
geometry property to filter on — confirmed live by a real
`InvalidParameterValue` exception naming it) returned real features at
`3.24–3.26°E`, genuinely east of the stated box, near Manacor/Artà. So
the capabilities bounding box understates real coverage — a live query
is the only way to confirm what's actually in scope. Plain KVP `BBOX=`
filtering timed out repeatedly against this server and was abandoned; a
proper `fes:Filter` POST request is what actually works. A different
data class from the existing Consell de Mallorca roadworks provider
covering the same island (registry key `mallorca`) — this is the named
road network, that one is closures/works — no dedup conflict, just two
providers legitimately covering the same island for different purposes.

**Spain's separate INSPIRE Addresses service (Catastro) was investigated
the same day and deliberately not built alongside this.** Its documented
WFS endpoint (`ovc.catastro.meh.es/INSPIRE/wfsAD.aspx`, per its own 2016
spec PDF) no longer responds — every request variant tried, including a
bare `GetCapabilities`, returns a generic error page, not a WFS
response; a bulk ATOM download route is confirmed live and current
instead. More significantly, Catastro's own confirmed licence
(`Licencia.pdf`) explicitly prohibits redistributing the *original* data
over the internet in unmodified form — original data may be used
privately or built into transformed, value-added products, but not
republished as-is — which conflicts with this SDK's usual convention of
committing a real trimmed API-response fixture per provider. Genuinely
unresolved, not silently dropped — see
[`docs/providers/pending.md`](pending.md).
