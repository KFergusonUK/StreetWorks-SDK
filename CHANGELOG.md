# Changelog

## [Unreleased]

### Added

- **France: BAN (Base Adresse Nationale)** (`streetworks.ban`) - the first
  non-UK gazetteer, native only (no canonical gazetteer type, no
  `streetworks.common` converter - deliberate, same as how the works side
  shipped natively across 0.3.0-0.4.0 before `Works`/`WorksSite` existed).
  Wraps both the credential-free geocoding API (`search`/`reverse`) and the
  bulk per-département/national `csv-bal` files (streamed, never loaded
  whole - the national file is ~1.4 GB gzipped). Verified live, not
  assumed: the documented API endpoint (`api-adresse.data.gouv.fr`) is past
  its stated 2026-01-31 sunset, so this client targets its confirmed-live
  replacement, `data.geopf.fr/geocodage`; the design brief's own claim that
  the new endpoint returned HTTP 400 did not reproduce - a plain
  `q=`/`lon=`&`lat=` request succeeds. Of the four bulk CSV format variants
  the brief named, only two (`csv`, `csv-bal`) exist as real downloadable
  files today - `csv-with-ids` and `csv-bal-with-lang` do not.
  **BAN is an address base, not a street register**: there is no
  `id_ban_toponyme` field under any format checked, but a street's identity
  is recoverable - every real address `id` is exactly
  `{street prefix}_{numero}`, and stripping the numero reproduces the same
  prefix for every address on the same street within one commune (verified:
  6/6 real addresses on one real street share it). This SDK exposes that
  as a derived `toponyme_id`, explicitly documented as not a literal BAN
  field. Also confirmed live: the API's `banId` and the bulk `csv-bal`
  format's `uid_adresse` are the *same* permanent UUID for the same real
  address, not just similarly-shaped identifiers; the plain `csv` bulk
  format carries neither, only the compact `id`.
  A user-supplied addendum mid-build corrected the brief's claim that
  street naming belongs to FANTOIR: FANTOIR was replaced by DGFiP's
  **TOPO** register in July 2023 and is now archived. Investigated live in
  response: BAN's plain `csv` format's `id_fantoir` column is, despite its
  name, already populated with post-2023 TOPO-length codes (9 characters,
  never the old 10-character FANTOIR form, across every département
  sampled) - and a real BAN `id_fantoir` value was confirmed, live, to
  join cleanly to DGFiP's TOPO API and return the matching street name.
  TOPO itself has no geometry column at all, so even a perfect join only
  recovers a street's name/history, never a centreline - France
  genuinely splits street *identity* (TOPO, DGFiP) from street *position*
  (BAN, IGN/communes), unlike the UK's unified USRN. TOPO is not wrapped by
  this SDK yet - investigated and documented, not built, per the addendum's
  own scope. Coordinates are WGS84 (`lon`/`lat`) throughout - confirmed
  consistent across the API and both bulk formats, and across mainland
  France and five sampled overseas départements; the bulk files' `x`/`y`
  columns are preserved in `.raw` but not modelled as a coordinate, since
  each overseas département uses its own local projection the file itself
  never states. Licence Ouverte / Open Licence 2.0 (Etalab). Registered in
  `streetworks.registry` as `ban` (`kind="gazetteer"`) - France now has two
  providers, so the `"france"` alias was removed from both `ban` and the
  existing `bisonfute` roadworks provider, and `get_provider("france")`
  now raises `AmbiguousProviderError` naming both, the same as `"germany"`.

