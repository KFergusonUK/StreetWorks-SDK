# Changelog

## [Unreleased]

### Added — Credentials wanted (scaffolds, unverified)

- **Australia: New South Wales (TfNSW Live Traffic Hazards) roadworks and
  major-events scaffold** (`streetworks.au.nsw`,
  `streetworks.common.from_nsw_livetraffic`) - this SDK's first Australian
  provider, opening a new `streetworks.au` cluster (the same
  per-country-file shape as `streetworks.datex2`/`streetworks.ogc`, since
  Australia has no national statutory works register like the UK's Street
  Manager - each state publishes its own traffic-disruption feed
  instead). A Phase 1 scaffold, grouped with Norway/Sweden/Denmark under
  **Credentials wanted** - not DATEX-family like those three, TfNSW's own
  GeoJSON hazards schema.
  Built from a dedicated investigation brief, then independently
  re-verified this session by reading TfNSW's own 42-page "Live Traffic
  NSW Developer Guide" (v1.9) directly rather than trusting the brief's
  paraphrase, plus a live, credential-free probe of the real endpoint.
  - **One adapter, parameterised over layer - not one per layer.** All
    six of TfNSW's hazard types (plus the differently-shaped
    `regional-lga-*` composites) share one real schema, confirmed from
    the guide's own tables, differing only in `layerName` and endpoint
    filename. `NswLiveTrafficClient.get_features`/`iter_features` are
    the general primitives; `get_roadworks`/`iter_roadworks` and the new
    `get_major_events`/`iter_major_events` are convenience wrappers over
    the two **planned** (works-relevant) layers this module covers - the
    four unplanned layers (incident/fire/flood/alpine) and the
    `regional-lga-*` composites are deliberately out of scope for a works
    SDK. `majorevent` has no real sample seen anywhere (unlike
    `roadwork` - see below), so its methods are flagged more speculative
    in the module docstring.
  - **`id` is unique only within a layer, confirmed from the guide's own
    property table** - a real roadwork `82681` and a real major-event
    `82681` are not guaranteed distinct. Every parsed feature now carries
    `layerName` alongside `id` (`parse_features` copies it down from the
    `FeatureCollection`), and `from_nsw_livetraffic` builds
    `Works.reference` as the composite `f"{layerName}:{id}"`, never the
    bare `id` - regression-tested by converting synthetic same-`id`
    roadwork/major-event features together and asserting distinct
    references.
  - **Confirmed live**: a bare request against
    `api.transport.nsw.gov.au/v1/live/hazards/roadwork-open.json` returns
    a genuine structured `401` from a real API gateway
    (`Layer7-API-Gateway`), not a generic error page - confirming the
    endpoint independent of any documentation's own claims. The CC-BY
    licence was independently re-confirmed via the TfNSW Open Data Hub's
    own catalogue page.
  - **A correction to the source investigation brief**: the brief
    described the roadwork endpoints as `roadwork/open`/`roadwork/closed`/
    `roadwork/all`; reading the guide's own Table 1 directly gives
    different literal filenames - `roadwork-open.json`/
    `roadwork-closed.json`/`roadwork.json`. Both path shapes return an
    identical generic 401 from the gateway, so this couldn't be settled
    by a live probe alone - the guide's own literal text is followed here
    as the more authoritative source, flagged as worth re-checking once
    real credentials are available.
  - **The exact `Authorization` header format is genuinely unconfirmed** -
    searched the full 42-page guide directly for "Authorization"/
    "apikey"/"Bearer": zero matches. Defaults to `apikey <key>` (the
    convention documented for other TfNSW Open Data APIs, not
    independently confirmed for this one), overridable via
    `NswLiveTrafficClient(header_format=...)` with no code change needed -
    the same "don't guess, make it correctable" discipline as Norway's
    Basic-vs-Bearer uncertainty.
  - **Test fixture is one real feature, not synthetic** - transcribed
    verbatim from the Developer Guide's own embedded worked example (id
    `82681`, "Nelligen Bridge replacement project"), CC-BY licensed, read
    directly from the PDF rather than trusted from a secondary summary
    (which, checked against the primary text, had hallucinated an
    `Authorization: Bearer <apikey>` claim the guide never actually
    states - caught and discarded before it could be shipped as fact).
  - **A real, previously-unflagged footgun found in that sample**: the
    real `subCategoryA` field holds the *literal string* `"null"`, not
    the JSON value `null` - `_clean_properties` (the guide's own
    documented "disregard empty/null properties" rule) deliberately does
    not treat the string as empty, only genuine `None`/`""`/whitespace/`[]`.
  - **No gazetteer join key exists anywhere in this feed** - `roads[]` is
    free text only (`mainStreet`/`crossStreet`/`suburb`/`region`/...),
    weaker than NWB's `bag_orl` gap (which at least carries an id) - there
    is nothing to join on at all, documented as a hard gap rather than
    worked around.
  - Coordinates are GeoJSON-native `[lon, lat]` (confirmed from the real
    sample - `[150.14, -35.65]` is genuine coastal NSW), never flipped to
    DATEX's `(lat, lon)` convention. Point geometry is a centroid;
    `encodedPolylines` (Google's Encoded Polyline Algorithm Format,
    decoded via a small new local decoder - no new dependency) grades
    higher when present, though the one real fixture record has none.
  - `start`/`end` map to `proposed_start`/`proposed_end` with `ESTIMATED`
    confidence throughout, never `actual_*` - the guide's own field
    description calls `end` the date a hazard "is **scheduled** to end,"
    true even once a record is closed, since nothing distinguishes a
    confirmed completion time from the last-known schedule.
  - Registered in `streetworks.registry` as `nsw`
    (`kind="roadworks"`, `territories={"Australia"}`,
    `network_scope=NetworkScope.UNKNOWN` - honest default, since it's
    unconfirmed whether the main layer includes council roads or only
    state roads), wired into `scripts/smoke_test.py`
    (`check_nsw_livetraffic` - checks both layers, but a `majorevent`
    failure doesn't fail the whole check given how speculative that layer
    is, skip-guarded on missing credentials) and `.env.example`. Ships
    the same import-time `UserWarning` mechanism as the other three
    Credentials-wanted providers.
  - Drafted (not opened) `help wanted` GitHub issue text in
    `docs/credentials-wanted-issues.md`, alongside the existing three.

