# Docs migration — mapping table (phase one)

The deliverable required by `docs-migration-brief.md`: every checklist
item mapped to its docs file and section. Legend: **✅ In README** =
preservation target, migrated below. **❌ Not in README** = seed-list
item that isn't actual README content, out of scope for this migration
(see `docs/migration-reconciliation.md` for detail on each).

**Post-write verification (added after the initial mapping table and
docs tree were first produced):** every distinctive numeric fingerprint
in the README (record counts, percentages — 61 in total, e.g.
`3,798,494`, `22,105`, `0.26%`) was mechanically checked against the
full `docs/` tree, and every one of the 49 `##` section headers was
checked for a corresponding home. This caught three real gaps, now
fixed: the `## Paris Chantiers (Ville de Paris)` section had been
described as migrated in this table but was never actually written into
`providers/europe.md`; the `## Ireland — MapRoad Roadworks Licensing`
and `## Greece` sections had only their condensed
`### Credentials wanted` table rows migrated, not their fuller
standalone-section prose (real detail lost: Greece's full real dataset
list, the `data.nap.imet.gr` TLS-handshake-hang finding, TII's 20-dataset
DATEX check); and the `## Development` section wasn't migrated anywhere
at all. All three are now fixed — see `providers/europe.md` and the new
`getting-started/development.md`. This is exactly the class of error a
"looks complete" read-through misses and a mechanical check catches, which
is why it's recorded here rather than silently corrected.

The README itself was read in full (all 3,652 lines, 49 `##` sections)
before this table was built, per the brief's own reconciliation
requirement — this is not the seed list alone.

## Data integrity principles

| Checklist item | Status | Docs location |
|---|---|---|
| Verify-first against live data; documentation is wrong on nearly every provider | ✅ | `concepts/data-integrity.md` §"Verify live, never trust documentation alone" |
| Never silently reproject; stated CRS stored on `Coordinate.crs` always | ✅ | `concepts/data-integrity.md` §"Never silently reproject"; full detail `concepts/crs-and-datums.md` |
| Never infer unstated data; stated-identifier-only joins (no name-matching) | ✅ | `concepts/data-integrity.md` §"Stated-identifier joins only" |
| Never synthesise a `Street` entity a source doesn't publish | ✅ | `concepts/data-model.md` §"No synthetic streets" |
| Z coordinates preserved, never defaulted to zero | ✅ | `concepts/data-model.md` §"Two additions to `Coordinate`" |
| No cross-provider deduplication (republication overlap AND jurisdictional-boundary overlap both legitimate) | ✅ | `concepts/data-model.md` §"Never deduplicate across providers" |

## Architectural principles

| Checklist item | Status | Docs location |
|---|---|---|
| SDK is pure transport — no inference, no business logic | ⚠️ partial | The literal phrase "pure transport" is not in the README; the *concept* is real and demonstrated throughout (see `concepts/data-integrity.md`) and stated once, differently worded, in `concepts/architecture.md` §"What this is (and isn't)". See reconciliation note. |
| Do not pre-abstract; extract shared helpers bottom-up on the second real consumer (`_web_mercator`, `ArcGISFeatureClient.extra_params`, `streetworks.socrata`, `_wkt.py`) | ⚠️ partial | The `streetworks.socrata`/`OGCFeaturesClient`/`ArcGISFeatureClient` extraction narrative *is* in the README and is migrated to `concepts/architecture.md` §"Shared clients: built bespoke, extracted on the second real consumer". `_web_mercator` and `ArcGISFeatureClient.extra_params` as *named* precedents are not in the README text (see reconciliation note) — the closed-form spherical-Mercator pattern itself is present under Main Roads WA, `providers/australia.md`. |
| Scaffold-prove-promote: build to module standard, no public API until a named consumer exists | ❌ | Not in README — see reconciliation note. |
| `source_grade` (`register` / `operator` / `traveller_info`) — machine-readable trustworthiness | ✅ | `concepts/data-model.md` §"Works model" |
| `territory` (country-level, UK nations as countries) on `Works` only | ✅ | `concepts/data-model.md` §"Works model" |
| `administrative_area` (data-owning authority; role-equivalence not size-equivalence) on `Works` only | ✅ | `concepts/data-model.md` §"Works model" |
| `WorksPlanning` is a separate type; planning artifacts never migrate canonical type as lifecycle progresses | ✅ | `concepts/data-model.md` §"Works model" |

