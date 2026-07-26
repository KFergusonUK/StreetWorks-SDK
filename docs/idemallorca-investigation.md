# IDEmallorca / Consell de Mallorca roadworks — investigation

Reconnaissance only, per the brief. No module, no client, no tests. All
findings below are live-verified against the real service on 2026-07-26,
not read off documentation alone — every claim marked "confirmed live" was
checked by an actual request, not assumed from a capabilities document.

## Answer, up front

**Buildable now, as real GeoJSON, via `streetworks.ogc.OGCFeaturesClient`** —
with one required non-default parameter (`output_format="application/json"`,
not the client's own default `"application/geo+json"` — see
[§2](#2-output-formats---tested-not-trusted)) and one CRS decision to make
explicitly (native EPSG:25831 vs. server-side reprojection to EPSG:4326 —
both genuinely work, see [§4](#4-crs)). This is **not** the GML-only case;
it does not touch the parked GML-reader decision.

## 1. Server / protocol

**GeoServer WFS**, not ArcGIS REST, not a bare capabilities-lying viewer.
Confirmed from the real `GetCapabilities` response
(`http://www.conselldemallorca.info/geoserver/SIT/incidencies_tram/wfs?request=getcapabilities`):

```xml
<ows:ServiceIdentification>
  <ows:Title>IDEmallorca Web Feature Service (WFS)</ows:Title>
  <ows:ServiceType>WFS</ows:ServiceType>
  <ows:ServiceTypeVersion>2.0.0</ows:ServiceTypeVersion>
  <ows:Fees>NONE</ows:Fees>
  <ows:AccessConstraints>NONE</ows:AccessConstraints>
</ows:ServiceIdentification>
<ows:ServiceProvider>
  <ows:ProviderName>Consell de Mallorca</ows:ProviderName>
  ...
  <ows:ElectronicMailAddress>idemallorca@conselldemallorca.net</ows:ElectronicMailAddress>
</ows:ServiceProvider>
```

WFS versions 1.0.0, 1.1.0, and 2.0.0 are all offered; requests below used
2.0.0. Two feature types matter here, both under workspace `SIT`:

- `SIT:incidencies_icon` — one point per incident, carries all the real
  attributes (type, dates, road, description — see §3).
- `SIT:incidencies_tram` — the affected road segment(s) per incident, as a
  `MultiLineString`, joined back to the icon layer by a shared `codi`
  (integer) field. Confirmed live: 16/17 real icons have a matching tram
  record; one (`codi=19612`, a lane closure on Ma-13) has an icon but no
  drawn segment — not every incident gets one, a real, minor gap, not a
  join-logic bug (checked: `tram_codes ⊆ icon_codes`, no tram-only
  orphans).

No ArcGIS REST server was found anywhere in this investigation — the
`ArcGISFeatureClient` doesn't apply here. `OGCFeaturesClient` (built for
exactly this shape: WFS `GetFeature` → GeoJSON) does.

**A real, minor server quirk**: `DescribeFeatureType` against the combined
`/geoserver/SIT/wfs` endpoint throws a server-side Oracle error
(`ORA-00942: table or view does not exist`) for `incidencies_tram`;
the same request against the *layer-specific* endpoint
(`/geoserver/SIT/incidencies_tram/wfs`) works fine and returns a clean
schema. `GetFeature` itself works identically on both endpoint forms —
only schema introspection is affected. Worth knowing if a future client
build does `DescribeFeatureType` calls; use the layer-specific URL.

## 2. Output formats - tested, not trusted

The capabilities document lists `application/json` as a real output
format (alongside `application/gml+xml; version=3.2`, `gml32`, `gml3`,
`GML2`, `text/xml` variants, `csv`, `SHAPE-ZIP`, KML). Per the brief's own
"test it" instruction — four other services in this SDK's history have
lied about their capabilities (PDOK's `CQL_FILTER`, Jersey's `outSR`,
ArcGIS pagination, Bulgaria's UTF-16-declared-UTF-8) — both were tested
directly, not trusted from the list:

- `outputFormat=application/json` → **real GeoJSON, confirmed live**:
  `Content-Type: application/json;charset=UTF-8`, a genuine
  `FeatureCollection`, correct `totalFeatures`, real geometry and
  attribute values (see §3 for a full example). Not a lie this time.
- `outputFormat=gml3` → **also real**, a genuine GML `FeatureCollection`
  response, confirmed live. Both formats work; this server isn't GML-only.

**One real incompatibility with this SDK's existing client, found by
testing, not assumed**: `OGCFeaturesClient.get_wfs_features()`'s own
default `output_format` is `"application/geo+json"` (see
`streetworks/ogc/client.py`) — a different, newer MIME type than the bare
`application/json` this GeoServer instance actually offers. Requesting
`application/geo+json` against this server returns **HTTP 200** (not even
an error status) wrapping an XML `InvalidParameterValue` exception:

```
InvalidParameterValue: Failed to find response for output format application/geo json
```

This is exactly the shape of failure the client's own docstring already
warns about for Mecklenburg-Vorpommern/Saxony-Anhalt (both genuinely
GML-only there) — except here it's a false negative, not a genuine
GML-only source: the fix is trivial, since `output_format` is already a
caller-supplied parameter, not hardcoded. A working call looks like:

```python
ogc.get_wfs_features(
    "http://www.conselldemallorca.info/geoserver/SIT/incidencies_icon/wfs",
    type_name="SIT:incidencies_icon",
    output_format="application/json",   # not the client's own default
    srs_name="EPSG:25831",              # see §4 - not the client's own default either
)
```

No client code changes needed — both defaults just need overriding for
this source, the same way Saxony's UTM33N already overrides `srs_name`
for `from_ogc_features`.

## 3. Real roadworks content

Confirmed live: 17 current incidents (as of 2026-07-26), all on real
island roads (`Ma-` prefixed route numbers — `Ma-1`, `Ma-13`, `Ma-20`,
`Ma-3420`, etc.), all genuinely current or near-future (dates observed
from 2026-07-23 through 2026-10-18).

Full real schema (`DescribeFeatureType` on `incidencies_icon`, the layer
that carries content — `incidencies_tram` is geometry-only, just `codi`/
`color`/`shape`, no dates or description at all):

| Field | Type | What it is |
|---|---|---|
| `codi` | int | Incident id, joins to `incidencies_tram.codi` |
| `icon` | int | Icon/marker code for the viewer |
| `tipoinc` | string | Incident type - **the discriminator**, see §6 |
| `inici` | string | Start, `DD/MM/YYYY HH:MM` |
| `fin` | string | End, `DD/MM/YYYY HH:MM` |
| `lastupd` | string | Last updated - **different date format**: `YYYY/MM/DD HH:MM` |
| `observacions` | string | Free-text description (Catalan) |
| `carretera` | string | Road number, e.g. `"Ma-13"` |
| `pkinici` / `pkfin` | float | Kilometre-point range along the road |
| `desinici` / `desfin` | string | Named description of each km-point (empty on every real record checked) |
| `sentit` | short | Direction code (0/1/2) |
| `sentit_desc` | string | Direction, spelled out - see below, a real decoded value, not opaque |
| `restriccio` | string | Restriction type, free text |
| `color` | short | Rendering colour code |
| `shape` | geometry | `Point` (icon layer) / `MultiLineString` (tram layer) |

A real "Obres" (roadworks) record, verbatim:

```json
{
  "type": "Feature",
  "id": "incidencies_icon.19612",
  "geometry": {"type": "Point", "coordinates": [509469.68081, 4411136.83972]},
  "properties": {
    "codi": 19612,
    "icon": 0,
    "tipoinc": "Obres",
    "inici": "28/07/2026 09:00",
    "fin": "30/07/2026 15:00",
    "lastupd": "2026/07/22 13:52",
    "observacions": "TALL DEL CARRIL DRET, cada dia laborable de 09:00 a 15:00 hores per obres ",
    "carretera": "Ma-13",
    "pkinici": 50,
    "desinici": "",
    "pkfin": null,
    "desfin": "",
    "sentit": 1,
    "sentit_desc": "sentit ascendent",
    "restriccio": "Tall de carril",
    "color": 2
  }
}
```

(`"TALL DEL CARRIL DRET, cada dia laborable de 09:00 a 15:00 hores per
obres"` — "RIGHT LANE CLOSURE, every working day from 09:00 to 15:00 for
roadworks".)

`sentit`/`sentit_desc` real values found (3): `0`/"ambdós sentits" (both
directions, 15/17), `1`/"sentit ascendent" (ascending, 1/17), `2`/"sentit
descendent" (descending, 1/17) — a genuinely decoded direction field, not
an opaque Alert-C-style code.

`restriccio` real values found (7, free text, not an enum): "Trànsit
altern" (alternating traffic, 5), "Tall de carril" (lane closure, 4),
"Tancada" (closed, 3), "Estrenyiment de calçada" (carriageway narrowing,
2), "Desviament provisional" (temporary diversion, 1), "Sense
restriccions" (no restrictions, 1), "Precaució" (caution, 1).

No silent truncation confirmed: `totalFeatures` (17) exactly matches the
number of `features` actually returned with no `count`/`maxFeatures`
parameter set.

## 4. CRS

**ETRS89 / UTM zone 31N, EPSG:25831 — confirmed, matches the brief's own
expectation exactly.** Stated explicitly in the capabilities document
(`<DefaultCRS>urn:ogc:def:crs:EPSG::25831</DefaultCRS>` on the
`incidencies_tram` feature type) and confirmed independently from real
coordinate magnitudes: `[529082.6315, 4380729.74252]` — an easting/northing
pair in exactly the right order of magnitude for Mallorca in UTM31N
(genuine WGS84 longitude/latitude for this location would read
~3.3/~39.6, two-three orders of magnitude smaller).

**A real, working server-side reprojection option, tested live**: passing
`srsName=EPSG:4326` on the `GetFeature` request returns genuinely
correct WGS84 coordinates — the same feature (`codi=19617`) came back as
`[3.33862, 39.57578]`, which is the geographically correct
longitude/latitude for that easting/northing pair. This isn't a guess or
a client-side conversion — GeoServer is doing a real, standards-compliant
transform server-side, and it's internally consistent (same feature,
same location, verified by hand).

**Recommendation, not a hard requirement**: per this SDK's standing CRS
policy (state what the source natively carries, never silently reproject
client-side — the same choice made for Belgium's Lambert 72 and
Lithuania's LKS-94), a future adapter should most likely request
`srsName=EPSG:25831` (the source's own native CRS) and label
`Coordinate.crs` accordingly, rather than leaning on the server's
reprojection to present a uniform WGS84 façade. Either is technically
sound; the native-CRS choice is just more consistent with precedent
elsewhere in this SDK.

## 5. Licence

**Unresolved — genuinely, not from lack of trying.** Checked:

- The WFS capabilities document itself: `<ows:Fees>NONE</ows:Fees>`,
  `<ows:AccessConstraints>NONE</ows:AccessConstraints>` — these are
  GeoServer's own unconfigured defaults, not a deliberate licence
  statement by Consell de Mallorca. Reported as a technical signal only,
  **not** treated as "confirmed open" — a blank field is not a licence
  grant.
- `conselldemallorca.es/es/idemallorca` (the geoportal landing page): no
  licence/reuse/"condicions d'ús" text found; the page is mostly Liferay
  CMS navigation chrome plus an INSPIRE-alignment statement, no terms.
- `conselldemallorca.cat/avis-legal` (the council's general legal notice):
  checked, no explicit data-reuse/licence clause found in the reachable
  content.
- No metadata catalogue (GeoNetwork or equivalent) was found linked from
  the geoportal to check per-dataset licence metadata against.

Per the brief's own rule: **reported as Unknown, not inferred as open**
despite `AccessConstraints: NONE` being suggestive. A future build should
either locate a real terms page (a direct email to
`idemallorca@conselldemallorca.net`, the contact address the capabilities
document itself states, would resolve this properly) or ship with the
same "licence unconfirmed" flag already used for Autobahn GmbH/Belgium's
predecessor cases.

## 6. Discriminator

**Clean and explicit — not the Cyprus problem.** `tipoinc` is a real,
small-cardinality type field, not free text needing inference. Full real
distribution from the live 17-incident pull:

| `tipoinc` | Count | English |
|---|---|---|
| `Manteniment` | 10 | Maintenance |
| `Obres` | 6 | Works |
| `Altres` | 1 | Other |

The one real `Altres` record, checked individually, is itself still
roadworks-shaped (a road closure, `restriccio="Tancada"`) but its
`observacions` states *"Restriccions de la DGT, cada dia de 10 a 22h"* —
"DGT restrictions" — suggesting this layer occasionally mirrors a
DGT-imposed restriction on a Consell-managed road rather than only
Consell's own works. Worth a caller's judgement call on whether `Altres`
counts as roadworks; `Obres`+`Manteniment` alone are unambiguous.

No accidents, weather, or event-type incidents appeared anywhere in this
live 17-record pull — this specific layer reads as roadworks/restrictions
-focused already, not a general traffic-incidents feed diluted with
unrelated categories. Can't rule out other `tipoinc` values existing in
data not currently live (this was a snapshot, not a historical query), but
the field itself is a clean, safe filter.

## Scope reality

Confirmed island-only, as the brief expected: every real `carretera` value
checked is `Ma-`-prefixed (Consell de Mallorca's own road numbering) —
no DGT national-network roads appear here, consistent with the brief's
framing that this is genuinely additive coverage, not a DGT duplicate.

**The cluster is real, not hypothetical** — checked, not assumed:

- **Menorca** has its own, separate IDE (`ide.cime.es`, operated by Consell
  Insular de Menorca) — confirmed reachable, WMS confirmed present (a
  "Base de referència de la IDE Menorca" reference layer service, per a
  third-party service directory). A roadworks/incidents-specific layer
  analogous to Mallorca's `incidencies_icon` was **not located** in this
  quick pass — worth a closer look before assuming it exists, not ruled
  out either.
- **Eivissa (Ibiza)** has a real, reachable open-data portal
  (`opendata.conselldeivissa.es` — note: served with a broken/self-signed
  TLS certificate, confirmed live, a real access friction point) of a
  different shape entirely (a CKAN-style dataset catalogue, not a
  GeoServer WFS). No roadworks/incidents dataset was found on a first pass
  of its dataset listing; not exhaustively searched.
- Formentera wasn't checked in this pass.

So: the pattern **structurally generalises** (each island runs its own
territorial IT unit and its own IDE) but **not uniformly** — Mallorca's
GeoServer-WFS shape is not guaranteed to repeat exactly on the other
islands; Eivissa already looks like a different publishing model
(open-data catalogue, not a live incidents WFS). Each island would need
its own verify-first pass, the same discipline already applied to every
adapter in this SDK — not a "wrap the same client three more times" job.

## Recommendation

1. **Build now.** GeoJSON is real and working; the CRS is confirmed and
   labellable; the discriminator is clean; the content is genuinely
   roadworks (island-scope, additive to DGT). This is a small, thin
   adapter over the existing `OGCFeaturesClient`, in the same shape as
   the German state roadworks clients — not a new machinery build.
2. **Two non-default parameters needed**, both already supported by the
   existing client, neither requiring new code:
   `output_format="application/json"` (not the client's own
   `"application/geo+json"` default — genuinely rejected by this server)
   and `srs_name="EPSG:25831"` (not the client's own `"EPSG:4326"`
   default — the source's real native CRS).
3. **Licence stays flagged unconfirmed** until either a terms page is
   found or `idemallorca@conselldemallorca.net` responds - ship the same
   way Autobahn GmbH did, not blocked on it.
4. **Worth opening as a cluster strand, cautiously** — real, additive,
   confirmed-generalising-in-structure coverage, but each island needs
   its own verify-first pass rather than being assumed identical to
   Mallorca's. Recommend: build Mallorca first (fully specified above),
   then a short recon pass each for Menorca/Eivissa/Formentera before
   committing to "build all four" as one brief.
