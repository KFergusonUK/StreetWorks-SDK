# Finding a provider

> Migrated verbatim from README.md's `## Finding a provider` and `## Status`
> sections, including the `### Credentials wanted` and `### Recently
> confirmed` subsections (phase one, lossless restructure — see
> `docs/migration-mapping.md`).

## Coverage

✓ live · ~ in progress · ✗ ruled out

**Europe**  ✓ Austria · Belgium · Bulgaria · Denmark · Finland · France · Germany · Gibraltar · Guernsey · Iceland · Italy · Jersey · Lithuania · Luxembourg · Netherlands · Norway · Portugal · Spain · Switzerland · Ireland · UK   ~ Greece · Sweden
**Americas**  ✓ Canada · United States
**Oceania**  ✓ Australia · New Zealand
**Asia**  ~ Singapore
**No known coverage**  ✗ China · Russia

*Several territories carry multiple data-owning authorities (Catalonia,
Basque Country, Mallorca, Madrid; the four UK nations) — see the
[module table](#module-table) below for the per-provider breakdown.
Jersey and Guernsey are listed separately from UK: Crown Dependencies with
their own providers ([`streetworks.arcgis.jersey`](uk.md#jersey-roadworkx-and-tigerweb-arcgis-rest),
[`streetworks.arcgis.guernsey`](uk.md#guernsey-street-gazetteer)), not one
of the four UK nations; Gibraltar is a British Overseas Territory, a
different constitutional category again, with its own
[`streetworks.gibraltar`](gibraltar.md). "In progress" also collapses two
genuinely different states (credentials-wanted vs.
documented-but-unavailable) for scannability — the matrix below
distinguishes these. **Canada, Portugal, Austria, and Ireland all moved
from in-progress to live** once DriveBC (British Columbia), Lisboa
(Condicionamentos de Trânsito), Vienna (verkehrswirksame Baustellen),
and Monaghan's own road network shipped — real coverage in each is
still partial (one province/city/county, not national — Austria's own
national ASFINAG feed stays a Credentials-wanted scaffold, and
Ireland's own national MapRoad roadworks stays a documented-unavailable
scaffold), same as every other ✓ entry that isn't literally
comprehensive; see [`docs/providers/canada.md`](canada.md),
[`docs/providers/portugal.md`](portugal.md),
[`docs/providers/austria.md`](austria.md) and
[`docs/providers/ireland.md`](ireland.md) for exactly what's covered
and what isn't. This is the canonical coverage roster; `docs/index.md`'s
copy quotes it rather than restating it independently.*

See this coverage plotted on a world map:
[`examples/roadworks_world_map.py`](../../examples/roadworks_world_map.py)
(registry-driven, so it stays current automatically — see
[`docs/examples.md`](../examples.md) for a real generated screenshot).

Everything in [`docs/providers/`](.) is organised by *technology* — you need to already
know that Spain publishes DATEX II, or that Saxony is `streetworks.ogc`, to
find the right import. `streetworks.providers()`/`get_provider()` answer the
question the other way round — "what covers X" and "give me Y's client" —
without needing that specialist knowledge first:

```python
>>> from streetworks import providers, get_provider
>>> providers(territory="England")
Street Manager
  England's statutory street works register - permits, works, inspections.
  Network scope: comprehensive
  Scope: Not Scotland (see the srwr provider), Wales (see trafficwales), or Northern Ireland (see trafficwatchni).
  Credentials: Street Manager API account (email + password)
  from streetworks.streetmanager import StreetManagerClient

... (5 more — OS Open USRN, DataVIA, D-TRO, Street Manager Open Data, UK Police)

>>> DGTClient = get_provider("dgt")   # the class, not an instance - constructors vary
>>> with DGTClient() as dgt:
...     situations = list(dgt.iter_roadworks())
```

`providers()` filters by `territory` (case-insensitive; `"UK"` expands to
the four nations — a query-time convenience only, never stored data),
`kind` (`"roadworks"` / `"addresses"` / `"streets"` / `"context"` — split
from one `"gazetteer"` value, see
[`docs/providers/europe.md`](europe.md#international-gazetteers--separate-strand)
for why lumping them together was a real mistake), and `credentials`
(`False` for the credential-free ones). `get_provider()` resolves a single
provider or a curated alias (`"finland"`, `"iceland"`, `"scotland"`, ...);
an ambiguous name (`"germany"` → four providers, `"france"`/`"netherlands"`/
`"norway"` → two each, a roadworks feed and an address register, `"spain"`
→ four roadworks feeds (DGT `multi_authority_interurban` national ex-
Catalonia/Basque, Consell de Mallorca `regional` insular — overlapping
with DGT, not disjoint, see
[Never deduplicate across providers](../concepts/data-model.md#never-deduplicate-across-providers)
— SCT `multi_authority_interurban` for Catalonia, and Euskadi
`multi_authority_interurban` for the Basque Country — DGT's two
exclusions, both now filled), `"england"` → several) raises naming every
real candidate rather than guessing which one you meant.

Every roadworks entry also carries a `network_scope` (`comprehensive` /
`multi_authority_interurban` / `strategic` / `motorway` / `regional` /
`varies_by_feed` / `not_applicable` / `unknown`) — what tier of the road
network its real data actually reaches, checked live rather than assumed
from a provider's stated remit (`docs/network-scope-audit.md`). This is
the field that stops "DGT covers Spain" from being misread as "DGT covers
every street in Valencia" — shown in `providers()`'s own rendering (see
`Network scope:` above), not just stored.

This is a discovery layer over the native interfaces below, not a
replacement for them — every provider still has its own full-fidelity
client, documented in its own section in [`docs/providers/`](.).

## Module table

| Module | Service | Direction |
|---|---|---|
| `streetworks.streetmanager` | [DfT Street Manager](https://department-for-transport-streetmanager.github.io/street-manager-docs/api-documentation/) — all nine APIs (Work, Reporting, Street Lookup, GeoJSON, Party, Data Export, Event, Sampling, Worklist), V6 & V7, sandbox & production | read + write |
| `streetworks.opendata` | [Street Manager Open Data](https://department-for-transport-streetmanager.github.io/street-manager-docs/open-data/) — AWS SNS push notifications | receive |
| `streetworks.datavia` | [Geoplace DataVIA](https://datavia.geoplace.co.uk/documentation) — full NSG layer catalogue over OGC WFS and WMS (rendered maps + feature info), Basic + OAuth2 | read |
| `streetworks.dtro` | [DfT Digital Traffic Regulation Orders](https://d-tro.dft.gov.uk/api-documentation/) — the legal orders behind speed limits, closures and restrictions; integration & production | read + write |
| `streetworks.srwr` | [Scottish Road Works Register](https://roadworks.scot/) — national register via Open Data CSV extracts (no credentials) | read |
| `streetworks.openusrn` | [OS Open USRN](https://osdatahub.os.uk/downloads/open/OpenUSRN) — every GB USRN with geometry, via the OS Downloads API (no credentials) | read |
| `streetworks.ban` | [BAN (Base Adresse Nationale)](https://adresse.data.gouv.fr/) — France's national address base, ~25M addresses, geocoding API + bulk per-département/national files (no credentials). **An address base, not a street register** — see [`docs/providers/europe.md`](europe.md) | read |
| `streetworks.bag` | [BAG (Basisregistratie Adressen en Gebouwen)](https://www.kadaster.nl/zakelijk/producten/adressen-en-gebouwen/bag-geopackage) — Netherlands' national addresses/buildings register, PDOK Locatieserver + a ~7.8 GB national GeoPackage (no credentials). Street identity is real but not its own table — see [`docs/providers/europe.md`](europe.md) | read |
| `streetworks.kartverket` | [Kartverket](https://www.geonorge.no/) — Norway's national address register + official (multilingual) place names, REST APIs + bulk CSV (no credentials). Not the same agency as the Vegvesen roadworks provider — see [`docs/providers/europe.md`](europe.md) | read |
| `streetworks.nvdb` | [NVDB](https://api.vegdata.no/) — Norway's national road network (Statens vegvesen), link topology + address placements via REST (no credentials). The `streets` counterpart to `kartverket`'s addresses — see [`docs/providers/europe.md`](europe.md) | read |
| `streetworks.nwb` | [NWB (Nationaal Wegenbestand)](https://www.rijkswaterstaat.nl/) — Netherlands' national road network, every named/numbered road with real line geometry, WFS + bulk GeoPackage (no credentials). The `streets` counterpart to `bag`'s addresses — see [`docs/providers/europe.md`](europe.md) | read |
| `streetworks.bdtopo` | [BD TOPO](https://geoservices.ign.fr/bdtopo) — France's national road network (IGN), segments + named streets via WFS (no credentials). The `streets` counterpart to `ban`'s addresses — see [`docs/providers/europe.md`](europe.md) | read |
| `streetworks.datex2` | [DATEX II](https://datex2.eu/) — European roadworks parser (v3/v2/v1), with adapters for NDW (Netherlands, XML), National Highways (England SRN, JSON), Digitraffic (Finland, its own JSON schema; no credentials), IRCA/Vegagerðin (Iceland, XML over SOAP; no credentials), Bison Futé (France, XML v2; no credentials), DGT (Spain, excl. Catalonia & the Basque Country, XML v3; no credentials), Verkeerscentrum Vlaanderen (Belgium/Flanders only, XML v3, real EPSG:31370 coordinates; no credentials), Ponts et Chaussées (Luxembourg, XML v2.3; no credentials), the Road Infrastructure Agency/LIMA (Bulgaria, XML v2.3, licence unconfirmed; no credentials), and the Basque Country (Euskadi, XML **v1.0** — the oldest schema version here, licence explicitly absent; no credentials); Statens vegvesen (Norway, confirmed 2026-07-30 — real coordinates are mixed CRS within the feed, see [Recently confirmed](#recently-confirmed)); plus three **[Credentials wanted](#credentials-wanted)** scaffolds pending a tester — Trafikverket (Sweden, its own XML/JSON API, not DATEX), Vejdirektoratet (Denmark, XML v3.2), and ASFINAG (Austria, genuine DATEX II — even less confirmed than Vejdirektoratet, since neither the real pull URL nor the auth mechanism is stated anywhere public; a hoped-for keyless RSS shortcut was checked live and confirmed to carry no roadworks) | read |
| `streetworks.au` | Australia — a per-state cluster (no national statutory register exists, unlike Street Manager). Transport for NSW's Live Traffic Hazards API (New South Wales roadwork + major-event hazards, GeoJSON) and DTP's Planned Disruptions (Victoria, permit-derived, richer structured impact/recurrence fields) — both confirmed 2026-07-30, see [Recently confirmed](#recently-confirmed) — plus Main Roads WA's WebEOC Roadworks (Western Australia, ArcGIS REST, no credentials, shipped live-verified with a real fixture), QLDTraffic Events (Queensland, TMR, no credentials via a real shared public API key, one typed feed over every `event_type`, confirmed live 2026-08-01), ACT's Temporary Traffic Management (the only municipal/local-street AU coverage, no credentials, CC BY-SA 4.0) and Tasmania's Roadworks - State Roads (the only AU provider with real line geometry, no credentials, licence genuinely unconfirmed); Traffic SA / DIT Roadworks (South Australia, ArcGIS MapServer) is a **[Credentials wanted](#credentials-wanted)** scaffold, blocked on a token-gated query endpoint behind a geo-restricted host. Road Report NT (Northern Territory) is registered as a documented, honestly-unavailable scaffold — investigated and found to have no published REST/GeoJSON API at all (its real backend is an undocumented SignalR hub), so `RoadReportNtClient()` always raises `ProviderUnavailableError` rather than pretending to work | read |
| `streetworks.nzta` | [NZTA (Waka Kotahi) Highway Information](https://opendata-nzta.opendata.arcgis.com/) — New Zealand's national state-highway roadworks, ArcGIS REST (no credentials, shipped live-verified with a real fixture, confirmed 2026-08-02). Not the same body as LINZ — see [`docs/providers/new-zealand.md`](new-zealand.md) | read |
| `streetworks.gnaf` | [G-NAF](https://data.gov.au/data/dataset/geocoded-national-address-file-g-naf) + [National Roads](https://digital.atlas.gov.au/), over the Digital Atlas of Australia — Australia's national address register (15.9M addresses) and national road network (4.3M segments, genuinely comprehensive down to local roads/footpaths), both ArcGIS REST, no credentials, confirmed live 2026-08-02. A real correction to the source investigation: the commercial Geoscape Roads API isn't the only option — this whole-of-government platform re-publishes both under CC BY 4.0 | read |
| `streetworks.linz` | [LINZ (Toitū Te Whenua)](https://data.linz.govt.nz/) — New Zealand's national address register, NZ Addresses over a public ArcGIS mirror (no credentials, confirmed live, CC BY 4.0). Also carries the `streets` counterpart — NZ Addresses: Roads/Road Sections — as a **[Credentials wanted](#credentials-wanted)** scaffold (schema + a real attribute sample confirmed, blocked on a real LINZ Data Service API key) | read |
| `streetworks.idee` | [IDEE Transportes](https://servicios.idee.es/wfs-inspire/transportes) — Spain's national road-transport network, published by IGN over an INSPIRE WFS (no credentials, confirmed live 2026-08-15). A different agency and data class from this SDK's existing Spanish roadworks coverage (DGT, Consell de Mallorca, SCT). Resolves a real association problem found by a dedicated prior investigation — a `RoadLink` carries geometry but no name at all; this client fetches `Road` (name/codes plus references to its `RoadLink`s) and batch-resolves the geometry in one `RESOURCEID` request per page, treating a broken cross-reference as a confirmed, real, non-fatal case. Licence CC BY 4.0. See [`docs/providers/europe.md`](europe.md#idee-transportes-spain-national-road-network) | read |
| `streetworks.lmi` | [Landmælingar Íslands (IS 50V)](https://gis.lmi.is/geoserver/wfs) — Iceland's national road network (no credentials, confirmed live 2026-08-17, 58,266 real segments), this SDK's first Icelandic streets/gazetteer provider. 84.0% carry a real stated name (corrected live from a naive 99.98% `IS NOT NULL` check — most unnamed rows store a literal single space, not `NULL`). A sibling INSPIRE Transport Networks layer on the same deployment carries no name field at all; this native IS 50V layer was built instead. Licence CC BY 4.0. See [`docs/providers/iceland.md`](iceland.md#landmælingar-íslands-is-50v-road-network) | read |
| `streetworks.digiroad` | [Digiroad](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows) — Finland's real national road/street network, over Väylävirasto's open WFS (no credentials, confirmed live 2026-08-17, 3,363,654 real features). This SDK's first Finnish streets/gazetteer provider — Maanmittauslaitos' own Maastotietokanta was checked first but genuinely requires a self-service API key, so this genuinely keyless deployment was built instead. Real bilingual (Finnish/Swedish) names carried via `Name.language`, never merged. Real 3D geometry — `Z` preserved through reprojection, never defaulted to zero. Licence CC BY 4.0. See [`docs/providers/finland.md`](finland.md#digiroad-finland) | read |
| `streetworks.osni` | [OSNI Open Data - Gazetteer - Streetnames](https://www.opendatani.gov.uk/) — Northern Ireland's street-name gazetteer (no credentials, confirmed live 2026-08-16, 25,643 real features). Jurisdiction-distinct, never folded under UK. The documented ArcGIS REST MapServer endpoint is currently down (the whole `services.spatialni.gov.uk` domain redirects to a broken holding page), so this client uses the real bulk-download route instead. Uses the feed's own `X_Coord`/`Y_Coord` (Irish Grid, `EPSG:29902` — corrected from an initial `EPSG:29903` guess once a directly comparable NI government service confirmed `29902` live for the same coordinate family, since the endpoint that would confirm OSNI's own CRS live is still down) rather than the download's own reprojected WGS84 geometry. Carries a real, fully-unique `USRN` field, scoped to `OSNI` rather than presented as a GB-national identifier. Graded honestly as a name+point gazetteer — no ASD-style richness. Licence OGL v3.0. See [`docs/providers/uk.md`](uk.md#osni-streetnames-northern-ireland-gazetteer) | read |
| `streetworks.dfi_roads` | DfI Roads Highway Network centreline — Northern Ireland's real, maintained road-network centreline geometry (no credentials, confirmed live 2026-08-16, 71,596 real sections). The geometry counterpart to `osni`'s name+point gazetteer. The promoted CSV/XML "open data" downloads are genuinely attribute-only — zero geometry — so this client uses the real ArcGIS FeatureServer behind the public map viewer instead, found by tracing the viewer app's own item/web-map/layer chain. Not built on the shared `streetworks.arcgis` client, since its `f=geojson`-first behaviour would silently reproject this service's real Irish Grid coordinates without ever triggering its native-format fallback. CRS is `EPSG:29902`, read directly from this service's own `spatialReference` — the same code `osni`'s own label was corrected to match. Real, genuinely two-valued `ADOPTION_S` field (Adopted/Unadopted); defaults to adopted-only. Licence OGL v3.0. See [`docs/providers/uk.md`](uk.md#dfi-roads-highway-network-centreline-northern-ireland) | read |
| `streetworks.anncsu` | [ANNCSU](https://www.anncsu.gov.it/) — Italy's national street-name register (no credentials, confirmed live 2026-08-16, 1,219,990 real streets), jointly run by Agenzia delle Entrate and ISTAT since DPCM 12 May 2016. Streets only — the same registry's address/civic-number side is real but has only partial coordinate coverage, scoped out (see [pending candidates](pending.md)). Uses the real national bulk ZIP+CSV download, not the separate live point-query API, since the API only supports municipality+name lookup, not "everything." **No geometry exists anywhere in this resource** — every `Street` converts with `GeometryGrade.ABSENT`, the same documented state OS Open USRN already establishes, not a gap in this build. Two real, independently-stated municipality identifiers kept (the "Belfiore" code and ISTAT's own code). Licence CC BY 4.0. See [`docs/providers/italy.md`](italy.md#anncsu-national-street-name-register) | read |
| `streetworks.autobahn` | [Autobahn GmbH](https://verkehr.autobahn.de/) — Germany's national motorway roadworks, its own JSON REST API, not DATEX (no credentials; **licence unconfirmed**, see [`docs/providers/europe.md`](europe.md)) | read |
| `streetworks.gibraltar` | [Gibraltar Street Gazetteer](https://www.geoportal.gov.gi/) — 277 real named road segments over HM Government of Gibraltar's own GeoServer WFS (no credentials, confirmed live 2026-08-16), this SDK's first British Overseas Territory coverage. The INSPIRE-mandated `TN_RoadTransportNetwork_RoadLink` layer carries no name field at all — the native `gibgis:roads_lb_vw` layer underneath is the real, named one. Genuinely multi-part `MultiLineString` geometry on 54% of records, handled via `Coordinate.parts`, never a first-line-only shortcut. **Licence unconfirmed** — built on instruction, see module docstring. See [`docs/providers/gibraltar.md`](gibraltar.md) | read |
| `streetworks.sct` | [Servei Català de Trànsit](https://transit.gencat.cat/) — Catalonia's real-time road incidents, a flat WFS/GML feed, not DATEX or GeoJSON (no credentials; open licence, confirmed) — fills the larger of DGT's two documented exclusions | read |
| `streetworks.vialietuva` | [Via Lietuva](https://get.data.gov.lt/) — Lithuania's national roadworks, the open data.gov.lt route (CSV, CC BY 4.0; no credentials), not the agreement-gated RTTI NAP; own small parser, not DATEX — real LKS-94 (EPSG:3346) coordinates, not WGS84 | read |
| `streetworks.ogc` | German *state* roadworks — Hamburg, Brandenburg, Saxony (open geodata over OGC WFS/direct GeoJSON download; no credentials) — plus Consell de Mallorca's island roadworks (Spain, WFS, no credentials, licence unconfirmed); a reusable OGC-features fetch client underneath, not roadworks-specific. **New in 0.7.0 — interface provisional**, may change as the gazetteer work exercises it | read |
| `streetworks.berlin` | Berlin's VIZ traffic-information-centre feeds — Landesmeldestelle + Verkehrsredaktion (no credentials, confirmed live 2026-08-08), the largest remaining German gap, merged via a verified id join key since neither feed alone is complete (an early assumption corrected by live data). Comprehensive city-wide streets, not state-network-only like Hamburg/Brandenburg | read |
| `streetworks.madrid` | Ayuntamiento de Madrid's INFORMO municipal traffic-incidents feed (no credentials, confirmed live 2026-08-08, 217 real incidents), the gap DGT's national coverage never reaches (municipal streets). The first-tried URL was dead — Madrid relaunched its open-data portal in February 2026; this client targets the real current host. Filters on the source's own `es_obras` flag, not a free-text guess — real evidence excludes both lane closures and, surprisingly, asphalt-resurfacing operations | read |
| `streetworks.arcgis` | [Jersey RoadWorkx](https://roadworks.gov.je/) (roadworks) and its real [Jersey Street Gazetteer](https://roadworks.gov.je/) sibling, [Guernsey Street Gazetteer](https://roadworks.gov.gg/) (both streets, licence unconfirmed, confirmed live 2026-08-16), [National Road Network (Canada)](https://geo.statcan.gc.ca/) (streets, Open Government Licence – Canada, confirmed live 2026-08-16), [Monaghan County Council road network](https://services-eu1.arcgis.com/YDJmfAKmZVpOnK2Q/) (segments, Ireland, licence unconfirmed, confirmed live 2026-08-16), and [TIGERweb](https://tigerweb.geo.census.gov/) (US Census Bureau road segments, public domain) — a reusable ArcGIS REST Feature/Map Service client underneath, not provider-specific (no credentials for any) | read |
| `streetworks.wzdx` | [WZDx](https://github.com/usdot-jpo-ode/wzdx) — US roadworks ("work zones") via the WZDx standard — parser (v3.1–v4.2), generic feed client, and USDOT registry helper (no credentials) | read |
| `streetworks.nycdot` | [NYC DOT Street Construction Permits](https://data.cityofnewyork.us/Transportation/Street-Construction-Permits-2022-Present/tqtj-sjs8) — New York City's own street-opening permit register (no credentials, confirmed live 2026-08-02), this SDK's second `source_grade=register` source after Street Manager and the first in the US. Not WZDx — a separate authority, separate shape, the local follow-on to 511NY's state coverage. Built on `streetworks.socrata`, a generic Socrata (SODA) client shared with `streetworks.wzdx.registry` | read |
| `streetworks.chicagodot` | [CDOT Street Closures](https://data.cityofchicago.org/Transportation/Transportation-Department-Permits-Street-Closures/jdis-5sry) — Chicago's own street-closure permit register (no credentials, confirmed live 2026-08-03), this SDK's second US city permit register after NYC. Native WGS84 GeoJSON Point geometry (no WKT/CRS question, unlike NYC) — `iter_roadworks()` filters on real `worktype` values since the dataset's own pre-filter alone still mixes in block parties, festivals and filming | read |
| `streetworks.paris` | [Chantiers à Paris](https://opendata.paris.fr/explore/dataset/chantiers-a-paris/) — the City of Paris's own occupation-permit register for street/public-space worksites (no credentials, confirmed live 2026-08-06), this SDK's third municipal permit register and the first on OpenDataSoft (the French/EU Socrata-equivalent), built bespoke. Geometry already WGS84 despite the underlying Lambert 93 survey CRS — OpenDataSoft reprojects on the way out. Licence ODbL 1.0 (share-alike), confirmed | read |
| `streetworks.drivebc` | [DriveBC](https://api.open511.gov.bc.ca/) — British Columbia's own Open511 road-events feed (no credentials, confirmed live 2026-08-08, 246 real events), this SDK's first Canadian roadworks provider. Built bespoke, not a general Open511 parser — only one real roadworks-events Open511 jurisdiction was found live. Two real, mutually-exclusive schedule shapes (`intervals`/`recurring_schedules`) both handled. Licence OGL-BC, confirmed live | read |
| `streetworks.lisboa` | Câmara Municipal de Lisboa's Condicionamentos de Trânsito feed (no credentials, confirmed live 2026-08-09, 694 real features), this SDK's first Portugal provider at any level — sidesteps the still-credential-parked national IMT NAP entirely. Real endpoint found by reading the platform's own Angular app bundle, not documented anywhere public; the catalogue's stale 2023 metadata doesn't reflect the genuinely current live data (453/694 real features carry a 2026 case id). Evidence-based `motivo` filter (68% classify as roadworks). Licence CC BY 4.0, confirmed live | read |
| `streetworks.maproad` | [MapRoad Roadworks Licensing](https://maproadroadworkslicensing.ie/MRL/) (Ireland) — registered as a documented, honestly-unavailable scaffold. A real, government-catalogued permit register (national + local roads) with a real API, but Ireland's own catalogue metadata (API Available: Yes, Open Data: No, Data Sharing: Yes, Personal Data: Yes) describes a formal, GDPR-gated data-sharing arrangement, not a self-service key — no published read-path shape found, so `MapRoadClient()` always raises `ProviderUnavailableError` rather than pretending to work. See [`docs/providers/ireland.md`](ireland.md#ireland--maproad-roadworks-licensing-documented-unavailable) | read |
| `streetworks.greece` | Greece — registered as a documented, honestly-unavailable scaffold, the same tier as Road Report NT. Its real NAP ([nap.gov.gr](https://data.nap.gov.gr/)) carries only POI/sensor data (truck parking, VMS/VDS, weather, floating car data) — no roadworks or DATEX II Situation dataset at all, confirmed via its own real dataset titles. The portal is also currently unreachable (a real live 502). `GreeceClient()` always raises `ProviderUnavailableError` rather than guessing | read |
| `streetworks.trafficwatchni` | [TrafficWatchNI](https://trafficwatchni.com/) — Northern Ireland roadworks/incidents RSS (DfI TICC; no credentials) | read |
| `streetworks.trafficwales` | [Traffic Wales](https://traffic.wales/) — Welsh motorway/trunk roadworks RSS, EN + CY (no credentials) | read |
| `streetworks.tfl` | [Transport for London Road Disruption](https://api.tfl.gov.uk/) — London's strategic-network live disruption feed (no credentials, confirmed live 2026-08-15, 118 real rows, 116 real Works rows), the accessible complement to Street Manager's own all-borough permit register — do-not-dedupe, a works on a TLRN red route can appear in both. Genuinely keyless; `app_key` is an optional rate-limit courtesy only. `category == "Works"` is a real, clean filter. Geometry states its own CRS explicitly (`EPSG:4326`) on every record. `corridorIds` is genuinely incomplete (44% of real Works rows) so it's never promoted to `street_ref`. `status` was `"Active"` on every real row checked, driving real VERIFIED date-confidence grading. Licence: TfL's own OGL v2.0-with-amendments terms, confirmed live, requiring three attribution statements | read |
| `streetworks.cciss` | [CCISS](https://www.cciss.it/) — Italy's real-time traffic bulletin RSS (no credentials, confirmed live 2026-08-03), reached via the keyless RSS route rather than the registration-gated DATEX II one. Confirmed as Italy's own official RTTI/SRTI National Access Point per the European Commission's own October 2025 NAP list | read |
| `streetworks.roma` | Roma Capitale's "Roma si trasforma" civic-interventions tracker (no credentials, confirmed live 2026-08-09, 1215 real records), filtered to real in-progress street/infrastructure work — a thin 5.7% slice of a general capital-projects feed, not a dedicated roadworks register. The most obvious candidate ArcGIS source doesn't exist; the real portal was found by reading its own JS bundle. Corrects a real coordinate-field bug in the source (`lon`/`lat` swapped). No dates in the schema — `date_confidence` always unknown. Licence unconfirmed | read |
| `streetworks.milano` | Comune di Milano's "Avvisi di manomissione" excavation-notice register (no credentials, confirmed live 2026-08-14, 139 real feature rows), this SDK's second Italy municipal coverage — resolves the "populous cities" pivot's own open question left by Rome falling off-board. Neither the Lombardy Socrata portal nor the first-guessed "cantieri" naming holds up; the real dataset was found via Milan's own CKAN portal under the real Italian legal term. Direct GeoJSON download, no API/WFS/key — a real quirk: the URL embeds a daily timestamp in its filename but CKAN resolves purely by resource UUID, so a stable non-timestamped URL is used. Real geometry is `Point`, genuine native WGS84, flipped to `(lat, lon)`. One `Works` per feature (protocol numbers are unique) — a utility-operator excavation register (water/electricity/gas/sewage/district-heating), not the city's own separate road-maintenance programme. Licence: CC-BY, confirmed live | read |
| `streetworks.canton_zurich` | Kanton Zürich's "Baustellen Kantonsstrassen" cantonal-road works register (no credentials, confirmed live 2026-08-14, 66 real feature rows), this SDK's first Swiss coverage. Found via opendata.swiss's own CKAN catalogue, a real GeoServer WFS run by the canton's Tiefbauamt. Two real layers carry the same 66 closures, not disjoint data — the richer real `Polygon` detail layer is used. `EPSG:2056` (Swiss LV95), stored unswapped. No unique identifier field exists anywhere in the schema — a composite key is 65/66 unique, but the one collision is two genuinely distinct real closures sharing every composite field, so `reference` stays `None` rather than a fabricated key. A genuinely informative two-value `status_baustelle` field (`aktiv`/`zukünftig`) drives real VERIFIED/ESTIMATED date-confidence grading. Deliberately not deduped against the separate Stadt Zürich coverage. Licence: opendata.swiss "Open use" — no attribution required, confirmed live via the resource's own `rights` field (its CKAN `license_id` is empty) | read |
| `streetworks.zurich` | City of Zürich's "Aktuelle Tiefbauprojekte im öffentlichen Grund" civil-engineering-projects register (no credentials, confirmed live 2026-08-14, 140 real feature rows), this SDK's second Swiss coverage. Found via the same opendata.swiss catalogue entry as the canton, the city's own GeoServer WFS — two real quirks confirmed live: only `application/vnd.geo+json` works (not the shared client's default), and the server 500s on WFS 2.0.0's plural `TYPENAMES` alone, needing the real working 1.1.0 `TYPENAME` sent alongside it. CRS is genuinely WGS84, confirmed empirically (real coordinates match the layer's own stated bounding box) despite an empty `DefaultSRS` capabilities tag. `baunr` (project number) is a real, 100%-unique identifier, unlike the canton's dataset. `kategorie` is a constant `"Grössere Baustelle"` — this feed is already curated to significant projects. Deliberately not deduped against the separate Kanton Zürich coverage. Licence: the same opendata.swiss "Open use" tier, confirmed live | read |
| `streetworks.copenhagen` | Københavns Kommune's "Gravetilladelser" excavation-permit register (no credentials, confirmed live 2026-08-10, 2240 real feature rows), this SDK's first Nordic coverage. The first-guessed dataset name and ArcGIS/OGC Features backend don't match reality — the real source is a WFS 1.0.0 GetFeature endpoint. Real geometry mixes Point/LineString/Polygon, with the same permit recorded once per shape; deduped by case number (`sagsnr`), preferring LineString over Point, Polygon never used. Licence: CC-BY-4.0, confirmed live | read |
| `streetworks.oslo` | Oslo kommune's "SøkSys" digging/work-permit case system (no credentials, confirmed live 2026-08-10, 1354 real feature rows), this SDK's second Nordic coverage. Neither early-guessed backend (Origo/Bymiljøetaten, or NVDB) matches reality — the real source, found by reading the public map's own JS bundle, is a permit system run by Geomatikk. Real coordinates are projected `EPSG:25832` (UTM32N), stored unswapped. Deduped by exact row id (drops real tiling-query duplicates), then grouped by activity into one `Works` with several `WorksSite`s where a permit genuinely spans distinct real sub-areas. Licence unconfirmed | read |
| `streetworks.helsinki` | City of Helsinki's "Kaivuilmoitus" (excavation-notification) register (no credentials, confirmed live 2026-08-13, 3431 real feature rows), this SDK's third Nordic coverage — resolves an earlier unconfirmed claim that a Helsinki roadworks dataset might not exist. Found via Helsinki Region Infoshare's CKAN catalogue, served from a live GeoServer WFS. Real geometry is `MultiPolygon`; grouped by `hakemustunnus` (application reference) into one `Works` with several `WorksSite`s where a notification genuinely spans distinct real sub-areas (up to 164 real rows under one reference). Real coordinates are projected `EPSG:3879` (ETRS-GK25FIN), stored unswapped even though the WFS can reproject to WGS84 on request. A genuinely informative two-value `status` field (`Käynnissä`/`Tuleva`) drives real VERIFIED/ESTIMATED date-confidence grading. Licence: CC-BY-4.0, confirmed live | read |
| `streetworks.vienna` | Stadt Wien's "verkehrswirksame Baustellen" traffic-relevant roadworks/closures register (no credentials, confirmed live 2026-08-14, 111 real feature rows), this SDK's second Austria coverage. The real data lives on Vienna's own GeoServer WFS, not the first-candidate `data.gv.at` URL (a JS-rendered SPA with no reachable content). Two real layers (`Point`, `LineString`) are genuinely disjoint, not the same data twice — both fetched and combined. CRS is `EPSG:31256` (MGI/Austria GK East), cross-verified via a WGS84 reprojection. A real correction to the initial framing: `ANTRAGSTELLER` shows genuine third-party applicants (utilities, the transit operator, a private developer), confirming this is a permit register — `source_grade=REGISTER`, not the initially assumed operator. Licence: Stadt Wien's stated general CC BY 4.0 policy, not per-dataset-confirmed | read |
| `streetworks.stockholm` | Stockholm's Trafikkontoret geodata WFS — a **[Credentials wanted](#credentials-wanted)** Phase 0 scaffold, worse-off than any other row here: every real surface tested (WFS/WMS `GetCapabilities`) 401s before any dataset name, layer, or field is ever revealed. Confirms a real risk flagged early on across the Nordic capitals, rather than disproving it — a promising "regional roadworks coordination map" lead traces back to the already credential-parked national Trafikverket system, not a separate Stockholm dataset. Whether a real roadworks dataset exists on this platform at all is genuinely unresolved | read |
| `streetworks.police` | [UK Police](https://data.police.uk/docs/) — street-level crime, as a worker-safety signal, not a street-works feed (no credentials) | read |
| `streetworks.common` | Canonical cross-provider works types (`Works`, `WorksSite`, `WorksPlanning`, `Coordinate`, `Notice`) with per-provider converters, alongside every native interface above | — |

## Underground assets (model only)

A different data class from everything above — buried utility assets
(pipes, cables, ducts, chambers), not roadworks and not a street
gazetteer — kept out of the module table on purpose, since that table's
"read"/"write" columns imply something queryable, and there is nothing to
query here yet.

| Module | Status | Notes |
|---|---|---|
| `streetworks.nuar` | **Testing-only reference model — not a live provider, not registered, not counted in [Coverage](#coverage)** | [NUAR (National Underground Asset Register)](https://www.nuar.uk/) — no consumption API exists yet: OS/GDS opened a synthetic-data Sandbox on 2026-08-07 to test access routes, but endpoints/auth/wire format are unpublished. The *data model*, however, is already public — the NUAR Harmonised Data Model (OGL v3.0, a UK profile of the approved OGC MUDDI standard) — so `UndergroundAsset` exists now, derived from that published schema, ready for a connector once the transport lands. `NUAR_CONNECTOR_LIVE` is `False`; importing the package warns. See [`docs/providers/pending.md`](pending.md) for the fuller writeup. |

## Status

Early alpha. **Authentication and read/consume access are verified against
the real systems for all providers except those in [Credentials
wanted](#credentials-wanted), below, plus Road Report NT, MapRoad
Roadworks Licensing, and Greece (none has a usable interface a credential
would unlock — see below)** (Norway/NSW/Victoria joined the
verified list on 2026-07-30 — see [Recently confirmed](#recently-confirmed)
for what real data changed): Street Manager (SANDBOX), Geoplace
DataVIA (live — including a real feature query), D-TRO (production token +
events search), the Open Data SNS parsing/verification pipeline, SRWR
Open Data (parsed against real published daily and monthly extracts),
OS Open USRN (Downloads API + GeoPackage reader), UK Police (live
`safety_signal()` and category queries against `data.police.uk`), WZDx
(parsed against 12 live agency feeds spanning v3.1–v4.2), Digitraffic/
Finland, IRCA/Iceland, Bison Futé/France, DGT/Spain, Belgium/Flanders,
Luxembourg, Bulgaria, Euskadi/Basque Country, Autobahn GmbH/Germany,
Via Lietuva/Lithuania, Consell de Mallorca, Servei Català de Trànsit,
the German states Hamburg, Brandenburg and Saxony (all parsed against
real live feeds), BAN/France (search, reverse and bulk-file parsing
all verified against `data.geopf.fr`/`adresse.data.gouv.fr`), and
BAG/Netherlands (Locatieserver search/suggest/reverse/lookup and the full
7.8 GB national GeoPackage, downloaded and read in full, not sampled), and
Kartverket/Norway (address API, SSR place-names API and bulk CSV verified
against `ws.geonorge.no`/`nedlasting.geonorge.no`, including a full-scale
`adressekode` over-merge check across two whole municipalities), and
NWB/Netherlands (WFS queries, counts and the two-hop Atom feed verified
against `geo.rijkswaterstaat.nl`/`service.pdok.nl`, including a real
municipality-scale `bag_orl` over-merge check and the live discovery that
PDOK's WFS silently ignores `CQL_FILTER`), BD TOPO/France (WFS queries
and counts verified against `data.geopf.fr`, including a real commune-scale
`identifiant_voie_ban` over-merge check on two whole communes, mainland
and overseas - the bulk GeoPackage route was investigated but not found
to be automatable), and NVDB/Norway (`/vegnett` and
`/vegobjekter` verified against `nvdbapiles.atlas.vegvesen.no`, including
the live confirmation - both by direct testing and in the API's own
documentation - that no credentials are required for reads, unlike
Statens vegvesen's own DATEX roadworks feed).

**Autobahn GmbH's licence is unconfirmed** - checked four independent
sources (see [`docs/providers/europe.md`](europe.md#autobahn-gmbh-germany-national-motorways)
for what was checked) and none state reuse/redistribution terms. Shipped
anyway, flagged deliberately rather than silently assumed open - confirm
your own rights before redistributing this data.

### Credentials wanted

Six providers ship as **scaffolds, not verified builds** — five
roadworks, one streets: implemented to each service's own documented/
confirmed API shape and covered by mocked tests, but never run against a
real authenticated response — each is genuinely blocked on access this
project doesn't have, not on unfinished code. **If you have access to any
of these, running the smoke test (`python scripts/smoke_test.py`) and
reporting back — ideally with one real trimmed record — is a genuinely
valuable contribution**, the same way a tester's real credentials
confirmed Norway/NSW/Victoria on 2026-07-30 (see
[Recently confirmed](#recently-confirmed), below). Every roadworks
module also warns at import time (`UserWarning`) with the same pointer;
LINZ's gate is per-method instead (`iter_roads()`/`iter_road_sections()`
raise a clear `ValueError` without a key — the sibling `iter_addresses()`
on the same client is already verified). Excluded from the
verified-providers claim above until confirmed. Drafted issue text lives
in [docs/credentials-wanted-issues.md](../credentials-wanted-issues.md).

| Provider | Confirmed | Pending | Credential | How to get it | Issue |
|---|---|---|---|---|---|
| Trafikverket (`streetworks.datex2.trafikverket`, Sweden) | Endpoint, `Situation` object name, and schema version `1.5` — all live, via a deliberate invalid-key probe returning a real structured 401 | The authenticated data pull itself; the real `MessageType`/`MessageCode` value that means roadworks specifically (unconfirmed in every source checked — `iter_roadworks()` honestly returns nothing until this is confirmed, see module docstring) | API key (not Basic Auth) | Free, **self-service**: [data.trafikverket.se](https://data.trafikverket.se/) or via [Trafiklab](https://www.trafiklab.se/api/other-apis/trafikverket/) — form, accept licence, verify email, key issued immediately | [help wanted](https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) |
| Vejdirektoratet (`streetworks.datex2.vejdirektoratet`, Denmark) | Genuine DATEX II 3.2, with `ConstructionWorks`/`MaintenanceWorks` and their full `constructionWorkType`/`roadMaintenanceType` enumerations stated explicitly in Vejdirektoratet's own protocol spec; the open metadata catalogue re-confirmed live (196 datasets, the roadworks one CC BY 4.0-licensed, no auth) | The authenticated REST pull itself; whether the `trafikmeldinger` response really nests as a list of independent DATEX XML strings, per the protocol doc | HTTP Basic Auth username/password **and** the actual pull URL — both issued per-dataset at registration, no public data URL exists | Free; register via [Dataudveksleren](https://du-portal-ui.dataudveksler.app.vd.dk/) | [help wanted](https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) |
| ASFINAG (`streetworks.datex2.austria`, Austria) — **worse-off than Vejdirektoratet: even the auth mechanism is unknown, not just the credential** | A real DATEX II Situations/SituationRecords roadworks dataset (`Baustellen`/`Instandhaltungsarbeiten`/`Sanierungen`), confirmed live from ASFINAG's own official dataset page; a hoped-for keyless RSS shortcut checked live and confirmed to carry only unplanned/safety events, not roadworks; CC-BY-4.0 licence with real supplementary conditions confirmed live | The real pull URL and the auth scheme itself (API key? Basic? Bearer? — not stated anywhere public, checked the dataset page, licence page, and the registration portal's own JS bundle); whether the response is a bare DATEX document or wrapped in an envelope | Unknown — issued at registration | ASFINAG Content Portal (`contentportal.asfinag.at`) — reachable, registration flow not walked through | [help wanted](https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) |
| Traffic SA (`streetworks.au.sa`, South Australia) — **blocked on two gates, not one** | The real field list, native SR, and pagination capabilities — all confirmed live from the layer's own public `?f=json` metadata; `iter_roadworks()` deliberately returns the full, unfiltered mix rather than guess a `REC_TYPE` filter with zero evidence | **No real feature has ever been retrieved**: the query endpoint 400s without an ArcGIS token, and whether that token is even self-service is itself unconfirmed (the token host returned a CloudFront 403 too); separately, `maps.sa.gov.au` geo-blocks some countries' network egress outright. Also open: whether `ROAD_NO`/`GIS_LINK_ID` are populated and genuinely join to a road register — a potential first for this AU cluster | ArcGIS token (self-service vs. gated: unresolved) | `location.sa.gov.au/arcgis/tokens/` — from a network egress the CloudFront restriction doesn't block | [help wanted](https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) |
| LINZ NZ Addresses: Roads/Road Sections (`streetworks.linz`, New Zealand) — **streets, not roadworks; the sibling `iter_addresses()` on the same client is already verified** | The real field lists and one real sample of attribute values for both layers, from LINZ's own public Koordinates metadata API (no key needed for this part); the real WFS URL shape (API key embedded in the URL path, confirmed from the layer's own `/services/` listing) | The authenticated WFS pull itself; whether `startIndex`/`count` pagination is genuinely honoured; **whether `road_id` genuinely cross-references to NZ Addresses' own `road_id`** — the single most interesting open question in this SDK's New Zealand cluster | LINZ Data Service (LDS) API key | Free, **self-service**: register at [data.linz.govt.nz](https://data.linz.govt.nz/) and create a "Data access only" key | [help wanted](https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) |
| Stockholm (`streetworks.stockholm`, Trafikkontoret) — **worse-off than every other row here: no schema of any kind confirmed** | Only that the platform exists and genuinely requires a key — real `HTTP 401` (`text/plain`, *"You must provide a valid key to consume this API."*) confirmed on both WFS and WMS `GetCapabilities` | Everything: no dataset/layer name, no field, no confirmed auth parameter placement (the one real example — a documented Parking-API query using `apiKey=` — is used here but unconfirmed for WFS specifically), and **whether a roadworks (`vägarbete`) dataset exists on this platform at all** — confirms a real risk flagged early across the Nordic capitals, rather than disproving it | Trafikkontoret API key | Registration path unconfirmed — the one guessed URL 404'd; try `api.it.tk@stockholm.se` or navigate from [openstreetgs.stockholm.se/home/](https://openstreetgs.stockholm.se/home/) | [help wanted](https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) |

**Three further, genuinely different cases: Road Report NT, MapRoad
Roadworks Licensing, and Greece aren't access-blocked in the usual
sense.** Kept in a separate table rather than folded into the one
above, since "Credential"/"How to get it" don't quite apply the way
they do for the other four:

| Provider | Confirmed | Pending | Credential | How to get it | Issue |
|---|---|---|---|---|---|
| Road Report NT (`streetworks.au.nt`, Northern Territory) — **no published interface, not a credential gate** | The real frontend's backend is a SignalR real-time hub (`"roadsReportingHub"`, a real hub method `"GetAllMajorRoadObstructions"`) — confirmed live by reading the site's own minified Angular bundle directly | Whether **any** documented REST/GeoJSON API exists for this data at all — `RoadReportNtClient()` always raises `ProviderUnavailableError` rather than build a client against reverse-engineered hub internals; see module docstring for why | N/A — no credential would fix this | N/A — the National Freight Data Hub's aggregate feed is a possible alternative route, unverified whether it carries real NT records | [help wanted](https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) |
| MapRoad Roadworks Licensing (`streetworks.maproad`, Ireland) — **a real API exists, but not for data consumers** | Ireland's own catalogue confirms a real, government-run API (`API Available: Yes`) covering both national and local roadworks licences — TII's own DATEX II feed was checked first and confirmed to carry no roadworks data at all | Whether a read-only path exists for a party who isn't a licence applicant or road authority — the same catalogue states `Open Data: No`, `Data Sharing: Yes`, `Personal Data: Yes` together, describing a formal GDPR-gated arrangement, not a self-service key; `MapRoadClient()` always raises `ProviderUnavailableError` rather than guess at an unpublished contract | N/A — no credential would fix this | Formal data-sharing agreement via `contact@rmo.ie`, not self-service | [help wanted](https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) |
| Greece (`streetworks.greece`) — **no roadworks source exists at all, and the NAP is currently down** | Greece's real NAP (`nap.gov.gr`) is confirmed as the official MMTIS/RTTI/SRTI/SSTP access point, and its own real dataset titles (checked directly) are all POI/sensor data — truck parking, KTEL timetables, floating car data, toll-operator VMS/VDS/weather | Whether any Greek source (national or toll-operator) ever publishes a roadworks/Situation dataset — `GreeceClient()` always raises `ProviderUnavailableError` rather than guess; the portal itself also returns a real live 502 right now, independent of the "no roadworks dataset" finding | N/A — no credential would fix this | N/A — no known route; a toll-operator feed, if one ever appears, would only be motorway-concession-only | [help wanted](https://github.com/KFergusonUK/StreetWorks-SDK/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) |

### Recently confirmed

Three former Credentials-wanted providers were confirmed on **2026-07-30**
by a tester running `scripts/smoke_test.py` with their own real
credentials — exactly the contribution the section above asks for. Kept
here as a record of what real data changed, not just moved silently into
the verified-providers claim above:

- **Statens vegvesen (Norway)** — 844 real roadworks situations, genuine
  DATEX II v3, real Norwegian-language comments. Real coordinates are
  genuinely mixed CRS within the same feed (~76% UTM zone 33N/`EPSG:25833`,
  ~24% WGS84) — now resolved per-record via `streetworks.common.from_vegvesen`
  and the new shared `streetworks.common._crs.resolve_coordinate_crs`
  helper (declared/inferred/corrected by real value range, axis order by
  magnitude, no silent reprojection); see the module docstring for the
  full finding and fix. No IP allow-listing was needed, resolving an open
  question.
- **TfNSW Live Traffic (NSW)** — found and fixed one real bug: the
  correct endpoint paths are `roadwork/open`-style, not
  `roadwork-open.json`-style (Phase 1 had followed the Developer Guide's
  own documented file-naming table over the source investigation's
  paraphrase — the guide turned out to be wrong about its own gateway).
  363 real roadwork + 19 real major-event features confirmed, including
  a real ~1.7% local-road minority and a real ~1.4% ferry-hazard impurity
  in the roadwork-only endpoint.
- **DTP Planned Disruptions (Victoria)** — found and fixed one real
  design mistake in this SDK's own converter: a GeometryCollection's
  LineString can span an entire route (~150km in one real example, not
  a worksite's own extent), so only the Point is used now. Confirmed
  coordinate order, timestamp format (naive ISO-8601, no UTC offset —
  genuinely unusual), and that `KeyID` really is the correct auth header,
  not the OpenAPI spec's own advertised scheme.

See each module's own docstring for the full detail behind every claim
above.
