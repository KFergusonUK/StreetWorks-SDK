# Pending provider candidates

> New content, not a migration. None of Portugal, Singapore, or Canada
> appear in README.md in this "candidate for investigation" framing —
> see `docs/migration-reconciliation.md`, Case 3, for what each name
> actually does appear as (Portugal: a future-gazetteer mention already
> migrated to [`docs/providers/europe.md`](europe.md#international-gazetteers);
> Canada: the fact that a real Quebec City WZDx feed is already
> registered, migrated to [`docs/providers/us.md`](us.md#wzdx);
> Singapore doesn't appear at all). Recorded here at the project owner's
> request as named candidates for future work.

Named as worth investigating next, but **not yet scoped, and not yet
checked for a live, accessible endpoint** — unlike every other entry in
[`docs/providers/index.md`](index.md), which only lists a provider once
its API shape has been confirmed one way or another (live-verified,
Credentials-wanted, or Documented-unavailable; see
[`docs/contributing/scaffolds.md`](../contributing/scaffolds.md)).

- **Portugal — roadworks partially built; streets gazetteer checked and
  ruled out at the national level, the same outcome as Germany.** Lisboa
  (Condicionamentos de Trânsito) is a real, confirmed roadworks provider,
  sidestepping the still-credential-parked national IMT National Access
  Point (`nap-portugal.imt-ip.pt`, an Angular SPA with no discoverable
  backend, genuinely unresolved not ruled out) entirely — see
  [`docs/providers/portugal.md`](portugal.md). **Streets** is a separate
  question, investigated 2026-08-16 — full findings in
  [`docs/portugal-streets-investigation.md`](../portugal-streets-investigation.md).
  Infraestruturas de Portugal (IP)'s promoted national road-network
  distribution is shapefile-only (its own ATOM feed's WFS-link element
  is a literal unfilled template placeholder, never wired up), but a
  real, live, keyless, queryable ArcGIS MapServer was found anyway by
  tracing IP's own public map viewer — the same technique that found DfI
  Roads' real backend. Its full field list (`roadnumber`/`jurisdicao`/
  `gestao`/`road1`) carries **no name field at all**; real sample values
  (`roadnumber="A1"`/`road1="IC1"`) are route-classification codes, not
  street names — the same "real geometry, no named-street identity"
  outcome Germany's BKG landed on. Porto and other municipalities remain
  genuinely unchecked/unbuilt — the same open, per-municipality fallback
  shape as Germany's own state fan-out.
- **Singapore** — no source investigated at all.
- **Canada — roadworks partially built, streets now fully built
  nationally.** British Columbia (DriveBC, Open511) is a real, confirmed
  roadworks provider, and Quebec City's WZDx feed was already covered —
  see [`docs/providers/canada.md`](canada.md). Ontario 511 was checked
  live (confirmed not to publish WZDx) but not built; other provinces
  and municipal roadworks portals (Toronto, Montreal, Vancouver) remain
  genuinely unchecked. **Streets is no longer pending at all** — the
  National Road Network (`streetworks.arcgis.nrn`), found 2026-08-16,
  is real, live, keyless, and covers all 13 provinces/territories
  nationally in one build (Segment only, the same TIGERweb/NWB
  outcome — see `docs/providers/canada.md`).
- **NUAR (National Underground Asset Register, UK) — a different case
  from every other entry on this page: the model is scoped, only the
  transport is still pending.** A new data class, not roadworks — buried
  utility assets (pipes, cables, ducts, chambers), not a street/works
  register. OS/GDS opened a secure **Sandbox** on 2026-08-07 (synthetic
  data; separate from live) to test expanded access routes **including a
  consumption API** — but that API's endpoints, auth and wire format are
  **unpublished** and use-case-gated, so the connector itself stays
  pending here. The *data model*, however, is already public: the
  **NUAR Harmonised Data Model**
  (`github.com/national-underground-asset-register/nuar-datamodel`,
  **OGL v3.0**, based on the approved **OGC MUDDI** standard) ships XMI +
  PostGIS DDL encodings, feature catalogues and codelists, with
  geometries defaulting to **EPSG:27700 (BNG)**. Because that schema is
  already public and confirmed, `streetworks.nuar` exists now as a
  **testing-only native model** (`UndergroundAsset`, derived from the
  published DDL column names, never coerced into `Works`/`WorksSite`) —
  see the module's own docstring for the full provenance. It carries no
  client, no endpoint, and no registry entry (`NUAR_CONNECTOR_LIVE` is
  `False`, and importing the package warns) — there is genuinely nothing
  to query yet. When the sandbox transport lands, this graduates the same
  way any other Credentials-wanted scaffold does; until then it is not a
  provider, just a ready shape for one. Because NUAR *data* is not open
  (legally enforceable access agreements), even a connector built against
  a confirmed transport would be bring-your-own-credentials only, never
  bundled. Scope: England, Wales, Northern Ireland (not Scotland,
  consistent with this SDK's existing OSG/Scotland gating). Sandbox trial
  applied for by the project owner, 2026-08.
- **Spain — Catastro (Dirección General del Catastro), INSPIRE
  Addresses (AD) — a different case again: real, current data exists,
  but the licence is the blocker, not the endpoint.** Investigated
  2026-08-15 alongside [IDEE Transportes](europe.md#idee-transportes-spain-national-road-network)
  (Spain's separate national road network, which *was* built the same
  day). Catastro's documented WFS endpoint
  (`ovc.catastro.meh.es/INSPIRE/wfsAD.aspx`) no longer responds to any
  request variant tried, including a bare `GetCapabilities` — a real
  ATOM bulk-download route is confirmed live and current instead
  (`ES.SDGC.AD.atom.xml`, per-province entries). The real blocker is
  Catastro's own confirmed licence (`Licencia.pdf`): the *original* data
  may not be redistributed over the internet in unmodified form — only
  "transformed, value-added" products may be — which conflicts with this
  SDK's usual convention of committing a real trimmed API-response
  fixture per provider. Not built until that's resolved, one way or
  another — either using only synthetic/structurally-representative
  fixtures instead of a real captured sample, or a clearer read on
  whether this SDK's own object conversion counts as "transformation"
  under that clause. Covers 95% of Spanish territory by the DGC's own
  stated completeness figure — Basque Country and Navarre run their own
  independent cadastral offices.
- **Germany — streets gazetteer, a two-part national ruling plus a
  state fan-out now in progress.** Full findings in
  [`docs/germany-streets-investigation.md`](../germany-streets-investigation.md)
  (national rulings investigated 2026-08-16, state fan-out started
  2026-08-20). BKG's federal ATKIS DLM250-based INSPIRE Transport
  Networks WFS (`sg.geodatenzentrum.de/wfs_dlm250_inspire`, confirmed
  live) is real but genuinely too coarse — a live 200-record sample
  found 0/200 records reference their own geometry via the standard
  `RoadLink` association, 86.5% carry no name at all, and the 13.5%
  that do are named tourist/scenic driving routes (e.g. "Romantische
  Straße"), not street names. BKG's own address product
  (Georeferenzierte Adressdaten) is confirmed partly sourced from
  Deutsche Post Direkt (commercial) and gated to "Federal authorities
  and eligible users" — not cleanly open. **The per-state fallback path
  is now real and partially built**: Hamburg's own joint address/
  street gazetteer (GAGES) is real, live, and keyless — 9,639 real
  streets, 100% named, shipped as `streetworks.hamburg`. Berlin was
  checked next and is genuinely blocked, not ruled out: its entire GDI
  WFS host (`gdi.berlin.de`) is confirmed live to be down for
  maintenance with no ETA, plausibly tied to its FIS-Broker system
  having been shut down 1 December 2025 in favour of new
  infrastructure — a real, reportable connectivity failure, not routed
  around; two real candidate datasets were found on `daten.berlin.de`
  before hitting the wall, worth a retry once the host is back.
  Brandenburg and Saxony remain genuinely unchecked.
- **Italy — ANNCSU's address/civic-number side (`accessi`), deliberately
  scoped out of the streets build, not blocked.** A different case from
  every other entry on this page: real, live, keyless, CC BY 4.0, and
  confirmed buildable — just not built yet, by choice, alongside
  `streetworks.anncsu` (streets only) on 2026-08-16. `accessi` is
  ANNCSU's own civic-number/address-point resource — real `CIVICO`
  (house number), `ESPONENTE`, real coordinates (`COORD_X_COMUNE`/
  `COORD_Y_COMUNE`, genuine WGS84, comma-decimal-separated — a real
  Italian-locale format, not a bug) and a real accuracy codelist
  (`METODO`, 5 values). The real gap: coordinates are only **~20%
  populated**, confirmed live in a real regional sample (Valle d'Aosta,
  19,297/94,302 real rows) — genuinely partial, not a small edge case.
  Real access is per-region bulk CSV (`getds.php?INDIR_<region>`, the
  same ZIP+CSV shape as the streets side) or the national `INDIR_ITA`
  file — both real and live, just larger and messier than the simpler
  streets resource. Would map to `Address`, joined to the already-built
  `Street` records via `PROGRESSIVO_NAZIONALE` (a real, stated link).
- **Isle of Man — streets gazetteer checked twice, genuinely not found
  open either time, the third Crown Dependency checked this session
  after Jersey and Guernsey both turned out real and buildable.**
  First investigated 2026-08-16 (live, not from documentation alone):
  the Island's own real ArcGIS Online organisation (`manngis`) was
  enumerated in full (329 real items) — no street/road/gazetteer
  dataset anywhere in it; its hosted `manngispubserver` ArcGIS REST
  deployment (`maps.gov.im`/`ppmaps.gov.im`) was walked folder by
  folder too, the same technique that found Jersey's and Guernsey's
  real services — real services exist (flood risk, basemaps, a
  `CorporateDynamicServices/ProdFeeds` points-of-interest layer with
  schools/GPs/bus stops/postboxes) but none is a street or road layer.
  A real Street Gazetteer product (BS7666-based) is referenced by the
  UK academic Chest/JISC digital-map licensing scheme
  (`chest.ac.uk/agreements/iom`) — genuinely real, but behind an
  academic-only licence agreement, not a public endpoint; blocked from
  a direct check of that page's own terms.

  **Re-investigated 2026-08-20 from a different angle, at the project
  owner's request — one new lead checked and ruled out, one real lead
  found and deliberately not built.** A new third-party platform,
  "Smart Island" (`smartisland.im`, run by a private Manx tech
  company, "AI-powered"), looked promising (structured addresses,
  named highways, 19,026 geographic records) but its own page states
  the source directly: *"Data from dankarran/isleofman-opendata
  derived from OpenStreetMap contributors"* — the same OSM-provenance
  disqualifier already applied to Bulgaria's Sofiaplan, ruled out on
  the same basis. A genuine first-party government dataset was found
  instead: the Isle of Man Government's own Land Registry "Land
  Transactions" open dataset (`gov.im`, confirmed live — a real
  minimal-user-agent WAF block was hit first, resolved with a normal
  realistic browser UA string, not evasion), OGL/Crown Copyright
  licensed, a monthly-updated CSV of every registered land transaction
  since 6 November 2000 — 44,132 real rows, a real `Street_Name` field
  99.99% populated, 4,107 distinct real Manx street names. **Not
  built, on the project owner's explicit call**: unlike Germany/
  Portugal's "real data, wrong shape" rulings, this is real data in
  the *right* shape (a genuine `Street_Name` per row) but with
  structurally incomplete coverage baked into what the dataset even
  is — only streets with at least one registered transaction since
  2000 appear at all, so it's a derived list, not a canonical
  register, the same category distinction as the earlier
  Bulgaria/Sofiaplan provenance calls but on completeness rather than
  provenance. Genuinely unresolved, not ruled out — either this same
  Land Registry source revisited with the caveat made explicit
  (closer to Monaghan's own "real but partial" precedent) or a direct
  enquiry to Isle of Man Government remains the real next step.
- **Gibraltar — roadworks checked, ruled out at the only real candidate
  found, not just unchecked.** Streets is now built
  (`streetworks.gibraltar`, see [`docs/providers/gibraltar.md`](gibraltar.md));
  roadworks is a separate question, investigated the same day
  (2026-08-16). The Geoportal's own GeoServer (the same real deployment
  streets uses) publishes a `gibgis:under_construction` polygon layer -
  live, keyless, 23 real features - but its schema, confirmed via
  `DescribeFeatureType`, carries **only a geometry field**: no name,
  date, description, status, or type attribute of any kind. Genuinely
  unusable as a works feed, not a licence or access blocker like
  Gibraltar's own streets side had - there is simply nothing to read
  beyond "a polygon exists somewhere." No other roadworks-shaped layer
  was found on this deployment. The Technical Services Department's own
  public-facing pages (`gibraltar.gov.gi/transport-traffic-and-technical-services`)
  were not checked for a separate, non-GIS works register - a real,
  open next step, not attempted this session.
- **Ireland — streets gazetteer investigated live and ruled out, a
  genuine structural finding, not a missing-data gap.** Roadworks was
  already covered (MapRoad, a documented-but-unavailable
  data-sharing-gated scaffold - see `streetworks.maproad`'s own module
  docstring); streets is a separate question, investigated 2026-08-16.
  National bodies checked first: Tailte Éireann's own real open-data
  catalogue (GeoHive/ArcGIS Online, CC BY 4.0) publishes administrative
  boundaries and a 1:250,000-scale generalised road layer with **no name
  field anywhere** (`FCsubtype`/`RTT` route-classification codes only,
  5,188 real features); TII's own live "National Road Network 2024"
  service is real but is the motorway/N-road tier only, with a `Road`
  field that's a real route code (`"M7"`, `"N06"`), not a street name -
  the same shape as Canada's own Trans-Canada Highway/National Highway
  System tiers. **The real, decisive finding**: Ireland's road network
  outside towns is genuinely organised by route *number*, not name - a
  real structural characteristic of the Irish system, confirmed live
  against two of the 31 County Councils' own independent ArcGIS Online
  feeds (a real per-authority fan-out, the same shape Germany's states
  have): Donegal's "Road Network" (4,409 real features, fields
  `Road_id`/`type`/`Electoral_Area` - `Road_id` values like `"N-13-21"`,
  no name field exists at all) and Monaghan's "Local_Roads" (1,612 real
  features, a `Road_Name` field that is itself a real L-road route
  number, e.g. `"L-31011-0"` - `Start_At`/`Finish_At` carry real
  junction/townland descriptions, not the road's own name). No Dublin
  City Council ArcGIS Online organisation was found to check the one
  place genuinely urban street names would most plausibly appear in the
  open. Not built - two real county pilots both confirmed the same
  numbered-not-named shape rather than one being an outlier worth
  building against.
- **Bulgaria — streets gazetteer investigated live and ruled out, on a
  provenance judgement call rather than a technical blocker.**
  Roadworks was already covered (the Road Infrastructure Agency/LIMA,
  `streetworks.datex2.bulgaria`); streets is a separate question,
  investigated 2026-08-17. National bodies checked first: the Geodesy,
  Cartography and Cadastre Agency's real, live ArcGIS/WFS deployment
  (`inspire.cadastre.bg`) publishes only `Administrative_Unit`,
  `Building`, `Cadastral_Parcel`, and `Geo_Names` - and that last one,
  despite the promising name, is a real hydrography/physical-geography
  gazetteer (rivers - real values include `"Тимок/Timok"`,
  `"Дунав/Dunav"`, the Danube), the same "general place-names register,
  not streets" trap Gibraltar's own `GN_GeographicalNames` was. The
  national open-data portal (`data.egov.bg`) genuinely blocks automated
  access (a real `403`, confirmed twice with realistic headers, not
  routed around per `docs/contributing/agent-boundaries.md`). **The
  real, decisive finding**: Sofia Municipality's own open-data platform
  (Sofiaplan, `api.sofiaplan.bg`) does have a real, live, keyless,
  comprehensive streets dataset (`osi_ulici`, 46,017 real features,
  51.9% named) - but its own stated `provider` field is `"ОСМ"`
  (OpenStreetMap), not an independent government survey. Two smaller,
  genuinely non-OSM alternatives exist on the same platform but are far
  narrower in scope: a 618-row field survey for one specific
  hydro-assessment area, and a 216-row cultural-heritage "paved
  streets" subset. Checked with the project owner and deliberately not
  built - this SDK's standing convention has been independent
  government registers or surveys, not a municipality's own republish
  of crowdsourced data, and Sofia's case didn't warrant being the first
  exception.

- **Sweden — streets gazetteer investigated live and ruled out, on
  registration gates rather than a technical or provenance blocker.**
  Roadworks was already covered by two Credentials-wanted scaffolds
  (Trafikverket's own DATEX-adjacent API and Stockholm Trafikkontoret,
  both requiring an `api_key` - see `docs/providers/europe.md`); streets
  is a separate question, investigated 2026-08-17. Two real national
  candidates were checked, both with genuine street-name fields and no
  provenance concerns, unlike Bulgaria: **NVDB** (Nationell VägDataBas,
  Trafikverket's national road database, CC0, confirmed via the OSM
  wiki's own field-description page to carry a real `Gatunamn` attribute)
  and **Lantmäteriet's Belägenhetsadress** (property/access-address
  product, fee-free since 2025-02-03, a real `Adressområde`/
  `gatuadressområde` street-name field per Lantmäteriet's own address
  spec PDF). **The real, decisive finding**: every live access route for
  both sources requires account registration. NVDB's Lastkajen download
  portal requires an email account plus accepting a licence agreement;
  its Öppna API/Datautbytesportalen route was confirmed live via
  Trafikverket's own nvdb.se page to allow browsing without login but
  require account registration to fetch data ("...kan du läsa utan att
  logga in, men om du vill hämta data behöver du registrera ett konto").
  A real, live-looking API key was found hardcoded in a public
  Trafikverket news article's client-side JavaScript (pointing at the
  same `api.trafikinfo.trafikverket.se` endpoint the existing roadworks
  scaffold targets) - not used, since it wasn't explicitly provided by
  the project owner and Trafikverket's own documentation confirms
  registration is the required path; using a scraped key would route
  around that gate, which `docs/contributing/agent-boundaries.md`
  explicitly rules out. Lantmäteriet's Belägenhetsadress Direkt route
  requires a Geotorget account issued via OAuth2 "behörighetsnycklar"
  only after access is already granted, with per-product purpose review
  under the Real Property Register Act and GDPR ("Omfattas av juridisk
  prövning... Särskilda användningsvillkor måste godkännas", confirmed
  live via Lantmäteriet's own versioned fee/delivery PDF) - not
  instant self-service. No municipal-level fallback (a Stockholm- or
  Gothenburg-scoped open dataset, matching the Marousi/Greece pilot
  pattern) has been checked yet - a real, open next step if this is
  revisited.

Following this project's own standing pattern (see
[`docs/roadmap.md`](../roadmap.md) and
[`docs/contributing/scaffolds.md`](../contributing/scaffolds.md)), any
of these moves to a real scaffold only once a genuine, checkable
endpoint has been found and its shape confirmed live — not before.
