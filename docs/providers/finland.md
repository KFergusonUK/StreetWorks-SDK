# Finland

> New content, not a migration. Finland's existing roadworks coverage
> (Digitraffic/Fintraffic, DATEX II via its own JSON schema) stays
> documented in [`docs/providers/europe.md`](europe.md#datex-ii-european-roadworks)
> — it's woven into that page's shared DATEX II field-extraction
> narrative alongside NDW/IRCA, not a standalone section, so it wasn't
> moved. This page covers Finland's new streets provider only.

## Digiroad (Finland)

This SDK's first Finnish streets/gazetteer coverage — a real sibling to
Finland's existing roadworks provider, from the same real government
department: Fintraffic (which runs Digitraffic) operates under
Väylävirasto, the same agency that publishes Digiroad — though the two
are genuinely different agencies' datasets, not a coincidence to
conflate.

```python
from streetworks.digiroad import DigiroadClient
from streetworks.common import from_digiroad_street

helsinki_bbox = (24.90, 60.14, 25.00, 60.22)  # (xmin, ymin, xmax, ymax), WGS84
with DigiroadClient() as digiroad:
    streets = [from_digiroad_street(f) for f in digiroad.iter_streets(bbox=helsinki_bbox)]
```

**Found by checking a different agency from the one that looked obvious
first.** Maanmittauslaitos (MML, the National Land Survey) publishes
Finland's general topographic database (Maastotietokanta) over a modern
OGC API Features service — but it genuinely requires a self-service API
key (confirmed live: the bare endpoint returns a real `401` with no
key), so per this project's own access-boundary rules it wasn't
registered for or built against. Checking further found Väylävirasto's
own separate WFS deployment instead (`avoinapi.vaylapilvi.fi`) —
confirmed live, genuinely keyless, no registration of any kind — which
turned out to carry Digiroad, Finland's real national road/street
database, not just the state-maintained road-asset-management layers
that dominate this same deployment's real 328-layer catalogue.

**A real cartographic-view duplication, confirmed live before picking
one layer — the same trap TIGERweb's own layers 0–9 were.** Three real
layer names (`dr_tielinkki_hall_lk`, `dr_tielinkki_toim_lk`,
`dr_tielinkki_tielinkin_tyyppi`) all resolve to the exact same real
underlying table — identical field list, identical real national count
(3,363,654), confirmed by comparing `DescribeFeatureType` output and
`resultType=hits` across all three.

**Real bilingual names — Finland's genuine official convention, not
duplication to dedupe.** `tienimi_su` (Finnish) and `tienimi_ru`
(Swedish) are both real, independently stated fields, both populated on
the large majority of real named segments checked live (a Helsinki
bbox: 4,198/5,000 with a Finnish name, 4,190/5,000 with a Swedish one).
`from_digiroad_street` carries each as its own `Name` via
`Name.language` (`"fi"`/`"sv"`) — the same mechanism the NSG's own
`_eng`/`_cym` pairs already use — never merged into one. Real,
recognisable examples confirmed live: `"Mannerheimintie"`/
`"Mannerheimvägen"` (Helsinki's most famous street).

**Real 3D geometry — `Z` genuinely present and preserved through
reprojection, confirmed live.** Every real `LineString` vertex checked
carries a genuine elevation value in metres (e.g. `92.867`), unchanged
whether or not `srsName=EPSG:4326` is requested. Per this SDK's own
data-integrity rule, `Z` is carried through exactly as given, never
defaulted to zero.

**CRS: native `EPSG:3067` (ETRS89 / TM35FIN), real WGS84 only when
explicitly requested** — the opposite default from Iceland's own WFS
(which defaults to WGS84). Unlike Gibraltar's and Iceland's own
GeoServer deployments, this one genuinely accepts `application/geo+json`
directly — no output-format workaround needed.

**Scale**: 3,363,654 real features nationally — TIGERweb/NRN-scale, and
this server also enforces a real ~5,000-feature-per-request cap
regardless of a larger requested count (confirmed live; the client
pages past it automatically). Querying without a bounding box is not
recommended.

**Licence: Creative Commons Attribution 4.0 International, confirmed
live directly from the dataset's own `avoindata.fi` catalogue entry**:
*"Väylävirasto on julkaissut rajapinnan Väyläviraston avoin
WFS-rajapinta lisenssillä Creative Commons Attribution 4.0
International License."*
