# Agent instructions

House rules for any coding agent (or human, following the same
discipline) working on `streetworks`. This is the load-bearing summary
— [`docs/contributing/agent-boundaries.md`](docs/contributing/agent-boundaries.md),
[`docs/concepts/data-integrity.md`](docs/concepts/data-integrity.md),
[`docs/contributing/scaffolds.md`](docs/contributing/scaffolds.md), and
[`CONTRIBUTING.md`](CONTRIBUTING.md) carry the full detail behind each
rule below.

## The one rule everything else follows from

**Verify live, never trust documentation alone.** A provider's own
docs, a design brief, or a plausible-sounding field name is a
hypothesis, not a fact — confirm it against a real request before it
goes in a docstring or a converter. This project's docstrings cite what
was actually observed live (real field values, real record counts, real
error messages) rather than what a spec claims. If something can't be
checked live, say so honestly rather than assuming it works.

## Data-handling rules

- **Never fabricate.** No invented street names, no guessed centroids
  from polygon geometry, no synthesised identifiers, no assumed CRS,
  no derived "Street" entity a source doesn't actually publish. A real
  gap (no name, no geometry, no identifier) is recorded as an honest
  gap — `GeometryGrade.ABSENT`, an empty `names` tuple, `None` — never
  papered over. See `docs/concepts/data-integrity.md`.
- **Never silently reproject or silently truncate.** Carry a source's
  stated CRS as given (`Coordinate.crs`), and detect + raise
  (`TruncatedResultError`) rather than quietly returning a partial
  result when a service's pagination can't be trusted — several real
  providers in this SDK have pagination or CRS-reprojection quirks that
  were only caught by testing live, not by reading the docs.
- **Real fixtures over synthetic ones.** Test fixtures are real,
  trimmed, captured API responses wherever a source's licence allows —
  not invented data — with a short note on what was trimmed and why.
- **No synthetic streets.** A `Street`/`Segment` is only ever emitted
  by a provider that actually publishes one; never derived by grouping
  addresses or route segments.

## Access boundaries (see `docs/contributing/agent-boundaries.md`)

- No registering for, or using, an account under any government or
  institutional identity to access a data source.
- No accepting a provider's terms of service or developer agreement on
  the project's behalf to unlock access. If a source needs that, it
  stays a documented, unavailable scaffold — see
  `docs/contributing/scaffolds.md`.
- No circumventing a WAF or bot-protection. A block is a real, honestly
  reportable finding, not something to route around.

## Licensing

No explicit licence document found is *not* the same as "don't build" —
several real providers here ship on the project owner's explicit
instruction rather than a discovered licence text (documented as such,
not overclaimed). An **explicit** "permission required" / rights-reserved
statement *is* a real blocker (see Spain's Catastro in
`docs/providers/pending.md`) unless the project owner explicitly
authorises building anyway — that authorisation is a judgement call for
the project owner, not something to infer.

## Adding a new provider

1. One module under `src/streetworks/<provider>/` (or
   `src/streetworks/arcgis/<name>.py` if it's a plain ArcGIS REST
   FeatureServer/MapServer — reuse `ArcGISFeatureClient`, don't
   reinvent it; same idea for `streetworks.ogc.OGCFeaturesClient` on
   classic WFS/OGC API Features sources), built on
   `streetworks._transport`, raising `streetworks.exceptions` types.
2. A converter in `src/streetworks/common/from_<provider>.py` into the
   shared `Works`/`WorksSite` or `Street`/`Segment`/`Address` model —
   see `docs/concepts/common-model.md`.
3. A registry entry in `src/streetworks/registry.py` — every roadworks
   entry needs a real, audited `network_scope`
   (`docs/network-scope-audit.md`), never left at the bare default.
4. A docs section in the relevant `docs/providers/<place>.md` (or a new
   file if the territory doesn't have one yet) — write the live
   evidence into the module docstring first, then mirror the key points
   into the docs page.
5. A `docs/providers/index.md` module-table row — `pytest` enforces
   registry ⟷ docs-table agreement
   (`test_registry_top_level_modules_match_docs_provider_table`), so a
   provider can't ship registered-but-undocumented or vice versa.
6. Tests: `respx`-mocked, real trimmed fixtures, no credentials needed
   to run the suite.
7. A `CHANGELOG.md` entry — including for a genuine negative finding
   (investigated, ruled out) recorded in `docs/providers/pending.md`,
   not just for a successful build.

## Before calling anything done

- `ruff check .` and `mypy` clean on every new/changed file.
- Full `pytest` suite green (credential-free).
- If it's a UI/example change, actually run it — type-checking is not
  the same as confirming the feature works.

## Scope of this SDK

Multi-provider roadworks/street-works/gazetteer data — see
[`README.md`](README.md) and [`docs/index.md`](docs/index.md) for the
full picture, [`docs/providers/index.md`](docs/providers/index.md) for
the live coverage matrix (81 providers as of the last count: 58
roadworks, 17 streets, 5 addresses, 1 context), and
[`docs/providers/pending.md`](docs/providers/pending.md) for genuine,
evidenced negative findings — territories checked and ruled out, not
just unstarted.
