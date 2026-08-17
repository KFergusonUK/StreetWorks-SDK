# Iceland

> New content, not a migration. Iceland's existing roadworks coverage
> (IRCA/Vegagerðin, genuine DATEX II) stays documented in
> [`docs/providers/europe.md`](europe.md#datex-ii-european-roadworks) —
> it's woven into that page's shared DATEX II field-extraction narrative
> alongside NDW/Digitraffic, not a standalone section, so it wasn't
> moved. This page covers Iceland's new streets provider only.

## Landmælingar Íslands (IS 50V road network)

This SDK's first Icelandic streets/gazetteer coverage — a real sibling
to Iceland's existing roadworks provider, not a coincidence: both this
layer's own real `gagnaeigandi` (data-owner) field and IRCA's own feed
point to the same real agency, **Vegagerðin** (the Icelandic Road
Administration), confirmed live, not assumed from the two providers
just happening to both be Icelandic.

```python
from streetworks.lmi import LmiStreetsClient
from streetworks.common import from_lmi_street

with LmiStreetsClient() as lmi:
    streets = [from_lmi_street(f) for f in lmi.iter_streets()]
```

**Found by walking the service's own full `GetCapabilities` (473 real
layers on `gis.lmi.is`'s GeoServer), not assumed from a promising layer
name.** `IS_50V:samgongur_linur` ("transport lines") is the real
national road-segment layer — 58,266 real features, part of
Landmælingar Íslands' IS 50V national 1:50,000 base map. A separate
`INSPIRE:is_tn_ro_lmi_roadlink` layer also exists on this deployment
(Iceland's own INSPIRE Transport Networks publication) but carries **no
name field anywhere** — the same "geometry with no identity" outcome
Germany's BKG and Gibraltar's own INSPIRE layer had. This native IS 50V
layer was built instead, precisely because it doesn't have that gap.

**Real names on 84.0% of features — confirmed against the complete real
dataset, not a naive check.** A first pass using `nafnfitju IS NOT
NULL` suggested 99.98% real coverage — wrong, and caught before
shipping: the real majority of unnamed rows store a literal
single-space string (`" "`), not a database `NULL`, so that filter
alone missed them. The real, corrected 84.0% (48,959/58,266) still
spans the full density range: `"Gnúpverjavegur"` (a real rural
connecting road) and `"Laugavegur"` (Reykjavík's own main shopping
street, 63 real segments) both appear — genuine urban coverage, not
just inter-town routes. `from_lmi_street` treats both a real blank
string and a real `NULL` as no name, never fabricating one.

**Real, additional route/section numbers alongside the name — not
instead of it, unlike Ireland's own Monaghan pilot.** `vegnr`/`kaflanr`
(e.g. `"325"`/`"01"`) are Vegagerðin's own real road-numbering scheme,
carried as a second `Identifier` (`scheme="road_number"`) alongside the
real name — a genuinely different shape from Ireland's rural roads,
which are numbered *instead of* named.

**A real GeoJSON output-format quirk, the same one Gibraltar's own
GeoServer has** — `application/geo+json` is rejected outright (a real
`400`); only plain `application/json` works, requested explicitly.
Unlike Gibraltar's own view-backed layer, this one paginates cleanly
with plain `COUNT`/`STARTINDEX` — no `sortBy` workaround needed,
confirmed live. **CRS: real WGS84 by default**, no `srsName` override
needed — confirmed live, though requested explicitly anyway. Genuinely
multi-part `MultiLineString` geometry occurs on a real minority of
records — `Coordinate.parts` is always used, the same discipline
`from_gibraltar`/`from_tigerweb` already established.

**Licence: Creative Commons Attribution 4.0 International, confirmed
live directly from Landmælingar Íslands' own licence page** (in
Icelandic): *"Opin gögn Landmælinga Íslands eru gefin út skv. Creative
Commons Attribution 4.0 International License"* — with a real stated
attribution format (Landmælingar Íslands' name, the dataset name, and
the date the data were fetched).