## Domain-specific findings

| Checklist item | Status | Docs location |
|---|---|---|
| UK permits issued per-USRN by statute; terraces share a parent USRN | ❌ | Not in README (checked via full read + targeted grep for "terrace"/"per-USRN") — see reconciliation note. |
| S50's only Street Manager-specific behaviour is fee suppression at the reporting layer; all other permit mechanics (deem clock, validity period, category engine) apply identically | ❌ | Not in README (checked via targeted grep for "fee suppress"/"deem clock") — this level of S50 domain detail lives in `s50-streetworks-connector-brief.md`, a separate investigation document, not the README. See reconciliation note. |
| Mallorca/DGT overlap is republication, not jurisdictional (earlier "genuinely additive" claim retracted) | ✅ | `concepts/data-model.md` §"Never deduplicate across providers"; `providers/europe.md` §"Consell de Mallorca (island roadworks)" |
| Belgium roadworks use Lambert-72 in fields labelled `<latitude>`/`<longitude>`; `from_datex2()` gained a `crs` parameter | ✅ | `providers/europe.md` §"DATEX II (European roadworks)" (Belgium paragraph); `concepts/crs-and-datums.md` |
| DATEX v1.0 `tpeglinearLocation` is lowercase (v2/v3 camelCase); was silently degrading 2-point lines to single points | ✅ | `providers/europe.md` §"Basque Country (Euskadi)" |
| China ruled out (GCJ-02 obfuscation incompatible with explicit-CRS discipline) | ❌ | Not in README (checked via targeted grep for "China"/"GCJ-02") — see reconciliation note. |
| Russia ruled out (sanctions / export controls) | ❌ | Not in README (checked via targeted grep for "Russia"/"sanctions") — see reconciliation note. |

## Write-path

| Checklist item | Status | Docs location |
|---|---|---|
| S50 connector is the first write-path adapter; three verbs (apply / start / stop) | ✅ | `concepts/write-path.md` |
| HA promoter credentials; `activity_type` pinned to `section_50`; ground-truthed against a real sandbox submission | ✅ | `concepts/write-path.md` |
| `streetworks.socrata` shared SODA client factored out as a shared module | ✅ | `concepts/architecture.md` §"Shared clients"; `providers/us.md` §"NYC DOT Street Construction Permits" |

## Provider coverage — UK

| Checklist item | Status | Docs location |
|---|---|---|
| Street Manager (read + S50 write-path connector) | ✅ | `providers/uk.md` §"Street Manager"; `concepts/write-path.md` |
| DataVIA/NSG | ✅ | `providers/uk.md` §"Geoplace DataVIA" |
| OS Open USRN | ✅ | `providers/uk.md` §"OS Open USRN" |
| National Highways | ✅ | `providers/europe.md` §"DATEX II (European roadworks)" (National Highways is documented as part of the DATEX II section in the README, not its own heading) |
| TrafficWatchNI | ✅ | `providers/uk.md` §"Northern Ireland & Wales" |
| Traffic Wales | ✅ | `providers/uk.md` §"Northern Ireland & Wales" |
| UK Police (worker-safety context) | ✅ | `providers/uk.md` §"UK Police" |
| D-TRO v4.0.0 | ✅ | `providers/uk.md` §"DfT D-TRO"; `roadmap.md` (the v4.0.0 migration bullet); `getting-started/installation.md` §"Status" |

