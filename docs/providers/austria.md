# Austria

> Vienna is this SDK's first keyless Austria coverage. The separate
> national ASFINAG motorway feed (`streetworks.datex2.austria`, genuine
> DATEX II) remains a Credentials-wanted scaffold - registration issues
> the real pull URL, and even the auth mechanism itself is unconfirmed;
> see [`docs/providers/index.md`](index.md#credentials-wanted)'s
> Credentials-wanted table. Do-not-dedupe: Vienna's municipal roadworks
> and ASFINAG's national motorway network are genuinely different road
> tiers, the same relationship every other national-vs-municipal pair in
> this SDK has (Copenhagen/Vejdirektoratet, Kanton Zürich/Stadt Zürich).

## Vienna (verkehrswirksame Baustellen)

Stadt Wien's own register of current and future traffic-relevant
roadworks and closures on the city's higher-order road network:

```python
from streetworks.vienna import ViennaClient
from streetworks.common import from_vienna

with ViennaClient() as vienna:
    features = vienna.iter_roadworks()  # both real layers, combined
works = from_vienna(features)
```

**The candidate URL a source brief proposed (`data.gv.at`) turned out
to be a JS-rendered SPA - the real data lives directly on Vienna's own
GeoServer WFS instead.** A plain unauthenticated fetch of any
`data.gv.at` catalogue page, including the CKAN-style API path the
brief's own dataset naming implied, returns an identical empty shell,
not real content. The real endpoint, found via web search:
`https://data.wien.gv.at/daten/geo` - a real, live, 377-layer WFS,
confirmed reachable with no key.

**Two real layers, genuinely disjoint - not the same data in two
formats, unlike Kanton Zürich's own two layers.**
`ogdwien:BAUSTELLENPKTOGD` ("verkehrswirksame Baustellen Punkte",
`Point`, 39 real features) and `ogdwien:BAUSTELLENLINOGD` ("...Linien",
`LineString`, 72 real features) - confirmed live: **zero real
`OBJECTID` overlap and zero location-name overlap** between the two.
Each real worksite is recorded once, as either a point or a line, not
both - both layers are fetched and combined for the complete picture
(111 real works total).

**Two real server quirks, both masked-failure risks - confirmed by
reading response bodies, not just status codes.** This GeoServer
returns a genuine `HTTP 200` wrapping an XML `InvalidParameterValue`
exception for the shared client's own `application/geo+json` default -
`application/json` is what actually returns real GeoJSON. It also
rejects both WFS 2.0.0's and 1.1.0's plural `TYPENAMES` alone (a real
`400`/structured `ExceptionReport`) - it needs 1.1.0's singular
`TYPENAME` sent alongside it, confirmed live that having both present
succeeds.

**CRS confirmed live, cross-verified two ways.** The WFS's own
`GetCapabilities` states `EPSG:31256` (MGI / Austria GK East) and the
real `GetFeature` response's own `crs` field agrees - and a same-feature
request reprojected to `EPSG:4326` landed on real Vienna coordinates
(`[16.36, 48.17]`, 10th district, matching that feature's own stated
`BEZIRK: 10`), confirming the native small-number GK East values are
genuinely correct, not a mislabelled CRS. `Coordinate.value` stays
plain `(x, y)`, never swapped; real `LineString` geometry populates
`Coordinate.points` with every real vertex.

**A real, genuinely categorical `BEHINDERUNGSART` (obstruction type)
field** - richer than Kanton Zürich's schema (no categorical field at
all): real values seen live include `Rohrlegung` (pipe-laying),
`Straßenbau` (road construction), `Kanalbau` (sewer construction),
`U-Bahnbau` (metro construction), and `Gleisbau` (tram-track
construction).

**A real correction to the source brief's own framing: this is a
permit register, not an operator publishing only its own works.** The
brief called Vienna's dataset "operator"-graded (Stadt Wien as the
traffic authority publishing its own works) - but `ANTRAGSTELLER`
(applicant)'s real values are genuine third-party applicants:
`Wiener Netze - Bereich Fernwärme`/`Bereich Gas` (the electricity/gas
utility), `Wiener Linien GmbH & Co KG` (the transit operator),
`Wienkanal` (the sewage utility), even `Privater Bauträger` (a private
developer) - alongside city departments (`MA28`/`MA31`/`MA29`). This
SDK ships it `source_grade = REGISTER`, the same tier as
Copenhagen/Helsinki/NYC DOT/Chicago, correcting the brief's assumption.
8/39 real point rows have `ANTRAGSTELLER = null` - a genuine partial
gap, left `None` rather than filled in.

**`ANSPRECHPERSON`/`ANSPRECHPERSON_TEL` are a genuinely mixed field** -
some real values are an individual's name (`Gerhard Baumann`), others
an organisational contact desk (`Kundenzentrum`,
`Kundentelefon Wiener Linien`) - preserved on `.raw` only, never
promoted to `promoter` (which `ANTRAGSTELLER` already covers cleanly).

**A real, confirmed CPython quirk in date parsing, not a bug in this
SDK's own `parse_iso8601`.** Real dates are shaped `"2026-08-10Z"` (a
bare date plus a bare `Z`, no time component).
`datetime.fromisoformat("2026-08-10+00:00")` itself silently drops the
UTC offset and returns a naive datetime - confirmed directly in a plain
Python shell, independent of this SDK's own code. No explicit status
field exists either - only planned `OBJEKT_BEGINN`/`OBJEKT_ENDE` dates
(2/39 real rows are future-starting), so `date_confidence` stays
uniformly `ESTIMATED`, the same call already made for
Lisboa/Paris/Milan/Stadt Zürich.

**A real, checked-and-correctly-excluded false lead**:
`ogdwien:BAUSPERRE82OGD`/`BAUSPERRE86OGD` ("Bausperre § 8 (2)/(6)")
sound roadworks-adjacent but are real Vienna Bauordnung (building code)
construction-freeze zoning restrictions - an urban-planning concept,
not a road closure.

**Licence: Stadt Wien's stated general open-data policy is CC BY 4.0**,
confirmed live from `digitales.wien.gv.at`'s own open-data page
(*"Die Publikation erfolgt in der Regel unter der Lizenz CC BY 4.0"*) -
a general stated practice, not this specific dataset's own confirmed
per-record licence field (the catalogue page that would carry that
field is the same JS-rendered SPA shell noted above).

**`network_scope`**: the dataset itself is explicitly scoped to
Vienna's "höherrangiges Straßennetz" (higher-order road network) - real
and comprehensive for that tier, but not every minor residential
street, stated honestly rather than implied exhaustive.
