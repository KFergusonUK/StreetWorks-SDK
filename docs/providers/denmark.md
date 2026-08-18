# Denmark

> Copenhagen is this SDK's first Nordic roadworks coverage, and Denmark's
> first *keyless* coverage — the separate national Vejdirektoratet feed
> (genuine DATEX II 3.2) remains credential-parked (registration issued
> per-dataset, no public data URL exists; see `docs/providers/index.md`'s
> Credentials-wanted table). Do-not-dedupe: Copenhagen and Vejdirektoratet
> are kept as two distinct providers, the same way NYC DOT and WZDx both
> cover the USA without merging. **Streets**: DAR (Danmarks
> Adresseregister), this SDK's first Danish streets/gazetteer provider —
> see below.

## Danmarks Adresseregister (DAR)

Denmark's national named-road register, hosted on **Datafordeleren**
(Denmark's national data-distribution platform), this SDK's first Danish
streets/gazetteer coverage:

```python
from streetworks.dar import DarClient
from streetworks.common import from_dar_street

with DarClient() as dar:
    streets = [from_dar_street(r) for r in dar.iter_streets()]
```

**Not the source originally investigated — the obvious one is being shut
down, found before any code was written.** DAWA (Danmarks Adressers Web
API, `api.dataforsyningen.dk`) was checked first and is genuinely
keyless, with a real national `vejstykker`/`navngivneveje` road-segment
dataset confirmed live (113,826 real features, real WGS84 GeoJSON, real
street names like `"Abel Cathrines Gade"`). But DAWA's own docs page
carries a live warning — *"DAWA lukker"* ("DAWA is closing") — confirmed
via web search: DAWA is being phased out toward **1 October 2026**
(investigated 2026-08-18, six weeks out), superseded by Datafordeleren.
Building a provider against a feed six weeks from shutdown would ship
something already due to break, so **DAR** — the actual successor,
hosted directly on Datafordeleren — was built instead.

**Real, live, genuinely keyless REST endpoint — confirmed directly, not
assumed from Datafordeleren's general portal**, which does push account
creation for its higher-sensitivity registers (CPR, CVR, property
valuation). A plain unauthenticated `GET` against
`https://services.datafordeler.dk/DAR/DAR/3.0.0/rest/Navngivenvej`
returns real national data (`200`, no auth header sent or required,
`Access-Control-Allow-Origin: *`).

**CRS: real ETRS89 / UTM zone 32N (`EPSG:25832`) only — no
server-side reprojection option, confirmed live, not assumed.** A
`srid=EPSG:4326` query parameter (following DAWA's own convention) was
tried and rejected with a real `400`: *"Parameter: srid unrecognized. Did
you mean: id?"*. `streetworks.common.from_dar` reprojects client-side via
a new closed-form Transverse Mercator inverse
(`streetworks.common._utm32n`) — no Helmert datum step needed, since
ETRS89 and WGS84 are coincident at this SDK's stated accuracy (the same
reasoning `streetworks.common._bng`'s own docstring gives for *why* BNG's
case, unlike this one, genuinely does need one). Cross-checked against
DAWA's own real WGS84 output for the same real road (Halvdansvej, kommune
`0217`/vejkode `2844`) before shipping: both agree to within a few
metres.