Not on the seed checklist, but real README content requiring its own
home: the `## Development` section (`pip install -e ".[dev]"`, `pytest`,
`ruff check .`, smoke test / integration suite commands) → migrated to
`getting-started/development.md`. The `## Ireland — MapRoad Roadworks
Licensing` and `## Greece` sections (both "documented, unavailable"
scaffolds) → migrated in full to `providers/europe.md`, cross-referenced
from the condensed table in `providers/index.md`.

Also migrated, not on the seed list: Street Manager Open Data (SNS push),
SRWR Open Data, Jersey RoadWorkx + TIGERweb (ArcGIS REST) — all in
`providers/uk.md`.

## Provider coverage — Europe

| Checklist item | Status | Docs location |
|---|---|---|
| Netherlands (NDW/DATEX II) | ✅ | `providers/europe.md` §"DATEX II (European roadworks)" |
| Finland | ✅ | `providers/europe.md` §"DATEX II (European roadworks)" |
| Iceland | ✅ | `providers/europe.md` §"DATEX II (European roadworks)" |
| France | ✅ | `providers/europe.md` §"DATEX II" (Bison Futé), §"BD TOPO", §"Base Adresse Nationale (BAN)" |
| Norway (scaffold) | ⚠️ corrected | Norway's DATEX roadworks feed (Statens vegvesen) is **confirmed, not a scaffold** — see `providers/index.md` §"Recently confirmed" (2026-07-30). Kartverket and NVDB (the same country's address/street registers) are also confirmed. See reconciliation note. |
| Spain (DGT) | ✅ | `providers/europe.md` §"DATEX II (European roadworks)" |
| Belgium | ✅ | `providers/europe.md` §"DATEX II (European roadworks)" |
| Luxembourg | ✅ | `providers/europe.md` §"DATEX II (European roadworks)" |
| Bulgaria | ✅ | `providers/europe.md` §"DATEX II (European roadworks)" |
| Lithuania | ✅ | `providers/europe.md` §"Via Lietuva (Lithuania)" |
| Mallorca | ✅ | `providers/europe.md` §"Consell de Mallorca (island roadworks)" |
| Catalonia | ✅ | `providers/europe.md` §"Servei Català de Trànsit (Catalonia)" |
| Basque Country | ✅ | `providers/europe.md` §"Basque Country (Euskadi)" |
| Sweden and Denmark as credential-blocked scaffolds | ✅ | `providers/index.md` §"Credentials wanted"; `providers/europe.md` §"DATEX II (European roadworks)" |
| Italy: RSS feed via cciss.it (EU NAP-listed) | ✅ | `providers/italy.md` |

Also migrated, not on the seed list: Germany (Autobahn GmbH, German
state roadworks/Hamburg/Brandenburg/Saxony, Berlin/VIZ), BAG
(Netherlands), NWB (Netherlands), Paris Chantiers (France, municipal).
All added after the seed checklist was written — see the reconciliation
note for why (they postdate the brief, or are gazetteer providers the
brief's provider-coverage section didn't enumerate).

## Provider coverage — US

| Checklist item | Status | Docs location |
|---|---|---|
| WZDx feed registry (NY State 511NY verified) | ✅ | `providers/us.md` §"WZDx (US Work Zone Data Exchange)" |
| NYC DOT permits | ✅ | `providers/us.md` §"NYC DOT Street Construction Permits" |
| Florida and Austin (WZDx, docs-only) | ✅ | `providers/us.md` §"WZDx" |
| Chicago DOT (Socrata) | ✅ | `providers/us.md` §"Chicago CDOT Street Closures" |

