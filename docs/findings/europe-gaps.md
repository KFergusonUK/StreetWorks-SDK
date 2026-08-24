# Europe gaps — research notes (2026-08-23)

Working notes from a live-verification pass over Europe's remaining roadworks
gaps, prompted by asking "any more country feeds we're missing?" after the
North American 511 sweep grew that platform's footprint the same way. Not
polished — kept close to what was actually found, so a future session (or
contributor) doesn't have to re-derive it. Three real providers came out of
this pass: `streetworks.brussels`, `streetworks.poland`, `streetworks.romania`
— see [`docs/providers/europe.md`](../providers/europe.md) for their full
writeups. This file is everything else: the leads that didn't turn into a
provider, and why.

## Belgium — Wallonia (parked)

Flanders' own DATEX II feed (`streetworks.datex2.belgium`) prompted checking
whether Belgium's other regions had equivalents. Brussels did (see
`streetworks.brussels`). Wallonia's own "Événements routiers en Wallonie"
dataset (catalogued on `transportdata.be`) is real but genuinely
credential-gated — its own resource listing states:

> "Access to this feed requires a username and password by sending a mail to
> the contact point with the reason for access."

`conditions_usage` on the same listing is `contractual-arrangement`, not an
open licence. Contact: `caroline.pourtois@spw.wallonie.be`
(Service public de Wallonie Mobilité et Infrastructures). Parked — this SDK
doesn't register accounts/agreements on a caller's behalf.

## Hungary — parked, contract-gated

`napportal.kozut.hu` is a real, rich DATEX II-based National Access Point
(Magyar Közút). Traced end-to-end the same way as Brussels/Romania/Poland:

1. The Angular app's compiled JS references `assets/app-config.json` at
   runtime.
2. That config states `"servicesBaseUrl": "https://napportal.kozut.hu/napp-portal-proxy"`.
3. The real API surface behind that base has proper DATEX II vocabulary
   endpoints — `/api/RoadworksDuration`, `/api/RoadworksScale`,
   `/api/ConstructionWorkType`, `/api/RoadMaintenanceType`,
   `/api/Situation/List`, `/api/getSituationsByProfileId`.

`GET /napp-portal-proxy/api/Situation/List` returns a plain `401`. The app's
own bundle explains why: real strings found inside it —
`data-consumer/subscription`, `GetConsumerContracts`,
`ServiceProviderProfile`, `ContractPartner` — confirm this NAP requires
registering as a formal "data consumer" under a contract, not a self-service
API key. Same tier as Wallonia above. Not pursued — outside this SDK's
standing rule against registering accounts/contracts on a caller's behalf.

## Czech Republic — unresolved (connectivity, not a block)

A real national traffic-data registry exists:
`registr.dopravniinfo.cz`, listing a source named "DDR - Běžné dopravní
informace" run by NDIC (Národní dopravní informační centrum), DATEX-style.

The entire `dopravniinfo.cz` domain cluster — the registry itself, the main
`dopravniinfo.cz` portal, and `nap.dopravniinfo.cz` — was **unreachable from
this session's sandboxed environment**. Every attempt (`curl`, with a browser
user-agent, generous timeouts) ended in a TLS/connection timeout (`curl`
error 28), never a `403` or explicit block. This reads as an
environment-specific reachability issue (geo-filtering, or the sandbox's
egress simply isn't welcome there), not a real dead end — the same class of
miss as Tennessee's TDOT infrastructure in the USA sweep (see
`docs/roadmap.md`'s USA gap-state history). Worth a retry from a different
network before concluding anything more.

## Slovakia — real leads found, none built

`data.slovensko.sk` ("Národný katalóg otvorených dát") is a proper DCAT-AP/
RDF catalogue. Its React bundle calls a config-lookup helper —
`Ys("sparql-endpoint-url", {})` — which resolves to a real, live **SPARQL
1.1 endpoint at `/api/sparql`**, returning `application/sparql-results+json`.
This is a genuinely reusable technique for any future Slovak lead: query
`dcat:Dataset`/`dct:title` for a keyword match, then walk
`dcat:distribution` to the resource's own `dcat:downloadURL`/`dct:format`
and the catalogue's own licence quality-metrics (it actively re-checks these
— the timestamps seen during this pass were from the day before, so this is
a live, maintained catalogue, not a static dump).

