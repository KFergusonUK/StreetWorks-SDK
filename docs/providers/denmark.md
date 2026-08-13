# Denmark

> Copenhagen is this SDK's first Nordic roadworks coverage, and Denmark's
> first *keyless* coverage — the separate national Vejdirektoratet feed
> (genuine DATEX II 3.2) remains credential-parked (registration issued
> per-dataset, no public data URL exists; see `docs/providers/index.md`'s
> Credentials-wanted table). Do-not-dedupe: Copenhagen and Vejdirektoratet
> are kept as two distinct providers, the same way NYC DOT and WZDx both
> cover the USA without merging.

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

**Built from `nordic-capitals-investigation.md`'s (Copenhagen/Oslo/
Stockholm/Helsinki) recommendation to build Copenhagen first. Live
verification corrected several of the brief's own guesses before any
code was written.** The brief guessed a dataset named "vejarbejde" over
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

**A real, load-bearing geometry finding the brief never anticipated:
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

## The rest of the Danish landscape

**Oslo** (Norway, `streetworks.oslo`) and **Helsinki** (Finland,
`streetworks.helsinki` — see
[`docs/providers/europe.md`](europe.md#helsinki-kaivuilmoitus)) are now
both built, resolving two more of `nordic-capitals-investigation.md`'s
findings; both needed real live-verification before building, since
neither matched the brief's own guess (Oslo's guessed Origo/NVDB
backend, Helsinki's own unconfirmed "does a dataset even exist"
question). **Stockholm** (Sweden) remains unbuilt — flagged "Rome-risk"
in the brief (its city open-data portal may publish road network/rules
rather than actual works) and key-gated, per that brief's own "not all
equal" prioritisation. A future pass should verify a real `vägarbete`
dataset actually exists on the city portal before writing any client
code — the same discipline that corrected the Copenhagen and Helsinki
briefs once actually checked.
