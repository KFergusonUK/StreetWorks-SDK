# Switzerland

> Kanton Zürich and Stadt Zürich are this SDK's first Swiss roadworks
> coverage, built together as two deliberately separate providers — a
> cantonal-road register and a city-streets register, genuinely
> non-overlapping (confirmed live: neither dataset's records appear in
> the other). Do-not-dedupe, the same discipline as every other
> national/regional-vs-municipal pair in this SDK (Copenhagen and
> Vejdirektoratet, NYC DOT and WZDx).

## Kanton Zürich (Baustellen Kantonsstrassen)

The canton's own roadworks register for its cantonal-road network, over
a real GeoServer WFS:

```python
from streetworks.canton_zurich import CantonZurichClient
from streetworks.common import from_canton_zurich

with CantonZurichClient() as canton_zurich:
    features = canton_zurich.iter_roadworks()  # raw, unfiltered
works = from_canton_zurich(features)
```

**Found via opendata.swiss's own CKAN catalogue** (`wfs-baustellen-
kantonsstrassen`, maintained by Geoinformation Kanton Zürich) — the real
WFS endpoint is `https://maps.zh.ch/wfs/TbaBaustellenZHWFS` ("Tba" =
Tiefbauamt, the canton's civil engineering office). Keyless — every
claim here came from a fully unauthenticated pull (66 real features at
investigation time).

**Two real layers, confirmed to carry the same underlying closures, not
disjoint data.** `ms:baustellen-uebersicht` (overview, `Point`
geometry) and `ms:baustellen-detailansicht` (detail, real `Polygon`
work-area footprints) — every sampled feature's non-geometry properties
match 1:1 across both layers by street/km-range/dates. This SDK uses
`baustellen-detailansicht`, the richer real geometry, the same
"prefer the detail layer" call already made for Oslo's own
majority-`Polygon` shape.

**CRS confirmed live: `EPSG:2056`** (Swiss LV95), stated explicitly in
the WFS's own `GetCapabilities` and matching real coordinate magnitudes
(`[2702540.6, 1261733.7]`) — requested explicitly, not reprojected, the
same policy as Mallorca/Saxony/Oslo/Helsinki. `Coordinate.value` stays
plain `(x, y)` = `(easting, northing)`, never swapped.

**A real format gotcha, the same shape Mallorca's own docstring already
documents for a different server**: this GeoServer doesn't offer the
shared client's own `application/geo+json` default — plain
`application/json` is what actually works, confirmed live.

**No unique identifier field exists anywhere in this schema — checked
every property, genuinely absent, not an extraction gap.** A composite
of `strassenbez`+`kmvon`+`kmbis`+`datum_baubeginn` is 65/66 unique in
the live data, but the one real collision is two genuinely distinct
closures (opposite directions of the same road, different times and
descriptions) sharing identical values on all four fields — proof a
fabricated composite key would misrepresent two real works as one, not
merely be imperfect. `reference` is left `None`, documented as a
genuine gap rather than guessed.

**`ansprechperson`/`telefonnummer` name an individual staff member, not
an organisation** — never promoted to `promoter`, which would
misrepresent a person as a company. `administrative_area` is hardcoded
to `"Kanton Zürich"` instead — endpoint provenance, not a record field.

**`status_baustelle` is a real, genuinely informative two-value
field** — `"aktiv (Bauzeit)"` (52/66 live) and
`"zukünftig (Bauzeit in Zukunft)"` (14/66 live), the same shape as
Helsinki's `Käynnissä`/`Tuleva` — drives real `VERIFIED`/`ESTIMATED`
date-confidence grading rather than always-`ESTIMATED`.

**Licence: opendata.swiss's "Open use" tier, confirmed live — but not
from the obvious field.** The dataset's own CKAN `license_id` is empty
at both the resource and parent-package level; the real licence only
surfaced via the WFS resource's separate `rights` field
(`https://opendata.swiss/terms-of-use#terms_open`). That tier permits
both non-commercial and commercial use with **no attribution
required** — the most permissive of opendata.swiss's four tiers,
comparable to CC0.

## Stadt Zürich (Aktuelle Tiefbauprojekte im öffentlichen Grund)

The City of Zürich's own current civil-engineering-projects register,
over its own GeoServer WFS — genuinely separate from the canton's
cantonal-road-only coverage above:

```python
from streetworks.zurich import ZurichClient
from streetworks.common import from_zurich

with ZurichClient() as zurich:
    features = zurich.iter_roadworks()  # raw, unfiltered
works = from_zurich(features)
```

**Found via the same opendata.swiss catalogue entry** (`aktuelle-
tiefbauprojekte-im-offentlichen-grund`) — real endpoint
`https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Aktuelle_Tiefbauprojekte_im_oeffentlichen_Grund`,
one real layer `aer_baustellen_a`, 140 real features at investigation
time.

**Two real server quirks, both confirmed live, neither documented
anywhere public:**
- This GeoServer's real `GetCapabilities` lists `application/vnd.geo+json`
  as its only JSON output format — not `application/json`.
- The server only accepts WFS 1.1.0's singular `TYPENAME` parameter, not
  2.0.0's plural `TYPENAMES` (`VERSION=1.1.0&TYPENAMES=...` genuinely
  500s; `VERSION=1.1.0&TYPENAME=...` succeeds) — its own capabilities
  list only `1.0.0`/`1.1.0` as supported versions, never `2.0.0`, at
  all. Rather than bypass the shared client's `TYPENAMES`-only request
  builder, `ZurichClient` passes both — confirmed live that a request
  carrying the (here, invalid) plural alongside the valid singular
  parameter still succeeds.

**CRS: genuinely WGS84, confirmed empirically despite an empty
`DefaultSRS` capabilities tag — a real metadata gap, not a parsing
miss.** The layer's own capabilities entry states
`<DefaultSRS></DefaultSRS>` (blank) and lists only
`<OtherSRS>EPSG:4326</OtherSRS>` as an alternative. A plain `GetFeature`
request with no `srsName` returned coordinates (`[8.57, 47.40]`) that
exactly match that same layer's own stated `WGS84BoundingBox`
(`8.462–8.605°E`, `47.326–47.432°N`) — confirming the real default
output genuinely is WGS84 even though the capabilities document never
says so. Requested explicitly as `EPSG:4326` regardless.

**A real, confirmed unique identifier — unlike the canton's dataset.**
`baunr` (project number, e.g. `"18071"`) is 140/140 distinct across the
full live pull.

**`kategorie` is a constant `"Grössere Baustelle"`** ("larger
construction site") across all 140 real rows — this dataset is already
curated to significant/major projects, not every minor street closure.
Stated honestly as scoped that way, not implied to be exhaustive.

**`projektleiter`/`projektleiter_email`/`tel` are again a named
individual (the project leader), not an organisation** — the same
treatment as the canton's own `ansprechperson`: preserved on `.raw`
only, `promoter` stays `None`.

**Licence**: the same opendata.swiss "Open use" tier as the canton,
confirmed live via the same resource `rights` field.
