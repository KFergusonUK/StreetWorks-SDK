# Germany streets gazetteer — investigation notes

Investigation only, per `germany-streets-brief.md`. Findings for steps
1 and 2 below are from real, live requests made 2026-08-16. Status:
**federal source ruled out, address layer ruled out, state fan-out
started 2026-08-20 — Hamburg built (`streetworks.hamburg`), Brandenburg
built (`streetworks.brandenburg`), Saxony built (`streetworks.geosn`),
Berlin genuinely blocked** — see `docs/providers/pending.md` for the
current summary.

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

## Verify-first step 3 — state fan-out (started 2026-08-20)

The brief's own fallback path — checking whether Hamburg, Brandenburg,
Saxony, and Berlin (the four states already touched for roadworks via
`streetworks.ogc.germany`/`streetworks.berlin`) expose a genuine
named-street layer via their own WFS/OGC API Features.

**Berlin — checked first, genuinely blocked, not ruled out.** Berlin's
own GDI WFS host (`gdi.berlin.de`, serving every real Berlin state
geodata WFS - addresses, street network, everything) is confirmed live
to be down for maintenance across every real path tried (a generic
German "Wartungsarbeiten" page, no ETA stated), confirmed via multiple
different guessed service paths and repeated retries over several
seconds, all returning the identical maintenance page. This lines up
with a real, separately-confirmed fact: Berlin's older FIS-Broker
system was fully shut down 1 December 2025 in favour of new
open-source infrastructure, so this outage plausibly reflects an
active migration rather than a permanent closure - but that couldn't
be confirmed from outside. Two real candidate datasets were found on
`daten.berlin.de` before hitting the wall (`Adressen Berlin` and
`Detailnetz Straßenabschnitte`, both real WFS entries) but neither is
checkable while the backing host is down. Revisit later - this is a
real, live, currently-open lead, not a dead end.

**Hamburg — checked, built.** Hamburg's own joint address/street
gazetteer, "Zentraler AdressService Hamburg" (GAGES, run by the
Statistisches Amt für Hamburg und Schleswig-Holstein plus the
Landesbetrieb Geoinformation und Vermessung), is real, live, and
keyless via a modern OGC API Features service
(`qs-api.hamburg.de/datasets/v1/gages_vereinfacht`, found via the
dataset's own catalogue page rather than the archived FIS-Broker-era
WFS the catalogue still lists as a legacy snapshot). 9,639 real
Hamburg street records, 100% carrying a real name, real Point geometry
genuinely reprojected server-side to WGS84 by default. Shipped as
`streetworks.hamburg.HamburgStreetsClient` / `from_hamburg_street` -
see `docs/providers/europe.md#zentraler-adressservice-hamburg-gages`
for the full write-up.

**Brandenburg — checked, built.** LGB's own "WFS BB-BE Gazetteer"
(`isk.geobasis-bb.de/ows/gazetteer_wfs`, found via Brandenburg's own
geoportal metadata record) is real, live, and keyless - 52,902 real
street records, 100% carrying a real name. A real, confirmed GML-only
WFS (no JSON output format exists - a real `outputFormat=application/
json` request was rejected with a genuine `400`), parsed directly via
the standard library's own `xml.etree.ElementTree` rather than the
shared JSON-first OGC client. `administrative_area` is reconstructed
from two real, independently-stated fields (`ortsnamePost` +
`zusatzOrtsname`), confirmed to match the record's own
`gemeindename_normalisiert`. Only real geometry stated is a `Polygon`
(areal extent) - `GeometryGrade.ABSENT` on every `Street`, the real
polygon preserved unmodified on `.raw`. A real, live-confirmed,
non-exhaustive Berlin presence was also found (8/500 real sample rows
carry Berlin's own state code, sourced from Geoportal Berlin's own
Amtliche Hauskoordinaten) - not claimed as exhaustive Berlin coverage,
since this build is scoped and documented as Brandenburg's own
provider. Shipped as `streetworks.brandenburg.BrandenburgStreetsClient`
/ `from_brandenburg_street` - see
`docs/providers/europe.md#wfs-bb-be-gazetteer-brandenburg` for the full
write-up.

**Saxony — checked, built.** Unlike Hamburg and Brandenburg, Saxony
turns out not to run a dedicated Gazetteer/DOG-style WFS at all - five
real, plausibly-named endpoint guesses
(`geodienste.sachsen.de/aaa/public_gazetteer/wfs`, `public_dog/wfs`,
`public_alkis_gazetteer/wfs`, `gazetteer/wfs`, `public_strassen/wfs`)
all returned a genuine `404`, and Saxony's own live ALKIS WFS abstract
text confirms its feature types are limited to
`Flurstücke, Gebäude, Tatsächliche Nutzungen, Verwaltungseinheiten,
Katasterbezirke` - no street or address feature type at all. The real
working path instead is GeoSN's own `Downloadbereich Hauskoordinaten`
bulk export - a real statewide address-point CSV (inside a ~51 MB ZIP,
the largest single download in this SDK's German-state cluster),
990,090 real address rows, deduplicated client-side in
`GeoSNStreetsClient.iter_streets()` to 42,824 real distinct
`(gmdschl, strschl)` street combinations, 100% carrying a real name.
Geometry is a real address point, reprojected client-side from
ETRS89/UTM zone 33N (`EPSG:25833`, confirmed standard `(Easting,
Northing)` order, no swap needed - cross-validated against a real
Frohburg address). `administrative_area` uses the real `gmd`
municipality name directly - no reconstruction needed, unlike
Brandenburg's own two-field join. Shipped as
`streetworks.geosn.GeoSNStreetsClient` / `from_geosn_street` - see
`docs/providers/europe.md#geosn-hauskoordinaten-saxony` for the full
write-up.

## Recommendation

Steps 1 and 2 are decisively closed and don't need re-checking unless
BKG's own services change. The state fan-out is now 3/4 done (Hamburg,
Brandenburg, Saxony); Berlin is worth a real retry once
`gdi.berlin.de` comes back from maintenance - note that Brandenburg's
own WFS BB-BE Gazetteer already carries a real, if non-exhaustive,
slice of Berlin street data in the meantime.
