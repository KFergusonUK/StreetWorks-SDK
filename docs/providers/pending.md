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

- **Portugal — partially built, no longer fully pending.** Lisboa
  (Condicionamentos de Trânsito) is now a real, confirmed provider,
  sidestepping the still-credential-parked national IMT National Access
  Point entirely — see [`docs/providers/portugal.md`](portugal.md). Porto
  and other municipalities, and the national NAP itself, remain
  genuinely unchecked/unbuilt.
- **Singapore** — no source investigated at all.
- **Canada — partially built, no longer fully pending.** British
  Columbia (DriveBC, Open511) is now a real, confirmed provider, and
  Quebec City's WZDx feed was already covered — see
  [`docs/providers/canada.md`](canada.md). Ontario 511 was checked live
  (confirmed not to publish WZDx) but not built; other provinces and
  municipal portals (Toronto, Montreal, Vancouver) remain genuinely
  unchecked.
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

Following this project's own standing pattern (see
[`docs/roadmap.md`](../roadmap.md) and
[`docs/contributing/scaffolds.md`](../contributing/scaffolds.md)), any
of these moves to a real scaffold only once a genuine, checkable
endpoint has been found and its shape confirmed live — not before.
