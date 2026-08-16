# Ireland

> `## Ireland — MapRoad Roadworks Licensing (documented, unavailable)`
> moved here verbatim from `docs/providers/europe.md` (no content
> change) now that Ireland has a real, live provider of its own
> (Monaghan, below) and warrants a dedicated page, the same promotion
> Canada/Gibraltar/Austria got. See `docs/migration-mapping.md` for the
> original phase-one placement.

## Monaghan County Council road network

This SDK's first Irish gazetteer coverage — a pilot for a real,
genuine 31-county fan-out, not a national build:

```python
from streetworks.arcgis.monaghan import MonaghanRoadsClient
from streetworks.common import from_monaghan_road

with MonaghanRoadsClient() as monaghan:
    segments = [from_monaghan_road(f) for f in monaghan.iter_roads("local")]
```

**Why a county, not a country — investigated live, not assumed.** A
national named-street source was checked first and ruled out: Tailte
Éireann's own open-data catalogue (CC BY 4.0) has administrative
boundaries and a 1:250,000-scale road layer with no name field at all;
TII's live "National Road Network 2024" is motorways/N-roads only, its
`Road` field a real route code (`"M7"`), not a name. What's real and
open instead is a genuine per-county fan-out — the same shape Germany's
states have — confirmed against two of the 31 County Councils' own
independent ArcGIS Online feeds before picking Monaghan as the first
pilot; see [`docs/providers/pending.md`](pending.md) for the full live
investigation, including why Donegal's own equivalent feed (checked the
same day) has no usable name field at all and wasn't the one chosen.

**Real Irish rural roads genuinely have no name — confirmed live, the
whole reason this pilot exists, not a data gap this converter works
around.** `Road_Name` is Ireland's own official route number
(`"L-31011-0"` for Local, `"R-183-12"` Regional, `"N-12-0"` National) —
real, stated, and carried honestly as an `Identifier`
(`scheme="road_number"`), never misrepresented as a street name.
`from_monaghan_road` produces `Segment` only, and its `names` field is
**always the empty tuple** — the same "no synthetic streets" discipline
TIGERweb's and NRN's own converters already established for their own
real segment-only outcomes. `Start_At`/`Finish_At` carry real
junction/townland descriptions instead (`"Creeve - 4 Roads"`) — how
these roads are genuinely identified in practice — preserved in `.raw`
only, since no canonical "described endpoint" field exists yet for a
single real source to justify inventing one.

**Three real, distinct road-class services, confirmed live** (not one
combined feed): `National_Roads` (27 real segments), `Regional_Roads`
(122), `Local_Roads` (1,612) — all on the same hosted deployment.
`Road_Class` (a plain real label, e.g. `"Local Tertiary"`) becomes
`StreetType.label`; `Municipal_District` becomes `administrative_area`
where stated (absent on every real `National_Roads` record, checked,
not assumed present). **CRS: real WGS84 by default** — the service's
stated native reference is `EPSG:2157` (Irish Transverse Mercator), but
a plain `f=geojson` request with no `outSR` already returns genuine
WGS84 coordinates, the same real behaviour TIGERweb's and NRN's own
services show. Pagination genuinely works (confirmed live: distinct
`OBJECTID`s at offsets 0 and 1000 on the 1,612-record `Local_Roads`
layer) and this service states a real `objectIdField` to page by.
**Licence unconfirmed** — no explicit statement found on the real
ArcGIS Online items checked, the same open-by-design situation Jersey's
own services have; built on the project owner's explicit instruction.

## Ireland — MapRoad Roadworks Licensing (documented, unavailable)

Investigated and registered honestly-unavailable, the same treatment
Road Report NT (Australia) already established (see
[`docs/providers/australia.md`](australia.md#act--tasmania--the-au-tail-plus-a-documented-northern-territory))
— not silently skipped, but not a working client either.

**TII's own DATEX II feed (`data.tii.ie`) was checked first and ruled
out as the roadworks source.** Its real, published dataset catalogue
(verified directly against its data.gov.ie mirror — all 20 real dataset
titles enumerated) carries travel times, weather, VMS/VDS, collision
rates, WIM sensor data, and traffic counts — no roadworks or Situation
publication at all.

**MapRoad Roadworks Licensing is the real roadworks source — a genuine
national permit register covering both national and local roads** (TII's
own national-road consents route through it; local authorities' regional/
local consents also do), run by the Road Management Office under the
Local Government Management Agency. If it were reachable, this would be
this SDK's third `source_grade=register` source, and the first genuinely
combined national+local one.

**Why it's a documented scaffold, not a working client.** Ireland's own
[PSB Data Catalogue entry](https://datacatalogue.gov.ie/dataset/maproad-roadworks-licensing-system)
states, together: `API Available: Yes`, `Open Data: No`, `Data Sharing:
Yes`, `Personal Data: Yes`. Read as a whole, this describes a real API
gated behind a formal, GDPR-relevant data-sharing arrangement — not a
self-service developer key the way Trafikverket/LINZ's are. Registration
for MapRoad itself (`rmo.ie`) is a real, formal process (download a
registration pack, complete it, email it to `contact@rmo.ie`) aimed at
licence *applicants*, not read-only consumers. No endpoint, schema, or
authentication mechanism for a read path was found published anywhere.
`MapRoadClient()` always raises `ProviderUnavailableError` immediately,
with no network call, rather than guessing at an unpublished private
contract with real personal-data implications — see
[`docs/providers/index.md#credentials-wanted`](index.md#credentials-wanted)
for the condensed table entry, and revisit if a documented read API, or
a confirmed data-sharing route for non-applicants, ever surfaces.
