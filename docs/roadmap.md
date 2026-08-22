# Roadmap

> Forward-looking **coverage roadmap**, organised by theme strand rather than
> version number — coverage doesn't cleave along release boundaries, so the old
> phase framing was dropped. The authoritative record of what is actually
> **live** is [`docs/providers/index.md`](providers/index.md); this page lists
> direction, live candidates, and open decisions (including declines with their
> reasons). The chronological build log is preserved below under
> [Build log](#build-log).

## Street Gazetteer Feeds

Streets and roadworks are **independent data classes from independent
custodians** — a territory with no roadworks feed can still have a perfectly
good open street gazetteer, and roadworks coverage shifts anyway (a
credential-blocked national could land tomorrow). So this strand is **not**
gated on roadworks; the trigger is an open street source, wherever one exists.

### Investigate and build — European territories with no streets coverage yet
**First candidates** — the SDK already operates in these, so the territory is
familiar (a prioritisation hint only, *not* a gate): Austria, Belgium, Bulgaria,
Denmark, Finland, Greece, Iceland, Lithuania, Luxembourg, Sweden, Switzerland.

**Rest of Europe** — no current SDK presence, investigate from scratch: Croatia,
Cyprus, Czechia, Estonia, Hungary, Latvia, Malta, Poland, Romania, Slovakia,
Slovenia; Albania, Bosnia & Herzegovina, Kosovo, Moldova, Montenegro, North
Macedonia, Serbia, Ukraine; and other European states as they surface.
Microstates (Andorra, Liechtenstein, Monaco, San Marino) typically sit inside a
neighbour's cadastre — fold in with that neighbour rather than as standalone
builds.

### Investigated, partially resolved — real open follow-on exists
- **Germany** — federal level ruled out (BKG's INSPIRE WFS has geometry but no
  real street names — DLM250 is route codes + scenic-route branding, no
  `net:link`). Hamburg / Brandenburg / Saxony / Berlin state-level layers never
  checked.
- **Portugal** — national level ruled out (IP's ArcGIS layer carries route
  codes, not names; national toponymy is 1:200k census places). Santa Maria da
  Feira confirms the open, per-municipality "Eixos de Via e Toponímia" shape
  (CC-BY) — found, not yet built. Porto and other municipalities unchecked.
- **Ireland** — national level ruled out (rural roads are genuinely numbered,
  not named). Monaghan proved the county-level pilot works (built); ~30 more
  county / city councils are the same shape, unbuilt.
- **Isle of Man** — genuinely unresolved, *not* ruled out: a real BS7666
  gazetteer exists but sits behind an academic-only licence; no open endpoint
  found. The last remaining Crown Dependency gazetteer gap.

> Already done — do not re-open: Italy (ANNCSU national register, ~1.22M
> streets), Jersey + Guernsey + Gibraltar gazetteers (Gibraltar is streets-only;
> its roadworks candidate was ruled out), Spain (IDEE Transportes), the
> France / Netherlands / Norway address+street pairs, US TIGERweb, Canada
> National Road Network.

## Adopted Highway Extents (UK-wide, where available)

The spatial **extent** of the adopted / maintainable highway — where the highway
boundary runs to (carriageway + footways + verges), the layer that defines
maintenance responsibility on the ground. Distinct from road **centrelines** (a
line down the middle tells you the road exists, not where the adopted extent
runs) and from the textual **List of Streets** register (the s36 list of
maintainable streets, name / USRN-based, no boundary).

- **England** — per-authority adopted-highway extent / highway-boundary polygons
  where published. Per-LHA (~150), patchy open availability — the lowest
  yield-per-effort strand here.
- **Scotland / Wales / Northern Ireland** — each roads authority holds
  maintainable-highway extent data; investigate where published open. (NI's DfI
  Roads centreline — already built — carries adoption *status* but is a
  centreline, not the extent.)

## New Roadworks Feeds

The **sub-national layer is already substantially built** — and not only cities:
the target is any sub-national permit-holding authority. City-level feeds are
live for Madrid, Paris, Lisbon, Milan, Rome, Copenhagen, Oslo, Helsinki, Vienna
and Berlin; region / canton / Land / community-level feeds for Kanton Zürich, the
German Land cluster (Hamburg / Brandenburg / Saxony / Berlin), Catalonia and the
Basque Country, and Monaghan (county) — plus NYC, Chicago and the Australian
states outside Europe. So most large European authorities now carry *both* a
national/strategic feed and a sub-national one. Stockholm was attempted but is
credential-blocked (whether an open roadworks dataset exists there at all is
unresolved). Forward work is filling regions, finishing partial nationals, and
extending to the next tier of authorities — not adding the layer from scratch.

### Partial-national — fill the remaining regions
- **Belgium** — Flanders live; add Wallonia (SPW) and Brussels (published
  separately, not yet wrapped).
- **Germany** — Autobahn + Hamburg / Brandenburg / Saxony / Berlin live; add the
  remaining states.

### National / strategic gaps
- **France** — Bison Futé (non-concessionary national) live; add the
  concessionary motorway networks (APRR / Vinci / Sanef).

### Credentials wanted — need a tester, not new investigation
The national motorway feeds behind several already-live cities sit here:
Austria (ASFINAG) · Denmark (Vejdirektoratet) · Sweden (Trafikverket) ·
Switzerland (ASTRA) · Stockholm (Trafikkontoret) · Portugal (IMT NAP) ·
South Australia (Traffic SA) · New Zealand (LINZ Roads).

### Sub-national / local-authority feeds — the next tier
Cities usually surface first — they have the GIS teams and open-data portals —
but the target is *any* sub-national permit-holding authority: county, unitary
authority, Land, canton, province, région, autonomous community, wherever one
publishes an open excavation / permit register. Investigate-first; an open
register is still the exception, so expect declines. Candidates: secondary
cities (Barcelona, Munich / Frankfurt / Cologne, Rotterdam / Amsterdam,
Marseille, Naples, Sofia, Vilnius) and non-city authorities in countries without
a national register — remaining German Länder, other Swiss cantons, further
Spanish autonomous communities, Italian regioni / province. (UK authorities are
already covered nationally by Street Manager / SRWR, so they aren't targets
here.)

### New territories / continents to extend
- **Singapore** — not yet investigated (LTA DataMall the likely route).
- **Canada** — National Road Network (streets), Québec (MTQ Travaux routiers),
  7 of 10 provinces plus Yukon (North American 511 platform), and Vancouver
  and Toronto (municipal) are all live. Remaining: Manitoba, Prince Edward
  Island, Northwest Territories, Nunavut (no matching feed found this
  session); Montréal (real datasets, currently broken — see
  [`docs/providers/canada.md`](providers/canada.md)); Atlantic provinces'
  municipal portals unchecked.

## Examples & derived layers *(not coverage)*
- **Roadworks-aware routing example** — OS Open Roads (keyless OGL, strategic
  base network) with live Street Manager works and D-TRO restrictions overlaid,
  demonstrating the dynamic disruption layer a router — or an AV — consumes on
  top of a base map. Open Roads is strategic, not AV-grade (no one-ways, turn
  restrictions, or lane geometry); framed honestly as an illustration of the
  overlay, not an AV base map.

## Build log

> Migrated verbatim from README.md's `## Roadmap` section (phase one,
> lossless restructure — see `docs/migration-mapping.md`). This is a
> chronological build log (`[x]` shipped, `[ ]` not yet built) — most
> `[x]` entries summarise a fuller write-up that lives in
> [`docs/providers/`](providers/index.md) or [`docs/concepts/`](concepts/architecture.md);
> this page is the log itself, not a duplicate of that detail. The two
> "separate strand" roadmap subsections (European & Crown Dependency
> roadworks; International gazetteers) are migrated in full in
> [`docs/providers/europe.md`](providers/europe.md#european--crown-dependency-roadworks--separate-strand)
> rather than repeated here, since they're Europe-specific research notes,
> not part of the main chronological checklist.

- [x] Pydantic model generation pipeline for the Street Manager swagger specs
- [x] Auto-pagination helpers for the Reporting API (`iter_permits()` etc.)
- [x] DataVIA WMS support (`get_map`, `get_feature_info`, `wms_capabilities`)
- [x] D-TRO publish models generated from the DfT JSON schemas, version-namespaced
      — see [docs/DTRO_SCHEMAS.md](DTRO_SCHEMAS.md). **`v4.0.0`, the
      production schema since 2026-06-01, is now generated and shipped
      alongside `v3.5.1`** (production still accepts both). Real, not
      cosmetic: `regulation` moved from a 1-item array to a plain object,
      `condition`/`conditionSet` were restructured, 8 `vehicleType` values
      moved to `vehicleUsageType`, `regulation.timeZone` is now fixed to
      `"Europe/London"` — see DTRO_SCHEMAS.md for the full diff.
      `DTROClient.validate_payload()`'s default is now `v4_0_0` (was
      `v3_5_1`) to match production — pass `version="v3_5_1"` explicitly for
      v3.5.1 payloads, and the raised `ValidationError` names which schema
      version it validated against, since both share the class name `Model`
