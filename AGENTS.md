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

## Commands

```bash
pip install -e ".[dev]"        # editable install + dev tooling (ruff, mypy, pytest)
ruff check .                   # lint
mypy                           # type-check (uses [tool.mypy] config)
pytest                         # full suite, credential-free
pytest -m integration          # opt-in: live/sandbox tests, need credentials
python scripts/smoke_test.py   # end-to-end smoke check
```

Live/integration runs (`smoke_test.py`, `pytest -m integration`) target
non-production by default and refuse production unless explicitly opted
in (`--allow-production` / `STREETWORKS_ALLOW_PRODUCTION=1`).

## Data-handling rules

- **Never fabricate.** No invented street names, no guessed centroids
  from polygon geometry, no synthesised identifiers, no assumed CRS,
  no derived "Street" entity a source doesn't actually publish. A real
  gap (no name, no geometry, no identifier) is recorded as an honest
  gap — `GeometryGrade.ABSENT`, an empty `names` tuple, `None` — never
  papered over. See `docs/concepts/data-integrity.md`.
- **Never silently reproject or silently truncate.** Carry a source's
  stated CRS as given (`Coordinate.crs`) and preserve Z where the source
  states it (never default it to zero); detect + raise
  (`TruncatedResultError`) rather than quietly returning a partial
  result when a service's pagination can't be trusted — several real
  providers in this SDK have pagination or CRS-reprojection quirks that
  were only caught by testing live, not by reading the docs.
- **Never deduplicate across providers.** Overlap between two providers
  is real data, not a bug. Both republication-style overlap (e.g. DGT
  and Consell de Mallorca in the Balearics) and jurisdictional-boundary
  overlap (e.g. National Highways and Street Manager on slip roads, or
  Kanton vs Stadt Zürich carrying the same closure) are expected and
  kept — deduping would silently drop genuine records.
- **Preserve provenance.** Every converter keeps the untouched source
  record(s) on `.raw`; the canonical model is additive over the native
  data, never lossy. Two independently-stated identifiers stay as two,
  not collapsed into one.
- **Grade honestly, don't assume.** `source_grade`
  (`REGISTER`/`OPERATOR`/`TRAVELLER_INFO`) and date-confidence
  (`VERIFIED`/`ESTIMATED`) must reflect what the source actually is and
  states, confirmed live — not what's convenient. A permit register with
  real third-party applicants is `REGISTER`; a status field that
  genuinely distinguishes active from future works earns real date
  confidence; when a source states neither, say so rather than inventing
  a grade. These are roadworks-provenance fields — a streets/addresses
  feed doesn't set them, and grades geometry via `GeometryGrade` instead.
- **Real fixtures over synthetic ones.** Test fixtures are real,
  trimmed, captured API responses wherever a source's licence allows —
  not invented data — with a short note on what was trimmed and why.
- **No synthetic streets.** A `Street`/`Segment` is only ever emitted
  by a provider that actually publishes one; never derived by grouping
  addresses or route segments.
- **Keep the dependency surface tiny.** Runtime dependencies are
  deliberately just `httpx` + `pydantic` (standard library otherwise —
  no GDAL, no geopandas). Do geometry / CRS work by hand or skip it (per
  the CRS rule above); don't pull in a heavy geo stack to sidestep the
  discipline.
- **Don't hand-edit generated models.** The Pydantic models under
  `streetmanager/models/` and `dtro/models/` are generated-and-committed
  (so PyPI users get them without running the generators) and
  ruff-excluded — regenerate via `scripts/generate_models.py` /
  `scripts/generate_dtro_models.py`, don't edit them by hand.

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

The skeleton is identical whether it's a **roadworks**, **streets**, or
**addresses** feed — module, docs, registry, index-table row, tests,
changelog. Two steps diverge by data class; both paths are spelled out.

1. One module under `src/streetworks/<provider>/` (or
   `src/streetworks/arcgis/<name>.py` for a plain ArcGIS REST
   FeatureServer/MapServer — reuse `ArcGISFeatureClient`, don't reinvent
   it; same idea for `streetworks.ogc.OGCFeaturesClient` on classic
   WFS / OGC API Features sources), built on `streetworks._transport`,
   raising `streetworks.exceptions` types (never call `httpx` directly —
   the shared transport centralises retries, backoff, `Retry-After` and
   error-mapping). Expose the iterator for the
   data class — `iter_roadworks()` for works, `iter_streets()` /
   `iter_addresses()` for a gazetteer (a source that publishes both, like
   a national register, exposes both siblings).