- **Australia: Victoria (DTP Planned Disruptions - Road) scaffold**
  (`streetworks.au.vic`, `streetworks.common.from_vic_disruptions`) - the
  second `streetworks.au` cluster member, and the **weakest-confirmed**
  Credentials-wanted provider yet: no real payload has ever been obtained
  anywhere (the OpenAPI spec's own Swagger UI can't preview one due to
  response size, and the linked technical documentation PDF returns
  `PublicAccessNotPermitted` from its blob storage - confirmed live this
  session, not just "not yet fetched"). Built from the real,
  machine-readable OpenAPI 3.0.1 spec - fetched and parsed directly this
  session, not trusted from a summary - plus a live gateway probe.
  - **A separate module from NSW, deliberately not one adapter per
    country.** NSW's "one adapter, parameterised over layer" pattern
    relies on every layer sharing one schema; Victoria publishes two
    independent APIs (planned vs. unplanned disruptions) on different
    version tracks with different schemas, so this module covers planned
    only - unplanned (v3, backed by a different system, the Road
    Incident Database) is out of scope, matching the source
    investigation's own explicit warning not to over-apply the NSW
    precedent here.
  - **A decisive, live-verified correction to the source investigation's
    own bet on a real docs-vs-docs conflict**: the investigation flagged
    that the human-facing dataset page names the auth header `KeyID`
    while the OpenAPI spec's own `securitySchemes` name
    `Ocp-Apim-Subscription-Key`/`subscription-key` (the standard Azure
    APIM names), and bet on the APIM names being right at the real
    gateway. A live probe settles it the other way: the gateway's own
    `WWW-Authenticate` error message reads `"Failed to find key field:
    KeyId"` for every header tried except `KeyID` itself, which instead
    gets `"API Key not authorized: <value>"` - proof the gateway
    recognises the field name and is rejecting the value, not failing to
    find it. The OpenAPI spec is simply wrong about its own gateway here
    - this module sends `KeyID`, not the spec's advertised scheme. The
    same live probe also resolved the investigation's other three
    docs-vs-docs conflicts (rate limit 10/min not 20, token-based
    pagination not page/limit, 10-minute cache not 30), all independently
    confirmed straight from the real spec text.
  - **A correction to this module's own design brief**: the brief
    proposed `administrative_area = localGovernmentArea`. Checked against
    `Works.administrative_area`'s own documented semantics (data
    *ownership*, not geography) - an LGA is where a disruption sits, not
    who owns the data, so `administrative_area` is set to "Department of
    Transport and Planning" instead (the real publishing authority, per
    the spec's own description), with `localGovernmentArea` folded into
    `WorksSite.location_description` alongside the road-name fields
    instead, where it belongs as a geography detail.
  - Real, richer-typed schema than NSW's, confirmed field-by-field from
    the spec's own `components.schemas`: a `duration.recurrences[]` with
    a genuine `daysDuration` integer and `allDay` boolean (versus NSW's
    free-text `periods[]`), a structured `impact` object - though its
    `delay`/`numberLanesImpacted`/`speedLimitOnSite` fields are **all
    typed `string` even where the names look numeric**, carried through
    unconverted rather than coerced to a number that might silently
    misparse a shape never seen live. `source.sourceName`/`sourceId`
    maps to `Works.promoter` - a do-not-deduplicate signal, the same
    multi-source-provenance lesson DGT/Consell de Mallorca's real
    republication case already established.
  - Geometry is a `GeometryCollection` wrapping Point/LineString entries
    (confirmed from the real schema, not NSW's bare-Point shape) -
    parsed preferring the first LineString for `Coordinate.points`, else
    the first Point. Coordinate order presumed GeoJSON `[lon, lat]`, and
    `duration.start`/`end`'s timestamp format presumed ISO-8601 via the
    SDK's existing tolerant parser - both genuinely unconfirmed, the
    parser fails to `None` rather than guess epoch-millis (NSW's format)
    if that assumption is wrong, the safer failure mode since a
    genuine-format date run through the wrong parser produces an
    obviously-implausible result rather than a plausible-looking wrong
    one.
  - Test fixture is **synthetic** (structurally correct per the real
    spec, invented values) - the first Credentials-wanted scaffold in
    this SDK with no real sample basis at all, unlike NSW's transcribed
    real example.
  - Registered in `streetworks.registry` as `vic` (`kind="roadworks"`,
    `territories={"Australia"}`, `network_scope=NetworkScope.UNKNOWN`),
    wired into `scripts/smoke_test.py` (`check_vic_disruptions`,
    skip-guarded on missing credentials) and `.env.example`. Ships the
    same import-time `UserWarning` mechanism as every other
    Credentials-wanted provider.
  - Drafted (not opened) `help wanted` GitHub issue text in
    `docs/credentials-wanted-issues.md`, alongside the existing four.

## [0.8.0] - 2026-07-28

### Changed

- **Breaking: `DTROClient.validate_payload()`'s default `version` changed
  from `"v3_5_1"` to `"v4_0_0"`**, matching DfT's production D-TRO schema
  since 2026-06-01 (see D-TRO `v4.0.0` below). Production still accepts
  v3.5.1 payloads, so this isn't simply a correction - pass
  `version="v3_5_1"` explicitly if that's genuinely what you're validating;
  calling `validate_payload()` with no `version` on a v3.5.1-shaped payload
  (`regulation` as a 1-item array) now fails, the mirror image of the
  previous default's trap against v4.0.0 payloads. The raised
  `pydantic.ValidationError` now also names the schema version directly in
  its message (`"...for v4_0_0 Model"`) - both versions' generated classes
  share the name `Model`, so a bare traceback couldn't otherwise say which
  schema actually rejected a payload.

- **`streetworks.registry`'s `Kind.GAZETTEER` split into `Kind.ADDRESSES` and
  `Kind.STREETS`** - a categorisation fix, not a cosmetic rename: with only
  BAN, BAG and Kartverket as examples of `"gazetteer"`, `providers()`
  supported the false conclusion "European gazetteers have no street
  geometry." They do - it lives in a *street* register, published
  separately by a different body, in every territory checked so far except
  the UK (which uniquely unifies both under the NSG). Reassigned: `datavia`
  and `openusrn` to `kind="streets"`; `ban`, `bag` and `kartverket` to
  `kind="addresses"`. Judgement call recorded, not agonised over: Kartverket
  also wraps SSR (Norway's official place-names register - settlements,
  natural features), which is neither addresses nor streets; kept under
  `addresses` rather than minting a third category for one member, noted in
  its own registry entry and this changelog. `ProviderEntry.capabilities()`
  now reports `"address lookup"`/`"street lookup"` in place of the old
  `"gazetteer/street lookup"`. This is purely additive to behaviour (no
  client, import path, or method signature changed) but **is** a breaking
  change to any code matching on `kind="gazetteer"` directly - there was no
  deprecation path available for an enum value rename, so this ships as a
  clean break, flagged here rather than silently.
  With the split, `providers()` is now a real coverage map, not just a
  filter: the UK has two `streets` providers (`datavia`, `openusrn`) and
  **zero** `addresses` - a genuine gap, not an oversight, since AddressBase
  is an OS Premium product, not open data (noted in the README's roadmap,
  not solved here - it may be the one territory where the address layer is
  genuinely blocked, the inverse of the European picture). France and
  Norway have `addresses` only, zero `streets`, until their own street
  registers are investigated; the Netherlands had the same gap until NWB
  (below) gave it the first territory with both layers.

### Added — Canonical gazetteer model

- **Canonical gazetteer model: `Street`, `Segment`, `Address`**
  (`streetworks.common.gazetteer`) - the gazetteer equivalent of what
  `Works`/`WorksSite` did for roadworks at 0.5.0, designed after the eight
  native street/address adapters (`datavia`, `openusrn`, `bdtopo`, `nvdb`,
  `nwb`, `ban`, `bag`, `kartverket`), from their real shapes, closing the
  international-gazetteers strand's design-session exit condition. Additive
  only - native interfaces unchanged. New converters:
  `from_datavia`/`from_openusrn`/`from_bdtopo`/`from_nvdb`/`from_nwb`/
  `from_ban`/`from_bag`/`from_kartverket`.
  **Three types, not two**: `Segment` is independent of `Street`, not a
  child of it - real data proves street/segment is many-to-many, not
  one-to-many (a real DataVIA ESU, `esuid` `4276210541888`, belongs to two
  distinct designated streets at once - Church Street and Church Street
  Villas, Durham; NVDB's real "Dalveien" address spans two
  topologically-unrelated `veglenkesekvenser`).
  **No synthetic streets**: `from_nwb` emits no `Street` at all - NWB
  states segments with a `bag_orl` reference, but this SDK's only built BAG
  route has no street row to be a `Street`, so Dutch street names arrive
  only via `Address.street_name`, a real gap flagged rather than worked
  around.
  **`Coordinate` gained two additive fields**: every point may now be a
  2-tuple or 3-tuple (Z survives, e.g. NVDB's real `LINESTRING Z` under
  EPSG:5973, never defaulted to 0), and a new `parts` field holds a real
  `MultiLineString`'s other lines (DataVIA's `StreetLines`) - existing
  2-tuple-only converters are unaffected.
  **`WorksSite` gained `street_ref: Identifier | None`** - populated from
  Street Manager's per-permit USRN; investigated and deliberately left
  `None` for SRWR, which states street identity only at the activity
  level (record type `004`) with no phase/site join, so populating it
  would have fabricated a link the source doesn't make.
  **Two design-brief assumptions corrected against real data**: the brief
  expected `Segment.names` to be BD-TOPO-only, but NWB's real `stt_naam`
  (even purely-numbered roads carry one, e.g. a real A79 motorway segment)
  populates it too; and DataVIA's real ESU schema (confirmed via WFS
  `DescribeFeatureType`, live, mid-session) has *no name field at all*,
  closing the brief's own open question about whether a real named
  sub-street ("Anchorage Terrace", part of Church Street, Durham) is
  recoverable from DataVIA at any level - it isn't, structurally, not just
  unpopulated.
  **Native promotions**: `nwb.Wegvak` gained `wvk_begdat` and six real
  house-number-range fields (`hnrstrlnks`/`hnrstrrhts`/`e_hnr_lnks`/
  `e_hnr_rhts`/`l_hnr_lnks`/`l_hnr_rhts`), previously only in `.raw`;
  `nvdb.Veglenke` gained `type_veg`/`type_veg_sosi` (the real `typeVeg`/
  `typeVeg_sosi` road-classification fields), likewise promoted from
  `.raw`.
  **New real fixtures**: two real DataVIA `StreetLines` payloads (Carr
  Street USRN 33909869, Church Street USRN 11713561) and a real
  `ESUStreets` payload, captured live this session with Durham-scoped
  credentials (field shapes are national, confirmed via
  `DescribeFeatureType`; field values are local to Durham) - DataVIA had no
  fixture of any kind before this. A synthetic, clearly-labelled bilingual
  fixture (Durham has no Welsh street names) exercises the `_eng`/`_cym`
  name-pair path.
  See `docs/gazetteer-field-dump.md` for the full field-by-field survey
  this model was built from.

### Added — Gazetteer providers

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

