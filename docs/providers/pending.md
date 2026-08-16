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
- **Germany — streets gazetteer, a two-part ruling: both the obvious
  federal source and the address layer are closed off, one real
  fallback path remains unchecked.** Full findings in
  [`docs/germany-streets-investigation.md`](../germany-streets-investigation.md)
  (investigated 2026-08-16). BKG's federal ATKIS DLM250-based INSPIRE
  Transport Networks WFS (`sg.geodatenzentrum.de/wfs_dlm250_inspire`,
  confirmed live) is real but genuinely too coarse — a live 200-record
  sample found 0/200 records reference their own geometry via the
  standard `RoadLink` association, 86.5% carry no name at all, and the
  13.5% that do are named tourist/scenic driving routes (e.g.
  "Romantische Straße"), not street names. BKG's own address product
  (Georeferenzierte Adressdaten) is confirmed partly sourced from
  Deutsche Post Direkt (commercial) and gated to "Federal authorities
  and eligible users" — not cleanly open. What's left unchecked: whether
  Hamburg, Brandenburg, Saxony, or Berlin (the four states already
  touched for roadworks) expose a genuine named-street layer of their
  own — real, open-ended per-state work, not started.
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
- **Isle of Man — streets gazetteer checked, genuinely not found open,
  the third Crown Dependency checked this session after Jersey and
  Guernsey both turned out real and buildable.** Investigated
  2026-08-16, live, not from documentation alone. The Island's own real
  ArcGIS Online organisation (`manngis`) was enumerated in full (329
  real items) — no street/road/gazetteer dataset anywhere in it; its
  hosted `manngispubserver` ArcGIS REST deployment
  (`maps.gov.im`/`ppmaps.gov.im`) was walked folder by folder too, the
  same technique that found Jersey's and Guernsey's real services — real
  services exist (flood risk, basemaps, a `CorporateDynamicServices/
  ProdFeeds` points-of-interest layer with schools/GPs/bus stops/postboxes)
  but none is a street or road layer. A real Street Gazetteer product
  (BS7666-based) is referenced by the UK academic Chest/JISC digital-map
  licensing scheme (`chest.ac.uk/agreements/iom`) — genuinely real, but
  behind an academic-only licence agreement, not a public endpoint;
  Cloudflare blocked a direct check of that page's own terms. Unlike
  Germany/Portugal's national-streets rulings, this isn't "real data,
  wrong shape" — it's "no open access route found at all." Genuinely
  unresolved, not ruled out — a future direct enquiry to Isle of Man
  Government (rather than more endpoint-hunting) is the real next step.

Following this project's own standing pattern (see
[`docs/roadmap.md`](../roadmap.md) and
[`docs/contributing/scaffolds.md`](../contributing/scaffolds.md)), any
of these moves to a real scaffold only once a genuine, checkable
endpoint has been found and its shape confirmed live — not before.