**A real, three-tier geometry fallback, found live rather than assumed
uniform.** 3/5000 (0.06%) of a live sample carry a real `null` in the
line field (`vejnavnebeliggenhed_vejnavnelinje`) — but 2 of those 3 still
carry a real `vejnavnebeliggenhed_vejtilslutningspunkter` ("road
connection points", WKT `MULTIPOINT`) alongside a real
`vejnavnebeliggenhed_vejnavneområde` ("road name area", WKT `POLYGON`).
The converter prefers the line where stated; falls back to the first real
connection point (`GeometryGrade.PUBLISHED`, not a gap) where there's a
point but no line; and only grades `GeometryGrade.ABSENT` where neither
exists (the third of the three, confirmed live: no line, no point, no
polygon at all). The polygon itself is never read into `Coordinate` —
kept `.raw`-only always, the same discipline `from_marousi_street`/
`from_guernsey_street` already established.

**Real name coverage: 99.96% (4998/5000) in a live sample** — the
highest of any streets provider this SDK has built. Real WKT
`MULTILINESTRING` is genuinely multi-part on most records (a named road
rarely reduces to one unbroken line) — parsed into `Coordinate.parts`,
never a first-part-only shortcut.

**`administrative_area` carries the real `administreresAfKommune`
4-digit kommune code**, kept as the raw code rather than resolved to a
name — no kommune-code-to-name lookup is fetched by this converter.

**Licence: CC BY 4.0, confirmed live** via Datafordeleren's own terms
page (`datafordeler.dk/vejledning/brugervilkaar/danmarks-adresseregister-dar/`):
*"Som bruger af frie grunddata er du underlagt CC BY 4.0 licens"*,
requiring attribution to Klimadatastyrelsen (SDFI's parent authority).

**No credentials required** — every claim above came from a fully
unauthenticated GET request.

## Copenhagen (Gravetilladelser)

Københavns Kommune's own excavation-permit register — real digging
permits granted on public roads or private shared roads across the city:

```python
from streetworks.copenhagen import CopenhagenClient
from streetworks.common import from_copenhagen

with CopenhagenClient() as copenhagen:
    features = list(copenhagen.iter_roadworks())  # raw, undeduped
works = from_copenhagen(features)  # deduped by sagsnr, one Works each
```

**Copenhagen was built first among the Nordic capitals. Live
verification corrected several early guesses before any
code was written.** The first guess was a dataset named "vejarbejde" over
an assumed ArcGIS Hub/OGC API Features backend. Checked directly on
`opendata.dk` (the shared Danish municipal open-data platform,
CKAN/Datopian-backed): the real, live dataset is titled
**"Gravetilladelser"** ("excavation permits") — *"Oversigt over
gravetilladelser givet på offentlige veje eller private fællesveje i
Københavns Kommune"* ("overview of digging permits granted on public
roads or private shared roads in the Municipality of Copenhagen"), per
the dataset's own live CKAN metadata
(`admin.opendata.dk/api/3/action/package_show?id=gravetilladelser`).
Its real backend is a classic **WFS 1.0.0 GetFeature endpoint**, not
ArcGIS/OGC Features:

```
https://wfs-kbhkort.kk.dk/k101/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=k101:gravetilladelser_aktiv_aabne&outputFormat=json&SRSNAME=EPSG:4326
```

Layer `gravetilladelser_aktiv_aabne` ("active, open") is already
server-side filtered to current permits — confirmed live, every one of
2240 real rows carries the literal `sagstype="Gravetilladelser"`, so no
client-side type filter is applied on top of it.

**A real, load-bearing geometry finding not anticipated going in:
this layer mixes `Point`, `LineString` and `Polygon` geometry, and the
same real permit is recorded once per geometry shape it has, not once
per permit.** Grouping the raw 2240 rows by `sagsnr` (the real case/
permit number) gives 1241 distinct real permits; every multi-row permit
has *identical* non-geometry properties across its rows (confirmed
against all 832 real multi-row cases) — a repeated `sagsnr` means "the
same permit, once per geometry representation" (e.g. one `Point` marker
plus one `Polygon` extent for the same real excavation), not several
distinct worksites the way Jersey's `PROJID`/NYC DOT's
`applicationtrackingid` group genuinely separate sites under one
project. Confirmed live: **zero** of the 1241 real permits are
Polygon-only — every one has a `LineString` or `Point` alternative — so
`from_copenhagen` dedupes by `sagsnr`, prefers `LineString` over `Point`,
and never needs to handle a polygon ring at all (cleaner than Paris's
own polygon case, which had no point alternative and had to fall back to
a separately supplied representative-point field; see
[`docs/providers/europe.md`](europe.md)). A secondary, pre-converted-to-
point layer exists (`gravetilladelser_aktiv_aabne_conv_pkt`) but is
confirmed live to cover only 691 of the 1241 real permits (56%) — not
used, since it would silently drop real permits the primary layer has.

**Coordinates are genuine WGS84** (`urn:ogc:def:crs:EPSG::4326`,
confirmed in the response's own embedded `crs` block, honouring the
explicit `SRSNAME=EPSG:4326` request parameter) — real raw GeoJSON
`[lon, lat]` order (confirmed against a real point, `[12.578, 55.640]`),
swapped to this SDK's `(lat, lon)` `Coordinate` convention.

**Real schema (12 fields, confirmed 100% populated, zero nulls across
all 2240 rows)**: `lokation` (free-text address), `sagsnr` (the real
case number, used as `Works.reference`), `projekt_start`/`projekt_slut`
(dates, real Danish `DD-MM-YY` format — e.g. `"04-07-26"`, not ISO-8601,
parsed via a bespoke `strptime`, timezone-naive since none is stated),
`tidspunkt_fra`/`tidspunkt_til` (daily permitted working hours, e.g.
`"07:00"`/`"18:00"`, combined into `operating_window`), `kategori` (the
real works-type enum — Fibernet, EL, Asfaltarbejder,
Brolægningsarbejder, Fjernvarme, Vejafvanding, ...), `gravetype` (which
street element is affected — Kørebane=carriageway, Fortov=sidewalk,
Cykelsti=bike path, P-Areal=parking — folded into
`location_description`), `bygherre` (the commissioning client, mapped to
`Works.promoter`), `entreprenoer` (the contractor — no dedicated model
field, folded into `traffic_management` instead of dropped, the same
"real field, no home, append don't drop" discipline Tasmania's own
`SITE_CONTACT` gets).

**`date_confidence` is `ESTIMATED`, never `VERIFIED`** — a granted
permit's stated window is not an independently confirmed "work is
happening" signal, the same discipline NYC DOT/Chicago/Paris apply.
**`street_ref` is never populated** — only free-text `lokation` exists,
no street/segment identifier.

**`source_grade="register"`** — this is a formal municipal permit
register (like Street Manager/NYC DOT/Chicago/Paris/Jersey), not a
road-operator traffic feed.

**Licence: CC-BY-4.0, confirmed live** via the dataset's own CKAN
metadata (`license_id: "CC-BY-4.0"`, explicit `license_url` to
`creativecommons.org/licenses/by/4.0/`) — a clean, confirmed-open
licence, no hedging required.

**No credentials required** — every claim above came from a fully
unauthenticated GetFeature request.

## Vejdirektoratet (national roadworks) — Credentials wanted

Denmark's national roadworks source — the Danish Road Directorate's own
genuine DATEX II 3.2 feed, credential-gated at the data-pull layer only.
Do-not-dedupe against Copenhagen above: national trunk roads vs. one
city's own excavation permits, the same relationship Kanton Zürich/Stadt
Zürich already establishes.

```python
from streetworks.datex2.vejdirektoratet import VejdirektoratetClient
from streetworks.common import from_datex2

# base_url is issued per-dataset at registration - no public constant exists
with VejdirektoratetClient(base_url=pull_url, username=username, password=password) as vd:
    for situation in vd.iter_situations():
        works = from_datex2(situation, territory="Denmark")
```

**Genuine, standard DATEX II vocabulary — confirmed from Vejdirektoratet's
own protocol spec, not inferred.** Real `sit:ConstructionWorks`/
`sit:MaintenanceWorks` `SituationRecord` types are explicitly enumerated,
both rolling up to a `Roadworks` class in the spec's own class diagram,
with real `constructionWorkType`/`roadMaintenanceType` values listed
(`constructionWork`, `roadWideningWork`, `resurfacingWork`, `roadworks`,
...). This is standard DATEX vocabulary this SDK's shared roadworks
discriminator already recognises — no Denmark-specific logic needed,
unlike Sweden (see Trafikverket above).

**No hardcoded data URL — genuinely different from every other DATEX
adapter in this SDK.** Vejdirektoratet issues the actual per-dataset
REST pull address during registration, not as a public constant
(confirmed: the protocol doc and the open catalogue both stop at
"configured when the dataset is set up," no public data endpoint exists
to probe). `VejdirektoratetClient` therefore takes `base_url` as a
required constructor argument, not a module default.

**The open metadata catalogue is genuinely open, confirmed live** — all
196 registered datasets are reachable keyless (DCAT/RDF-XML), including
the specific roadworks dataset ("OOV2 Trafikmeldinger"), tagged
`road-work-information`, `datex-II`, and licensed `CC_BY_4_0` in the
catalogue's own per-dataset licence field — confirmed per-dataset, not
assumed from the catalogue in general (other datasets in the same
catalogue carry different licences). Only the actual data pull remains
credential-gated.

**Auth: HTTP Basic, stated verbatim in the protocol documentation** —
*"A request must use HTTP Basic Authentication... username and password
are configured in DU when the dataset is set up"* — both the scheme and
the fact that credentials are per-dataset, not global, are stated
directly rather than inferred. Credentials: registration via
[Dataudveksleren](https://du-portal-ui.dataudveksler.app.vd.dk/),
confirmed live and reachable. Licence: **CC BY 4.0**, confirmed live and
per-dataset (see above). See
[`docs/providers/index.md#credentials-wanted`](index.md#credentials-wanted)
for the condensed table entry.

## The rest of the Danish landscape

**Oslo** (Norway, `streetworks.oslo`) and **Helsinki** (Finland,
`streetworks.helsinki` — see
[`docs/providers/europe.md`](europe.md#helsinki-kaivuilmoitus)) are now
both built, resolving two more open questions across the Nordic capitals;
both needed real live-verification before building, since
neither matched the first guess (Oslo's guessed Origo/NVDB
backend, Helsinki's own unconfirmed "does a dataset even exist"
question). **Stockholm** (Sweden, `streetworks.stockholm` — see
[`docs/providers/europe.md`](europe.md#stockholm-trafikkontoret--credentials-wanted))
confirms a real risk flagged early on rather than disproving it — every
real surface tested (WFS/WMS `GetCapabilities`) requires an API key
before revealing even a layer name, let alone whether a `vägarbete`
dataset exists at all, so it ships as a Phase 0 Credentials-wanted
scaffold (see [Credentials wanted](index.md#credentials-wanted)) rather
than a live-verified build — the same discipline that corrected the
Copenhagen and Helsinki teams' own early guesses once actually checked,
applied here to an outcome that stayed genuinely blocked instead of
resolving cleanly.