- **Netherlands: BAG (Basisregistratie Adressen en Gebouwen)**
  (`streetworks.bag`) - the third gazetteer, and the last before the
  canonical-model design session (per the design brief's own framing),
  native only. Wraps the credential-free PDOK Locatieserver (`search`/
  `suggest`/`reverse`/`lookup`) and the bulk GeoPackage (`bag-light.gpkg`,
  current status only, no history), whose download URL is discovered from
  an Atom feed every call rather than hardcoded - PDOK republishes monthly
  and the filename can change, the same NDW lesson.
  **THE critical first check - is `openbare ruimte` (street) its own
  object? - was answered against the real, full, 7.8 GB national
  GeoPackage, downloaded in full over this session (~26 minutes), not
  sampled or assumed from documentation**: no, it isn't - `gpkg_contents`
  lists exactly five tables (`woonplaats`, `pand`, `verblijfsobject`,
  `standplaats`, `ligplaats`), all five carrying real geometry, and street
  name/id survive only as `openbare_ruimte_naam`/
  `openbare_ruimte_identificatie` flattened onto every address. Verified
  at full national scale via direct SQL, not sampled: grouping all
  ~10.04M addressable objects (`verblijfsobject`/`standplaats`/`ligplaats`)
  by that id gives 245,893 / 2,980 / 1,546 distinct real street ids
  respectively, zero of which map to more than one distinct street name in
  any table, and zero rows with a null street id anywhere.
  The fuller picture needed checking the *other* real product too: the
  full-history XML extract (investigated via HTTP range requests against
  the real 3.6 GB zip - a nested zip-of-zips, one member per BAG object
  type - without downloading it whole; not parsed, per the brief's own
  scope) confirms `openbare ruimte` genuinely *is* a first-class,
  separately-versioned BAG object there, with its own identity and a real
  `status` lifecycle - but still carries no geometry of its own in either
  product (confirmed: zero of 36 real national `OpenbareRuimte` XML member
  files contain a geometry element, for any of its real `type` values,
  while `Woonplaats`/`Standplaats`/`Ligplaats` all do). So the honest
  answer has three parts, not two: a street is a genuine registered
  object, with a real lifecycle; it never carries geometry, in any
  product; and *which* product you pull from changes whether you can see
  it directly as a row at all - a three-part shape distinct from both the
  UK (street = geometry) and France (street has neither a row nor
  geometry, and only one product exists to check).
  Also confirmed live in the XML extract: a bitemporal `voorkomen`
  versioning model (validity period *and* registration period tracked
  separately) - documented, not parsed, the same "investigate, don't
  build" scope the design brief drew around this product.
  A correction to the design brief: "Gemeente" (municipality) is not part
  of the BAG at all, per Kadaster's own disclaimer in the (explicitly
  unofficial) `GEM-WPL-RELATIE` helper file - `Woonplaats` (settlement) is
  BAG's real administrative concept. Also corrected: the live Atom feed's
  own `<rights>` element names **CC0 1.0 Universal**, not the "Public
  Domain Mark 1.0" the brief named - a different (if similarly permissive)
  legal instrument. A `"weg"` (street) Locatieserver result can carry a
  real `MULTILINESTRING` geometry with `fl=*`, but its `bron` field says
  `"BAG/NWB"` - that line comes from NWB (a separate national roads
  dataset), not BAG itself, so it's kept reachable via `.raw` rather than
  promoted to a field that would misattribute it. Registered in
  `streetworks.registry` as `bag` (`kind="gazetteer"`) - the Netherlands
  now has two providers, so the `"netherlands"` alias was removed from
  both `bag` and the existing `ndw` roadworks provider, matching how
  `"france"` was handled for BAN.

- **Norway: Kartverket (Matrikkelen Adresse + SSR stedsnavn)**
  (`streetworks.kartverket`) - the fourth gazetteer, and the last before
  the canonical-model design session, native only. Wraps the
  credential-free address REST API (`search`/`search_nearby`), the SSR
  place-names REST API (`search_places`/`search_names`/`nearby_places`/
  `object_types`/`languages`), and bulk CSV downloads discovered via an
  Atom feed - genuinely not GML-only, unlike Spain: Kartverket publishes
  CSV, FGDB, GML, PostGIS and SOSI side by side for the same dataset,
  confirmed live via the Geonorge catalogue, so CSV was picked
  deliberately for the same standard-library-only reason every other bulk
  provider in this SDK was.
  **Multilingual naming - the finding the design brief flagged as most
  likely to change the canonical model - lives on the SSR *place*, not the
  address, confirmed live, not assumed**: a real place
  (Karasjok/Kárášjohka/Kaarasjoki, `stedsnummer` 868181) carries three
  parallel official names (Norwegian, Northern Sámi, Kven) in one
  `stedsnavn` array, each independently statused (two `"godkjent og
  prioritert"` - approved and prioritised; the Kven one only `"foreslått
  og prioritert"` - proposed, not yet approved). But a real address in the
  same Sámi-majority municipality ("Čalbmebealskáidi 1") carries exactly
  one `adressenavn`, in Northern Sámi, with no parallel Norwegian name
  anywhere on the record - even though SSR does have a real, dedicated
  `"Adressenavn"` object type (one of 291 real legal types confirmed live),
  that street's own entry there is single-language too. So multilingual
  officialdom turned out to be a property of some SSR places, not a
  systematic property of Norwegian street addressing - `PlaceName.names`
  is modelled as a list for exactly this reason.
  `adressekode` (a street key carried *inside* the address dataset itself
  - between the UK's separate street register and France's separate tax
  register) is real, clean and municipality-scoped: verified at full
  scale, not sampled, via the same over-merge check BAN's `toponyme_id`
  and BAG's `openbare_ruimte_identificatie` both got - two whole real
  municipalities' bulk files (Karasjok, 1,896 addresses/139 codes; Oslo,
  106,154 addresses/2,535 codes), zero codes mapping to more than one
  street name in either. The same live search that surfaced this also
  confirmed the municipality-scoping directly: "Karl Johans gate 1"
  resolves to three different real addresses in three different
  municipalities, each with its own `adressekode`.
  No product checked gives a street geometry of its own - a separate
  Kartverket/Statens vegvesen product, NVDB Vegnett, does hold real
  road-network line geometry, noted but not built, the same treatment
  France's TOPO and the Netherlands' NWB got. That makes three of the four
  European gazetteers built in this SDK with no street centreline of their
  own.
  Two design-brief corrections, both live-verified: SSR's default output
  CRS is the *same* `EPSG:4258` as the address API (the brief suggested
  checking for a difference; only the query's *input* flexibility differs,
  accepting `25833` alongside `4258` via `koordsys`) - and the "requires an
  agreement with Kartverket" note some catalogues attach turned out to
  name a completely different, SOAP-based, access-restricted service
  (`MatrikkelAPI`), not the open REST APIs this module wraps. Also found:
  the bulk Atom feed mislabels every entry's `type` attribute as
  `application/gml+xml` even for real CSV entries (this module reads the
  URL's filename, never the `type`), and per-entry `<rights>` isn't always
  `"Kartverket"` - some municipalities (confirmed: Karasjok) name the real
  local data steward instead.
  Registered in `streetworks.registry` as `kartverket` (`kind="gazetteer"`)
  - Norway now has two providers, so the `"norway"` alias was removed from
  both `kartverket` and the existing `vegvesen` roadworks provider (a
  different Norwegian agency, with the opposite access story - see
  Credentials wanted, below), and `get_provider("norway")` now raises
  `AmbiguousProviderError` naming both, matching `"france"`/`"netherlands"`.

- **Netherlands: NWB (Nationaal Wegenbestand)** (`streetworks.nwb`) - the
  first non-UK street-geometry provider, native only, the `kind="streets"`
  counterpart to `bag`'s `kind="addresses"`. Wraps the credential-free WFS
  (`query`/`count`, real `CQL_FILTER` support) and a two-hop Atom feed
  (bulk GeoPackage discovery + streamed download - unlike every other Atom
  feed in this SDK, NWB's index feed points to a second per-dataset feed,
  which only then lists the real download).
  **A real, stated join to BAG exists, confirmed live**: `bag_orl`
  (carried on every wegvak/road-segment) is literally BAG's own
  `openbare_ruimte_identificatie` - same format, same commune-code prefix,
  verified by matching a real wegvak's `bag_orl` against BAG's own id
  space - making the Netherlands the first territory in this SDK where an
  address register and a street-geometry register can be joined by a
  stated identifier, not a name match. Verified at real municipality
  scale (Harlingen, 1,886 wegvakken), not sampled: grouping by `bag_orl`
  gives 378 clean groups, zero mapping to more than one street name - but
  the join isn't universal (96 of 1,886 real wegvakken, ~5%, carry no
  `bag_orl` at all), and name-based grouping alone is measurably less
  reliable (7 of 385 real (municipality, name) groups span two different
  real `bag_orl` values - e.g. "Sédyk" is one display name covering two
  genuinely different BAG street objects). `Wegvak.toponyme_id()` returns
  `bag_orl` where present and `None` otherwise, never falling back to the
  name, which would silently over-merge in exactly these real cases.
  Corrected the design brief's own WFS paging warning, live: `count`
  paging works fine - the brief's two failed attempts almost certainly
  hit an unencoded `+` in `outputFormat=application/geopackage+sqlite3`,
  which decodes server-side as a literal space (confirmed: that exact
  rejection message reproduces the failure). But a real bug of the same
  shape was found in its place: **PDOK's WFS silently ignores
  `CQL_FILTER` entirely** - a query filtered to one real municipality
  returned wegvakken from 280+ different municipalities, unfiltered, both
  for actual features and for `resultType=hits` counts - while
  Rijkswaterstaat's own WFS filters correctly on the identical query
  (confirmed: exactly the requested municipality, matching the bulk-file
  count exactly). Since filtering is the entire point of a live-query
  route, `NWBClient.query()`/`count()` target Rijkswaterstaat directly;
  the bulk GeoPackage download stays on PDOK's Atom feed, which is
  unaffected (a static file, not a filtered query) and matches this SDK's
  existing convention for other Dutch open data. Also confirmed live:
  geometry is route-dependent (the WFS's GeoJSON reports plain
  `LineString`; the bulk GeoPackage encodes every real wegvak as a
  `MULTILINESTRING` wrapping exactly one line part, a GeoPackage/FME
  export convention, not genuinely multi-part segments - carried through
  unconverted, never silently unwrapped); CRS is EPSG:28992, matching
  BAG; licence is CC0 1.0 Universal, matching BAG too, confirmed from the
  Atom feed's own `<rights>` element rather than a portal page (the same
  correction BAG's own licence needed). Registered in
  `streetworks.registry` as `nwb` (`kind="streets"`) - the Netherlands
  now has three providers (`ndw` roadworks, `bag` addresses, `nwb`
  streets), so `get_provider("netherlands")` raises
  `AmbiguousProviderError` naming all three.