Also migrated, not on the seed list: TIGERweb (in `providers/uk.md`,
alongside Jersey), Paris Chantiers (in `providers/europe.md` — this is a
**France** provider, not US; the seed checklist's implicit US framing for
"municipal permit registers" doesn't apply — see reconciliation note).

## Provider coverage — Australia / NZ

| Checklist item | Status | Docs location |
|---|---|---|
| Australia: QLD verified | ✅ | `providers/australia.md` §"QLDTraffic Events (Queensland)" |
| TAS/ACT built and verified | ✅ | `providers/australia.md` §"ACT & Tasmania" |
| SA and NT scaffolded | ✅ | `providers/australia.md` §"Traffic SA / DIT Roadworks"; §"ACT & Tasmania" (NT paragraph) |
| G-NAF addresses + National Roads via Digital Atlas of Australia | ✅ | `providers/australia.md` §"G-NAF & National Roads (Australia)" |
| New Zealand: NZTA works (ArcGIS) + LINZ gazetteer (NZ Addresses + Roads/Sections) | ✅ | `providers/new-zealand.md` |

Also migrated, not on the seed list: NSW and Victoria (the two providers
confirmed 2026-07-30, see `providers/index.md` §"Recently confirmed"),
Main Roads WA.

## Provider coverage — pending

| Checklist item | Status | Docs location |
|---|---|---|
| Portugal (credential-parked) | ❌ | Not in README as a pending *provider* — "Portugal SNIG" appears once, in passing, as a future gazetteer name in `providers/europe.md` §"International gazetteers — separate strand". See reconciliation note. |
| Singapore (credential-parked) | ❌ | Not in README at all. See reconciliation note. |
| Canada (DriveBC Open511, future strand) | ❌ | Not in README as a pending provider — Canada appears once, as a fact that a real Quebec City WZDx feed is *already* registered and covered (`providers/us.md` §"WZDx"), not as a future DriveBC strand. See reconciliation note. |

Real "not yet built" content that *is* in the README, migrated instead:
`roadmap.md` (the full chronological `[ ]`-item checklist: D-TRO v5.0.0,
Sweden/Denmark DATEX Phase 1, further DATEX NAPs, OS NGD) and
`providers/europe.md` §"European & Crown Dependency roadworks — separate
strand" / §"International gazetteers — separate strand" (Guernsey,
Mobilithek, UK local-authority ArcGIS roadworks, Spain Catastro, Germany
Geoportal, Portugal SNIG, the UK GeoPlace gazetteer SOAP API).

## Contributing / scaffolds

| Checklist item | Status | Docs location |
|---|---|---|
| Two scaffold states: credentials-wanted vs documented-but-unavailable — distinction preserved | ✅ | `providers/index.md` §"Credentials wanted" (full tables); `contributing/scaffolds.md` (summary + pointer) |
| Help-wanted issue pattern (smoke test + one real trimmed record confirms an adapter) | ✅ | `providers/index.md` §"Credentials wanted"; `contributing/scaffolds.md` |
| Agent boundaries: AI agents must not create government accounts, accept terms of service, or circumvent WAF-hardened private backends | ❌ | Not in README (checked via targeted grep for "WAF"/"terms of service"/"government account"). See reconciliation note. |

## Governance / meta

| Checklist item | Status | Docs location |
|---|---|---|
| MIT licensed | ✅ | `governance/licensing.md` §"SDK licence" |
| Personal-capacity framing — developed independently, not on behalf of Durham County Council | ❌ | Not in README. See reconciliation note. |
| Submitted to UK Strategic Data Roadmap (OCDO/GDS), Data Architecture category; Data Governance flagged as most useful support area given European-feed licensing uncertainty | ❌ | Not in README. The *underlying fact* "European-feed licensing uncertainty is real and recurring" **is** independently true and demonstrated — see `governance/licensing.md`'s closing paragraph, built from the real per-provider licence findings, not from this checklist item. See reconciliation note. |
| Chris Carlon: original concept, minor testing, merged PR (Section 58 support, Street Manager v6 models) | ❌ | Not in README. See reconciliation note. |
| `pip install streetworks`; PyPI since ~June 2026; pre-1.0, "developing and growing" | ⚠️ partial | `pip install streetworks` and pre-1.0/"Early alpha" status **are** in the README, migrated to `getting-started/installation.md`. The specific PyPI-since-June-2026 date and the phrase "developing and growing" are not in the README text. See reconciliation note. |