Example query used:

```sparql
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT ?dataset ?title WHERE {
  ?dataset a dcat:Dataset .
  ?dataset dct:title ?title .
  FILTER(CONTAINS(LCASE(STR(?title)), "doprav") || CONTAINS(LCASE(STR(?title)), "uzáver"))
} LIMIT 50
```

Two real candidates surfaced, neither built:

### "Dopravné a krízové situácie – online" (MINV, CC0)

Published by the Ministry of Interior. Real categories:
`Dopravná nehoda` (traffic accident), `Dopravná situácia` (traffic
situation), `Iná situácia (Krízová situácia)` (other/crisis), `Mimoriadna
situácia` (extraordinary situation), `Neprejazdná cesta` (impassable road),
`Neprejazdná cesta v jednom smere` (impassable road, one direction),
`Povodeň` (flood), `Spomalená premávka` (slowed traffic), `Uzavretá/riziková
oblasť` (closed/risky area). Real category codes: `ZD1`–`ZD9`, `ZE0`.

Real page: `portal.minv.sk/wps/portal/domov/sluzby_pz/dopravne_krizove_situacie`
— a live "Download (CSV)" button exists. Backend is an IBM WebSphere Portal
app (`PA_esispz-situations`, Esri/Dojo-based). Traced two real endpoints:

- `POST /wps/PA_esispz-situations/servlet/situations/export/csv` (the CSV
  export the button submits to — a hidden form with fields
  `situationsExportRegionId`/`Categories`/`StatusCode`/`ShowPlanned`/
  `ValidFrom`/`ValidTo`/`Locale`)
- A GET "resource-serving" AJAX URL embedded in the page as
  `situationsAjaxUrl`, a WebSphere-style `!ut/p/a1/...` navigational-state
  token ending `res/id=QCPgetSituations/...`

Both return an empty `500` (`{}`) — tried with default/empty params, with
all nine real category codes explicitly listed, and with a proper session
cookie established by GETting the page first. None of that unblocked it; the
exact required request shape wasn't found (possibly array-style param
encoding, a CSRF/referrer check, or something tied to the specific
`!ut/p/a1/...` render-state token expiring/being single-use).

Even if unlocked: this is a police/crisis-management register, not a
roadworks-specific one — closures could be accident- or flood-caused, not
just construction, the same category-ambiguity problem Japan's JARTIC has
(see [`docs/findings/japan.md`](japan.md)). Real per-record text-reading
would be needed to separate the two, the same way Romania's own "ongoing
closures" section needed it.

### TTSK (Trnava region) road/bridge reconstructions — cleanest technical fit, not built

