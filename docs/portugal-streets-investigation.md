# Portugal streets gazetteer — investigation notes

Investigation only. No module, no client, no tests. All findings below
are from real, live requests made 2026-08-16, following up on a partial,
older finding recorded in `docs/nap-survey.md` (the IMT NAP section)
that never made it into `docs/providers/pending.md`. Status: **the real,
live, queryable national road-network source is confirmed too coarse —
same outcome as Germany — the municipal fallback path started 2026-08-20,
Lisboa built (`streetworks.arcgis.lisboa`).**

## Step 1 — the national NAP (IMT) — still unresolved

`nap-portugal.imt-ip.pt`, Portugal's listed RTTI NAP (operated by IMT,
Instituto da Mobilidade e dos Transportes), remains exactly as
`docs/nap-survey.md` found it: an Angular single-page app with no
server-rendered content and no discoverable backend API. The only
concretely findable route is `/nap/multimodalsupply`, which covers MMTIS
(schedules/network topology/NeTEx-SIRI) — a different EU regulation from
RTTI, not roadworks-shaped. Not re-investigated further here since
nothing has changed; genuinely unresolved, not ruled out.

## Step 2 — Infraestruturas de Portugal (IP)'s real road network (ruled out)

`docs/nap-survey.md` had already noted IP (Infraestruturas de Portugal,
the actual national road authority) publishes real national road-network
geometry, and described it loosely as "as WFS" — worth checking properly
rather than trusting that summary.

**The promoted distribution is shapefile-only, confirmed live, not
assumed.** IP's own "Rede Rodoviária Nacional" dataset on `dados.gov.pt`
(licensed `cc-by`) has exactly one resource: a `.zip` of shapefiles in
`PT-TM06/ETRS89`. DGT's (Direção-Geral do Território, Portugal's
national mapping agency) separate "Redes de Transporte de Portugal
Continental 1:200 000" — the actual INSPIRE Transport Networks
distribution — offers WMS (rendering only), an ATOM download service,
and a bulk `.zip`, but **no WFS**: its own ATOM feed's XML contains the
INSPIRE spec's optional WFS-link element **still commented out, with the
literal unfilled template placeholder** (`href="http://xyz.org/wfs?..."`)
— a real, decisive confirmation that no direct-access query service was
ever wired up for this dataset, not an oversight in this search. This
same ATOM feed also states `<rights>Sujeito a licenciamento</rights>`
("subject to licensing") for this dataset — a real discrepancy against
`dados.gov.pt`'s own `cc-by` label for the nominally same data, not
reconciled here.

**A real, live, queryable route exists anyway — found by tracing IP's
own public map viewer, the same technique that found DfI Roads' real
backend.** IP's own ArcGIS Online item (`webmap_rede_rodoviaria_2023`,
owned by `infraestruturasdeportugal.pt`'s real org account) resolves to
a real, keyless, queryable ArcGIS **MapServer**:
`https://utility.arcgis.com/usrsvcs/servers/8e3c86cecb8c4d1f93db7005f14d9ee5/rest/services/SiteExternoV3RedeRodoviaria2023/MapServer`
(`capabilities: Map,Query,Data`, confirmed live). Layer 8 ("Estradas IP
Gestão Directa" — IP direct-management roads) is real `esriGeometryPolyline`.

**Bottom line: real geometry, no named-street identity — the same
outcome as Germany's BKG, checked directly, not assumed from the
1:200 000 scale alone.** The layer's full real field list is `objectid`,
`roadnumber`, `jurisdicao`, `gestao`, `road1`, `shape` — no name/
designation field at all. Real sample values confirm `roadnumber`/
`road1` are route-classification codes, not street names:
`roadnumber="A1"`/`road1="IC1"`, `roadnumber="A13"`/`road1="IC3"`,
`roadnumber="A14"`/`road1="IP3"` (`A`=motorway, `IC`=Itinerário
Complementar, `IP`=Itinerário Principal — Portugal's own national road
classification tiers, not local road/street names). Geometry is served
in Web Mercator (`wkid: 102100`/`latestWkid: 3857`) — not independently
re-verified against the dataset's own stated native `PT-TM06`/`ETRS89`,
since the schema question already settles this as unbuildable for a
named-street gazetteer regardless of CRS.

## Step 3 — municipal fallback (started 2026-08-20, Lisboa built)

**Lisboa — checked, built.** Câmara Municipal de Lisboa (CML) runs its
own real Geodados ArcGIS Online organisation (`geodados_CML`, ~130 real
items) — walked in full, not found from documentation. Two real
candidates were checked and set aside first: `Topónimos` (on CML's
`Cartografia_Base` service — only 40 real neighbourhood-label points,
not streets) and `Rede Viária` (same service — 3,763 real named
segments, but live grouping found only 375 distinct street names,
Lisbon's structuring/backbone network, not exhaustive). **The real,
official register is `Toponímia de Lisboa`** (on CML's
`Cultura_Toponimia` service) — 3,671 real records, 100% named, already
one row per street, each carrying genuine municipal-decree provenance
(real deliberation/edict dates, former names, a prose naming-history
essay). Geometry is real `LineString`/`MultiLineString`, confirmed
genuine WGS84 live despite the service's own stated Web Mercator native
CRS. Licence: real, explicit CC0. Shipped as
`streetworks.arcgis.lisboa.LisboaStreetsClient` /
`from_lisboa_street` — see
`docs/providers/portugal.md#toponímia-de-lisboa-cml` for the full
write-up.

Whether Porto or any of the Área Metropolitana de Lisboa's other 17
municipalities publish their own genuine named-street layer has **not**
been investigated — real, open-ended per-municipality work, the same
shape as Germany's state fan-out.

## Recommendation

Steps 1 and 2 are decisively closed and don't need re-checking unless
IMT or IP change what they publish. Step 3 (municipal fan-out) is now
started, with Lisboa done — Porto and the rest of the Área
Metropolitana de Lisboa remain a real, open next step if picked back
up.
