# INSPIRE GML investigation — Spain's road transport network WFS

Investigation only. No code, no module, no reader was built. Endpoint:
`https://servicios.idee.es/wfs-inspire/transportes` (WFS 2.0.0, deegree,
INSPIRE Annex I Theme 7, CC BY 4.0, no credentials). All findings below are
from real, live requests made this session.

**Bottom line: build it, but scope it as a two-feature-type join, not a
single-feature-type GML reader.** Test 1's answer is neither the clean
"inline" case nor the fatal "unjoinable href" case the brief posed as the
two poles — it's a third case: bare hrefs everywhere, but the identifiers
are real, dereferenceable, and batchable in one extra round trip. Geometry
is safe (Test 3: zero curves in 1,000 real features). The harmonised layer
is genuinely thin at the `RoadLink` level but not at the `Road` level one
hop away (Test 2).

---

## Test 1 — the association problem (decisive)

**`RoadLink` itself carries no path to a name at all**, checked at the
schema level, not just by sampling: `RoadLinkType` extends
`tn:TransportLinkType` with an *empty* `<sequence/>` — it adds nothing.
Every field on a real `RoadLink` (`centrelineGeometry`, `fictitious`,
`startNode`/`endNode`, `beginLifespanVersion`, `validFrom`/`validTo`) comes
from the shared base type. The one field that could theoretically carry a
name inline — `TransportLinkType.geographicalName` (`minOccurs="0"`) — is
schema-legal but **absent on all 20 real `RoadLink` features sampled**,
including the 2 of 20 that were genuine (non-`fictitious`) links, not just
the 18 through-intersection connectors. So even the "does it come back
inline" question doesn't apply to `RoadLink` — there's no name-shaped field
present to be inline or not.

**The real association runs the other way**, and through a type the brief
didn't name: `tn-ro:RoadName` → `tn-ro:Road` → `tn-ro:RoadLink`. A real
`RoadName` feature, fetched with no resolve parameter at all:

```xml
<tn-ro:RoadName gml:id="TN-RO_ROADNAME_NOM_VI30650003412">
  <net:networkRef>
    <net:LinkReference>
      <net:element xlink:href="...GetFeatureById...ID=TN-RO_ROAD_VIAL_LI30650003412#TN-RO_ROAD_VIAL_LI30650003412"/>
      <net:applicableDirection xlink:href=".../LinkDirectionValue/bothDirections"/>
    </net:LinkReference>
  </net:networkRef>
  <tn-ro:name>
    <gn:GeographicalName>
      <gn:spelling><gn:SpellingOfName><gn:text>RD OESTE DE CARRUS</gn:text></gn:SpellingOfName></gn:spelling>
    </gn:GeographicalName>
  </tn-ro:name>
</tn-ro:RoadName>
```

The name itself (`RD OESTE DE CARRUS`) is real and inline on `RoadName` —
no resolve needed for that part. But `networkRef` points to a
**`tn-ro:Road`**, not a `RoadLink` — a third feature type, not mentioned in
the brief, sitting between name and geometry.

