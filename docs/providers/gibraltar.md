# Gibraltar

> New content, not a migration. This SDK's first British Overseas
> Territory coverage — a genuinely different constitutional category
> from the UK's Crown Dependencies (Jersey, Guernsey), so it gets its
> own page rather than folding into [`docs/providers/uk.md`](uk.md).
> Streets only — a real roadworks/construction layer was found and
> checked, but carries no usable attributes at all; see below.

## Gibraltar Street Gazetteer

HM Government of Gibraltar's real, live named-road layer, over the
Geoportal's own GeoServer WFS:

```python
from streetworks.gibraltar import GibraltarStreetsClient
from streetworks.common import from_gibraltar_street

with GibraltarStreetsClient() as gibraltar:
    streets = [from_gibraltar_street(f) for f in gibraltar.iter_streets()]
```

**Found by walking the service-wide WFS capabilities, not just the
INSPIRE workspace the public viewer app links to.**
`download.geoportal.gov.gi/geoserver` publishes two real workspaces:
`inspire` (the EU/INSPIRE-mandated layers — including
`TN_RoadTransportNetwork_RoadLink`, real link geometry but confirmed
live to carry **no name field anywhere in its schema**, the same
"geometry with no identity" outcome Germany's BKG ATKIS DLM250 WFS had)
and a richer native `gibgis` workspace underneath the same server.
`gibgis:roads_lb_vw` — confirmed live to be the real, distinct,
named-road layer, 277 real streets — is what this module uses. Real
Gibraltar street names confirmed live: `"Witham's Road"`, `"Winston
Churchill Avenue"`, `"Windmill Hill Road"`.

**`label` is a composed display string, not a single real name —
confirmed live across the full 277-record layer.** `label` and `name`
genuinely differ on 59/277 (21%) of records, always the same real
shape: `label` is `"{name} - {collname1}[ - {collname2}]"` (a real
example: `"Queensway - Dockyard Road - Dockyard Approach Road"` has
`name="Queensway"`, `collname1="Dockyard Road"`,
`collname2="Dockyard Approach Road"` — three genuinely separate real
street names for one segment, often an English name alongside a real
Llanito/Spanish local one, e.g. `"New Street"`/`"Calle Nueva"`).
`from_gibraltar_street` never reads `label` itself — `name`/`collname1`/
`collname2` each become their own `Name` where real and non-blank,
rather than fusing them into one unsearchable compound string.

**Genuinely multi-part `MultiLineString` geometry on a real majority of
records — confirmed live, not assumed single-part from a handful of
samples.** 150 of 277 real features (54%) carry more than one line
within their `MultiLineString` (a real road drawn as several
disconnected pieces, e.g. where crossed by a junction) — `from_gibraltar_street`
always populates `Coordinate.parts`, the same real multi-part handling
`from_tigerweb` already established, never a first-line-only shortcut.

**A real GeoJSON output-format quirk, confirmed live.** This server
rejects `application/geo+json` outright
(`InvalidParameterValue: Failed to find response for output format
application/geo+json`) — only plain `application/json` works, passed
explicitly rather than relying on `streetworks.ogc.OGCFeaturesClient`'s
own documented default. **CRS: real WGS84 output confirmed live when
explicitly requested** — `srsName=EPSG:4326` genuinely reprojects this
layer's native `EPSG:25830` (ETRS89 / UTM zone 30N) geometry
server-side, unlike some services this SDK has built against (Jersey's
own roadworks layer ignores `outSR` entirely).

**No pagination needed at this real size (277), but checked live rather
than assumed safe** — a single request with a generous `count` returns
everything in one round trip. A real GeoServer quirk was found and
worked around: combining `count`/`startIndex` pagination on this
*view*-backed layer without an explicit `sortBy` fails outright
(`Cannot do natural order without a primary key`) —
`GibraltarStreetsClient.iter_streets` always sorts by `inspireId` and
checks `numberMatched` against what it actually received, raising
rather than silently truncating if this layer ever grows past one page.

**A real `tho_ref` cross-reference to a separate, more granular layer**
(`gibgis:thoroughfare_pl`, 2,026 real segment-level features, only
~30% named on a live sample) exists but isn't consumed here — a real
future strand, the same way Jersey's own `Projects` layer is noted but
unused.

**No usable roadworks feed found.** A real `gibgis:under_construction`
polygon layer exists (23 real features live) but its schema carries
**only a geometry field — no name, date, description, or type
attribute at all** — genuinely unusable as a works feed, checked via
`DescribeFeatureType`, not assumed from the layer's promising name
alone.

**Licence: no single confirmed open-licence document found, built on
instruction rather than a discovered text — the same basis Jersey
shipped on.** The Geoportal's own disclaimer states reproduction/
redistribution needs "prior approval of HM Government of Gibraltar,"
qualified by "unless otherwise specified" — no more specific override
text was found on the Download Service or Publications pages checked
this session. Real, live-captured records are committed as this
module's test fixtures on the project owner's explicit instruction.
Confirm your own reuse/redistribution rights before redistributing data
pulled through this module further downstream.
