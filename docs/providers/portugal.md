# Portugal

> New content, not a migration — Portugal wasn't a built provider at the
> time of the phase-one docs migration (see `docs/providers/pending.md`,
> which this section now supersedes for Lisboa specifically). The
> national IMT National Access Point remains credential-parked and
> unbuilt; this is Portugal's first coverage at any level, reached by
> sidestepping that entirely via a separate keyless municipal feed.

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

## The rest of the Portuguese landscape

Not built — the national IMT National Access Point remains
credential-parked (access requested, not yet granted). Lisboa was
chosen specifically because it sidesteps that wait entirely. Other
Portuguese municipalities (Porto, and others) haven't been investigated
this session.
