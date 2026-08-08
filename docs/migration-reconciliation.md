# Docs migration — reconciliation note (phase one)

Per `docs-migration-brief.md`'s own instruction, the seed checklist was
treated as scaffolding, not ground truth. The actual README.md (3,652
lines, 49 `##` sections) was read in full before writing anything, and
every seed-checklist item was checked against it directly — several with
a follow-up targeted `grep` for the exact claimed wording, not just my
recollection of the read-through. See `docs/migration-mapping.md` for the
item-by-item table this note summarises.

## Case 2 — in the README, not on the seed checklist

This is the large majority of what actually got migrated. The seed
checklist's "Provider coverage" sections were short *name lists*
("Netherlands (NDW/DATEX II), Finland, Iceland, France, Norway
(scaffold), Spain (DGT), Belgium, ..."); the real README carries, for
every one of those names, several paragraphs of live-verified findings —
exact record counts, discriminator fields, CRS corrections, licence
text, grouping evidence, parser bugs found and fixed. None of that depth
was anticipated by the seed list, and all of it is preserved verbatim in
`docs/providers/`. Rather than re-list it here (it's already fully
itemised in `docs/migration-mapping.md`'s per-provider rows and, in
full, in the provider pages themselves), the headline additions worth
flagging explicitly:

- **Norway is not a scaffold.** The seed checklist says "Norway
  (scaffold)"; the real README shows Statens vegvesen's DATEX roadworks
  feed was **confirmed live on 2026-07-30** (844 real situations, mixed
  CRS resolved per-record) — it graduated out of Credentials-wanted
  before this checklist was written. Likewise Kartverket (addresses) and
  NVDB (streets), the same country's other two providers, are both
  confirmed, not scaffolded.
- **Five providers postdate the seed checklist entirely**: Germany
  (Autobahn GmbH, the Hamburg/Brandenburg/Saxony state-roadworks
  cluster, and Berlin/VIZ), BAG (Netherlands addresses), NWB (Netherlands
  streets), and Paris Chantiers (France, municipal). None appear on the
  seed list at all — the checklist was seeded from an earlier point in
  the project's history. All are fully migrated into
  `docs/providers/europe.md`.
- **The whole `## Roadmap` section** (a ~460-line chronological build
  log) isn't represented on the seed checklist in any form. It's
  migrated in full to `docs/roadmap.md`.
- **The whole "Never deduplicate across providers" principle**, its own
  named subsection in the README with a full worked justification, is
  only thinly gestured at by the seed checklist's one-line "no
  cross-provider deduplication" bullet. Migrated in full to
  `docs/concepts/data-model.md`.
- **The whole `## Canonical gazetteer model` section** (`Street`,
  `Segment`, `Address` — a second canonical type system alongside
  `Works`) isn't on the seed checklist at all. Migrated in full to
  `docs/concepts/data-model.md`.

## Case 3 — on the seed checklist, not in the README

Checked by full read-through and, for each of these, a follow-up
targeted `grep` across the whole README to make sure a passing mention
hadn't been missed:

- **UK per-USRN/terraces claim** ("UK permits issued per-USRN by
  statute; terraces share a parent USRN"). Not present anywhere.
- **S50 fee-suppression/deem-clock detail** ("S50's only Street
  Manager-specific behaviour is fee suppression at the reporting
  layer..."). Not present in the README. This level of Section 50 domain
  detail exists in `s50-streetworks-connector-brief.md` (a separate
  investigation document supplied earlier in this project, not README
  content) — genuinely true and well-evidenced there, just not migrated
  here since it was never in the migration source document.
- **China exclusion** (GCJ-02 obfuscation). Not present.
- **Russia exclusion** (sanctions/export controls). Not present.
- **Agent boundaries** (no government accounts, no ToS acceptance, no
  WAF circumvention). Not present in the README — this lives in project
  conventions/CLAUDE.md-adjacent material, not the README.
- **"Scaffold-prove-promote" / "no public API until a named consumer
  exists"** as a formally named principle. Not present as such — the
  README's actual `## Design principles` section states four different,
  shorter principles (migrated verbatim to `docs/concepts/architecture.md`).
  The underlying *behaviour* (credentials-wanted scaffolds, promoted once
  confirmed) is real and is documented in full under
  `docs/providers/index.md` §"Credentials wanted" — just never phrased
  as "scaffold-prove-promote" in the source text.
- **`_web_mercator`, `ArcGISFeatureClient.extra_params`** as named
  architectural precedents for "extract shared helpers bottom-up." Not
  named in the README text. The *pattern itself* is real and stated
  explicitly for three other shared clients (`streetworks.socrata`,
  `OGCFeaturesClient`, `ArcGISFeatureClient` — see
  `docs/concepts/architecture.md`), and the closed-form spherical-Mercator
  technique `_web_mercator` implements is described (unnamed) under Main
  Roads WA in `docs/providers/australia.md`.
- **Personal-capacity framing** ("developed independently, not on behalf
  of Durham County Council"). Not present.
- **Strategic Data Roadmap / OCDO / GDS submission**. Not present.
- **Chris Carlon attribution** (concept, testing, merged PR). Not
  present.
- **PyPI-since-June-2026 date, "developing and growing" phrase**. Not
  present — the README does state pre-1.0/"Early alpha" status and the
  `pip install streetworks` command, both migrated; the specific date and
  phrase aren't in the source text.
- **Portugal / Singapore / Canada (DriveBC Open511) as pending
  providers**. None of the three appear in the README in that framing.
  "Portugal" appears exactly once, as a future gazetteer name in a list
  alongside Spain Catastro and Germany Geoportal (migrated, see
  `docs/providers/europe.md` §"International gazetteers"). "Canada"
  appears exactly once, as the fact that a real Quebec City WZDx feed is
  *already* registered (migrated, `docs/providers/us.md` §"WZDx").
  "Singapore" does not appear at all.

None of the case-3 items were silently folded into the docs tree. Per
the brief's own instruction, they're noted here as out of scope for this
*migration*, not evaluated for whether they should become new material
in docs — that's an explicit phase-two (or later) editorial call for the
project owner to make, not something this pass decided unilaterally.

## Post-write mechanical verification

After the initial pass, I didn't just trust my own read-through summary
— I ran three independent mechanical checks against the finished
`docs/` tree:

1. **Every distinctive number in the README** (61 record counts/
   percentages, e.g. `3,798,494`, `22,105`, `0.26%`) — checked present
   somewhere in `docs/`.
2. **Every one of the 49 `##` section headers** — checked for a
   corresponding home.
3. **Every URL in the README** (54 total) — checked present in `docs/`.

This caught three real gaps that a read-through alone had missed,
described accurately in `docs/migration-mapping.md` rather than quietly
patched over:

- `## Paris Chantiers (Ville de Paris)` had been *described* as migrated
  to `providers/europe.md` but the section was never actually written —
  fixed.
- `## Ireland — MapRoad Roadworks Licensing` and `## Greece` each have
  their own full standalone README section, richer than their condensed
  `### Credentials wanted` table row (real detail that was missing: the
  full real dataset-title list for Greece, the `data.nap.imet.gr`
  TLS-handshake-hang finding, TII's own 20-dataset DATEX check for
  Ireland) — both fuller sections are now migrated to `providers/europe.md`.
- `## Development` (the `pip install -e ".[dev]"`/`pytest`/`ruff check`/
  smoke-test/integration-suite commands) wasn't migrated anywhere at all
  — fixed, now `getting-started/development.md`.

The URL check surfaced one deliberate, non-gap: 6 URLs unconfirmed in
`docs/` are the CI/PyPI/licence badge links at the very top of
README.md (lines 3–6) — presentational status badges, not informational
content. These are left on the README itself; they'll stay there in
phase two as well, since a front-door README keeps its build/version
badges regardless of how much prose moves to `docs/`.

## What this means for the exit gate

`docs-migration-brief.md`'s exit condition is that every checklist item
maps to a named docs location. `docs/migration-mapping.md` provides that
mapping for the full, reconciled checklist (seed items confirmed against
the README, case-2 additions found while reading it, case-3 items
explicitly marked out of scope with the reason why). The README itself
was not modified in this pass — it remains the reference copy, as the
brief requires, until this mapping and the docs tree it produced are
reviewed.