2. A converter in `src/streetworks/common/from_<provider>.py` into the
   shared model **for that class — `Works`/`WorksSite` for roadworks,
   `Street`/`Segment`/`Address` for a gazetteer** (see
   `docs/concepts/common-model.md`). Either way: preserve `.raw`, grade
   geometry honestly, label CRS, never synthesise a street. The native
   client returns raw decoded JSON (`dict`); this converter and the
   generated Pydantic models are opt-in layers the caller applies, not
   the client's return type.
3. A registry entry in `src/streetworks/registry.py`. Every entry sets
   `kind` (`roadworks` / `streets` / `addresses` / `context`). Then, by
   class:
   - **roadworks** — a real, audited `network_scope`
     (`docs/network-scope-audit.md`) plus a `source_grade`
     (`REGISTER`/`OPERATOR`/`TRAVELLER_INFO`) and date-confidence that
     reflect the source honestly, never left at the bare default.
   - **streets / addresses** — no `network_scope` or `source_grade`
     (those are roadworks-provenance concepts); the gazetteer-integrity
     rules carry the load instead (honest `GeometryGrade`, labelled CRS,
     no synthetic streets).
4. A docs section in the relevant `docs/providers/<place>.md` (or a new
   file if the territory doesn't have one yet) — write the live
   evidence into the module docstring first, then mirror the key points
   into the docs page. Show **both** access paths in the guide: the
   native, full-fidelity client (`iter_roadworks()` / `iter_streets()` /
   `iter_addresses()`, the provider's own rich types) and — where a
   converter exists — the common-model path (`from_<provider>(...)` into
   `Works` / `Street` / `Address`). Documenting both is the point of the
   SDK; `docs/concepts/common-model.md` is the companion for the
   conversion side.
5. A `docs/providers/index.md` module-table row — `pytest` enforces
   registry ⟷ docs-table agreement
   (`test_registry_top_level_modules_match_docs_provider_table`), so a
   provider can't ship registered-but-undocumented or vice versa.
6. Tests: `respx`-mocked, real trimmed fixtures, no credentials needed
   to run the suite.
7. A `CHANGELOG.md` entry — including for a genuine negative finding
   (investigated, ruled out) recorded in `docs/providers/pending.md`,
   not just for a successful build.

A **distinct legal jurisdiction gets its own entry** — the Crown
Dependencies (Jersey, Guernsey, Isle of Man), Gibraltar (a British
Overseas Territory), and the devolved UK nations each stand alone, never
folded under "UK". Coverage can
legitimately be sub-national (a city, a canton, a county) — state that
in `network_scope` rather than overclaiming national reach.

**Don't invent a unified national client.** There is deliberately no
country-level aggregation — merging Street Manager, SRWR and the NI /
Wales feeds into one "UK roadworks" client is exactly the fabricated
equivalence the SDK refuses (the registry comments say as much).
Discovery *by* territory is supported — `providers(territory="UK")`
lists what's there — but each provider stays its own native module: the
caller composes, the SDK doesn't pretend the sources are one.

## Model & branch discipline

- **Defer, don't pre-build.** Don't add a canonical field or capability
  until a real, provider-agnostic consumer needs it. A single confirmed
  source, or a throwaway example, doesn't justify promoting a field —
  linear referencing stayed deferred on one confirmed source for exactly
  this reason.
- **No drive-by scope changes.** Stay on the branch's stated task. A new
  source spotted mid-build, or a refactor idea, is a separate piece of
  work — record it (the roadmap, an issue, or `pending.md`), don't
  smuggle it into an unrelated branch.

## Before calling anything done

- `ruff check .` and `mypy` clean on every new/changed file.
- Full `pytest` suite green (credential-free).
- If it's a UI/example change, actually run it — type-checking is not
  the same as confirming the feature works.
- `__version__` in `src/streetworks/__init__.py` must equal the version
  in `pyproject.toml` — update both together; they drift easily.

## Scope of this SDK

Multi-provider roadworks/street-works/gazetteer data — see
[`README.md`](README.md) and [`docs/index.md`](docs/index.md) for the
full picture, [`docs/providers/index.md`](docs/providers/index.md) for
the live coverage matrix and current provider count (that table is
`pytest`-enforced against the registry, so treat it — not any number
memorised elsewhere — as the source of truth for what's live), and
[`docs/providers/pending.md`](docs/providers/pending.md) for genuine,
evidenced negative findings — territories checked and ruled out, not
just unstarted.
