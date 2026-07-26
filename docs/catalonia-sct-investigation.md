# Catalonia (Servei Català de Trànsit) — investigation

Reconnaissance only, per the brief. No module, no client, no tests. All
findings below are live-verified on 2026-07-26, not read off documentation
alone — every claim marked "confirmed live" was checked by an actual
request, not assumed from a portal page.

## Answer, up front

**Yes, a real roadworks/incidents feed exists, confirmed live — not just
cameras or statistics.** It is genuinely GML/WFS-XML, not GeoJSON, DATEX,
ArcGIS, or CSV. **Build now** — but as a small, self-contained bespoke
parser (flat records, no nesting), not the existing GeoJSON-only
`OGCFeaturesClient` and not the general "GML-reader" decision this SDK has
parked elsewhere (Mecklenburg-Vorpommern/Saxony-Anhalt/CartoCiudad) — this
feed's real shape is simple enough not to need that heavier machinery.

This closes the Catalonia gap DGT leaves open, and — a genuine bonus found
while checking the other DGT exclusion — **the Basque Country turns out
to publish real DATEX II already, parseable by this SDK's existing shared
parser with zero code changes**, confirmed by a live test (see
[Basque Country](#basque-country-a-bonus-finding-not-built) below). Both
findings make the Spain picture genuinely three-way *plus* a fourth
strong candidate: DGT (national, ex-Catalonia/Basque) + Consell de
Mallorca (insular) + SCT (Catalonia, this investigation) + a
credible-but-uninvestigated-in-depth Basque Country feed.

## 1. Finding the real feed — the portal page didn't show it directly

`transit.gencat.cat/ca/el_servei/dades-estadistiques/dades-obertes/` is
mostly navigation chrome; the actual dataset links live on Catalonia's
central open-data portal, a Socrata deployment at
`analisi.transparenciacatalunya.cat`. Two SCT-published Transport-category
datasets matter here (found via the portal's own listing, not guessed):

- **"Incidències viàries en temps real a Catalunya"** ("Real-time road
  incidents in Catalonia", Socrata id `uyam-bs37`) — the one this
  investigation is about.
- "Incidències viàries a les carreteres de Catalunya" (`5wp5-7t2p`) — a
  secondary catalogue entry whose own column list is a set of road names
  (`A-2`, `C-12`, `N-152`, ...), i.e. it links to **per-road** RSS feeds
  rather than one combined feed — noted, not chased further, since the
  combined real-time one is strictly more useful.

Querying `uyam-bs37`'s own Socrata metadata
(`/api/views/uyam-bs37.json`) — not the SODA row/column API, which
**returns HTTP 403** ("no row or column access to non-tabular tables";
this dataset is stored as an `href`-type asset, not a native Socrata
table) — surfaces the real access points directly:

```json
"metadata": {
  "additionalAccessPoints": [
    {"urls": {
      "rss": "http://www.gencat.cat/transit/opendata/incidenciesRSS.xml",
      "xml": "http://www.gencat.cat/transit/opendata/incidenciesGML.xml"
    }}
  ]
}
```

Both fetched directly, live, 2026-07-26 — both real, both current
(`Last-Modified` matched the fetch time to the minute on both).

## 2. What server / protocol, what format — tested, not trusted

**Not DATEX, not ArcGIS, not CSV. Two real formats, same underlying data:**

- **RSS** (`incidenciesRSS.xml`, ~60 KB) — a plain RSS 2.0 channel, one
  `<item>` per incident, human-readable `<title>`/`<description>` text
  only, **no coordinates, no structured fields**. Real example:

  ```xml
  <item>
    <guid isPermaLink='false'>149992801</guid>
    <pubDate>Sun, 26 Jul 2026 15:53:00 GMT</pubDate>
    <title>OBRES. Circulació amb retencions (Retenció)</title>
    <link>https://cit.transit.gencat.cat</link>
    <description>A-2 | JORBA | Sentit Est cap a BARCELONA | Punt km. 545-543 | 17:53</description>
  </item>
  ```

- **`incidenciesGML.xml`** (~150 KB, the one worth building on) — genuine
  **WFS 1.0.0 `GetFeature`-shaped output**: a `wfs:FeatureCollection` root,
  one `gml:featureMember` per incident, real `gml:Point` geometry, and a
  flat set of typed sibling fields per record (not deeply nested — see
  §5). The `xsi:schemaLocation` on the root element points at
  `http://localhost:8080/sct-gis/wfs?...` — a real, live artefact of
  however this snapshot is rendered server-side, but **not an externally
  reachable endpoint** (checked directly: `transit.gencat.cat/sct-gis/wfs`
  and equivalent guesses all 404). The only real, working public access
  point is the fixed `incidenciesGML.xml` URL itself, refreshed
  continuously (`"Freqüència d'actualització": "Contínua"` in the
  dataset's own metadata, confirmed by `Last-Modified` matching fetch
  time) — a snapshot-pull pattern, the same shape as NDW's or
  Luxembourg's fixed-URL DATEX downloads, not a parameterised query
  service.

**This is real GML in the sense of using the GML geometry vocabulary
(`gml:Point`, `gml:coordinates`) inside a `wfs:FeatureCollection`
envelope — but it is not the complex, deeply-nested, INSPIRE-style
official GML application schema this SDK's parked GML-reader decision was
about.** Every record here is flat: one geometry element plus a dozen
scalar sibling elements, no nested feature collections, no nested complex
types. A small bespoke parser (plain `ElementTree`, matching by local
name the same way this SDK's own DATEX parser already does) is enough —
this does **not** need to wait on a general GML-reader build.

## 3. Access — fully open, no gate

Both URLs are plain, unauthenticated `GET` requests — no API key, no
registration, no rate-limit response observed. `Content-Type:
application/xml` on both, standard HTTP caching headers
(`Last-Modified`/`ETag`) present and genuinely changing between checks.

## 4. Licence — verbatim, confirmed genuinely open

The dataset's own metadata states `"licenseId": "SEE_TERMS_OF_USE"` and
links `attributionLink`:
`https://administraciodigital.gencat.cat/ca/dades/dades-obertes/informacio-practica/llicencies/`.
That page states, verbatim (Catalan original):

> **Llicència oberta d'ús d'informació - Catalunya**
>
> [...] és un acord de llicència que permet els usuaris compartir,
> modificar i utilitzar lliurement aquesta informació de manera flexible
> només respectant certes condicions establertes a la secció de
> Condicions d'ús. [...]
>
> **Què permet aquesta llicència?**
> La reutilització de la informació. La distribució i la comunicació
> pública de la informació. La transformació de la informació per fer-ne
> obres derivades, per a tot el món i sense cap limitació temporal [...]
>
> **Condicions d'ús**
> No es pot alterar el contingut de la informació. No es pot desnaturalitzar
> el sentit de la informació. Cal citar la font de la informació de la
> manera següent: Generalitat de Catalunya. Departament de [nom
> departament] [...] S'ha d'informar de la darrera data d'actualització de
> la informació.

English translation: **"Open licence for information use - Catalonia"** —
an agreement permitting users to freely share, modify, and use this
information flexibly, subject only to conditions in the Terms of Use
section. What it permits: reuse of the information; distribution and
public communication of the information; transformation into derivative
works, worldwide and without time limitation. Conditions: the content may
not be altered; its meaning may not be misrepresented; the source must be
cited as "Generalitat de Catalunya. Department of [department name]"; the
last update date of the information must be stated.

This dataset's own `attribution` field states the citation value
directly: **"Departament d'Interior"**. Genuinely open, genuinely
confirmed (not "unconfirmed" like several other sources checked this
session) — analogous in spirit to CC BY: free reuse/redistribution/
derivative works with an attribution condition, not a share-alike or
non-commercial restriction.

## 5. CRS

**WGS84 (EPSG:4326), confirmed live, not assumed.** Every real
`gml:Point` states
`srsName="http://www.opengis.net/gml/srs/epsg.xml#4326"` explicitly, and
real coordinate values confirm it: `2.27873636,41.56623599` (a real point
near Barcelona) — the right order of magnitude for Catalonia in decimal
degrees, and in **`lon,lat` order** (GML/WFS convention, comma-separated,
period decimal), not `lat,lon`. 100% coordinate coverage confirmed
(165/165 real records checked carried a `gml:Point`).

## 6. Discriminator — clean, not the Cyprus problem

**`tipus`/`descripcio_tipus`** is a real, small, explicit type code -
confirmed live, not free-text inference. Full distribution from a live
165-incident pull:

| `tipus` | `descripcio_tipus` | Count |
|---|---|---|
| `3` | **Obres** (Works) | 136 |
| `2` | Retenció (Congestion/tailback) | 18 |
| `4` | Cons (Cones - temporary lane markers) | 11 |

**136/165 real, live, current records are explicitly typed as roadworks**
— by far the richest, cleanest roadworks signal of any Spanish source
checked this session (cleaner than DGT's cause-based inference, cleaner
than Mallorca's three-value `tipoinc`). A second, richer field,
**`causa`**, sub-types the works themselves with real free-text (not the
discriminator, a description layer on top of it): *"Treballs de
manteniment"* (maintenance work, 42), *"Millora de traçat"* (route
improvement, 14), *"Obres en general"* (general works, 12),
*"Reforçament de ferm"* (pavement reinforcement, 9), *"Estabilització de
talús"* (slope stabilisation, 8), *"Senyalització horitzontal"* (road
marking, 8), *"Canalització de fibra"* (fibre-optic conduit laying, 7),
*"Construcció de rotonda"* (roundabout construction, 5), and others.

## 7. Real record shape

Full real schema, confirmed live (one `gml:featureMember` per incident,
under element `cite:mct2_v_afectacions_data`):

| Field | Example | What it is |
|---|---|---|
| `geom` | `gml:Point`, WGS84 lon,lat | Location |
| `identificador` | `149674405` | Incident id |
| `tipus` | `3` | Type code - **the discriminator**, see §6 |
| `subtipus` | `61` | Sub-type code (not decoded here - meaning not checked) |
| `carretera` | `C-15` | Road number |
| `pk_inici` / `pk_fi` | `2.20` / `13.20` | Kilometre-point range |
| `causa` | `Senyalització vertical` | Free-text specific cause |
| `cap_a` | `HORARI: 21 a 5h` (also seen as a destination town name on other records) | Direction/destination **or** a time-window note - genuinely dual-purpose, confirmed inconsistent across real records, not a parsing artefact |
| `data` | `Sat, 25 Jul 2026 17:49:07 GMT` | Timestamp (RFC-822 style, real UTC) |
| `nivell` | `2` | Severity level, real values 1-5 seen live (not decoded here) |
| `sentit` | `Ambdos sentits` / `Creixent` | Direction of travel - real, human-readable, not opaque |
| `descripcio` | `Calçada restringida` | Short status description |
| `descripcio_tipus` | `Obres` | Type, human-readable - **matches `tipus`**, see §6 |
| `font` | `SCT` | Source attribution |

A full real "Obres" record, verbatim:

```json
{
  "geom": "1.72629587,41.29309171",
  "identificador": "149674405",
  "tipus": "3",
  "subtipus": "61",
  "carretera": "C-15",
  "pk_inici": "2.20",
  "pk_fi": "13.20",
  "causa": "Senyalització vertical",
  "cap_a": "HORARI: 21 a 5h",
  "data": "Sat, 25 Jul 2026 17:49:07 GMT",
  "nivell": "2",
  "sentit": "Ambdos sentits",
  "descripcio": "Calçada restringida",
  "descripcio_tipus": "Obres",
  "font": "SCT"
}
```

(`"Senyalització vertical"` — "vertical signage" (a sign-installation
works cause); `"Calçada restringida"` — "carriageway restricted".)

**Honest gap, confirmed live**: `cap_a` is genuinely dual-purpose across
real records - sometimes a destination town (`"GIRONA"`, `"BARCELONA"`),
sometimes a free-text time-window note (`"HORARI: 21 a 5h"`, "hours: 9pm
to 5am"). A future build should carry this through as-is rather than
guessing which meaning applies to a given record.

## 8. Network scope — multi-authority within Catalonia, like DGT's own shape

Real road-number prefixes checked across a live 165-record pull span
**several road authorities' networks, not one**: `C-` (the Generalitat's
own regional network, 51), `B-`/`BV-`/`BP-` (Barcelona provincial
council, 38 combined), `GI-`/`GIV-`/`GIP-` (Girona provincial, 26
combined), `T-`/`TV-`/`TP-` (Tarragona provincial, 11 combined), `L-`/
`LV-` (Lleida provincial, 3 combined), plus real state-network entries
(`N-`/`NII-`, 14; `A-`/`AP-`, 18) still appearing within Catalan
territory. This is the same shape of finding the network-scope audit
already made for DGT (`docs/network-scope-audit.md`) - a multi-authority
*interurban* aggregator (the Generalitat's own network plus all four
provincial deputació networks plus some state roads within the region),
not a single authority's network and not confirmed to reach municipal
streets. **Overlap with DGT was not checked in this pass** - DGT
officially excludes Catalonia entirely, so no overlap is expected, but
given the confirmed DGT/Mallorca precedent, this is worth a direct check
before treating the two as strictly disjoint if a future build combines
them.

## Basque Country — a bonus finding, not built

The brief asked to flag whether the Basque Country (DGT's other
exclusion) publishes similarly - investigate, don't build. It does, and
the finding is stronger than expected:

Spain's own national NAP (`nap.dgt.es`) lists a real, separate dataset,
**`incidencias-dt-gv`**, published by the Basque Government's own
Dirección de Tráfico (Trafikoa), pointing at a live, working DATEX II
endpoint:

```
GET http://infocar.dgt.es/datex2/dt-gv/SituationPublication/all/content.xml
→ HTTP 200, 582 KB, publicationTime matched the fetch time
```

**Confirmed live: this SDK's existing shared parser
(`streetworks.datex2.iter_situations_full`) reads it successfully with
zero code changes** - a diagnostic test only, nothing built:

```
120 situations parsed, 96 with at least one roadworks record
Real xsi:types seen: MaintenanceWorks (78), ConstructionWorks (23) -
the clean, dedicated discriminator this SDK already handles, not a
generic-record case like DGT's or Belgium's.
Real road prefixes: GI- (Gipuzkoa, 37), N- (state roads, 22), A- (12),
BI- (Bizkaia, 11), AP- (10) - genuinely spans all three Basque provinces
plus some state roads within the territory, the same multi-authority
shape as Catalonia's and DGT's own feeds.
```

Two real caveats, found but not resolved (out of scope for "investigate,
don't build"): the schema is **DATEX II v1.0** (`d2LogicalModel
modelBaseVersion="1.0"`), an older version than every other DATEX adapter
in this SDK targets (all v2/v3) - it happens to parse correctly because
this SDK's parser matches by local element name regardless of namespace,
but the CRS, full field coverage, and licence were **not** checked in
this pass, only existence and rough shape. The NAP dataset page itself
states **`"Tipo de Licencia": "No licence - No contract"`** - genuinely
unconfirmed/none stated (a filter-menu URL elsewhere on the NAP site
suggested `cc-by`, but that was a catalogue filter option, not this
dataset's own stated licence - the dataset page's own text is the one
trusted here). Worth its own dedicated investigation before building,
same discipline as Menorca/Eivissa were left for the Mallorca work.

## Recommendation

1. **Build Catalonia (SCT) now.** Real, live, open, well-licensed, richly
   and cleanly typed. Needs a small bespoke parser for the flat WFS/GML
   snapshot shape (not the GeoJSON-only `OGCFeaturesClient`, and not a
   wait on the general GML-reader decision - this feed's shape doesn't
   need that heavier machinery). CRS is WGS84, confirmed, no reprojection
   question at all - simpler than Belgium/Lithuania/Mallorca in that
   respect.
2. **Basque Country is a strong, credible build candidate for a future
   session** - already parses with zero code changes on a diagnostic
   test, a clean dedicated discriminator, multi-province coverage - but
   genuinely not investigated to the same depth as Catalonia here (no
   CRS check, no full field mapping, no licence resolution). Recommend a
   short, dedicated follow-up investigation, not folding it into the
   Catalonia build.
3. Once built, Spain's picture is genuinely four-way:  DGT (national,
   multi-authority interurban, ex-Catalonia/Basque) + Consell de Mallorca
   (insular, overlapping with DGT at the edges - see
   `docs/network-scope-audit.md`) + SCT (Catalonia, multi-authority
   interurban within the region) + a credible-but-unbuilt Basque Country
   feed - a genuine, concrete illustration of Spain's real regional
   fragmentation, not a tidy national/regional split.