- [ ] D-TRO `v5.0.0` — in development, not yet built. Presented contents
      include refactored speed-limit regulation modelling, a new attribute
      distinguishing diversion-route geometry styles, additional
      `vehicleType` and `regulationType` values, and new validation rules
      (`pointGeometry` no longer usable for speed limits; `directedLinear`
      mandatory for some `regulationType`s)
- [x] Scottish Road Works Register - Open Data provider (`streetworks.srwr`).
      The authenticated SRWR/Aurora web-services API is restricted to Scottish
      authorities and utilities; contributions from SRWR users welcome.
- [x] **Common models** (`streetworks.common`): canonical cross-provider types
      (`Works`, `WorksSite`, `WorksPlanning`, `Coordinate`, `Notice`) with explicit
      per-provider converters (`from_srwr`, `from_streetmanager`, `from_datex2`,
      `from_wzdx`, `from_trafficwatchni`, `from_trafficwales`), so the same code
      handles works data from any provider — native full-fidelity interfaces
      retained, `.raw` always keeps the source record(s); `Works` also carries
      `territory`/`administrative_area` location provenance so a mixed
      cross-provider list can be filtered by where the data comes from
- [x] OS Open USRN: credential-free GB-wide USRN lookup with geometry (`streetworks.openusrn`)
- [x] Northern Ireland roadworks (TrafficWatchNI RSS) and Wales motorway/trunk
      roadworks (Traffic Wales RSS) — all four UK nations now have coverage