- **Provider discovery** (`streetworks.registry`, exposed as
  `streetworks.providers()`/`get_provider()`) - purely additive: no existing
  import path, class, or behaviour changed. Answers "what covers X" and
  "give me Y's client" without needing to already know which technology a
  country publishes over - `providers(territory="Wales")`,
  `providers(kind="gazetteer")`, `providers(credentials=False)`,
  `get_provider("spain")`. One registry entry per provider (22 total as of
  this release, covering every provider package in the SDK - a coverage
  test asserts this stays true), each carrying territory, credentials, licence,
  source grade, and the exact working import line.
  Capabilities (`entry.capabilities()`) are **derived by inspecting the
  real client class**, never a hand-maintained dict - including one level
  into known sub-API objects (Street Manager's `.work`/`.reporting`
  attributes, discovered by reading `__init__`'s own source, not
  hardcoded), which is what lets `streetmanager`'s write/publish and
  planning-artifact capabilities show up correctly despite living on
  nested classes rather than flat methods.
  Ambiguous lookups (`get_provider("germany")` → four providers,
  `"england"` → seven) raise naming every real candidate rather than
  guessing; an unknown territory passed to `providers()` warns and returns
  empty rather than raising or silently returning nothing.
  A genuine performance bug was caught and fixed before shipping, not
  after: the first working version imported `SourceGrade` from
  `streetworks.common.models`, which (via `streetworks.common`'s package
  `__init__`) transitively imported every `from_<provider>` converter and
  therefore every provider's client module, including httpx - pulling in
  24 heavy modules just to import the registry, exactly the cost this
  module's own design was supposed to rule out. Fixed by storing
  `source_grade` as a plain string (a `str` `Enum`'s members compare equal
  to their string values either way) instead of importing the real enum
  type; confirmed live that `import streetworks.registry` and
  `import streetworks` now pull in zero httpx/pydantic modules, and that
  `get_provider()` still imports the target client lazily, only on call.
  Two real, previously-undocumented gaps surfaced while verifying every
  territory/licence claim against actual module docstrings rather than
  copying the design brief on trust: Street Manager and DataVIA never
  state their territory anywhere in code or README prose (England+Wales
  here is inferred by elimination against SRWR/TrafficWatchNI covering the
  other nations separately, not an explicit statement); NDW and
  Digitraffic state no licence anywhere either, and a live check of both
  portals found nothing (`licence_confirmed=False`, the same honest-gap
  convention Autobahn's module already established).

## [0.7.0] - 2026-07-19

### Added

- **Finland: Digitraffic** (`streetworks.datex2.digitraffic`) - the first
  provider of the European DATEX expansion, and the first adapter to prove
  the National-Highways pattern (a source that isn't DATEX-shaped itself
  can still produce the same shared `Situation`/`SituationRecord` models)
  a second time. Verified against the live feed (574-575 real features,
  not assumed): Digitraffic's Simple-JSON is its own schema, not a JSON
  serialisation of DATEX II. Every field mapping decision is documented in
  the module rather than glossed over - `record_type` is a hardcoded
  compromise (Digitraffic has no maintenance/construction discriminator),
  `road_maintenance_type` takes the single most specific work-type entry
  rather than a joined composite, `validity.status` stays `None` always
  (no lifecycle field exists in the feed, checked exhaustively - so
  `date_confidence` honestly comes out `UNKNOWN` throughout), and location
  geometry is documented as area-level (the situation's, shared across
  every phase-derived record - confirmed on a live 3-phase situation with
  three different road numbers under one geometry), not phase-precise -
  `road_number`/`alert_c_location` are the precise per-phase locators.
  `administrative_area` comes from a new `provinces()` helper (province,
  confirmed *not* an ELY-centre - that field doesn't exist in this feed),
  verified safe to reuse one value per situation across all 610 phases in
  the live feed, zero exceptions. Credential-free; no Alert-C location-code
  decoding (only the human-readable name is preserved, same as elsewhere).
- **`SituationRecord`/`Situation` gained a `.raw` field**, for all three
  DATEX sources, matching the `.raw` pattern already used elsewhere in this
  SDK (WZDx's `RoadEvent`, SRWR's `Record`) - a real, pre-existing gap
  surfaced while reviewing Finland's field mapping, not new to Finland.
  Populated for National Highways and Digitraffic (free - their payloads
  are already fully in memory). Left `None` for the streaming XML parser
  (NDW and raw DATEX v2/v3) deliberately, not by oversight: each XML
  element is cleared after yielding to keep the verified ~170 MB feed /
  ~35 MB memory characteristic, and a stored reference would go stale
  under the caller.
- **Iceland: IRCA/Vegagerðin** (`streetworks.datex2.irca`) - genuine DATEX
  II v3 XML (not a bespoke JSON schema like Finland/National Highways),
  reused through the existing shared parser's field-extraction logic.
  Credential-free, confirmed reliably reachable across multiple independent
  live fetches (no API key, no IP allow-listing) - unlike Norway (see
  below), this one ships complete. Verified field-by-field against real
  data: `record_type` is a genuine `xsi:type` discriminator
  (`MaintenanceWorks`, not a hardcoded compromise), location is always
  `PointLocation`/`pointByCoordinates` (checked across every situation on
  two independent fetches - zero `LinearLocation`, zero Alert-C),
  `road_maintenance_type` is a real, low-cardinality (`"roadworks"`) field,
  and `administrative_area` has no genuinely-stated source field anywhere in
  the feed (checked exhaustively - every unique element name across a full
  live fetch), so it's left unset rather than inferred. Licence confirmed to
  permit free reuse, redistribution, and commercial exploitation, with
  mandatory attribution ("Based on information provided by the Icelandic
  Road and Coastal Administration (IRCA)"), baked into the module
  docstring. Shares SOAP request-construction plumbing
  (`streetworks.datex2._snapshotpull`) with the (pending) Norway adapter,
  since both expose the identical `snapshotPull/2020` WSDL interface.
- **`streetworks.datex2.parser` gained `iter_situations_full`/
  `iter_roadworks_full`** - the same field extraction as
  `iter_situations`/`iter_roadworks`, but parsing the whole document into
  memory at once instead of streaming, so `Situation.raw`/
  `SituationRecord.raw` get populated with their source XML `Element`.
  `iter_situations` (streaming, clears elements) exists specifically for
  huge feeds like NDW's ~170 MB dump, where that memory bound is worth
  losing `.raw` for; Iceland's response is ~250 KB, nowhere near that scale,
  so `streetworks.datex2.irca` uses the `_full` variant and gets `.raw`
  fidelity for free. Norway's `VegvesenClient` still uses the streaming
  form pending Phase 2 confirming its real response size.
- **Norway: Statens vegvesen** (`streetworks.datex2.vegvesen`) - **Phase 1
  scaffold, pending live verification.** Built against Statens vegvesen's
  own WSDL/service catalogue (probed live) and a real snapshotPull document
  from Iceland's sibling implementation (used to validate that the shared
  parser handles a real SOAP-wrapped response unchanged, not as a claim
  about Norway's own feed shape). Blocked on credentials for Phase 2 live
  verification - not usable against real Norwegian data yet; see the module
  docstring for the three explicitly open questions.
- **France: Bison Futé/the DIRs** (`streetworks.datex2.bisonfute`) - genuine
  DATEX II **v2** XML for the non-concessionary national road network,
  reused through the existing shared parser (the `_full` variant, like
  Iceland - `.raw` populated). Credential-free, verified against the live
  feed (256 situations, 170 roadworks: 150 `MaintenanceWorks`, 20
  `ConstructionWorks`). Every single roadworks record (170/170) carries
  WGS84 coordinates alongside an Alert-C reference - coordinates taken,
  Alert-C preserved not decoded. `administrative_area` (the DIR region,
  e.g. `"Direction interdépartementale des routes/DIR Sud-Ouest"`) is
  genuinely stated on 170/170 roadworks records but on a different, coarser
  field than the shared model's `source_name` (a fine sub-office); a new
  `dir_regions()` helper reads it from each record's `.raw` XML directly,
  the same shape of solution as Digitraffic's `provinces()`. Published
  under the Licence Ouverte / Open Licence 2.0 (Etalab), confirmed via the
  official data.gouv.fr dataset page. France's real data (TPEG linear
  locations, Alert-C names) is what surfaced two genuine, pre-existing gaps
  in the *shared* DATEX parser - see Fixed, below.
- **`Coordinate` gained a `points` field.** Every converter with real
  multi-vertex line geometry available (WZDx's `LineString`, Street
  Manager's `LineString`, DATEX's `LinearLocation`/TPEG segments) used to
  collapse it to a single point when building the common model - a real,
  confirmed loss (not a documented convention, despite one docstring
  framing it that way), not just a France-specific gap. `value` stays one
  representative point (the first vertex) for every existing point-only
  consumer; `points` now carries the whole line when one genuinely exists
  (`None` for a real point location), with `points[0] == value` always.
  Fixed in `from_wzdx`, `from_streetmanager`, and `from_datex2` together,
  once, rather than per-provider.
- **Spain: DGT** (`streetworks.datex2.dgt`) - the DGT (Dirección General de
  Tráfico) National Access Point's SituationPublication, genuine DATEX II
  v3 (Level C, Spanish-extended profile), credential-free. Reused through
  the existing shared parser unchanged - no bespoke parsing path, same as
  NDW/Iceland/France. Verified against the live feed (2026-07): 656
  situations, 391 roadworks records, 100% coordinate coverage. Coverage is
  national except Catalonia and the Basque Country, which run their own
  regional traffic authorities and publish separately.
  Surfaced and fixed a genuine *discriminator* gap in the shared
  parser/model, not just a field-mapping one - DGT has zero
  `MaintenanceWorks`/`ConstructionWorks` records anywhere in the feed; it
  publishes roadworks as a generic record type
  (`RoadOrCarriagewayOrLaneManagement`, mostly, but also `SpeedManagement`
  and `AbnormalTraffic`) discriminated only by
  `cause/causeType=roadMaintenance` + `roadMaintenanceType=roadworks`.
  `SituationRecord.is_roadworks` now checks that pair additively when the
  xsi:type isn't one of the two dedicated types (confirmed not to change
  any other adapter's real fixture), and `road_maintenance_type` itself
  gained a matching deep-path fallback since Spain nests it under
  `cause/detailedCauseType` rather than as the record's direct child. The
  road identifier is stated as `roadName` (e.g. `"N-400"`), not
  `roadNumber` like NDW/France, so `_parse_location` gained a fallback for
  that too. `administrative_area` comes from a new `provinces()` helper -
  the real per-record province (e.g. `"Toledo"`), genuinely stated on
  391/391 real roadworks records but nested in a Spanish location
  extension, not on the shared model - same shape of solution as France's
  `dir_regions()`. Published under Creative Commons Attribution (CC BY),
  confirmed via the DGT NAP's own CKAN dataset metadata.
- **`streetworks.datex2.parser` gained an optional `provider` keyword** on
  all four public entry points (`iter_situations`/`iter_roadworks` and
  their `_full` variants), threaded through parsing - a public,
  backwards-compatible API addition, independent of any one country.
  Field-mapping fallbacks (the Spain-motivated ones above, and any future
  ones) now log at DEBUG level naming the provider, field, record id and
  the value used, so a future source doing something a third way is
  visible rather than silent. IRCA, Bison Fute and DGT pass their own
  label automatically; NDW's documented usage calls the parser directly,
  so the README example now passes `provider="NDW"` explicitly.
- **Germany: Autobahn GmbH** (`streetworks.autobahn`) - national motorway
  roadworks via Autobahn GmbH's own open JSON REST API, credential-free.
  Not DATEX II and not OGC/WFS, so it has its own small parser rather than
  routing through `streetworks.datex2` - the same shape of choice as WZDx
  for the US. Verified against a live fetch of all 113 real roads (2026-07,
  zero failures): 2,873 roadworks records grouping into 997 works via a
  genuine two-level identifier-prefix spine (599 multi-record groups, 599/599
  agreeing on their overall end date, zero disagreements) - including
  cross-road grouping, since 50/997 real prefixes span more than one road
  (a junction works gets listed under every connecting road's own
  response). Every real record carries `LineString` geometry (2-767
  vertices), kept whole, not collapsed to a point; native axis order is
  genuinely reversed within one record (`coordinate` is lat/long,
  `geometry.coordinates` is GeoJSON lon/lat) and flipped explicitly in
  `from_autobahn`, same as WZDx. Two real road-list traps confirmed live:
  lowercase route suffixes (`A64a`/`A99a`), and `"A60 "` (trailing space) -
  not a formatting quirk on the one real A60, but a genuinely separate,
  always-empty duplicate entry that must not be stripped (stripping it
  would silently refetch the real `"A60"` entry's 20 records under the
  wrong id). Dates are a deliberate, documented exception to "never infer,
  only take what's stated" (in the same register as Digitraffic's
  `validity.status` caveat): no end-date field exists anywhere in the API,
  and no start-date field at all for `SHORT_TERM_ROADWORKS` records
  (0/1,184 real ones carry it) - dates for those come from parsing
  `description[]` free text, five real shapes handled (long-term
  Beginn/Ende, the overall-measure end, and three short-term shapes -
  single-day, overnight/multi-day, and a recurring-weekly pattern
  collapsed to its outer bounding window), reaching 100%
  (`ROADWORKS`)/99.7% (`SHORT_TERM_ROADWORKS`) coverage; `Roadworks.is_start_verified`
  distinguishes a real `startTimestamp` from a text-derived one.
  Timezone is Europe/Berlin via `zoneinfo`, not a fixed offset - DST is
  genuinely observed in the data. **Licence unconfirmed** despite checking
  four independent sources (govdata.de's CKAN catalogue, the MDM portal,
  the community `bundesAPI/autobahn-api` docs, and the official autobahn.de
  app page - none state reuse/redistribution terms) - shipped deliberately
  with this caveat, flagged prominently in the module docstring and
  README rather than silently assumed open; test fixtures are
  structurally-real synthetic data, not committed real records, for the
  same reason.
- **Germany: state roadworks** (`streetworks.ogc`) - a new, reusable
  generic OGC WFS/OGC API Features GeoJSON client (`OGCFeaturesClient`,
  deliberately not roadworks-specific - built gazetteer-ready for future
  work, since German gazetteers are commonly published the same way),
  plus a declarative per-state field-map registry
  (`streetworks.ogc.germany`) that one shared converter
  (`streetworks.common.from_ogc_features`) reads generically - adding a
  state means a new field-map entry, not a new converter. Two states
  shipped, both verified against real data (2026-07): Hamburg (130
  features, `Point` geometry, dates `DD.MM.YYYY`) and Brandenburg (487
  features, `LineString` geometry, dates ISO, 100% coordinate coverage,
  0 out-of-bounds on the mandatory axis-order sanity check both states'
  tests run). Both publish under Datenlizenz Deutschland - Namensnennung -
  Version 2.0 (dl-de/by-2-0), confirmed directly from each WFS's own
  `GetCapabilities` document. Hamburg's access mode (WFS vs. a "direct
  GeoJSON download") was genuinely ambiguous before checking - confirmed
  live the download is a ZIP wrapper around the same WFS, not a separate
  source; the direct `GetFeature` call is canonical. One real field name
  differs from what was documented before checking: Brandenburg's road
  field is `Straßenummner` (double "n", a typo in the source schema
  itself). Mecklenburg-Vorpommern was checked and **parked**: confirmed
  live GML-only (its WFS explicitly rejects `application/geo+json`) and
  its licence is only vaguely stated, two independent reasons. Ships one
  `Works` per feature (1:1, no grouping) - Brandenburg's `ID` field showed
  a real but imperfect (~81-88% agreement, no corroborating field) grouping
  signal, raised rather than acted on unilaterally, consistent with the
  project's record-identity discipline.
- **Germany: Saxony (Sachsen)** added to `streetworks.ogc` - 1,531 real
  closures + 813 diversions, `LineString` geometry, via a direct GeoJSON
  ZIP download (Saxony has no queryable WFS/Features service at all -
  confirmed exhaustively via the GDI-DE catalogue's own metadata, 5 real
  records checked, none link a working WFS despite an operator news item
  once referencing one). Genuinely has no WGS84 source anywhere (checked
  its WMS, its download, and its "planned works" dataset's own ISO
  metadata) - ships in its real CRS, `EPSG:25833` (UTM33N), carried
  through and labelled explicitly on `Coordinate.crs` rather than parked
  or silently reprojected, the same policy this SDK already applies to
  its British National Grid providers (OS Open USRN, DataVIA, Street
  Manager) - `StateFieldMap` gained a `crs` field and
  `OGCFeaturesClient`/`from_ogc_features` are now CRS-aware throughout,
  not hardcoded to EPSG:4326. Dates are mostly `DD.MM.YYYY` but 639 of
  3,062 real date fields (21%) carry a real hour suffix
  (`"16.08.2026  08 Uhr"`) - parsed rather than dropped, preserving a
  genuinely-stated time instead of collapsing to midnight. Saxony's `ID`
  field shows the same shape of grouping signal Brandenburg's does (1,531
  features, only 1,133 distinct values) - raised in the module docstring,
  not acted on, consistent with the existing 1:1 policy.

  Also investigated and **parked**: Saxony-Anhalt (GML-only, confirmed by
  testing `OUTPUTFORMAT=application/json` directly against the real WFS;
  its licence is also explicitly "non-commercial use only," not merely
  unconfirmed), Mecklenburg-Vorpommern (unchanged from before - GML-only,
  vague licence), NRW (publishes road network data, not roadworks - a
  gazetteer concern; actual roadworks route to the gated Mobilithek/DATEX
  path), and Bavaria (BAYSIS has no Baustellen/roadworks layer at all).

