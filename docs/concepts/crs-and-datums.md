# CRS and datum discipline

> Assembled from README.md (phase one, lossless restructure — see
> `docs/migration-mapping.md`). `Coordinate.crs` is always stated, never
> assumed — this page collects every provider's real, confirmed CRS
> finding in one place. Full per-provider context lives in
> [`docs/providers/`](../providers/index.md); this is the CRS-specific
> cross-cutting slice of it, not a duplicate.

**The standing rule**, stated at several of its real points of application
(verbatim; see [`docs/concepts/data-integrity.md`](data-integrity.md) for
the full "never silently reproject" collection): a non-4326 CRS is never
silently reprojected, only carried through and labelled explicitly on
`Coordinate.crs`.

## Non-WGS84 roadworks/works providers, confirmed live

- **Street Manager / DataVIA** (England) — British National Grid (`EPSG:27700`), the UK's native register CRS throughout.
- **Belgium (Verkeerscentrum Vlaanderen)** — Belgian Lambert 72 (`EPSG:31370`). *"every real coordinate in this feed is Belgian Lambert 72... confirmed from the feed's own `srsName` attribute and from the coordinate values themselves (the source XML still calls the fields `<latitude>`/`<longitude>`, which is genuinely misleading taken at face value)."*
- **Via Lietuva (Lithuania)** — Lithuanian national grid, LKS-94 (`EPSG:3346`), **with reversed WKT axis order**: *"`POINT (6061836 567621)` states `(Northing, Easting)`, not `(Easting, Northing)`, confirmed from real value ranges."*
- **German state roadworks — Saxony** — `EPSG:25833` (UTM33N); *"genuinely has no WGS84 source anywhere... Rather than park a source this rich... over an axis-order technicality, Saxony ships with its real CRS carried through and labelled explicitly."* (Hamburg and Brandenburg are both confirmed WGS84 over WFS.)
- **Jersey RoadWorkx** — `EPSG:3109` ("ETRS89 / Jersey Transverse Mercator") — *"confirmed live via a sibling service on the same deployment that states the `wkid` directly, cross-checked byte-for-byte against EPSG:3109's own published WKT parameters; `outSR` is **not** honoured by this service."*
- **Main Roads WA** — native Web Mercator on the source layer; `outSR=4326` confirmed honoured live, but a runtime guard is built anyway (a closed-form spherical-Mercator inverse, deliberately **not** `pyproj`) since GeoJSON strips any per-feature CRS statement and a sibling ArcGIS deployment (Jersey's) is confirmed to silently ignore `outSR`.
- **QLDTraffic (Queensland)** — `EPSG:7844` (GDA2020), *"confirmed live on every single feature via its own embedded GeoJSON `crs` member, never assumed or silently relabelled `EPSG:4326`."*
- **Tasmania (Roadworks - State Roads)** — GDA94/MGA zone 55, genuinely different from WA/SA's Web Mercator; `outSR=4326` confirmed honoured live, but this module *"deliberately does not reuse WA/SA's closed-form Web Mercator reprojection guard, since applying that formula to a different projection would silently produce wrong, not just imprecise, coordinates."*
- **NYC DOT** — NAD83 / New York Long Island (`EPSG:2263`), *"inferred from real coordinate-value-range evidence and the near-universal NYC city-agency GIS convention, not an explicitly stated dataset SRID, and never silently reprojected to WGS84."*
- **Consell de Mallorca** — ETRS89/UTM31N (`EPSG:25831`); the server can reproject to WGS84 on request (tested, genuinely correct) but the native CRS is requested and labelled instead, per the standing policy.
- **G-NAF & National Roads (Australia)** — native SR `EPSG:7844` (GDA2020), `outSR=4326` confirmed honoured live.

## Compound / 3D CRS

- **NVDB (Norway)** — `EPSG:5973`, *not* the design brief's expected plain `EPSG:25833`: *"a compound 3D CRS ('ETRS89-NOR / UTM zone 33N + NN2000 height'), not a plain 2D UTM33 one — every real geometry is a genuine `LINESTRING Z` with real altitude values, matching the CRS exactly."* Z is preserved, never defaulted to zero — see [`docs/concepts/data-model.md`](data-model.md).

## Mixed CRS within a single feed

- **Statens vegvesen (Norway, DATEX II)** — *"Real coordinates are genuinely mixed CRS within the same feed (~76% UTM zone 33N/`EPSG:25833`, ~24% WGS84) — now resolved per-record via `streetworks.common.from_vegvesen` and the new shared `streetworks.common._crs.resolve_coordinate_crs` helper (declared/inferred/corrected by real value range, axis order by magnitude, no silent reprojection)."*

## Confirmed WGS84 despite a non-WGS84 underlying survey CRS

- **Paris Chantiers** — *"Geometry is already WGS84, despite the underlying survey CRS being Lambert 93... OpenDataSoft reprojects on the way out, so no CRS transform was needed here."*
- **Berlin (VIZ)** — geometry served in WGS84 degrees on both feeds despite the underlying Paris/Berlin data itself being surveyed non-WGS84 upstream (OCIT/GeoJSON conversion reprojects server-side).
- **BD TOPO (France)** — *"CRS is also route-specific here: the WFS declares WGS84 on every real response, mainland and overseas alike; IGN's documentation states the (unreachable) bulk file uses Lambert-93 — plausible, not independently re-confirmed."*

## Axis order — checked, not assumed, per source

- **WZDx** — always `(longitude, latitude)` GeoJSON order — *"the reverse of DATEX's `(latitude, longitude)`."*
- **Autobahn GmbH** — *"Native axis order is genuinely reversed within one record: the `coordinate` field is `(lat, long)`, `geometry.coordinates` is GeoJSON `(lon, lat)` — both native in `Roadworks`, flipped explicitly in `from_autobahn`, same as WZDx."*
- **Via Lietuva** — WKT axis order reversed from the usual convention (see above).
- **German state roadworks** — *"WFS 2.0/EPSG:4326 can come back lat/lon (the reverse of GeoJSON's mandated lon/lat), the same trap the DataVIA WMS work already documented. Every real coordinate from Hamburg and Brandenburg falls inside Germany's true lon/lat bounds... confirmed in a mandatory test per state, not just eyeballed once."*
- **DataVIA (WMS)** — *"Coordinates default to British National Grid (EPSG:27700), which sidesteps the WMS 1.3.0 lat/lon axis-order trap that bites with EPSG:4326."*

## Gazetteer (address/street) providers

- **BAG (Netherlands)** / **NWB (Netherlands)** — `EPSG:28992`, confirmed matching between the two (NWB is the `streets` counterpart to BAG's `addresses`).
- **BAN (France)** — WGS84 (`lon`/`lat` stated directly on bulk/geocoding records).
- **BD TOPO (France)** — see above (route-specific).
- **Kartverket (Norway)** — SSR's default output CRS confirmed the *same* `EPSG:4258` as the address API — *"the brief's own CRS hint about the SSR API needing separate verification from the address API turned out backwards... only its query-input flexibility differs."*
- **TIGERweb (US)** — a statistical/cartographic product; CRS handling inherited from the shared `ArcGISFeatureClient` guard.