**Resolve does not work on this reference, tested both ways.** With no
resolve param, and with `RESOLVE=local` explicitly set (matching the
service's own declared `ResolveLocalScope=*`), the `net:element` stayed a
bare `xlink:href` in both responses — byte-identical. `RESOLVE=all` +
`RESOLVEDEPTH=*` was tried live and **never returned** — abandoned after
15+ minutes with zero bytes received, not a clean timeout or error. Given
`ImplementsRemoteResolve=FALSE` is at least honestly declared, this is
consistent — but the practical lesson is that *local* resolve is also dead
in practice here, contradicting what `ResolveLocalScope=*` implies. **A
fourth service now caught misrepresenting (or at least not usefully
implementing) its own declared capability**, alongside PDOK/Jersey/ArcGIS.

**But the identifiers do support a clean join** — fetching a real `Road`
by the id `RoadName` gave (a working one; see caveat below):

```xml
<tn-ro:Road gml:id="TN-RO_ROAD_VIAL_LI30690001214">
  <net:link xlink:href="...ID=TN-RO_ROADLINK_VIAL_TR30690003091#..."/>
  <net:link xlink:href="...ID=TN-RO_ROADLINK_VIAL_TR30690003140#..."/>
  <!-- 12 real net:link hrefs total, one per constituent RoadLink -->
  <tn:geographicalName>
    <gn:GeographicalName><gn:spelling><gn:SpellingOfName><gn:text>ALQUERIA</gn:text></gn:SpellingOfName></gn:spelling></gn:GeographicalName>
  </tn:geographicalName>
  <tn-ro:localRoadCode>72</tn-ro:localRoadCode>
  <tn-ro:nationalRoadCode xsi:nil="true" nilReason="unknown"/>
</tn-ro:Road>
```

`Road` carries the name inline too (`ALQUERIA` — duplicating `RoadName`,
making `RoadName` largely redundant if you're going to `Road` anyway) plus
`localRoadCode`, and a real list of `net:link` hrefs, each a genuine,
dereferenceable `RoadLink` id. **These are not GetFeatureById-only** — WFS
2.0's `RESOURCEID` parameter accepts a comma-separated list and was
confirmed live to return all requested `RoadLink`s, geometry included, in
one request:

```
GET .../transportes?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature
    &RESOURCEID=TN-RO_ROADLINK_VIAL_TR30690003091,TN-RO_ROADLINK_VIAL_TR30690003140,TN-RO_ROADLINK_VIAL_TR30690003394
→ 200, numberReturned="3", full geometry for all three
```

So the real shape for "one named road, with geometry" is **two HTTP round
trips**: fetch `Road` (or `RoadName`→`Road`), collect its `net:link` ids,
then one `RESOURCEID`-batched `GetFeature` for all of them. Bounded, not
open-ended.

**Caveat, found not assumed**: of 3 real `RoadName`→`Road` hrefs followed,
1 returned `403 OperationProcessingFailed: feature not found` — a stale or
broken reference the service itself generated. Confirmed with the
byte-exact href (no transcription error) and confirmed `GetFeatureById`
works correctly in general (a known-good `RoadLink` id resolved fine). Not
systemic on this small sample (2 of 3 worked), but real — a reader would
need to treat a broken cross-reference as an expected, non-fatal case.

## Test 2 — is the harmonised layer actually populated?

At the `RoadLink` level: **geometry plus almost nothing**, confirmed
exactly as the brief worried. The complete real, populated field set on a
`RoadLink` is: `inspireId`, `beginLifespanVersion`,
`endLifespanVersion`/`validFrom`/`validTo` (nil/unpopulated on every
sample), `centrelineGeometry`, `fictitious`, `startNode`/`endNode` (bare
hrefs to `RoadNode`, not resolved). No name, no class, no lane count, no
authority, no road number — all of that lives in other feature types.

One layer up, at `Road`: real content exists — name (`ALQUERIA`) and
`localRoadCode` (`72`), confirmed live. And the classification/attribute
types the brief named are real and populated too, each following the same
reverse-reference pattern via `net:networkRef`/`net:element` back to a
specific `RoadLink` id — confirmed live for all four:
`tn-ro:FunctionalRoadClass`, `tn-ro:FormOfWay`, `tn-ro:NumberOfLanes`, and
`tn:MaintenanceAuthority` (this last one is network-wide, not road-specific
— a sampled, unfiltered fetch returned an airport-node example first,
confirming it spans transport modes rather than being a road-only type).

So the honest answer has two parts: `RoadLink` alone is exactly the "27
countries of unnamed centrelines" the brief was worried about — it serves
"plot streets," not "link to works" or "get street names." But the
harmonised model *does* carry names, road codes, and functional
classification — one hop away, in real, populated, separately-fetchable
feature types, each following one consistent reverse-reference pattern.
Whether that's "populated enough" depends entirely on whether the extra
round trips are acceptable — see Test 1's two-round-trip shape.

## Test 3 — do curved geometries actually appear?

No. **Zero** curve elements (`gml:Curve`, `gml:MultiCurve`,
`gml:CompositeCurve`, `gml:Arc`, `gml:CurveSegment`) across 1,000 real
`RoadLink` features fetched in one batch. Every geometry is a plain
`gml:LineString`/`gml:posList`, exactly 1,000 of 1,000. The filter
capabilities advertising curve support describe what the *service* can
theoretically accept/return in general, not what this dataset's real
content contains — a real instance of capabilities overstating what's
actually there, in the safe direction this time. A reader would still need
to *detect and refuse* a curve element on principle (per the brief's own
rule), but on this evidence it would never actually fire against Spain's
real data.

## Notes in passing

- **GML version served by default (no `outputFormat` specified):** 3.2 —
  `xmlns:gml="http://www.opengis.net/gml/3.2"` on every real response.
- **`srsName` form: neither of the two forms named in the brief.** Every
  real response used the OGC "http URI" form,
  `http://www.opengis.net/def/crs/EPSG/0/4258` — not the URN form
  (`urn:ogc:def:crs:EPSG::4258`) and not the bare short form (`EPSG:4258`).
  By OGC convention this URI form carries the same axis-order mandate as
  the URN form, and the real coordinate values confirm it in practice: a
  real `posList` pair `40.911071 0.261676` is (lat, lon) — 40.91°N is a
  plausible Spanish latitude, 0.26° a plausible longitude; the reverse
  would place the point in the Arabian Sea. **Axis order is genuinely
  lat/lon, matching EPSG:4258, not assumed.**
- **`srsDimension`**: never present on any real element checked — no 3D
  signal anywhere; every `posList` was strictly `lat lon lat lon ...` pairs,
  confirmed by counting values (always even, always 2 per vertex).

## Recommendation

Buildable, but not as originally scoped. A bounded reader here means:
parsing two feature types (`RoadLink` for geometry, `Road` for name/code),
following `net:link` hrefs via a batched `RESOURCEID` fetch rather than
per-link `GetFeatureById` calls or the (non-functional) `resolve`
parameter, and treating an individual broken cross-reference as an
expected, skippable case rather than a fatal error. That's real, additional
scope beyond "parse features, geometry, attributes" — but it's a fixed,
two-hop, two-request shape, not an open-ended INSPIRE client that has to
chase `FunctionalRoadClass`/`FormOfWay`/`NumberOfLanes`/`MaintenanceAuthority`
too. Whether that extra hop is worth it is a scoping call for whoever
picks this up next, not answered here.