- **France: BD TOPO (IGN)** (`streetworks.bdtopo`) - the third non-UK
  street-geometry provider, native only, the `kind="streets"` counterpart
  to `ban`'s `kind="addresses"`. Wraps the credential-free Géoplateforme
  WFS (`query_troncons`/`query_voies_nommees`/`count_troncons`, real
  `CQL_FILTER` support confirmed live, including for `resultType=hits`
  counts).
  **`voie_nommee` (named street) is real, confirmed live, and gives
  France a genuine two-level spine** - the strongest structural finding
  this design strand has had: every real `voie_nommee` carries its own
  stable `cleabs` and a real `liens_vers_supports` link down to a
  `troncon_de_route` segment, confirmed live end to end (a real
  `voie_nommee`'s link resolved to the expected segment, with matching
  name and BAN fields). Neither NWB nor the UK's USRN has this two-level
  structure.
  **The join to BAN is real, stated, and richer than NWB's `bag_orl`**:
  both `voie_nommee` and every `troncon_de_route` carry
  `identifiant_voie_ban` in exactly BAN's own compact toponyme-id format,
  *and* a second, independent identifier, `id_ban_odonyme` (a street-level
  BAN UUID that BAN's own API/bulk files never expose directly).
  Verified at real commune scale, not sampled, on two whole communes
  (Ambérieu-en-Bugey, mainland; Basse-Terre, Guadeloupe, overseas):
  grouping by `identifiant_voie_ban` and checking against `nom_voie_ban`
  (BAN's own name) gives zero over-merged groups in either. A real, minor
  nuance surfaced along the way: BD TOPO's own crowd-sourced name field
  (`nom_collaboratif`) had one abbreviation variant under the same BAN id
  in Basse-Terre ("R SALVADOR ALLENDE" vs "Rue du Président Salvador
  Allende") - not a genuine identity conflict, and gone entirely once
  checked against `nom_voie_ban` instead, which is why both name fields
  are kept rather than one being treated as noise.
  **Left/right structure is real**, confirmed live: `troncon_de_route`
  carries independent `_gauche`/`_droite` names, BAN ids, and even INSEE
  commune codes (a segment on a commune boundary can genuinely have two
  different communes, one per side) - a real structural difference from
  both NWB and the UK's USRN.
  **No automated bulk GeoPackage download route was found**, a genuine,
  thoroughly-investigated gap, not an oversight: IGN's documented download
  portal (`geoservices.ign.fr/telechargement`) now redirects to
  `cartes.gouv.fr`, a JavaScript single-page app with no discoverable
  static resource list; `data.gouv.fr`'s own BD TOPO dataset lists 149
  resources, none an actual GeoPackage file; the legacy `wxs.ign.fr` host
  no longer resolves; and the WFS itself does not offer GeoPackage as an
  output format (confirmed live via its own `GetCapabilities` - only GML,
  GeoJSON, KML and CSV). Only the WFS is built as an access route. A
  `BDTopoDatabase` GeoPackage reader is still provided, for a file
  obtained manually from `cartes.gouv.fr`, but - flagged plainly, not
  hidden - it was never verified against a real downloaded file, only
  against the WFS's own confirmed-live table/column naming, which IGN
  documents as generated from the same underlying data model.
  CRS is also route-specific here: the WFS declares WGS84 (EPSG:4326) on
  every real response checked, mainland and overseas alike; IGN's
  documentation states the (unreachable) bulk GeoPackage uses RGF93 /
  Lambert-93 (EPSG:2154) instead - plausible and consistent with every
  other IGN product, but not independently re-confirmed here. Real 3D
  coordinates (a genuine altitude third value) are confirmed present on
  `troncon_de_route`. Licence Ouverte / Open Licence ETALAB 2.0, confirmed
  via data.gouv.fr's dataset metadata - the same licence as `ban` and
  `bisonfute`.
  A note on naming, worth stating plainly: this is unrelated to DGFiP's
  **TOPO** register (`ban`'s FANTOIR successor, see above) despite the
  near-identical name - different agency, different product.
  Registered in `streetworks.registry` as `bdtopo` (`kind="streets"`) -
  France now has three providers (`bisonfute` roadworks, `ban` addresses,
  `bdtopo` streets), so `get_provider("france")` raises
  `AmbiguousProviderError` naming all three.

- **Norway: NVDB (Nasjonal vegdatabank)** (`streetworks.nvdb`) - the
  fourth non-UK street-geometry provider, native only, the
  `kind="streets"` counterpart to `kartverket`'s `kind="addresses"`, and
  the last planned provider in the international-gazetteers strand.
  **Task one, checked first, per the design brief's own instruction**: no
  credentials required for reads - confirmed live (only a required
  `X-Client` self-identifying header, not an API key; a bare request
  without it returns HTTP 400) and confirmed in NVDB's own API
  documentation ("Det er ikke nødvendig å registrere en bruker..." - "It
  is not necessary to register a user..."). This is the striking
  asymmetry the brief asked about: Statens vegvesen's own DATEX roadworks
  feed (`streetworks.datex2.vegvesen`) remains one of this SDK's
  credential-blocked, unverified providers (see Credentials wanted,
  below), while NVDB, from the same agency, is wide open.
  **`veglenkesekvens` (road link sequence) is purely topological -
  confirmed live, it carries no name of its own**, only `lengde`,
  `porter` (network junctions) and `veglenker` (its own geometry-bearing
  sub-links with linear-referencing ranges). Naming and addressing live
  in a separate object type (`Adresse`, NVDB type 538), whose
  `adressekode` is confirmed live to be the *same* identifier
  `streetworks.kartverket` already models - a real, stated join to
  Matrikkelen addresses, never a name match.
  **The genuinely important structural finding, confirmed live**: one
  real address (`adressekode` 1140, "Dalveien") is placed on *two
  different, topologically-unrelated* link sequences (384 and 2399262) -
  so Norway's naming layer and topological layer are not nested the way
  France's `voie_nommee`/`troncon_de_route` are (one aggregating its own
  clean set of segments via a direct link field). Two "two-level
  spines," two different organising principles - exactly the disagreement
  this design strand needed. A third identifier system exists too,
  `vegsystemreferanser` (administrative road-numbering, e.g. the real
  `"KV1140 S1D1 m0-65"`), preserved in `.raw`, not modelled as a
  first-class field.
  **CRS corrected live: EPSG:5973, not the design brief's expected
  EPSG:25833** - a compound 3D CRS ("ETRS89-NOR [EUREF89] / UTM zone 33N
  + NN2000 height"), not a plain 2D UTM33 one; every real geometry
  checked is a genuine `LINESTRING Z` with real altitude values, matching
  exactly. **Licence corrected too: NLOD 1.0 (Norsk lisens for offentlige
  data), not Elveg's CC BY 4.0** - confirmed from the NVDB API's own
  documentation (`nvdb-vegdata/apidokumentasjon` on GitHub, the real
  source behind `api.vegdata.no`) rather than assumed from Kartverket's
  Elveg distribution metadata, per the brief's own instruction. Same
  underlying road network, two different publishers, two different
  licences.
  REST is this module's only access route - both endpoints paginate with
  a real cursor and accept a `kommune` filter, confirmed live at real
  scale, so the CSV export service (`nvdb-eksport`) was evaluated and not
  built, per the brief's "don't build two routes for the same job."
  Registered in `streetworks.registry` as `nvdb` (`kind="streets"`) -
  Norway now has three providers (`vegvesen` roadworks, `kartverket`
  addresses, `nvdb` streets), so `get_provider("norway")` raises
  `AmbiguousProviderError` naming all three.

- **USA: TIGERweb** (`streetworks.arcgis.tigerweb`, `kind="streets"`,
  `territories={"USA"}`) - the fifth non-UK street-geometry provider, and
  the first outside Europe, built on the new `ArcGISFeatureClient` (see
  Client infrastructure, below). Layers 0-9 are a real cartographic scale
  pyramid, not distinct road classes - confirmed live by comparing feature
  counts (layers 1/2 both 17,612 nationally, 4/5/6 all 248,106, 7/8 both
  16,150,491 - the same data at different generalisation tiers, a real
  correction to the initial design brief's framing). Produces `Segment`
  only, never a `Street` - checked live, not assumed: no layer anywhere in
  the service aggregates segments under a named-street entity, the same
  shape as the Netherlands. No Address Ranges layer exists over this REST
  service either (checked across all 35 real `TIGERweb/` services) -
  `Segment.address_ranges` stays on its NWB-only footing. MTFCC carried
  undecoded (`S1100`/`S1200`/`S1400`/others observed live e.g. `S1630`), no
  lookup table bundled. Public domain (17 U.S.C. Sec. 105) - real fixtures
  committed.

### Added — Roadworks providers

- **Sweden (Trafikverket) and Denmark (Vejdirektoratet) DATEX-family
  roadworks scaffolds** (`streetworks.datex2.trafikverket`,
  `streetworks.datex2.vejdirektoratet`) - see Credentials wanted, below.

- **Belgium (Verkeerscentrum Vlaanderen) and Luxembourg (Ponts et
  Chaussées/CITA) DATEX adapters** (`streetworks.datex2.belgium`,
  `streetworks.datex2.luxembourg`) - DATEX II v3 and v2.3 respectively,
  both credential-free, reused through the existing shared parser/model.
  Live-verified: Belgium ~100 situations/86 roadworks records, Luxembourg
  ~110 situations/161 roadworks records. Two real findings surfaced by
  Belgium's data changed *shared* code, not just this adapter:
  - A second, differently-shaped discriminator gap from Spain/DGT's:
    67/86 real roadworks-relevant records use the generic
    `RoadOrCarriagewayOrLaneManagement` xsi:type, discriminated only by
    `roadOrCarriagewayOrLaneManagementType=newRoadworksLayout` (a real
    DATEX II v3 standard value). Added to
    `SituationRecord.is_roadworks` additively - confirmed this doesn't
    over-match the 61 real same-xsi:type records with genuinely different
    values (`narrowLanes`, `roadClosed`, `contraflow`,
    `singleAlternateLineTraffic`), which can arise from accidents/events,
    not just works.
  - Real coordinates are stated in **Belgian Lambert 72 (`EPSG:31370`)**,
    not WGS84 - confirmed from the feed's own `srsName` attribute and the
    coordinate values themselves (the source XML still calls the fields
    `<latitude>`/`<longitude>`, which is genuinely misleading taken at
    face value). `streetworks.common.from_datex2()` gained a `crs`
    keyword parameter (default `EPSG:4326`, unchanged behaviour for every
    other DATEX adapter) so this is stated explicitly, never silently
    reprojected, per this SDK's standing CRS policy - the same choice
    already made for Saxony's UTM33N and the UK's British National Grid
    providers.

  Belgium's coverage is **Flanders only**, not all-Belgium - confirmed
  live via `supplierIdentification/nationalIdentifier` (`"BETICV"`,
  Belgium Traffic Information Centre Vlaanderen) and the dataset's own
  name; Wallonia publishes a separate feed, not wrapped here. Belgium's
  real licence (transportdata.be's own terms of use) prohibits
  distributing the data to third parties for commercial purposes, so -
  since this SDK is itself redistributed openly - its test fixture is
  **synthetic** (real confirmed shape, invented values), the same call
  already made for Autobahn GmbH's unconfirmed licence; Luxembourg's
  fixture is real, trimmed from a live pull, under **CC0 1.0 Universal**.
  Both registered in `streetworks.registry` (`kind="roadworks"`) and
  wired into `scripts/smoke_test.py`.

- **Bulgaria (Road Infrastructure Agency/LIMA) DATEX adapter**
  (`streetworks.datex2.bulgaria`) - DATEX II v2.3, credential-free, reused
  through the existing shared parser/model. Live-verified: 150 real
  roadworks records. Two real findings, one adapter-local, one shared:
  - The NAP-listed host (`lima.api.bg`) is unreachable (connection
    refused); the real, working host is `datasheet.api.bg`, which serves
    roadworks at a date-stamped URL rather than a fixed one, so
    `BulgariaClient.get_situations()` is a two-step fetch (resolve today's
    file link from the catalogue page, then fetch it). LIMA's roadworks
    catalogue also splits into three datasets ("Closed Roads"/r01, 14
    records; "Closed Roadways"/r02, 46 records; "Short-term Road
    Construction"/r03, 150 records) - checking real record IDs across all
    three confirmed r03 is a strict superset of the other two, so this
    adapter fetches r03 alone rather than merging and de-duplicating
    three files. The real file's own XML declaration also claims
    `encoding="UTF-16"` while the actual bytes are UTF-8 - a genuine
    mislabelling a strict parser rejects outright; corrected before
    parsing, kept local to this adapter since no other feed in this SDK
    has shown the same issue.
  - A third, distinct discriminator type: every real record uses the bare
    `Roadworks` xsi:type directly - not schema-typical (`Roadworks` is
    normally DATEX II's abstract base, not a concrete `xsi:type`), but
    real, live data, and distinct in shape from both Spain's cause-based
    check and Belgium's generic-value case. Added to
    `streetworks.datex2.models.ROADWORKS_TYPES` - confirmed zero drift via
    a live before/after roadworks-count regression across France, Spain
    and Belgium.

  Real WGS84 coordinates throughout, but every location states three
  points, of which the shared parser captures only the first - same
  behaviour as every other point-kind location in this SDK, documented
  rather than changed. **Licence unconfirmed**: no licence text exists on
  the reachable host, and the real terms page sits behind the unreachable
  `lima.api.bg`, so - per the Autobahn GmbH/Belgium precedent - the test
  fixture is **synthetic** (real confirmed shape, invented values).
  Registered in `streetworks.registry` (`kind="roadworks"`) and wired into
  `scripts/smoke_test.py`.

- **Lithuania (Via Lietuva) roadworks adapter** (`streetworks.vialietuva`,
  `streetworks.common.from_vialietuva`) - the **open data.gov.lt CSV
  route**, not the RTTI NAP NAPCORE lists (that listed NAP is
  agreement-gated and 403s without one); CSV, not DATEX, so it has its own
  small parser, the same shape of choice already made for Autobahn/WZDx.
  Live-verified: 9,762 real `Remontas` (road repairs) rows, 100%
  coordinate coverage.
  - Checked all four of the dataset's tables, not just the one modelled.
    `Kliutis` (obstacles - real road-condition hazards, e.g. "weakened by
    spring thaw") and `Renginys` (events - real car-rally-stage closures)
    are genuinely not roadworks, not forced into `Works` - the same call
    already made for UK Police. `KelioAtkarpa` (road sections) is
    gazetteer-shaped reference data (road number/name/km-range, no
    restriction content); confirmed live every real `road_id` joins to it
    (886/886), exposed as `ViaLietuvaClient.road_sections()`, the same
    auxiliary-lookup role `dir_regions()`/`provinces()` play for Bison
    Futé/DGT.
  - **Real coordinates are Lithuanian LKS-94 (`EPSG:3346`)**, not WGS84 -
    the third non-WGS84 roadworks provider in this SDK, after Belgium's
    Lambert 72. **The source's own WKT axis order is also reversed** -
    `POINT (northing easting)`, not the usual `(easting, northing)`,
    confirmed from real value ranges (first number always in Lithuania's
    real northing band, second always in its real easting band). Carried
    through unconverted, both facts stated explicitly via
    `from_vialietuva`'s `crs` parameter and its own docstring, not
    assumed.
  - A repair's full path (a real `MULTILINESTRING`) is preferred when
    stated (6,984/9,762 real rows, 71.6%); the rest are point-only - 100%
    coordinate coverage either way.
  - Real, honest data-quality finding: 25/9,762 real rows (~0.26%) are
    plainly unfiltered test data (`aprasymas` literally `"test"`/
    `"testuojam;"` or similar), structurally identical to a genuine row
    otherwise.

  Real trimmed fixtures used throughout (CC BY 4.0 confirmed via the
  dataset's own licence field on data.gov.lt). Registered in
  `streetworks.registry` (`kind="roadworks"`) and wired into
  `scripts/smoke_test.py`.

- **Consell de Mallorca (island roadworks) adapter**
  (`streetworks.ogc.mallorca`, `streetworks.common.from_mallorca`) - built
  from a dedicated recon pass (`docs/idemallorca-investigation.md`), then
  live-verified again during the build. Genuinely additive to DGT (Spain),
  not a duplicate: DGT's national DATEX feed doesn't carry Consell-managed
  island roads at all (confirmed live - a DGT query around Alcúdia
  returned only ~5 works island-wide). Reuses `OGCFeaturesClient` directly,
  no new client shape.
  - **A real, masked-failure format gotcha**: this GeoServer rejects the
    client's own `output_format="application/geo+json"` default, but with
    HTTP 200 wrapping an XML error body, not an error status. Every call
    here passes `output_format="application/json"` explicitly at the call
    site (not a change to the shared client's default), plus an explicit
    `FeatureCollection` shape check as a second guard against this exact
    kind of quiet failure.
  - **A two-layer join, verified not total**: `incidencies_icon` (points,
    all real content) and `incidencies_tram` (affected-segment
    `MultiLineString`s - one real record genuinely has 2 parts) are joined
    by a shared `codi`. 16/17 real incidents in one live pull had a
    matching tram; one is point-only, handled honestly (a real
    `Coordinate`, `parts` left `None`, never a fabricated line).
  - Real CRS is ETRS89/UTM31N (`EPSG:25831`), labelled and carried through
    unconverted, despite the server offering a genuinely correct
    server-side WGS84 reprojection - not used, per this SDK's standing CRS
    policy (the same choice already made for Belgium/Lithuania).
  - Discriminator (`tipoinc`) is clean: `"Obres"`/`"Manteniment"` are
    fetched as roadworks; `"Altres"` is excluded after checking its one
    real example read as a DGT-imposed restriction, not Consell's own
    works.
  - `territory="Spain"`, `administrative_area="Consell de Mallorca"` - as
    a second Spain roadworks provider, DGT's `"spain"` alias is removed
    (`get_provider("spain")` now resolves through the territory-ambiguity
    path, same as `"france"`/`"norway"`/`"germany"`).

  **Licence unconfirmed** (checked the WFS capabilities, the IDEmallorca
  geoportal, and the Consell's general legal notice - no explicit reuse
  terms found anywhere), so the test fixture is synthetic, same precedent
  as Autobahn GmbH/Belgium/Bulgaria. **Mallorca only, not a Balearic
  cluster** - Menorca and Eivissa were checked and don't publish the same
  way. Registered in `streetworks.registry` (`kind="roadworks"`) and wired
  into `scripts/smoke_test.py`.

- **Servei Català de Trànsit (Catalonia) roadworks adapter**
  (`streetworks.sct`, `streetworks.common.from_sct`) - built from a
  dedicated recon pass (`docs/catalonia-sct-investigation.md`), filling
  the larger of DGT's two documented exclusions (DGT explicitly omits
  Catalonia and the Basque Country). Live-verified: 165 real current
  incidents, 136 typed `descripcio_tipus` `"Obres"` (roadworks).
  - The real feed (`incidenciesGML.xml`) is genuine WFS/GML - a
    `wfs:FeatureCollection` with real `gml:Point` geometry - but flat and
    simple (one geometry plus a dozen scalar fields per record, no
    nesting), so it gets its own small, contained parser (plain
    `ElementTree`, no new dependency), the same shape of choice already
    made for Autobahn GmbH. **Deliberately does not touch or depend on**
    this SDK's parked general INSPIRE-GML-reader decision.
  - Discriminator (`descripcio_tipus`) is clean: checked, not assumed,
    that the two non-`"Obres"` real values (`"Retenció"`/congestion,
    `"Cons"`/temporary lane measures) genuinely aren't roadworks -
    including one real edge case (a `"Retenció"` record whose free-text
    `causa` says `"Obres"`), deliberately not reclassified, since the
    dedicated type field is trusted over a secondary free-text hint.
  - **No start/end validity window exists anywhere in this feed** - a
    genuinely real-time, continuously-refreshed current-state feed, not
    a works schedule (confirmed via the dataset's own metadata and by
    watching `Last-Modified` change between live pulls). `date_confidence`
    is always `unknown` and no proposed/actual dates are populated -
    the one real timestamp this feed states reads as "when this record
    was last reported," not "when the works start," so it's never
    promoted into a date field it would misrepresent.
  - CRS is WGS84, confirmed live - the simplest CRS story of any Spanish
    adapter in this SDK, no reprojection question at all.
  - `network_scope=multi_authority_interurban`, the same shape as DGT's
    own real data - real road-number prefixes span the Generalitat's own
    network plus all four provincial councils' networks plus some state
    roads within Catalan territory.
  - Licence is Catalonia's own "Llicència oberta d'ús d'informació" -
    confirmed genuinely open (reuse, distribution and derivative works
    permitted worldwide, attribution required), so the test fixture is
    real, trimmed from a live pull - the cleanest licence of any Spanish
    source checked this session.
  - As a third Spain roadworks provider, `get_provider("spain")` now
    names all three (`dgt`, `mallorca`, `sct`) via the territory-
    ambiguity path.
  - **The Basque Country (DGT's other exclusion) was investigated
    alongside this, not built** - a genuinely promising finding: a real,
    live DATEX II v1.0 feed (`infocar.dgt.es/datex2/dt-gv/...`) that this
    SDK's existing shared parser already reads successfully with zero
    code changes (120 situations, 96 with roadworks, a clean
    `MaintenanceWorks`/`ConstructionWorks` discriminator) - flagged for
    its own dedicated future investigation (licence there is genuinely
    unresolved), not folded into this build.

- **Basque Country (Euskadi) roadworks adapter**
  (`streetworks.datex2.euskadi`) - fills the other of DGT's two
  documented exclusions, via the existing shared `from_datex2` converter
  (no bespoke converter needed). Genuine DATEX II **v1.0** - the oldest
  schema version in this SDK. Live-verified: 96/119 real situations carry
  a roadworks record (101 records total). **Also surfaced a real, additive
  shared-parser bug, fixed alongside this adapter - see Fixed, below.**
  - **Coordinate coverage is genuinely partial - the only Spanish/DATEX
    adapter in this SDK below 100%**: of 101 real roadworks records, 36
    have a real 2+-point line, 6 a single point, and 59 state location
    purely via Alert-C plus a road number and distance along it (no
    coordinates at all).
  - A real per-record province field (`administrativeArea`, nested three
    levels deep) is exposed via its own `provinces()` helper, the same
    shape as DGT's own - all three Basque provinces confirmed live,
    genuinely inconsistent casing kept as stated, not normalised; a real
    `"Desconocida"` (unknown) placeholder is excluded, not treated as a
    name.
  - `network_scope=multi_authority_interurban`, the same shape as DGT's
    and SCT's own real data (state roads plus all three Diputación Foral
    networks). CRS is WGS84, confirmed live from real point values.
  - **Licence: the publisher states "No licence - No contract" -
    literally, not "unconfirmed."** Genuinely more restrictive than an
    unconfirmed licence, not less - absence of a licence grants no
    permission, since copyright is automatic and default-restrictive; a
    licence is what *adds* permissions. Never documented as "assumed
    open" anywhere. Calling the public endpoint needs no licence, so the
    client is built freely, but the test fixture is **synthetic** (real
    confirmed shape, invented content) - committing real records here
    would be redistribution, which nothing here permits.
  - As the fourth Spain roadworks provider, `get_provider("spain")` now
    names all four (`dgt`, `euskadi`, `mallorca`, `sct`) via the
    territory-ambiguity path.

- **Jersey RoadWorkx** (`streetworks.arcgis.jersey`, `kind="roadworks"`,
  `territories={"Jersey"}`) - this SDK's first Channel Islands coverage,
  built on the new `ArcGISFeatureClient` (see Client infrastructure,
  below), and the client's proving ground for a real pagination trap: its
  `RoadWorks` layer states `supportsPagination: false`, and it's true in
  an unusually literal way - `resultOffset` returns HTTP 200 with a
  plausible page every time, but it's silently the *same* first page
  regardless of offset (confirmed at offsets 0/500/1000/2000/21000); the
  real total is 22,105 records behind a `maxRecordCount` of 1,000, so a
  naive query silently returns under 5% of the data with no error.
  Live-verified this session to retrieve all 22,105 real Jersey records
  with zero duplicates via `ArcGISFeatureClient`'s object-id-range
  fallback.
  Real `RoadWorks` features group by `PROJID` into one `Works` per
  project (confirmed the same real shape as Street Manager's
  `work_reference_number`/`permit_reference_number`); the real `STATUS`
  field (`"In Progress"`/`"Finished"`/`"Pending"`) *is* the planned/future
  dimension, no separate layer needed. CRS confirmed live to be EPSG:3109
  ("ETRS89 / Jersey Transverse Mercator") via a sibling service on the same
  deployment stating the `wkid` directly, cross-checked byte-for-byte
  against EPSG:3109's own published WKT - `outSR` is not honoured by this
  service (also confirmed live). **No explicit licence document found** (no
  `copyrightText` anywhere, not catalogued on Jersey's own open-data
  portal, and the public-facing site gates behind a login the REST API
  itself doesn't need) - but the data is confirmed intended for open
  public consumption, so real, live-captured records are committed as test
  fixtures, the same basis Autobahn GmbH's roadworks shipped on.

### Added — Registry & discovery

- **Network-scope audit + `network_scope` registry field**
  (`docs/network-scope-audit.md`) - audited every roadworks provider for
  what tier of the road network its *real* data actually reaches, not its
  stated remit, and wired the result into `streetworks.registry`: a new
  `NetworkScope` enum (`comprehensive` / `multi_authority_interurban` /
  `strategic` / `motorway` / `regional` / `varies_by_feed` /
  `not_applicable` / `unknown`) and a `network_scope` field on every
  `ProviderEntry`, surfaced directly in `providers()`'s own rendering -
  additive, no client behaviour changes.
  - **Corrects an already-shipped claim, stated plainly rather than
    quietly edited.** The Consell de Mallorca adapter above shipped
    describing DGT and Consell de Mallorca as "genuinely additive, not a
    duplicate." A live check found this wrong: DGT's own real data
    reaches Mallorca (`Ma-`/`Me-` prefixed records, confirmed via real
    road-number prefixes, not assumed from DGT's "national" description),
    and 2 of DGT's Balearic records were checked directly against Consell
    de Mallorca's own feed and matched almost exactly on road, km-range
    and end-date - republication of the same real works, not two
    authorities' records for adjacent land (no independent reference
    field exists on DGT's side to attribute it otherwise, and the matched
    geometry sits within, not beside, the same work-zone span). Corrected
    everywhere the original claim appeared: this changelog's own history
    is left as-is (a record of what was believed at the time), but the
    README, `docs/idemallorca-investigation.md`, both modules' own
    docstrings, and `examples/compare_active_works.py` are all updated.
  - DGT itself turned out broader than "national roads" implies: real
    road-number prefixes reach ~10 regional/provincial/insular
    authorities too (`CV-`/Comunidad Valenciana, `M-`/Madrid, and the
    Balearic ones above), never municipal streets - reclassified
    `multi_authority_interurban`, a new enum value the original 5-value
    proposal didn't anticipate.
  - Two providers turned out genuinely two-tier depending on which part
    of their own feed is queried - TrafficWatchNI (NI-wide strategic,
    all-roads within Belfast) and Saxony (broader than its Hamburg/
    Brandenburg siblings, aggregating district and municipal roadworks
    alongside state roads). Kept in the existing free-text `scope_note`
    rather than growing the enum per-provider, per the audit's own
    restraint.
  - New standing principle, added to the README:
    [never deduplicate near-identical works across providers](#never-deduplicate-across-providers) -
    a permit is issued per authority, not per physical worksite, so two
    providers' records for what looks like the same location can both be
    genuinely correct; the same lesson `examples/collaboration_finder.py`
    already applies one level down (never merging a Street Manager permit
    with its own amendment), one level up.
  - `tests/test_registry.py` extended: every `kind="roadworks"` entry must
    set `network_scope` explicitly (never the bare `None` default, which
    now means "this concept doesn't apply" - reserved for non-roadworks
    kinds), the same "can't ship without it" discipline the registry's
    own package-coverage test already applies.

- **Provider discovery** (`streetworks.registry`, exposed as
  `streetworks.providers()`/`get_provider()`) - purely additive: no existing
  import path, class, or behaviour changed. Answers "what covers X" and
  "give me Y's client" without needing to already know which technology a
  country publishes over - `providers(territory="Wales")`,
  `providers(kind="gazetteer")`, `providers(credentials=False)`,
  `get_provider("spain")`. One registry entry per provider, each carrying
  territory, credentials, licence, source grade, and the exact working
  import line.
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

### Added — Client infrastructure

- **`streetworks.arcgis` - a generic ArcGIS REST (MapServer/FeatureServer)
  client**, the third client shape in this SDK after the DATEX/JSON
  adapters and `OGCFeaturesClient`. Built fresh, not a generalisation of
  `OGCFeaturesClient`/`DataViaClient` - they share almost nothing but
  "fetches geodata over HTTP." Verified against two genuinely different
  real consumers - Jersey RoadWorkx and TIGERweb (see Roadworks providers
  and Gazetteer providers, above).
  **The real pagination trap this client exists to handle**: some ArcGIS
  services report `supportsPagination` metadata that doesn't match their
  real behaviour (Jersey's `RoadWorks` layer claims `false`, and
  `resultOffset` silently returns the same first page at every offset,
  confirmed live at 0/500/1000/2000/21000 - a naive query would return
  under 5% of the data with no error). `ArcGISFeatureClient.iter_features`
  verifies live rather than trusting either metadata claim, falling back
  to object-id-range paging the moment offset-paging fails to advance
  (confirmed live to work for Jersey; TIGERweb's own layers state, and
  genuinely honour, real offset pagination), and raises the new
  `TruncatedResultError` if neither strategy is usable - never silently
  returns a partial result.
  New exception: `streetworks.exceptions.TruncatedResultError`.

### Added — UK Police: worker-safety context

- **`streetworks.police` bulk CSV download**:
  `PoliceClient.bulk_download_csv(forces, *, date_from, date_to, ...)` drives
  data.police.uk's custom CSV download (https://data.police.uk/data/) - a
  CSRF-protected HTML form plus an async job, not a JSON endpoint like every
  other method on this client, but fully scriptable with a plain cookie jar
  and no browser. Verified live end-to-end for 1-, 3-, and 12-month
  single-force requests (all ready within seconds; 12 months of Durham is a
  3.5MB zip). Adds a small local retry (fresh CSRF token each attempt) for a
  transient 403 observed live under repeated use - not one of the shared
  transport's retryable statuses, since 403 correctly means "no" everywhere
  else in this SDK. Returns every row keyed by the CSV's own real column
  names; the CSV's `Crime type` ("Violence and sexual offences") maps to the
  JSON API's slug (`violent-crime`) via `crime_categories()`'s existing
  `name`/`url` pairs, confirmed live to match exactly - no separate mapping
  file needed, despite there being a published one
  (`police-uk-category-mappings.csv`) that maps something else entirely.
  Also documents a real, live-verified caveat: a per-force export can carry
  a small amount of geographic cross-force contamination (~0.4% of rows for
  one real Durham check) that `Falls within` cannot be used to filter
  (confirmed live: every row, including the contaminating ones, carries
  that force's own name in that column).
  **New example**: `examples/crime_context_lsoa/` - LSOA-level (not
  neighbourhood-team-level) crime context keyed to a specific worksite
  (point + radius, live-tested; or a USRN against an already-downloaded OS
  Open USRN GeoPackage, implemented but not live-tested end-to-end - see its
  own README), with a real 2021 Census population denominator instead of
  area. Population and boundary geometry both come from one ONS ArcGIS
  FeatureServer query (via the existing `streetworks.arcgis.ArcGISFeatureClient`),
  which structurally removes the 2011/2021 LSOA-vintage-mixing risk at the
  source rather than just checking for it downstream. Defaults to a 12-month
  window (versus the neighbourhood example's 3) now that ingestion is a
  single bulk download rather than hundreds of live polygon queries -
  shrinkage, quintile/tercile/refuse-to-band tiers, and suppression for
  too-few-crimes areas all carry over from the neighbourhood example's
  design. Live-verified against Durham Constabulary, worksite centred on
  Newton Aycliffe town centre. See its own README for the full method,
  the architectural split (police ingestion in `streetworks.police`; ONS
  population/boundary and worksite geometry kept example-local, not
  promoted into the library), and what it deliberately does not attempt.

- **`streetworks.police` neighbourhood support**: `PoliceClient.neighbourhoods(force)`,
  `.neighbourhood(force, id)`, and `.neighbourhood_boundary(force, id)`
  (`GET /{force}/neighbourhoods`, `/{force}/{id}`, `/{force}/{id}/boundary`).
  Verified live, not from the docs: boundary coordinates are stated as
  **strings** (coerced to `float` here); a boundary is always a single,
  closed ring - no multipolygon, no holes; and real rings aren't guaranteed
  simple (a real ring, Leicestershire's `NC04`, has near-duplicate
  consecutive vertices and at least one spike) - returned exactly as
  received, never silently repaired. `neighbourhood_boundary()` returns
  `(lat, lng)` pairs in the same order `street_level_crimes_in_area`
  already expects.
  **`street_level_crimes_in_area` now survives large polygons** (a real
  neighbourhood boundary can be hundreds of vertices - Leicestershire's
  `NA41` is 2,972 points, confirmed live) - public signature unchanged.
  Coordinates are written to 5 decimal places (~1m, far finer than the
  source data's own anonymisation), and the request switches from `GET` to
  a form-encoded `POST` automatically once the query would exceed a safe
  URL length - live-verified against a real 2,972-point boundary (`GET` for
  the small boundary fetch, `POST` for the resulting crimes query). A `503`
  (the API's real response when a polygon is too complex, even over `POST`)
  now raises `streetworks.exceptions.ServerError` naming the problem
  instead of the shared transport's generic message - silently returning
  `[]` here would make an unqueried area look crime-free. A response at
  exactly the API's 10,000-result cap now emits a `UserWarning`, since that
  count may be a truncation, not the true total.
  **New example**: `examples/crime_context/` - a neighbourhood-banded
  recorded-crime context map for a whole force (rolling 3-month window,
  ending at the most recent month `street_level_availability()` itself
  reports data for rather than a fixed guess back from today, rates
  shrunk toward the force mean and banded into quintiles - falling back to
  terciles, or refusing to band at all below a minimum area count - *within*
  the force only, a sequential single-hue ramp rather than red/amber/green,
  and a method/limitations panel embedded in the page itself rather than a
  footnote) - built entirely on the two additions above plus the existing
  `SAFETY_RELEVANT_CATEGORIES`. Live-verified against Durham Constabulary's
  71 real neighbourhoods. See its own README for the full method and what it
  deliberately does not attempt (no per-street scoring, no cross-force
  comparison, not a risk assessment).
  **Also corrected**: the README's "sync and async clients" claim was
  inaccurate for several modules, not just this one - checked directly
  against the source rather than assumed. `streetworks.police` has no
  `AsyncPoliceClient` (nor do `bag`, DATEX II, `autobahn`, `ogc`, `wzdx`,
  `trafficwatchni`, `trafficwales`, or the ArcGIS-based providers) - the
  README now names which modules do and don't, rather than claiming async
  everywhere.

### Added — D-TRO v4.0.0

- **D-TRO `v4.0.0` publish models** (`streetworks.dtro.models.v4_0_0`),
  generated from DfT's real schema with the existing
  `scripts/generate_dtro_models.py` tooling - additive, `v3.5.1` models
  untouched. v4.0.0 became the production schema on 2026-06-01 (confirmed
  directly from the DfT repo's own release announcements); production
  continues to accept v3.5.0/v3.5.1 payloads too, so this is additive
  coverage, not a cut-over.
  **A real, non-cosmetic payload-shape migration**, not a drop-in schema
  swap - see `docs/DTRO_SCHEMAS.md` for the full diff, verified against
  both DfT's own written release notes and the two schemas' real `$defs`
  directly: `regulation` moved from a 1-item array to a plain object;
  `condition`/`conditions`/`conditionSet` were restructured (`conditionSet`
  is now a single object, not an array; `condition` gained its own nested
  `conditionSet` property; a new `permitCondition` type exists with no
  v3.5.1 equivalent - found in the schema diff, not mentioned by name in
  DfT's own notes); `regulation.timeZone` is now fixed
  (`"const": "Europe/London"`); 8 real `vehicleType` values
  (`policeVehicle`, `schoolBus`, and 6 others) moved to `vehicleUsageType`;
  `sourceActionType` gained `"fullRevoke"`. Tests validate a real DfT
  v4.0.0 example payload and exercise three of these changes directly
  (`tests/test_dtro_models_v4_0_0.py`).
  **`DTROClient.validate_payload()`'s default is now `v4_0_0`** (was
  `v3_5_1`) - see the Changed section above for this as its own flagged
  behaviour change. Its "no models for this version" error message now
  lists both shipped versions, and a raised `ValidationError` now names
  which schema version it validated against, since both versions' generated
  classes share the name `Model`.
  Checked and found unchanged: client endpoints, headers, auth, payload
  limits. Two real v4.0.0-era changes are **not** schema concerns and are
  reported, not built here: a new polygon-based spatial search capability
  on `POST /search` (Integration only as of the DfT announcement checked),
  and new service-generated response metadata (creation/update/up-version
  timestamps) that isn't part of the publish schema this SDK validates
  against.
  D-TRO `v5.0.0` (in development, not yet built) was checked against this
  namespacing pattern: it scales cleanly (purely parametrised on the
  version string) except for that one hardcoded error-message string,
  which needs a one-line update whenever a version is added - noted in
  DTRO_SCHEMAS.md so it isn't forgotten next time.

### Added — Credentials wanted (scaffolds, unverified)

- **Sweden (Trafikverket) and Denmark (Vejdirektoratet) DATEX-family
  roadworks scaffolds** (`streetworks.datex2.trafikverket`,
  `streetworks.datex2.vejdirektoratet`) - Phase 1 scaffolds, **not verified
  builds**, grouped with Norway (`vegvesen`, shipped 0.7.0) under a new
  **"Credentials wanted"** README section, since all three share the same
  shape of gap: implemented to a confirmed API/schema shape, covered by
  mocked tests against synthetic fixtures, but never run against a real
  authenticated response - genuinely blocked on credentials this project
  doesn't have, not on unfinished code.
  - **Sweden**: Trafikverket's own bespoke XML-request/JSON-response
    envelope, not DATEX II - like Digitraffic wraps Finland, needs its own
    request/parse path onto the shared `Situation`/`SituationRecord`
    models rather than the streaming DATEX parser. Confirmed live via a
    deliberate invalid-key probe: the endpoint, the `Situation` object
    name, and schema version `1.5` (a genuine structured `401`, not a
    generic error page). The real `MessageType`/`MessageCode` value that
    means roadworks specifically is genuinely unconfirmed after checking
    several sources - rather than guess, `record_type` preserves
    `MessageType` verbatim, so `iter_roadworks()` honestly returns nothing
    until a credentialed pull confirms the real discriminator value;
    `iter_situations()` is the way to see everything in the meantime.
    Licence: CC0 1.0 Universal.
  - **Denmark**: genuine DATEX II 3.2, confirmed directly from
    Vejdirektoratet's own protocol specification (`sit:ConstructionWorks`/
    `sit:MaintenanceWorks` and their full `constructionWorkType`/
    `roadMaintenanceType` enumerations stated explicitly, not inferred),
    so it reuses the existing shared streaming parser unchanged, the same
    shape of solution as `vegvesen`. The open metadata catalogue
    (196 datasets, no auth) was re-verified live; the specific roadworks
    dataset confirmed road-work-themed and **CC BY 4.0**-licensed
    per-dataset, not assumed from the catalogue in general. No public data
    URL exists - the real per-dataset pull address and HTTP Basic Auth
    credentials are both issued together at registration, so
    `VejdirektoratetClient` takes `base_url` as a required argument rather
    than a module constant, unlike every other DATEX adapter here.
  - Both ship an import-time `UserWarning` pointing at the "help wanted"
    issue tracker - a genuinely new mechanism, added here and retrofitted
    onto `vegvesen` too for consistency (previously signalled only via a
    docstring admonition and `ProviderEntry(verified=False, ...)`, which
    still remain the source of truth for tooling).
  - Both registered in `streetworks.registry` (`kind="roadworks"`,
    `network_scope=NetworkScope.UNKNOWN` - honest default, not a guess,
    same as `vegvesen`), wired into `scripts/smoke_test.py`
    (`check_trafikverket`/`check_vejdirektoratet`, skip-guarded on missing
    credentials) and `.env.example`. Test fixtures are **synthetic**
    (structurally real shapes, invented values) since neither adapter has
    ever seen real data - `tests/test_trafikverket.py` deliberately
    asserts `iter_roadworks()` stays empty even for a deviation a human
    would recognise as roadworks (`MessageType: "Vägarbete"`), to keep
    that honesty regression-tested.
  - Drafted (not opened) `help wanted` GitHub issue text for both, plus
    Norway's, in `docs/credentials-wanted-issues.md`.

### Fixed

- **DATEX v1.0 linear locations silently degraded to a single point.**
  Found by reading the "pleasant surprise" of Euskadi's zero-code-change
  parse more carefully, per this project's own standing habit: the shared
  parser only recognised `tpegLinearLocation` (the v2/v3 spelling), not
  v1.0's own `tpeglinearLocation` (lower-case `l`) - confirmed by direct
  byte search of the real Basque feed (74/74 real linear-location records
  use the lower-case v1.0 spelling, 0 use the v2/v3 one). Before the fix,
  the shared parser's two-point `from`/`to` extraction never matched it,
  silently degrading a real 2-point line into a single point via the
  generic fallback. Fixed as a second, fallback lookup in
  `streetworks/datex2/parser.py` (v2/v3 spelling tried first) - confirmed
  via a live before/after regression across France, Spain, Belgium,
  Luxembourg and Bulgaria: identical roadworks counts and multi-point-
  location counts, zero drift.

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
