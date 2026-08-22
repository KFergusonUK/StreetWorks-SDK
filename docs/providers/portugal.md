# Portugal

> New content, not a migration — Portugal wasn't a built provider at the
> time of the phase-one docs migration (see `docs/providers/pending.md`,
> which this section now supersedes for Lisboa specifically). The
> national IMT National Access Point (NAP) itself remains a real
> registration/catalogue portal, not a data host — see
> [Infraestruturas de Portugal](#infraestruturas-de-portugal-condicionamentos)
> below for how national coverage was reached anyway.

## Infraestruturas de Portugal (Condicionamentos)

Portugal's national real-time road restrictions/roadworks feed, run by
IP (Infraestruturas de Portugal) — this SDK's first Portugal *national*
roadworks provider; Lisboa (below) is municipal:

```python
from streetworks.arcgis.ip import IPRoadworksClient
from streetworks.common import from_ip

with IPRoadworksClient() as ip:
    works_list = from_ip(list(ip.iter_roadworks()))
```

**Found by tracing IP's own live public "Trânsito em Tempo Real" page**
(`servicos.infraestruturasdeportugal.pt/pt-pt/viajar-na-estrada/transito-em-tempo-real`),
the same technique that found Lisboa's and Road Report NT's real
backends: the page embeds a real ArcGIS Instant App
(`infraestruturas.maps.arcgis.com/apps/instant/basic/...`), resolved via
the sharing REST API to its real webmap
(`webmap_viajar_na_estrada_sem_cameras_featurelayer`), which names four
real operational layers on one shared `utility.arcgis.com` MapServer
(`webapps/viajar_na_estrada2024`): Condicionamentos (this module),
Outras Ocorrências, Acidentes, and a Serra da Estrela driving-conditions
layer — none of the other three consumed here.

**This directly supersedes the earlier NAP-survey finding** that the
national NAP itself (`nap-portugal.imt-ip.pt`) carries no roadworks
content — genuinely true, confirmed again this session by reading its
own JS bundle end to end (zero roadworks vocabulary anywhere: it's a
real registration/access-management portal — users, suppliers, access
requests, contracts — not a data host). A real sign-in flow was traced
and confirmed working technically (a genuine `POST
.../api/authentication/signin` with a custom `Auth: Basic` header,
confirmed via a matching CORS preflight), but a real registered account
returned a clean `404` — consistent with the account still being under
IMT's own review ("in analysis"), not a technical fault on either side.
IP publishes this Condicionamentos feed entirely separately from the
NAP system, so national coverage doesn't depend on that approval at all.

**93 real active records, confirmed live 2026-08-22.** `tipo ==
"MaintenanceWorks"` (86) or `"ConstructionWorks"` (2) are genuine
roadworks — 88/93. The other two real values are confirmed, not
assumed, to be something else: `PoorRoadInfrastructure` (4, a real
defect *report* — a damaged guardrail, a fallen sign — not active
repair work) and `GenericIncident` (1, a real event-driven closure).
The two sibling layers on the same service, checked live rather than
trusted by name, are genuinely not roadworks either — Outras
Ocorrências (77 real records: `EnvironmentalObstruction`/
`VehicleObstruction`/`GeneralObstruction`/`EquipmentDamageObstruction`/
`AnimalPresenceObstruction`) and Acidentes — so `Condicionamentos`
alone is the right, sufficient layer.

**A real "no defined end" placeholder in `datafim`, confirmed live —
not assumed.** 3 of 34 real non-null `datafim` values are the exact
same sentinel, `2556143999000` (2050-12-31 23:59:59 UTC) — a fabricated
far-future date meaning "no end stated," the same class of finding
WZDx's own placeholder-date handling already documents for this SDK.
Never surfaced as a real date.

**Geometry: real `f=geojson` output is genuine WGS84**, confirmed live
by comparing a real decoded point against that same record's own
separately-stated `latitude`/`longitude` attribute fields (identical to
six decimal places) — despite the layer's native `shape` geometry being
Web Mercator (`wkid 102100`/`3857`), the same "check per-service, don't
assume" discipline TIGERweb's and DC's own docs establish.

**Licence: unconfirmed** — no `licenseInfo`/`accessInformation` on the
real ArcGIS item, and no terms found specific to this dataset. Ships
anyway, flagged prominently, the same honest-gap tier as Autobahn
GmbH/Jersey/NYC DOT in this SDK.

## Lisboa (Condicionamentos de Trânsito)

The Câmara Municipal de Lisboa's (CML) own traffic-conditioning feed —
active and planned restrictions across the city, mixing real roadworks
with deliveries, parking reservations, house moves, filming and public
events:

```python
from streetworks.lisboa import LisboaClient
from streetworks.common import from_lisboa

with LisboaClient() as lisboa:
    features = list(lisboa.iter_roadworks())  # evidence-based motivo filter
works = from_lisboa(features)
```

**A key gating check — is the live platform actually current, or a stale
2023 snapshot? — resolved before writing any client code.** The
catalogue record for this dataset (`dados.gov.pt`) states *"Última
atualização: 22 de maio de 2023"* — taken alone, exactly the kind of
stale-portal signal that has meant a dead dataset elsewhere in this SDK
(the Chicago dead-dataset lesson, Madrid's moved portal). But that page
describes the catalogue entry, not the underlying data: CML's real live
platform (`condicionamentos-transito.cm-lisboa.pt`, a live Angular
single-page app with no data in its own page source) has a backend found
by reading the app's own bundled JS — the same technique that found Road
Report NT's real backend earlier in this project — and that backend is
genuinely current: 453/694 real features carry a **2026** `pedido`
(case-reference) id.

**The real endpoint isn't documented anywhere public.** The app's own
`environment` config states `ws: "//lisboa.city-platform.com/percursos/ws/app/public"`;
the component that renders closures appends `"/traffic/closures/"`.
Confirmed live: a single keyless `GET` on
`https://lisboa.city-platform.com/percursos/ws/app/public/traffic/closures/`
returns the full real GeoJSON `FeatureCollection` — 694 real features at
investigation time, no pagination, no server-side filtering (the app
itself filters client-side).

**Roadworks filter: `motivo` (free-text reason), evidence-based, not a
clean boolean like Madrid's `es_obras`.** 27 real distinct values exist
in this pull:

| `motivo` | Count | Roadworks? |
|---|---|---|
| CARGAS E DESCARGAS/OBRAS | 181 | ✅ contains "OBRA" |
| BETONAGENS/CARGAS DESCARGAS | 127 | ✅ explicit set (concrete pouring) |
| CARGAS E DESCARGAS | 72 | ❌ bare deliveries, no "OBRAS" suffix |
| OBRA - FAIXA DE RODAGEM | 65 | ✅ contains "OBRA" |
| LIGAÇÃO DE RAMAL - PASSEIO E ESTACION. | 33 | ❌ ambiguous, excluded |
| OBRA - PASSEIO E ESTACION. | 30 | ✅ contains "OBRA" |
| ACESSO DE VEÍCULOS À OBRA | 29 | ✅ contains "OBRA" |
| RESERVA DE ESTACIONAMENTO | 28 | ❌ parking reservation |
| BETONAGENS | 25 | ✅ explicit set |
| LIGAÇÃO DE RAMAL - FAIXA DE RODAGEM | 24 | ❌ ambiguous, excluded |
| MUDANÇAS | 18 | ❌ house/office moves |
| PLANTAÇÃO / PODA DE ÁRVORES | 13 | ❌ tree planting/pruning |
| AUTOGRUA | 13 | ❌ mobile crane truck, ambiguous |
| REPAVIMENTAÇÕES | 6 | ✅ explicit set (repaving) |
| SUBSTITUIÇÃO DE CAIXA MULTIBANCO | 5 | ❌ ATM replacement |
| FILMAGENS | 4 | ❌ filming |
| MONTAGEM DE GRUA | 4 | ✅ explicit set (crane erection) |
| OBRAS NO SUBSOLO - PASSEIO E ESTACION. | 3 | ✅ contains "OBRA" |
| CONCENTRAÇÃO | 3 | ❌ gathering/rally |
| PROCISSÃO | 2 | ❌ procession |
| OBRAS NO SUBSOLO - FAIXA DE RODAGEM | 2 | ✅ contains "OBRA" |
| EVENTO | 2 | ❌ event |
| DESMONTAGEM DE GRUA | 1 | ✅ explicit set (crane dismantling) |
| MANIFESTAÇÃO | 1 | ❌ demonstration |
| ILUMINAÇÃO PÚBLICA | 1 | ❌ public lighting |
| PINTURAS | 1 | ❌ road-marking paint, too rare/ambiguous |
| SONDAGENS - PASSEIO E ESTACION. | 1 | ❌ geotechnical survey, not construction itself |

**473/694 (68%) classify as roadworks**: anything containing the
substring `"OBRA"` (Portuguese for "works"), plus a small explicit set of
values that are clearly construction activity without literally
containing that word (`BETONAGENS`, `REPAVIMENTAÇÕES`, `MONTAGEM DE
GRUA`/`DESMONTAGEM DE GRUA`). **Genuinely ambiguous values are excluded,
not guessed either way** — most notably `LIGAÇÃO DE RAMAL` (utility
branch-line connection, 57 real records combined — plausibly involves
excavation, but never states "obra" and isn't confirmed construction
rather than a simple hookup) and `AUTOGRUA` (mobile crane truck, 13 real
records — could be for a house move as easily as a worksite).

**Geometry: real `MultiLineString`, not `Point`/`LineString` like this
SDK's other municipal sources.** 666/694 real features have exactly one
sub-line; a handful have up to 7. Only the first sub-line's vertices are
used — the same deliberate simplification `from_berlin` already makes
for a `GeometryCollection` carrying multiple `LineString` entries, since
`Coordinate` supports one line per point, not several. CRS: `EPSG:4326`
— evidenced from the same app bundle's own WMS map-layer requests
(`SRS=EPSG:4326`) and independently consistent with the real coordinate
ranges (~-9.1 to -9.2°E, ~38.7-38.8°N — genuine Lisbon values), not the
projected PT-TM06/EPSG:3763 easting/northing pair initially
flagged as a real possibility for Portuguese data.

**Dates: `periodos_condicionamentos` is a list, not one window** — a
genuinely richer shape than Madrid/DriveBC's single start/end. 665/694
real features have exactly one period, but up to 4 real periods exist on
some. Each period states `date_min`/`date_max` (bare dates) and separate
`hour_min`/`hour_max` (daily time-of-day), plus a real `is_interrupted`
flag — `True` on 583/727 real periods (the majority, not an edge case),
meaning "not currently in effect within its own window." `from_lisboa`
combines the first period's start and the last period's end into one
`WorksSite` window, the same multi-interval handling already used for
DriveBC; `is_interrupted` stays on `.raw` rather than forced into a field
that doesn't fit it.

**Network scope: `comprehensive`** — 27 distinct freguesias (parishes)
confirmed live, matching Lisbon's real administrative divisions, plus
some records explicitly scoped `"TODAS"` (all) — genuinely city-wide,
not a subset of the network.

**Licence: CC BY 4.0, confirmed live** at `dados.gov.pt`'s catalogue page
for this exact dataset (*"Licença: Creative Commons Attribution 4.0 - CC
BY 4.0"*, publisher "Município de Lisboa") — the same page whose stale
"última atualização" date prompted the freshness check above; the
licence statement isn't dated the same way and is treated as still
governing the live data, the same official CML dataset either way.

## Toponímia de Lisboa (CML)

Lisbon's own official street naming register, run by the same Câmara
Municipal de Lisboa (CML) that publishes the roadworks feed above — but
a genuinely separate real service (CML's Geodados ArcGIS Online
organisation, not the Angular closures app). This SDK's first
Portuguese streets/gazetteer coverage:

```python
from streetworks.arcgis.lisboa import LisboaStreetsClient
from streetworks.common import from_lisboa_street

with LisboaStreetsClient() as lisboa:
    streets = [from_lisboa_street(f) for f in lisboa.iter_streets()]
```

**National streets were already ruled out** — Infraestruturas de
Portugal's own promoted road-network service carries only
route-classification codes (`roadnumber`/`road1`, e.g. `"A1"`/`"IC1"`),
no name field at all (see
[`docs/portugal-streets-investigation.md`](../portugal-streets-investigation.md)).
Rather than stop there, this checks the capital itself — the same "try
the capital/a city" fallback shape Germany's own state fan-out uses.

**Found by walking CML's real Geodados ArcGIS Online organisation
(`geodados_CML`, ~130 real items), not from documentation alone — and
two other real candidates on that same organisation were checked and
set aside first**, both genuinely real but the wrong shape:

- `Topónimos` (on CML's `Cartografia_Base` service) — only 40 real
  point features, but neighbourhood/district labels ("Belém", "Baixa",
  "Alvalade"), not streets.
- `Rede Viária` (same service) — 3,763 real named road segments, but
  live grouping found only **375 distinct street names** across them —
  Lisbon's structuring/backbone road network, plainly not exhaustive
  for a city this size.

**`Toponímia de Lisboa` (on CML's `Cultura_Toponimia` service) is the
real, official register instead** — **3,671 real records, 100% carrying
a real name**, and, unlike the structuring-network layer, already one
row per street (confirmed live: a single `Avenida da Liberdade` record,
not several segments sharing the name). Each record carries genuine
municipal-decree provenance: real `DATA_DELIBERACAO_CAMARARIA`/
`DATA_EDITAL`/`DATA_PUBLICACAO`/`DATA_EDITAL_GOVERNO_CIVIL` dates, real
`DENOMINACOES_ANTERIORES` (former names — e.g. "Rua do Possolo" was
previously "Rua da Boa-Morte"), and a real prose `HISTORIAL` essay on
the name's origin, some running to several paragraphs — none of these
has a home on this SDK's canonical `Street` model, so all three stay on
`.raw` only.

**Geometry is real, and genuinely WGS84 — confirmed live, not assumed
from the service's own stated CRS.** The service's `spatialReference`
states Web Mercator (`EPSG:3857`), but a live `f=geojson` request (no
`outSR` requested) returns genuine WGS84 coordinates — the same
"GeoJSON output reprojects regardless of the layer's stated native CRS"
behaviour already documented for TIGERweb. A genuine `MultiLineString`
is real here too (a real "Avenida Ucrânia" spans 7 discontinuous
`paths` in one record) — carried via `Coordinate.parts`, GeoJSON's own
`(lon, lat)` axis order preserved rather than flipped (the same choice
`from_nrn`/`from_datavia` already make for their own GeoJSON-native
sources).

**`administrative_area` carries the real, verbatim `FREGUESIAS` string**
— a street can genuinely cross a parish boundary, and CML states this
as one comma-joined field (e.g. "Alcântara (Nova Freguesia), Belém
(Nova Freguesia)"), not two separate fields, so relaying it verbatim is
honest, not a fabricated join.

**Licence: real, explicit CC0** (`"Aplica-se a licença Creative Commons
CCZero"`, confirmed via the service's own `licenseInfo`), alongside a
real non-legal-use cartography caveat also stated there
(`"Cartografia não homologada, não podendo ser utilizada para fins
legais"`).

## The rest of the Portuguese landscape

National roadworks coverage is now live via IP directly (above) — the
NAP registration itself is a separate, still-pending track (account
under IMT's review), not a blocker for coverage. Streets is ruled out
nationally (see above) but not exhaustively — the Área Metropolitana de
Lisboa's other 17 municipalities, and other Portuguese cities (Porto and
others), haven't been checked individually; a real, open next step in
the same shape as Germany's state fan-out, if picked back up.