### Fixed

- **DATEX `alert_c_location` returned a raw numeric location-table code
  instead of the human-readable name.** The shared XML parser read
  `specificLocation` (e.g. `"17855"`), ignoring the sibling
  `alertCLocationName` (e.g. `"Fos"`) that actually states the name -
  confirmed on France's live feed, 787/787 real Alert-C blocks carry both.
  A linear location can state two points (primary/secondary); if the first
  name found is an empty placeholder, later ones are tried before falling
  back to the raw code - the same "skip empty, take the first real one"
  discipline as the multilingual-comments fix, one level up. Not a
  France-specific bug: it had simply never been exercised by real Alert-C
  data before (Digitraffic has its own, different, already-correct code
  path).
- **DATEX TPEG linear locations only kept one endpoint's coordinates.** A
  segment's `from`/`to` endpoints (each with their own `pointCoordinates`)
  used to collapse to whichever one the parser's generic "first
  `pointCoordinates` found anywhere" search happened to hit first (`to`,
  on France's real feed) - silently dropping the other, genuinely-present
  endpoint. Now captured as a real 2-point line (`from` then `to`).

- **Multilingual DATEX fields could silently return an empty string.** The
  shared XML parser's `_multilingual()` helper took the *first* `<value>`
  in a `values/value[lang]` structure regardless of whether it was empty -
  some real feeds (confirmed on Iceland's IRCA feed) list an empty
  placeholder value (e.g. `lang="en"`) before the real text in another
  language. This silently dropped real comment text (and any other field
  routed through `_multilingual`) on every DATEX provider with this value
  ordering. Now skips empty entries and returns the first non-empty value.
  Verified against NDW, National Highways, and Digitraffic fixtures
  (unaffected - they don't have this ordering) and confirmed it now
  correctly surfaces real text on the Iceland/Norway fixtures.

## [0.6.1] - 2026-07-11

### Added

- **Location provenance on `Works`**: `territory` (country-level - UK
  nations count as countries, plus `"USA"`, `"Netherlands"`, etc.) and
  `administrative_area` (the sub-national body that *owns* the data one
  level down - a UK highway authority, a US state DOT, a Dutch province,
  or a national operator's own name where the operator IS the authority),
  so a consumer can filter a mixed cross-provider `list[Works]` by where
  the data comes from. `administrative_area` is populated only where a
  provider genuinely states it, never inferred from a coordinate, and is
  consistent *within* a territory but not size-comparable *across* them.
  `WorksSite` gained read-only `territory`/`administrative_area`
  properties that delegate to the parent `Works` (single source of truth,
  convenient access from a site alone).
  - `from_srwr` gained an optional `districts` parameter: District (099)
    records are excluded from `Activity` bundles by the reader (they're
    file-section reference data, not activity data), so decoding
    `notifiable_district_id` to a name needs it passed in explicitly;
    without one, the bare district ID is used.
  - `from_datex2` gained explicit `territory`/`administrative_area`
    keyword parameters - it's one shared converter for NDW and National
    Highways precisely because they produce the same model, but
    Netherlands vs England can't be told apart from a `Situation` alone,
    and National Highways' `source_name` is a generic `"roadworks"`
    label, not an authority name.
  - `from_wzdx` gained the same two parameters, `territory` defaulting to
    `"USA"` - WZDx's publishing state lives on the registry entry, not
    the road event, so it can't be derived from events alone either.
  - `from_streetmanager`, `from_trafficwatchni` and `from_trafficwales`
    populate them directly from existing provider data (or a hardcoded
    territory where the feed is nation-wide with nothing sub-national to
    report).

## [0.6.0] - 2026-07-10

### Added

- **US work zones: WZDx** (`streetworks.wzdx`): a parser-first provider for
  the US Work Zone Data Exchange standard - one schema-level GeoJSON parser
  plus a generic client that fetches any agency's feed URL (WZDx is
  published independently by ~40+ agencies, not one central API), and a
  registry helper against the USDOT feed registry. Built and verified
  against 12 live feeds spanning WZDx v3.1-v4.2 (Hawaii, Maryland, Indiana,
  NY/TRANSCOM, Missouri, Louisiana, Kentucky, Washington, Minnesota,
  Delaware, Idaho, Québec), not a single sample - caught real cross-agency
  variation a narrower check would have missed: `core_details` nesting is
  v4-only (v3.1 feeds are flat), the feed-info key isn't cleanly
  version-gated (`feed_info` vs the older `road_event_feed_info`, one v4.2
  feed emits both), geometry varies (LineString/MultiPoint, sometimes both
  in one feed), and two genuinely different cross-reference mechanisms
  exist in the wild (`relationship.parents`/`.children` vs
  `core_details.related_road_events`). Confirmed real placeholder/garbage
  dates at scale (one live feed's "current" records span years 2019-2040).
  Every field read is defensive - nothing raises on a malformed record.
- **Common models**: `streetworks.common.from_wzdx` converter, mapping
  `event_type == "work-zone"` records to `WorksSite` (detour/device/
  restriction events are WZDx's analogue of DATEX measures and stay
  native-only). `source_grade` is `operator`; `date_confidence` prefers
  WZDx's accuracy-enum fields over its boolean verified flags, per the two
  different encodings observed live. Coordinate axis order is verified
  against `from_datex2`'s actual behaviour (not assumed) and explicitly
  flipped from WZDx's native GeoJSON `(lon, lat)` to this SDK's
  `(lat, lon)` convention for `EPSG:4326`, with a dedicated cross-converter
  test asserting the two can't silently drift apart.
- `streetworks._dt`: the fractional-second-tolerant ISO-8601 parser
  (previously local to `streetworks.datex2`) is now shared - WZDx feeds hit
  the exact same problem (`datetime.fromisoformat` only accepts 0/3/6-digit
  fractional seconds on Python < 3.11) with even worse precision (7 digits
  on a Washington State feed) than the case that broke `datex2` on 3.10.

## [0.5.0] - 2026-07-09

### Added

- **Common models** (`streetworks.common`): canonical cross-provider types -
  `Works` (the umbrella: reference, location, promoter/source), `WorksSite`
  (the dated, actionable unit - Street Manager permits, SRWR phases, DATEX
  roadworks records), `WorksPlanning` (planning artifacts - PAAs, Forward
  Plans - kept a distinct type so a record never migrates canonical type as
  its lifecycle status changes), `Coordinate` (value plus an explicit CRS
  label, never silently reprojected) and `Notice`. `SourceGrade` and
  `DateConfidence` let consumers filter by trustworthiness without
  provider-specific knowledge. Converters (`from_srwr`, `from_streetmanager`,
  `from_datex2`, `from_trafficwatchni`, `from_trafficwales`) sit alongside
  each provider's native, full-fidelity interface - every canonical object
  keeps `.raw` pointing back at its source record(s).
  - SRWR: joins Phase (007) to Undertaker-Phase (008) by `phase_number` -
    no such join existed before.
  - Street Manager: groups permits by `work_reference_number`; a PAA and the
    permit that later supersedes it share one reference, confirmed live -
    the PAA becomes `WorksPlanning`, not a site. New
    `reporting.forward_plans()`/`iter_forward_plans()` (sync + async) feed
    Forward Plans in; real sandbox data showed these already carry their
    eventual work reference (the design spec assumed they're free-floating
    until converted), so `Works` gained a `plannings` field.
  - DATEX (NDW + National Highways): one converter serves both adapters,
    since they already share the same `Situation` model. `date_confidence`
    is computed from real `validityStatus` values observed in the National
    Highways fixture (`active`/`suspended` -> verified, `planned` ->
    estimated).
  - TrafficWatchNI / Traffic Wales: thin converters (RSS items have no
    umbrella reference); `date_confidence` is always `unknown`.
- **Traffic Wales parser upgrade** (`streetworks.trafficwales`): rebuilt
  against a live fetch of the real feed rather than a synthetic sample.
  `FeedItem` now carries `coordinate` (WGS84, from `georss:point`),
  `road`/`direction`/`location_from_to`/`work_type`/`restriction` (parsed
  positionally from both ends of the colon-delimited title - segment count
  and order both vary across real items), `severity` (free text - the feed
  mixes closure-type and genuine severity wording), `start`/`end`/
  `last_updated` (from labelled description fields, 4-digit years,
  preferred over the title's 2-digit dates), `operating_window` and
  `source`. Prerequisite for the Traffic Wales common-model converter.

## [0.4.0] - 2026-07-08

### Fixed

- Reporting auto-pagination now recognises the live API's `has_next_page`
  key (snake_case); previously only the camelCase `hasNextPage` implied by
  the swagger reference was checked, so iteration stopped after one page
  against the real service. Both spellings are now accepted.
  Live-verified and reported by Chris Carlon.
- DATEX II timestamp parsing (`streetworks.datex2.parser._dt`) now tolerates
  non-standard fractional-second precision - National Highways' live API
  emits 2-digit fractions (e.g. `"2026-05-18T08:22:29.29Z"`), which
  `datetime.fromisoformat` silently fails to parse on Python < 3.11 (only
  0/3/6-digit fractions are accepted there). Caught by CI running the matrix
  down to 3.10, not by local testing on a newer interpreter.

### Added

- **National Highways provider** (`streetworks.datex2.nationalhighways`):
  a DATEX II v3.4 adapter for England's Strategic Road Network Road and
  Lane Closures service. Unlike NDW, National Highways returns its closures
  as JSON, not XML, so it gets its own parsing path onto the shared
  `Situation`/`SituationRecord` models; handles both single- and
  multi-location records and cursor pagination via the `x-next` header.
  Live-verified, including the undocumented-as-mandatory
  `X-Response-MediaType: application/json` header the real API requires.
- **UK Police provider** (`streetworks.police`): a thin adapter over
  `data.police.uk`'s street-level crime endpoints (no credentials), plus a
  `safety_signal()` helper that aggregates crime near a point into a
  worker-safety signal for lone working / unfamiliar sites, filtered to the
  categories that actually bear on personal risk. Not a street-works
  dataset in its own right - documented caveats for historical-not-live and
  area-level-not-site-level data. Live-verified.
- `examples/quickstart.py` is now resilient: every provider demo runs
  inside a try/except so one unreachable or misconfigured feed no longer
  aborts the rest of the tour, and it now includes National Highways and
  UK Police alongside the existing providers.

## [0.3.0] - 2026-07-06


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
  configured provider (see above for the 0.4.0 resilience update).

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

## 0.1.0 2026-07-04

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