- [x] UK Police crime data (`streetworks.police`) as a worker-safety signal —
      no API exists for roadworker abuse directly, so this is the closest
      honest proxy; `safety_signal()` filters to the categories that bear on
      personal safety — verified against the real API
- [ ] Traffic Wales DATEX II feeds (richer than the RSS; access on application)
- [ ] Scottish street gazetteer (OSG portal open data); Northern Ireland gazetteer
      (Wales street gazetteer is already covered by the Geoplace NSG via DataVIA)
- [x] **DATEX II parser** (v3 + v2 SituationPublication roadworks) with the
      NDW (Netherlands, XML) open-data adapter — verified against the real national feed
- [x] National Highways (England SRN) DATEX II v3.4 **JSON** adapter
      (`streetworks.datex2.nationalhighways`), cursor pagination via `x-next` —
      verified against the real API
- [x] Finland (Digitraffic) DATEX adapter (`streetworks.datex2.digitraffic`)
      — its own JSON schema, not a DATEX-II serialisation, mapped onto the
      same shared models; verified against the real feed, no credentials
- [x] Iceland (IRCA/Vegagerðin) DATEX adapter (`streetworks.datex2.irca`) —
      genuine DATEX II v3 XML over a SOAP `snapshotPull` interface, reused
      through the existing shared parser unchanged; verified against
      multiple independent live fetches, no credentials
- [x] France (Bison Futé/the DIRs) DATEX adapter (`streetworks.datex2.bisonfute`)
      — genuine DATEX II v2 XML for the non-concessionary national network,
      reused through the existing shared parser; verified against the real
      feed (256 situations, 170 roadworks, 100% coordinate coverage), no
      credentials. Surfaced and fixed two real gaps in the shared parser
      itself (`alert_c_location` name preference, TPEG linear from/to
      geometry) - not France-specific bugs, just never exercised before
- [x] Spain (DGT) DATEX adapter (`streetworks.datex2.dgt`) — genuine DATEX
      II v3 (Level C, Spanish-extended profile), reused through the existing
      shared parser; verified against the real feed (656 situations, 391
      roadworks, 100% coordinate coverage), no credentials. Coverage excl.
      Catalonia & the Basque Country. Surfaced and fixed a genuine
      *discriminator* gap, not just a field-mapping one — DGT has zero
      `MaintenanceWorks`/`ConstructionWorks` records at all, so
      `SituationRecord.is_roadworks` gained an additive cause-based check
      (`roadMaintenance`/`roadworks`), plus a `roadName` fallback for the
      road identifier (Spain never states `roadNumber`)
