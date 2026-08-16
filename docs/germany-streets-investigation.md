# Germany streets gazetteer — investigation notes

Investigation only, per `germany-streets-brief.md`. No module, no
client, no tests. All findings below are from real, live requests made
2026-08-16. Status: **federal source ruled out, address layer ruled
out, state fan-out not yet checked** — parked, not abandoned; see
`docs/providers/pending.md` for the current summary.

## Verify-first step 1 — BKG federal streets (ruled out)

**Endpoint**: `https://sg.geodatenzentrum.de/wfs_dlm250_inspire` (also
reachable at the `sgx.` host), WFS 2.0.0, INSPIRE Annex I Theme 7
(Transport Networks), based on **ATKIS DLM250** — confirmed live
(`GetCapabilities` returns HTTP 200, 166,511 bytes). Same INSPIRE
schema family already used for Spain's IDEE Transportes
(`tn-ro:Road`/`RoadLink`/`RoadNode`/`FunctionalRoadClass`/`FormOfWay`/
`NumberOfLanes`/`RoadServiceType`/`RoadSurfaceCategory`/`ERoad`) — but
**no `tn-ro:RoadName` feature type is offered at all**, unlike Spain's
service.

**Bottom line: too coarse, no named-street identity.** A real
`GetFeature` pull (`tn-ro:Road`, 200-record sample) found:

- **0/200 records have a populated `net:link`** — unlike Spain, where
  `Road` → `RoadLink` resolves cleanly, Germany's federal `Road`
  entities don't reference their own geometry via the standard
  association at all. A first real sample record
  (`gml:id="DLM250_Road_DEBKGDL200007AU7_2"`) had both
  `tn:geographicalName` and `net:link` stated `nilReason="other:
  unpopulated"`/`nilReason="true"`, with only a bare classification
  code (`nationalRoadCode: "K1"`).
- **173/200 (86.5%) have no `geographicalName` at all** — nil, not
  empty string, confirmed by checking the nil-reason attribute per
  record, not just an empty-text heuristic.
- **The 27/200 (13.5%) that *do* have a name are named tourist/scenic
  driving routes, not street names**: real `gn:text` values found live
  include *"Schwäbische Dichterstraße"*, *"Schwarzwald-Bäderstraße"*,
  *"Route der Industriekultur"*, *"Schwäbische Albstraße : Straße der
  Staufer"*, *"Romantische Straße"*, *"Badische Weinstraße"* — themed
  driving routes ("Romantic Road", wine routes), the German equivalent
  of a "Route 66" brand name, not what "named street" means for this
  SDK's gazetteer model.
- Real `nationalRoadCode` values sampled: `K1`, `LAs52`, `K2007`,
  `K8233`, `K49`, `K76`, `L3247`, `B519`, `B169`, `L84`, `B410`, `L362`,
  `L654`, `L341`, `L73`, `L83`, `St2064`, `L562`, `L3289`, `St2118` —
  real German road-classification codes (`K` = Kreisstraße/county road,
  `L` = Landesstraße/state road, `B` = Bundesstraße/federal road,
  `St` = Staatsstraße, a Bavaria-specific state-road prefix), matching
  a classified route network, not local street identity.

**Conclusion**: BKG's federal ATKIS DLM250-based INSPIRE service is a
1:250,000-scale classified road network (motorways down to county
roads), confirmed live to carry no local/urban named-street content.
Per the brief's own decision gate ("BKG insufficient → minimal state
cluster only"), a clean federal single-source build is off the table.

## Verify-first step 2 — address layer (ruled out)

BKG's own product documentation for **Georeferenzierte Adressdaten
(GA)** confirms the brief's own hypothesis directly: of ~23.7M real
address records, **~620,000 are sourced from Deutsche Post Direkt
GmbH** (a commercial data provider), and access runs through the "V
GeoBund" contract for **"Federal authorities and eligible users"** —
not a generic open self-service download the way this SDK's other
address registers are. Not cleanly open.

**Conclusion**: per the brief's own fallback ("If addresses aren't
cleanly open → Germany lands as a streets-only entry"), no German
address register is buildable now regardless of what happens with
streets.

## Verify-first step 3 — state fan-out (not yet checked)

The brief's own fallback path — checking whether Hamburg, Brandenburg,
Saxony, and Berlin (the four states already touched for roadworks via
`streetworks.ogc.germany`/`streetworks.berlin`) expose a genuine
named-street layer via their own WFS/OGC API Features — has **not**
been investigated. This is real, open-ended work: four separate
per-state checks, not a quick follow-up. Nothing found or ruled out
here yet.

## Recommendation

Park here. If picked back up, start directly at step 3 (state
fan-out) — steps 1 and 2 are decisively closed and don't need
re-checking unless BKG's own services change. Per the brief's own
scope discipline: prove the shape on one state first, then stop and
report back before fanning out to all four.
