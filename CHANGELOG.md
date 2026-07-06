# Changelog

## [Unreleased]

### Fixed

- Reporting auto-pagination now recognises the live API's `has_next_page`
  key (snake_case); previously only the camelCase `hasNextPage` implied by
  the swagger reference was checked, so iteration stopped after one page
  against the real service. Both spellings are now accepted.
  Live-verified and reported by Chris Carlon.

### Added

- **Northern Ireland provider: TrafficWatchNI** (`streetworks.trafficwatchni`)
  and **Wales provider: Traffic Wales** (`streetworks.trafficwales`): open,
  credential-free roadworks/incidents RSS feeds (5-minute refresh) with
  best-effort typed extraction and raw text always preserved. Honest
  caveat: traveller-information feeds, not works registers. With these,
  all four UK nations have coverage. Attribution requirements (DfI TICC /
  Traffic Wales) are documented and baked into module docstrings.
- **DATEX II support** (`streetworks.datex2`): streaming, namespace-tolerant
  parser for SituationPublication roadworks (DATEX II v3 and v2) with typed
  situations, records, validity and normalised locations, plus an `NDWClient`
  adapter for the Netherlands' credential-free national open data. Verified
  against the real 172 MB Dutch planned-works feed (14,577 situations parsed
  in ~7 s at ~35 MB memory).
- **Street Manager Section 58 support** (`reporting.section_58s()` and the
  `active_section_58()` derived view, sync + async), the documented
  "derived view" convention, committed v6 generated models, and a swagger
  URL fix in the model generator. Contributed by Chris Carlon (#1).
- **DataVIA WMS support**: `wms_capabilities()`, `get_map()` (rendered NSG
  map images) and `get_feature_info()` ("what's at this pixel?") on both
  sync and async clients. Handles the WMS 1.3.0/1.1.1 dialect differences
  (CRS vs SRS, I/J vs X/Y) and surfaces the classic
  exception-XML-with-HTTP-200 failure as a proper error. WMS layer names
  are unprefixed (unlike the WFS's `ms:` feature types - live-verified);
  the `Layer` enum works for both, and WMS-only aggregate layers such as
  `"Streets"` can be passed as strings.
- `examples/quickstart.py` + `.env.example`: a one-file tour that loads
  credentials from `.env` and retrieves a little real data from every
  configured provider.

## [0.2.0] - 2026-07-05


### Added

- **New provider: OS Open USRN** (`streetworks.openusrn`) - GB-wide USRN
  lookup with street geometry via the OS Downloads API (OpenData, no key).
  Streamed ~300 MB GeoPackage download and a stdlib-only reader (sqlite3 +
  minimal WKB-to-WKT decoding), so no GDAL or geospatial dependencies.
- **New provider: SRWR Open Data** (`streetworks.srwr`) - Scotland's
  national road works register via its credential-free Open Data CSV
  extracts (OGL v3). Streaming parser for the multi-record-type format
  (spec v2.02), typed records for every SRWR record type, Activity
  grouping, latest-occurrence dedup for monthly/yearly archives, coded-
  value lookup, and a download client with the spec-recommended retry
  logic. Verified against real published daily (45k records) and monthly
  (4M records) extracts.
- Auto-pagination for the Street Manager Reporting API: `iter_permits()`,
  `iter_inspections()`, `iter_fixed_penalty_notices()`, `iter_reinstatements()`
  and `iter_alterations()` on both sync and async clients follow the API's
  `offset`/`hasNextPage` contract so callers never page by hand.
- Generated Pydantic models for the D-TRO v3.5.1 data specification
  (`streetworks.dtro.models.v3_5_1`), plus `DTROClient.validate_payload()`
  to check publish payloads locally before submission. Generation pipeline
  in `scripts/generate_dtro_models.py` with the schema stored under
  `specs/dtro/v3_5_1/`.

## 0.1.0 (unreleased)

Initial release.

- `streetworks.streetmanager`: sync + async clients for all nine Street
  Manager APIs (V6/V7, sandbox/production) with automatic auth, token
  refresh, retries and rate-limit handling. Explicit `authenticate()` method
  for fail-fast credential/connectivity checks.
- Connectivity smoke test (`scripts/smoke_test.py`) and skip-guarded
  integration test suite (`pytest -m integration`) for verifying against the
  real test/sandbox systems.
- `streetworks.opendata`: SNS receiver toolkit — parsing, signature
  verification, subscription auto-confirmation, event extraction.
- `streetworks.datavia`: OGC WFS client for Geoplace DataVIA - Basic and
  OAuth2 client-credentials auth, full NSG layer catalogue, composable
  OGC filters (USRN, DWithin, Intersects, BBOX, attribute equality),
  documentation-faithful POST GetFeature bodies, KVP GET, paging iterator,
  and all documented output formats.
- `streetworks.dtro`: DfT Digital Traffic Regulation Orders client -
  OAuth2 client credentials with token caching, integration/production
  environments, publish (body/file/gzip), retrieve, delete, events search,
  signed-URL full CSV export, provisions (create/update/delete, with the
  distinct `App-Id` header), schemas, and search. Token metadata exposed via
  `token_info`. Verified against the official OpenAPI spec and Postman
  collection.