- [x] Belgium (Verkeerscentrum Vlaanderen) and Luxembourg (Ponts et
      Chaussées/CITA) DATEX adapters (`streetworks.datex2.belgium`,
      `streetworks.datex2.luxembourg`) — DATEX II v3 and v2.3 respectively,
      both credential-free, both reused through the existing shared parser.
      Verified against real feeds: Belgium ~100 situations/86 roadworks
      records, Luxembourg ~110 situations/161 roadworks records. Belgium
      surfaced two real, *shared*-code-level findings: a second, differently
      shaped discriminator gap from Spain's (`RoadOrCarriagewayOrLaneManagement`
      + `roadOrCarriagewayOrLaneManagementType=newRoadworksLayout`, additive,
      confirmed not to over-match the 61 real same-xsi:type records with
      genuinely different values), and real coordinates stated in Belgian
      Lambert 72 (`EPSG:31370`), not WGS84 — `from_datex2()` gained a `crs`
      parameter (default `EPSG:4326`) so this is stated explicitly rather
      than assumed, coordinates carried through unconverted per this SDK's
      CRS policy. Belgium's coverage is Flanders only (confirmed via
      `nationalIdentifier="BETICV"`), not all-Belgium — documented like
      France's/Spain's own partial-coverage precedent. Belgium's real
      licence (transportdata.be's own terms) prohibits commercial
      redistribution to third parties, so its test fixture is synthetic
      (real shape, invented values) rather than trimmed from a live pull —
      Luxembourg's is real, under CC0
- [x] Bulgaria (Road Infrastructure Agency/LIMA) DATEX adapter
      (`streetworks.datex2.bulgaria`) — DATEX II v2.3, credential-free,
      reused through the existing shared parser. Verified against the real
      feed: 150 roadworks records (the "Short-term Road Construction"/r03
      dataset, confirmed a strict superset of the other two roadworks
      categories LIMA publishes, "Closed Roads"/r01 and "Closed
      Roadways"/r02 — checked by comparing real record IDs across all
      three, not assumed). The NAP-listed host (`lima.api.bg`) is
      unreachable; the real host is `datasheet.api.bg`, whose file URL is
      date-stamped, so this adapter is a two-step catalogue-then-file
      fetch. Surfaced a third, distinct discriminator type — every real
      record uses the bare `Roadworks` xsi:type directly (not
      `MaintenanceWorks`/`ConstructionWorks`, not a generic-value case like
      Belgium's) — added to `ROADWORKS_TYPES`, confirmed zero drift across
      every other adapter's real fixture data. Also surfaced a genuine
      mislabelled-encoding bug in the source feed itself (XML declares
      `encoding="UTF-16"`; actual bytes are UTF-8), corrected before
      parsing. Real WGS84 coordinates, but three points per location where
      the shared parser captures only the first, same as every other
      point-kind location in this SDK. **Licence unconfirmed** — no
      licence text on the reachable host, and the real terms page sits
      behind the unreachable `lima.api.bg` — so, per the Autobahn
      GmbH/Belgium precedent, its test fixture is synthetic
- [x] Germany (Autobahn GmbH) national motorway adapter (`streetworks.autobahn`)
      — its own JSON REST API, not DATEX; verified against a live fetch of
      all 113 roads (2,873 roadworks, zero failures), no credentials. A
      genuine two-level spine (works/phases) confirmed live, cross-road
      grouping (a junction project can be split across two roads' API
      responses), and a documented free-text date-parsing exception
      (99.7% coverage on the class with no date field at all). **Licence
      unconfirmed** despite checking four independent sources — shipped
      anyway, flagged prominently, not silently assumed open
- [x] Lithuania (Via Lietuva) roadworks adapter (`streetworks.vialietuva`)
      — the open data.gov.lt CSV route (CC BY 4.0), not the agreement-gated
      RTTI NAP (403s without one); own small parser, not DATEX. Verified
      against the real feed: 9,762 real `Remontas` (road repairs) rows,
      100% coordinate coverage. Checked all four of the dataset's tables,
      not just the one modelled — `Kliutis` (obstacles, real road-condition
      hazards) and `Renginys` (events, real car-rally closures) are
      genuinely not roadworks, not forced into `Works`; `KelioAtkarpa`
      (road sections) is gazetteer-shaped reference data, exposed as a
      separate `road_sections()` lookup (confirmed live: every real
      `road_id` joins, 886/886), the same role `dir_regions()`/`provinces()`
      play for Bison Futé/DGT. Real coordinates are Lithuanian LKS-94
      (`EPSG:3346`), not WGS84 — the third non-WGS84 roadworks provider in
      this SDK — **and** the source's own WKT states axis order as
      `(Northing, Easting)`, reversed from the usual WKT convention,
      confirmed from real value ranges, not assumed. Also surfaced a real
      data-quality quirk: 25/9,762 real rows (~0.26%) are unfiltered test
      data, structurally identical to genuine rows otherwise. Real trimmed
      fixtures used throughout (CC BY 4.0 confirmed)
- [x] German state (Bundesland) roadworks (`streetworks.ogc`) — a reusable
      generic OGC WFS/Features/direct-download GeoJSON client plus a
      declarative per-state field-map registry, one shared converter
      reading it (adding a state is a field map, not a new converter).
      Hamburg, Brandenburg and Saxony shipped, verified against real data
      (130 + 487 + 1,531 features, 100% coordinate coverage, 0
      out-of-bounds on the mandatory axis-order check each). Saxony has
      no queryable service at all — WMS + a direct GeoJSON ZIP download
      only — and no WGS84 source anywhere, so it ships in its real CRS
      (EPSG:25833/UTM33N), carried through and labelled explicitly, never
      reprojected, the same policy this SDK already applies to its BNG
      providers. Mecklenburg-Vorpommern and Saxony-Anhalt checked and
      **parked** (both GML-only; Saxony-Anhalt's licence also explicitly
      non-commercial); NRW and Bavaria parked too (network-only geodata /
      no Baustellen layer, not GML/CRS issues). Both Brandenburg's and
      Saxony's `ID` fields showed a real but imperfect grouping signal —
      raised, not acted on; ships 1:1 like every other provider without
      corroborated grouping evidence. Client built gazetteer-ready
      (generic GeoJSON fetch, CRS-aware) but no gazetteer features added
      yet — separate design session pending
- [x] Consell de Mallorca (island roadworks) adapter (`streetworks.ogc.mallorca`,
      `streetworks.common.from_mallorca`) — built from a dedicated recon
      pass (`docs/idemallorca-investigation.md`), which first (wrongly)
      framed this as "genuinely additive to DGT, not a duplicate." A
      later audit (`docs/network-scope-audit.md`) corrected this: DGT's
      own data does reach Mallorca, and overlaps with Consell de Mallorca
      for at least some higher-impact works (same road/km-range/end-date,
      confirmed live) — see
      [Never deduplicate across providers](concepts/data-model.md#never-deduplicate-across-providers).
      Reuses `OGCFeaturesClient` directly, no new client shape. Two real
      findings from the build,
      not just the recon: this GeoServer masks a bad `output_format` as
      HTTP 200 wrapping an XML error rather than an error status (worked
      around at the call site, not in the shared client, plus an explicit
      `FeatureCollection` validation as a second guard); and the two-layer
      icon/tram join (`codi`-keyed) isn't total — 16/17 real incidents in
      one live pull had a matching affected-segment line, one is
      point-only, handled honestly (a real point `Coordinate`, never a
      fabricated line). CRS is real ETRS89/UTM31N (`EPSG:25831`), labelled
      and not reprojected, despite the server offering a genuinely correct
      server-side WGS84 transform. Discriminator (`tipoinc`) is clean;
      `"Altres"` (other) is excluded after checking its one real example
      read as a DGT-imposed restriction, not Consell's own works.
      **Licence unconfirmed** (checked capabilities, geoportal, and legal
      notice — none state terms), so the fixture is synthetic, same
      precedent as Autobahn GmbH/Belgium/Bulgaria. Mallorca only — Menorca
      and Eivissa were checked and don't publish the same way, so this
      isn't the head of a committed Balearic cluster
- [x] **Network-scope audit + `network_scope` registry field**
      (`docs/network-scope-audit.md`) — audited every roadworks provider's
      *real* network reach (not its stated remit) and wired the result
      into `streetworks.registry` as a new `NetworkScope` enum
      (`comprehensive` / `multi_authority_interurban` / `strategic` /
      `motorway` / `regional` / `varies_by_feed` / `not_applicable` /
      `unknown`), shown directly in `providers()`'s own rendering. The
      headline finding corrected an already-shipped claim: DGT (Spain)
      turned out to be a multi-authority interurban aggregator (state +
      ~10 real regional/provincial/insular prefixes, confirmed live), not
      a single national network, and genuinely overlaps with Consell de
      Mallorca for some higher-impact Balearic works — the "genuinely
      additive, not a duplicate" framing shipped with the Mallorca
      adapter was wrong, corrected here rather than quietly, everywhere
      it appeared (the docs, the investigation doc, both modules'
      docstrings, the `compare_active_works.py` example). Also surfaced
      two genuine two-tier providers (TrafficWatchNI: NI-wide strategic
      plus all-roads-in-Belfast; Saxony: state+district+municipal,
      broader than its Hamburg/Brandenburg siblings) — kept in the
      existing free-text `scope_note` rather than growing the enum one
      value per idiosyncrasy, per the audit's own restraint. Established
      a standing principle from this:
      [never deduplicate near-identical works across providers](concepts/data-model.md#never-deduplicate-across-providers) —
      a permit is issued per authority, not per physical worksite, so two
      providers' records for what looks like the same location can both
      be genuinely correct
- [x] Servei Català de Trànsit (Catalonia) roadworks adapter
      (`streetworks.sct`, `streetworks.common.from_sct`) — built from a
      dedicated recon pass (`docs/catalonia-sct-investigation.md`),
      filling the larger of DGT's two documented exclusions. The real
      feed is genuine WFS/GML (a `wfs:FeatureCollection` with real
      `gml:Point` geometry) but flat and simple - one geometry plus a
      dozen scalar fields per record, no nesting - so it gets its own
      small, contained parser (plain `ElementTree`, no new dependency),
      the same shape of choice already made for Autobahn GmbH, and
      **deliberately does not touch or depend on** this SDK's parked
      general INSPIRE-GML-reader decision. Verified against the live
      feed: 165 real current incidents, 136 typed `descripcio_tipus`
      `"Obres"` (roadworks) - checked, not assumed, that the other two
      real values (`"Retenció"`/congestion, `"Cons"`/temporary lane
      measures) genuinely aren't roadworks, including one real edge case
      (a `"Retenció"` record whose free-text `causa` says `"Obres"`,
      deliberately not reclassified - the dedicated type field is trusted
      over the secondary hint). CRS is WGS84, confirmed live, the
      simplest CRS story of any Spanish adapter in this SDK. **No start/
      end validity window exists anywhere in this feed** - a genuinely
      real-time, continuously-refreshed current-state feed, not a works
      schedule, so `date_confidence` is always `unknown` and no
      proposed/actual dates are populated, rather than promoting a
      "last reported" timestamp into a date field it would misrepresent.
      `network_scope` is `multi_authority_interurban`, the same shape as
      DGT's own real data (Generalitat network + all four provincial
      councils' networks + some state roads within Catalan territory).
      Licence is Catalonia's own "Llicència oberta d'ús d'informació" -
      confirmed genuinely open, so the test fixture is real, trimmed from
      a live pull, the cleanest licence of any Spanish source checked
      this session. As a third Spain roadworks provider,
      `get_provider("spain")` now names all three (`dgt`, `mallorca`,
      `sct`) via the territory-ambiguity path. The Basque Country (DGT's
      other exclusion) was investigated alongside this, not built - see
      `docs/catalonia-sct-investigation.md` for a genuinely promising
      finding (a real, live DATEX II feed this SDK's existing shared
      parser already reads with zero code changes)
- [x] Basque Country (Euskadi) DATEX adapter (`streetworks.datex2.euskadi`)
      - fills DGT's other documented exclusion, via the shared `from_datex2`
      converter (no bespoke converter needed). Genuine DATEX II **v1.0**,
      the oldest schema version in this SDK - reading it carefully
      surfaced a real, additive parser fix, not just a config tweak:
      `tpeglinearLocation` (lower-case), not the v2/v3
      `tpegLinearLocation` - confirmed by direct byte search (74/74 real
      linear-location records use the lower-case spelling), which had been
      silently degrading a real 2-point line into a single point via the
      generic fallback. Fixed as a second, fallback lookup, tried after
      the v2/v3 spelling - confirmed via a live before/after regression
      across France, Spain, Belgium, Luxembourg and Bulgaria that nothing
      else changed. Live-verified: 96/119 real situations carry a
      roadworks record (101 records total), coordinate coverage is
      genuinely partial (42/101, ~42%) - the only Spanish/DATEX adapter in
      this SDK below 100%, the rest stating location via Alert-C plus a
      road number and distance only. A real per-record province field
      (`administrativeArea`, all three Basque provinces confirmed,
      genuinely inconsistent casing kept as stated) is exposed via its own
      `provinces()` helper, the same shape as DGT's; a real
      `"Desconocida"` (unknown) placeholder is excluded, not treated as a
      name. `network_scope` is `multi_authority_interurban`, the same
      shape as DGT's and SCT's own real data. **Licence: the publisher
      states "No licence - No contract" - literally, not "unconfirmed,"
      genuinely more restrictive than an unconfirmed licence** (absence of
      a licence grants no permission - it is not "free to use"), so the
      test fixture is synthetic, never real data, and the docs/docstrings
      never say "assumed open." As the fourth Spain roadworks provider,
      `get_provider("spain")` now names all four (`dgt`, `euskadi`,
      `mallorca`, `sct`)
- [x] **Provider registry & discovery** (`streetworks.providers()`/
      `get_provider()`, `streetworks.registry`) — territory/kind/credentials
      browsing and single-provider lookup over every provider above, derived
      capabilities (never a hand-maintained per-provider flag), registered
      keeping heavy imports lazy (importing the registry pulls in zero
      provider client modules). See [`docs/providers/index.md`](providers/index.md)
- [x] France BAN (Base Adresse Nationale) — the first non-UK address
      register (`streetworks.ban`), native only, no canonical gazetteer
      type yet (see
      [International gazetteers](providers/europe.md#international-gazetteers--separate-strand)).
      Verified live: the documented API endpoint had moved and the design
      brief's own claim it 400'd did not reproduce; two of four bulk CSV
      formats named in the brief don't exist as real files; there is no
      `id_ban_toponyme` field, but a street's identity is recoverable by
      stripping the numero from any real address `id` (verified: 6/6 real
      addresses on one street share it); BAN's `banId`/`uid_adresse`
      identifiers were confirmed, live, to be the *same* UUID as each other,
      not just similarly-shaped. Also surfaced BAN's `id_fantoir` column is,
      despite the name, already a post-2023 TOPO-length code — confirmed via
      a live join to DGFiP's TOPO register, FANTOIR's real (and now
      archived) replacement
- [x] Netherlands BAG (Basisregistratie Adressen en Gebouwen) — the third
      address register (`streetworks.bag`), native only, no canonical
      gazetteer type yet. The critical shape check (does a street get its own table?)
      was answered against the full real ~7.8 GB national GeoPackage, not a
      sample: no, `openbareruimte` isn't one of its 5 tables — only
      confirmed as a genuine first-class, separately-versioned BAG object by
      also checking the (investigated, not parsed) full-history XML extract.
      Neither product gives a street geometry of its own. Verified at full
      national scale: ~10.04M addressable objects group cleanly into
      250K+ real street ids by name, zero over-merged. Licence corrected
      live from the Atom feed's own `<rights>` element: CC0 1.0 Universal,
      not the Public Domain Mark the brief named
- [x] Norway Kartverket (Matrikkelen Adresse + SSR stedsnavn) — the fourth
      and last address register before the canonical-model design session
      (`streetworks.kartverket`), native only. Confirmed live: multilingual
      naming lives on the SSR *place*, not the address — a real place
      (Karasjok/Kárášjohka/Kaarasjoki) carries three parallel official
      names (Norwegian/Northern Sámi/Kven), each independently statused,
      while a real address in the same municipality has exactly one name,
      in Sámi, with no parallel Norwegian form anywhere on the record.
      `adressekode` (a street key carried *inside* the address dataset
      itself) verified clean and municipality-scoped at full scale across
      two whole municipalities (Karasjok 1,896/139, Oslo 106,154/2,535),
      zero over-merged. Bulk CSV confirmed real (not GML-only, unlike
      Spain) via a live Atom feed with two documented quirks (a mislabelled
      `type` attribute on every entry; per-entry `rights` that isn't always
      "Kartverket"). The brief's own CRS hint about the SSR API needing
      separate verification from the address API turned out backwards:
      SSR's default output CRS is the *same* EPSG:4258, confirmed live -
      only its query-input flexibility differs. Also resolved a genuine
      documented ambiguity: the "requires an agreement" note some
      catalogues attach to Kartverket refers to a completely different,
      SOAP-based, access-restricted service (`MatrikkelAPI`), not the open
      REST APIs this module wraps
- [x] Split registry `kind="gazetteer"` into `"addresses"` and `"streets"` -
      a real analytical error, not a cosmetic rename: with BAN, BAG and
      Kartverket as the only three examples, "European gazetteers have no
      street geometry" looked true, but it's false - the geometry lives in
      a *street* register, published separately by a different body,
      everywhere this SDK has checked so far except the UK (which unifies
      both under the NSG). `datavia`/`openusrn` reassigned to `streets`;
      `ban`/`bag`/`kartverket` to `addresses`. Kartverket also wraps SSR
      (place names - neither addresses nor streets) - kept under
      `addresses` rather than minting a third category for one member, a
      deliberate judgement call recorded in its own registry entry.
      `providers()` is now a real coverage map: the UK has two `streets`
      providers and zero `addresses` (AddressBase is an OS Premium
      product, not open data - noted as a real gap below, not solved
      here); France/Netherlands/Norway had `addresses` only, zero
      `streets`, until NWB (next) gave the Netherlands the first
      territory with both
- [x] Netherlands NWB (Nationaal Wegenbestand) — the first non-UK
      street-geometry provider (`streetworks.nwb`), native only, the
      `streets` counterpart to `bag`. Confirmed live: a real, stated join
      to BAG exists (`bag_orl`, literally BAG's own
      `openbare_ruimte_identificatie` — same format, same commune-code
      prefix, verified against a real municipality), making the
      Netherlands the first territory in this SDK where an address
      register and a street-geometry register can be joined by a stated
      identifier rather than a name match. That join isn't universal
      (~5% of a real municipality's wegvakken carry no `bag_orl`) and
      name-based grouping alone is measurably less reliable (7 of 385 real
      street-name groups in one municipality span two different `bag_orl`
      values) — `Wegvak.toponyme_id()` returns the id or `None`, never a
      name-based guess. Corrected the design brief's own WFS paging
      warning (an unencoded `+` in `outputFormat`, not a paging bug) but
      found a real one of its own: PDOK's WFS silently ignores
      `CQL_FILTER` entirely (a "filtered" query returned all 280+
      municipalities unfiltered), while Rijkswaterstaat's own WFS filters
      correctly on the identical query — so live queries target
      Rijkswaterstaat directly, bulk download stays on PDOK's Atom feed
      (unaffected, a static file). Licence corrected the same way BAG's
      was: CC0 1.0 Universal, confirmed from the Atom feed's own
      `<rights>` element
- [x] France BD TOPO (IGN) — the third non-UK street-geometry provider
      (`streetworks.bdtopo`), native only, the `streets` counterpart to
      `ban`. Confirmed live: `voie_nommee` (named street) is real and
      gives France a genuine two-level spine — its own stable id
      (`cleabs`), a real link down to `troncon_de_route`
      (`liens_vers_supports`, confirmed to resolve to the matching real
      segment) — the strongest structural input this design strand has
      had. Every segment also carries a real, stated join to BAN
      (`identifiant_voie_ban`, exactly BAN's own compact toponyme-id
      format, plus `id_ban_odonyme`, a street-level BAN UUID BAN's own
      API never exposes directly), verified clean at real commune scale
      on two whole communes, mainland and overseas, zero over-merged
      against BAN's own name field. Real left/right structure confirmed
      too (independent names, BAN ids, even INSEE commune codes per
      side — neither NWB nor the UK's USRN has this). Also worth flagging on
      its own: `id_ban_odonyme` isn't just a cross-reference - it's a
      street-level BAN UUID that BAN's own API/bulk files never expose
      directly, so this SDK can join a French street to its BAN address
      cloud by a real permanent id that isn't obviously reachable from
      either provider alone. **No automated bulk GeoPackage route was
      found** despite substantial live investigation (IGN's download
      portal now redirects to a JS SPA with no static resource list; the
      legacy host no longer resolves; the WFS itself doesn't offer
      GeoPackage output) — a genuine, documented gap: only the WFS is
      built. CRS is also
      route-specific: the WFS is WGS84, confirmed live; the unreachable
      bulk file's documented Lambert-93 is not independently re-confirmed
- [x] Norway NVDB (Nasjonal vegdatabank) — the fourth non-UK
      street-geometry provider (`streetworks.nvdb`), native only, the
      `streets` counterpart to `kartverket`. **Task one, checked first as
      the brief demanded**: no credentials required for reads, confirmed
      both live and in the API's own documentation — the opposite access
      story to Statens vegvesen's own DATEX roadworks feed
      (`streetworks.datex2.vegvesen`, this SDK's one credential-blocked
      provider), from the same agency. Confirmed live: `veglenkesekvens`
      is purely topological, no name of its own; naming lives in a
      separate `Adresse` object type (NVDB type 538) whose `adressekode`
      is confirmed to be the *same* identifier `streetworks.kartverket`
      already models — a real join, not a name match. The genuinely
      important structural finding: one real address can span multiple,
      topologically-unrelated link sequences (confirmed live,
      `adressekode` 1140 "Dalveien" placed on two different sequences) —
      Norway's naming and topological layers are not nested the way
      France's `voie_nommee`/`troncon_de_route` are, a real disagreement
      between two "two-level spines." CRS corrected live: EPSG:5973 (a
      compound 3D CRS, UTM33N + NN2000 height), not the design brief's
      plain EPSG:25833 guess — every real geometry is genuine
      `LINESTRING Z` with real altitude values, matching. Licence
      corrected too: NLOD 1.0, confirmed from the NVDB API's own
      documentation, not Elveg's CC BY 4.0 — same network, different
      publisher, different licence
- [x] Norway (Statens vegvesen) DATEX adapter (`streetworks.datex2.vegvesen`)
      — **Phase 2 confirmed (2026-07-30)**, see
      [Recently confirmed](providers/index.md#recently-confirmed).
      Real coordinates are genuinely mixed CRS within the same feed
      (~76% UTM zone 33N/`EPSG:25833`, ~24% WGS84) — resolved per-record via
      the new `streetworks.common.from_vegvesen` converter and shared
      `streetworks.common._crs.resolve_coordinate_crs` helper, not a single
      `crs=` guess. Genuine DATEX II v3 (`modelBaseVersion="3"`), settling
      the v2-vs-v3.1 version caveat in v3's favour
- [ ] Sweden (Trafikverket) adapter (`streetworks.datex2.trafikverket`) —
      **Phase 1 scaffold built, pending live verification**, grouped with
      Norway under [Credentials wanted](providers/index.md#credentials-wanted).
      Confirmed live: endpoint, `Situation` object name, schema version 1.5.
      Its own bespoke XML-request/JSON-response envelope, not DATEX —
      Trafikverket's real roadworks-identifying `MessageType`/`MessageCode`
      value is unconfirmed, so `iter_roadworks()` honestly returns nothing
      pending a credentialed pull, see module docstring
- [ ] Denmark (Vejdirektoratet) adapter (`streetworks.datex2.vejdirektoratet`)
      — **Phase 1 scaffold built, pending live verification**, grouped with
      Norway/Sweden under [Credentials wanted](providers/index.md#credentials-wanted).
      Genuine DATEX II 3.2, confirmed from Vejdirektoratet's own protocol spec; the
      open metadata catalogue re-verified live (196 datasets, roadworks one
      CC BY 4.0). No public data URL — credentials and the pull URL are both
      issued per-dataset at registration, see module docstring
- [ ] Further DATEX II adapters: Mobilithek (DE), transport.data.gouv.fr (FR)
      — per-NAP verification needed
- [x] **WZDx (US Work Zone Data Exchange)** parser (`streetworks.wzdx`,
      v3.1–v4.2), a generic feed client, and a USDOT registry helper —
      verified against 12 live agency feeds, not one sample
- [x] **CWZ (Connected Work Zone) 1.0** parsing support added to
      `streetworks.wzdx` — unlocked a real, live, keyless feed (PurposeBuilt
      Systems) immediately; Massachusetts DOT/Colorado DOT/Illinois DOT's
      own real CWZ feeds also parse, credential-gated pending a real key
      none were obtained for. See
      [docs/providers/us.md](providers/us.md#wzdx-us-work-zone-data-exchange)
- [x] Washington DC DDOT Construction Permits (`streetworks.arcgis.dc`) —
      this SDK's third US city permit register, and its first over a plain
      ArcGIS REST `MapServer` rather than Socrata. See
      [docs/providers/us.md](providers/us.md#washington-dc-ddot-construction-permits)
- [x] Québec (MTQ Travaux routiers, `streetworks.quebec`) — this SDK's first
      Canadian provincial roadworks provider, built over the existing
      generic `OGCFeaturesClient`. See
      [docs/providers/canada.md](providers/canada.md#québec-mtq-travaux-routiers)
- [x] **North American 511 platform** (`streetworks.na511`) — one commercial
      REST API shape confirmed, live, reused byte-for-byte across 9
      government agencies in two countries: Ontario (keyless, fully
      shipped), Alberta, Saskatchewan, New Brunswick, Newfoundland and
      Labrador, Nova Scotia, Yukon (Canada), plus Nevada and Georgia (USA —
      found independently of the WZDx/CWZ US registry, which has no row for
      either). **Alberta confirmed with a real authenticated key
      (2026-08-22)** — 302 real events round-tripped through the identical
      parsing, surfacing a real correction (the `EventType` enum has six
      values, not three). See
      [docs/providers/canada.md](providers/canada.md#north-american-511-platform-ontario-alberta-saskatchewan-new-brunswick-newfoundland-and-labrador-nova-scotia-yukon)
- [x] Vancouver Road Ahead (`streetworks.vancouver`) — this SDK's first
      Canadian municipal roadworks provider, reusing
      `streetworks.opendatasoft.OpenDataSoftClient` directly, no new fetch
      code needed. See
      [docs/providers/canada.md](providers/canada.md#vancouver-road-ahead)
- [x] Toronto Road Restrictions/Closures (`streetworks.toronto`) — this
      SDK's second Canadian municipal roadworks provider. Surfaced and
      fixed a real, live JSON defect (a stray un-escaped backslash in a
      free-text field) via a dedicated repair step, caught and corrected by
      a dedicated no-op test before shipping. See
      [docs/providers/canada.md](providers/canada.md#toronto-road-restrictionsclosures)
- [x] USA WZDx/CWZ coverage-gap survey — every US state + DC with zero row
      in the WZDx/CWZ registry checked for an alternative feed, the same
      way NYC DOT/Chicago DOT were originally found outside that registry.
      Real leads found for North Dakota (a licence decision needed, not
      more investigation) and South Carolina/Tennessee (both blocked on
      transient state — an empty feed and a dead host, respectively — not
      unwritten code); the rest confirmed genuine dead ends. See
      [docs/providers/pending.md](providers/pending.md)
- [ ] Ordnance Survey NGD / Linked Identifiers?

See [`docs/providers/europe.md`](providers/europe.md#european--crown-dependency-roadworks--separate-strand)
for the "European & Crown Dependency roadworks" and "International
gazetteers" separate-strand notes that follow this checklist in the
original README.

Contributions welcome — see [CONTRIBUTING.md](../CONTRIBUTING.md).
