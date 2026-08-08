# README slim-down — removal map (phase two)

Per `docs-migration-phase-two-brief.md`'s rule: **nothing removed unless
provably present in docs.** Every row below is a `##`/`###` section that
existed in the pre-slim README (3,652 lines, confirmed via `git show
<pre-slim-commit>:README.md`) and was removed in this pass. Every one of
these was already confirmed migrated, verbatim or in full, during phase
one — see `docs/migration-mapping.md` for the original per-item
evidence (including the post-write mechanical check that caught three
real gaps and fixed them before this phase started). This table doesn't
repeat that evidence; it re-confirms the mapping still holds and records
what's now gone from the README itself.

No block was deleted without a row here. Nothing is left with no docs
home — the three case-3 items (personal-capacity framing, agent
boundaries, etc.) were never in the README in the first place, so
there's nothing to remove for them; they were added as new docs content
separately (see `docs/migration-reconciliation.md`'s "Post-migration
addendum").

| Removed README section | Docs home |
|---|---|
| `## Finding a provider` (the `providers()`/`get_provider()` walkthrough + full module table) | `docs/providers/index.md` §"Module table" (top of page) |
| `## What this is (and isn't)` | `docs/concepts/architecture.md` §"What this is (and isn't)" |
| `## Status` (verified-providers prose, Autobahn licence caveat, write-path status, D-TRO v4.0.0 note) | `docs/providers/index.md` §"Status"; `docs/concepts/write-path.md` (write-path verification status); `docs/roadmap.md` (D-TRO v4.0.0) |
| `### Credentials wanted` | `docs/providers/index.md` §"Credentials wanted" |
| `### Recently confirmed` | `docs/providers/index.md` §"Recently confirmed" |
| `## Prerequisites: credentials` | `docs/getting-started/quickstart.md` §"Prerequisites: credentials" |
| `## Verify your setup` | `docs/getting-started/quickstart.md` §"Verify your setup" |
| `## Street Manager` | `docs/providers/uk.md` §"Street Manager"; `docs/concepts/write-path.md` (S50 connector) |
| `## Street Manager Open Data (SNS push)` | `docs/providers/uk.md` §"Street Manager Open Data (SNS push)" |
| `## Geoplace DataVIA` | `docs/providers/uk.md` §"Geoplace DataVIA" |
| `## DfT D-TRO` | `docs/providers/uk.md` §"DfT D-TRO" |
| `## Scottish Road Works Register (SRWR) Open Data` | `docs/providers/uk.md` §"Scottish Road Works Register (SRWR) Open Data" |
| `## OS Open USRN` | `docs/providers/uk.md` §"OS Open USRN" |
| `## Base Adresse Nationale (BAN)` | `docs/providers/europe.md` §"Base Adresse Nationale (BAN)" |
| `## Basisregistratie Adressen en Gebouwen (BAG)` | `docs/providers/europe.md` §"Basisregistratie Adressen en Gebouwen (BAG)" |
| `## Kartverket (Norway)` | `docs/providers/europe.md` §"Kartverket (Norway)" |
| `## NVDB (Norway)` | `docs/providers/europe.md` §"NVDB (Norway)" |
| `## NWB (Netherlands)` | `docs/providers/europe.md` §"NWB (Netherlands)" |
| `## BD TOPO (France)` | `docs/providers/europe.md` §"BD TOPO (France)" |
| `## DATEX II (European roadworks)` | `docs/providers/europe.md` §"DATEX II (European roadworks)" |
| `## Autobahn GmbH (Germany, national motorways)` | `docs/providers/europe.md` §"Autobahn GmbH (Germany, national motorways)" |
| `## Via Lietuva (Lithuania)` | `docs/providers/europe.md` §"Via Lietuva (Lithuania)" |
| `## German state roadworks (OGC WFS)` | `docs/providers/europe.md` §"German state roadworks (OGC WFS)" |
| `## Berlin (VIZ)` | `docs/providers/europe.md` §"Berlin (VIZ)" |
| `## Consell de Mallorca (island roadworks)` | `docs/providers/europe.md` §"Consell de Mallorca (island roadworks)" |
| `## Servei Català de Trànsit (Catalonia)` | `docs/providers/europe.md` §"Servei Català de Trànsit (Catalonia)" |
| `## Basque Country (Euskadi)` | `docs/providers/europe.md` §"Basque Country (Euskadi)" |
| `## Jersey RoadWorkx and TIGERweb (ArcGIS REST)` | `docs/providers/uk.md` §"Jersey RoadWorkx and TIGERweb (ArcGIS REST)" |
| `## Main Roads WA (ArcGIS REST)` | `docs/providers/australia.md` §"Main Roads WA (ArcGIS REST)" |
| `## QLDTraffic Events (Queensland)` | `docs/providers/australia.md` §"QLDTraffic Events (Queensland)" |
| `## Traffic SA / DIT Roadworks (South Australia) — Credentials wanted` | `docs/providers/australia.md` §"Traffic SA / DIT Roadworks (South Australia)" |
| `## ACT & Tasmania — the AU tail, plus a documented Northern Territory` | `docs/providers/australia.md` §"ACT & Tasmania" |
| `## NZTA & LINZ (New Zealand)` | `docs/providers/new-zealand.md` |
| `## G-NAF & National Roads (Australia)` | `docs/providers/australia.md` §"G-NAF & National Roads (Australia)" |
| `## WZDx (US Work Zone Data Exchange)` | `docs/providers/us.md` §"WZDx (US Work Zone Data Exchange)" |
| `## NYC DOT Street Construction Permits (New York City)` | `docs/providers/us.md` §"NYC DOT Street Construction Permits (New York City)" |
| `## Chicago CDOT Street Closures` | `docs/providers/us.md` §"Chicago CDOT Street Closures" |
| `## Paris Chantiers (Ville de Paris)` | `docs/providers/europe.md` §"Paris Chantiers (Ville de Paris)" |
| `## Ireland — MapRoad Roadworks Licensing (documented, unavailable)` | `docs/providers/europe.md` §"Ireland — MapRoad Roadworks Licensing" |
| `## Greece (documented, unavailable)` | `docs/providers/europe.md` §"Greece" |
| `## Northern Ireland & Wales (traveller-information RSS)` | `docs/providers/uk.md` §"Northern Ireland & Wales (traveller-information RSS)" |
| `## Italy — CCISS (traffic bulletin RSS)` | `docs/providers/italy.md` |
| `## UK Police (crime data — a worker-safety signal)` | `docs/providers/uk.md` §"UK Police (crime data — a worker-safety signal)" |
| `## Common models` | `docs/concepts/data-model.md` §"Works model" |
| `### Never deduplicate across providers` | `docs/concepts/data-model.md` §"Never deduplicate across providers" |
| `## Canonical gazetteer model (Street, Segment, Address)` | `docs/concepts/data-model.md` §"Canonical gazetteer model" |
| `## Design principles` | `docs/concepts/architecture.md` §"Design principles" |
| `## Roadmap` (chronological `[x]`/`[ ]` log) | `docs/roadmap.md` |
| `### European & Crown Dependency roadworks — separate strand` | `docs/providers/europe.md` §"European & Crown Dependency roadworks — separate strand" |
| `### International gazetteers — separate strand` | `docs/providers/europe.md` §"International gazetteers — separate strand" |
| `## Development` | `docs/getting-started/development.md` |

## What stayed, and why

- **Badges** (CI/PyPI/Python/licence, lines 3–6) — presentational chrome,
  not migrated content; stays on the README regardless of how much prose
  moves, per phase one's own note on this.
- **Title, one-line description, "We do this..." quote, intro code
  block** — the front door's identity; kept verbatim.
- **`## Install`, the `## Quickstart` intro code block and
  `cp .env.example`/`python examples/quickstart.py` commands** — kept
  inline and runnable, not linked away, per the brief's explicit
  instruction that a newcomer should get value from the README alone.
- **The one-line `Contributions welcome — see CONTRIBUTING.md`** — kept
  verbatim, already exactly the "one line + link" shape the brief asks
  for.
- **`## Licence`** — kept verbatim (MIT / Crown copyright / OGL v3.0
  attribution), with a new link into `docs/governance/licensing.md` for
  the full per-provider licence index.

## What's new on the README (not a removal, an addition)

- The personal-capacity disclaimer, near the top — its first *visible*
  home (previously docs-only, per the project owner's own decision on
  timing during phase one). Full statement in
  `docs/governance/attribution.md`.
- A short "Coverage at a glance" paragraph, replacing the full module
  table with a summary + link — new prose, not migrated from anywhere,
  since the brief explicitly asks for a thin summary here rather than a
  reproduction of the (now docs-only) full list.
- The "Documentation" navigation block, mirroring `docs/index.md`'s own
  map so the two front doors (GitHub README, `docs/index.md`) point to
  the same tree.