Found via the same SPARQL search: "Rekonštrukcie mostov, ciest a priepustov
SÚC TTSK" and siblings ("...z EÚ", i.e. EU-funded). All are the same
publisher (`legal-subject/37836901`, TTSK — Trnavský samosprávny kraj, one
of Slovakia's 8 self-governing regions), just different map layers of one
ArcGIS Hub item.

Real distribution: `rss-dcat-opendata-ttsk.hub.arcgis.com`, plain
**ArcGIS Hub GeoJSON** export, licensed **CC BY 4.0** (confirmed via the
catalogue's own quality metrics). Two real layers on item
`5cd16656e0fe494188eaee51d98a200b`:

- `?layers=0` — bridges, 35 real features, real fields `Okres` (district),
  `Stredisko` (maintenance depot), `Cesta` (road number), `ID_mosta`
  (bridge id), `Nazov` (project name), `Stav` (status), `Rozpocet_r`
  (budget year)
- `?layers=3` — roads, 26 real features, real `LineString` geometry in
  **Web Mercator (EPSG:3857)**, same field set plus `Shape_Leng`

Real `Stav` values form a genuine project lifecycle: `Rekonštrukcia
plánovaná` (planned) → `Rekonštrukcia prebieha` (in progress) →
`Rekonštrukcia dokončená` (completed) — the same shape as Roma's own
`Progettazione → Gara → Cantiere → Fine lavori`.

This is the technically easiest thing found in Slovakia — plain ArcGIS Hub
GeoJSON is a pattern this SDK already has many working examples of. Two real
caveats, not yet resolved, before building:

1. Every real record's `Rozpocet_r` is `2023` or `2024` — no `2025`/`2026`
   seen in either layer. The exported filename itself contains `_beta_`
   (`Rekonštrukcie_mostov_ciest_a_priepustov_v_TTSK_beta_-...`), suggesting
   this might be a pilot dataset that's stopped being updated rather than a
   live one. Worth checking currency (e.g. does TTSK's own portal show
   newer projects than this export?) before building.
2. It's regional, not national — Trnava is 1 of 8 Slovak self-governing
   regions. Worth checking whether the other 7 (Bratislavský, Trenčiansky,
   Nitriansky, Žilinský, Banskobystrický, Prešovský, Košický) publish a
   similar ArcGIS Hub layer before deciding whether regional-only coverage
   is worth shipping on its own.

## Croatia — no lead found yet

HAK (Hrvatski autoklub / Croatian Auto Club) is a road-safety association,
not the national road operator — not the right target. The likely
traffic-info domain, `promet.hr`, returns a `404` at root; not explored
further (may need a different path, or the real operator name — Hrvatske
ceste for state roads, Hrvatske autoceste/HAC or Autocesta Rijeka-Zagreb/ARZ
for motorways). Needs a fresh search pass, not just a URL to retry.

## Albania — checked and ruled out, not just unfound

Prompted by a direct question ("does Albania have a roadworks feed?") after
a detour into whether Albania is in Europe at all (it is - Southeastern
Europe, Balkan Peninsula). Checked live, not guessed - three real pages
found on ARRSH's (Autoriteti Rrugor Shqiptar, the Albanian Road Authority,
`arrsh.gov.al`) own site, none of them a real structured feed:

- **"Informacion i Gjendjeve te Rrugeve"** ("Road Conditions Information",
  `arrsh.gov.al/informacion-i-gjendjeve-te-rrugeve.html`) - a real, currently
  updated WordPress category archive (most recent post dated 17 Aug 2026),
  but unstructured news/press-release posts (e.g. "Në aksin Tiranë-Durrës
  vijon puna për zgjerimin e autostradës" - "Work continues on widening the
  Tirana-Durrës highway") - no coordinates, no start/end dates, no
  extractable fields at all, just prose. Genuinely thinner than even
  Romania's HTML dispatch board (see above), which at least has real
  `<table>` rows with per-record fields.
- **"Open Data"** (`arrsh.gov.al/open-data`) - a real page, but its own
  stated content ("LISTA E TË DHËNAVE TË HAPURA TË ARRSH" - "LIST OF
  ARRSH'S OPEN DATA") is a legally-mandated transparency-law disclosure
  list (legal texts, budget/financial data, procurement procedures,
  complaints mechanisms) - the same "real label, wrong content" pattern
  Greece's own NAP already established in this SDK. No CSV/JSON/XML link
  anywhere on the page.
- **"Rruga Dixhitale"** ("Digital Road", `arrsh.gov.al/rruga-dixhitale`) -
  turned out to be a citizen-complaints/reporting-tracker platform
  ("Statistika përfundimtare mbi ankimimet e zgjidhura" - "final statistics
  on resolved complaints"), not a public roadworks data feed.
- Albania's own national open data portal (`opendata.gov.al`) is
  **WAF-blocked from this environment entirely** - every path tried,
  including the bare homepage, returned a real F5/BIG-IP ASM "Request
  Rejected" response - left alone, not bypassed, consistent with this
  SDK's standing rule.

**How to apply**: a genuine dead end for a structured feed at the national
road-authority level, not an unfound one - the same tier as Greece
(real NAP, wrong content) rather than Czech Republic (real lead,
environment-blocked) or Croatia (no lead traced yet). Worth revisiting only
if a differently-named source surfaces (e.g. a municipal Tirana portal, or
retrying `opendata.gov.al` from a network the WAF doesn't block), not by
re-checking ARRSH's own site again.

## Related: an earlier, separate NAP survey

[`docs/findings/nap-survey.md`](nap-survey.md) is a different, earlier pass over
European National Access Points (via NAPCORE's own registry), and already
covers Slovakia from a different angle — it found `cdb.sk`'s own DATEX II
NAP (written agreement + X.509 mTLS certificate required), which is a real,
separate source from the `data.slovensko.sk`/MINV/TTSK findings above, not a
duplicate. Worth reading both if picking Slovakia back up.
