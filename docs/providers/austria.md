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
> **Streets**: BEV's own federal street-name register, this SDK's first
> Austrian streets/gazetteer coverage - see below.

## Österreichisches Adressregister (BEV)

Austria's national street-name register, run by BEV (Bundesamt für
Eich- und Vermessungswesen, the Federal Office of Metrology and
Surveying):

```python
from streetworks.bev import BevStreetsClient
from streetworks.common import from_bev_street

with BevStreetsClient() as bev:
    streets = [from_bev_street(r) for r in bev.iter_streets()]
```

**Not the first source found - BEV's own product page is a paid shop, a
separate free line was found instead.**
`bev.gv.at/Services/Produkte/Adressregister/` lists a per-record priced
product (e.g. €0.045/record for 1m-geocoded addresses, ordered via
"Bestellformulare"/"BEV Shops") - its own downloadable sample ZIP turned
out to be a single-municipality demo (Zell am See, 190 real rows), not
the national dataset. A **separate, free, CC-BY-4.0 product line** is
published directly on BEV's own GeoNetwork data portal,
`data.bev.gv.at` (distinct from the general `data.gv.at` national
portal, a JS SPA with no easily discoverable API) - confirmed live via
its own ISO19139 metadata: *"Für dieses Produkt gilt die Standardlizenz
CC-BY-4.0"*, access constraint `noLimitations`.

**137,767 real national street rows, 100% carrying a real name, zero
duplicate `SKZ`** - the same pure name-registry shape ANNCSU (Italy)
already established. Joined against a real 2,092-row municipality table
(`GEMEINDE.csv`, a clean 1:1 join confirmed against the complete
dataset) so `administrative_area` carries a resolved name, not a bare
code - unlike Denmark's DAR, which left its own raw kommune code
unresolved since no lookup table was fetched there.

**No geometry anywhere in this resource - `GeometryGrade.ABSENT` on
every real `Street`, not a gap in this build.** Real coordinates exist
only on a much larger sibling address-level resource (a real 325 MB
`ADRESSE.csv`, plus a separate ~183 MB INSPIRE address product,
`AT-INSPIRE_AD_Address`, both confirmed live) - deliberately not
fetched here, the same streets-built/address-side-scoped-out call
ANNCSU already made for its own `accessi` sibling.

**A real, disclosed limitation: a dated snapshot, no stable "latest"
alias found.** This product is published periodically (roughly twice
yearly - live-confirmed Stichtag dates include 01.04.2025 and
01.10.2025) under a URL that bakes the snapshot date in
(`..._Stichtagsdaten_20251001.zip`) - `BASE_URL` points at the most
recent snapshot confirmed live at investigation time (2026-08-18); a
future maintainer will need to update it once BEV publishes a newer
one, a real constraint stated honestly rather than engineered around.

**Licence: Creative Commons Attribution 4.0 International (CC BY
4.0)**, confirmed live from this product's own ISO19139 metadata -
required attribution wording stated verbatim: *"© Österreichisches
Adressregister, Stichtagsdaten vom 01.10.2025"* (the date changes per
snapshot).

**No credentials required** - every claim above came from a fully
unauthenticated GET request.

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

**The candidate URL first proposed (`data.gv.at`) turned out
to be a JS-rendered SPA - the real data lives directly on Vienna's own
GeoServer WFS instead.** A plain unauthenticated fetch of any
`data.gv.at` catalogue page, including the CKAN-style API path the
early dataset naming implied, returns an identical empty shell,
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

**A real correction to the initial framing: this is a
permit register, not an operator publishing only its own works.** Vienna's
dataset was first assumed "operator"-graded (Stadt Wien as the
traffic authority publishing its own works) - but `ANTRAGSTELLER`
(applicant)'s real values are genuine third-party applicants:
`Wiener Netze - Bereich Fernwärme`/`Bereich Gas` (the electricity/gas
utility), `Wiener Linien GmbH & Co KG` (the transit operator),
`Wienkanal` (the sewage utility), even `Privater Bauträger` (a private
developer) - alongside city departments (`MA28`/`MA31`/`MA29`). This
SDK ships it `source_grade = REGISTER`, the same tier as
Copenhagen/Helsinki/NYC DOT/Chicago, correcting the initial assumption.
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

## ASFINAG (national motorway network) — Credentials wanted

Austria's national motorway/expressway roadworks source — ASFINAG's own
genuine DATEX II feed, the same credential-gated shape as Denmark's
Vejdirektoratet, but **less confirmed**: even the auth mechanism itself,
not just the credential value, is unknown. Do-not-dedupe against Vienna
above — genuinely different road tiers, national motorways vs. one
city's higher-order network.

```python
from streetworks.datex2.austria import AsfinagClient
from streetworks.common import from_datex2

# base_url is issued at registration; auth mechanism is unconfirmed, so
# this client accepts a pre-configured httpx.Client instead of guessing one
with AsfinagClient(base_url=pull_url, client=my_authenticated_httpx_client) as asfinag:
    for situation in asfinag.iter_situations():
        works = from_datex2(situation, territory="Austria")
```

**Confirmed from ASFINAG's own official dataset page** on Austria's
National Access Point (`mobilitaetsdaten.gv.at`, checked live 2026-08-14):
the dataset covers real event types `Baustellen` (roadworks),
`Instandhaltungsarbeiten` (maintenance), `Sanierungen` (renovations),
stated explicitly as **DATEX II Situations with SituationRecords**, on
the ASFINAG motorway/expressway network. Real technical metadata is
stated (format XML, update rate 1 minute, transfer mode pull), but no
sample is downloadable without registration.

**A hoped-for keyless RSS shortcut was checked live and ruled out, not
just assumed unavailable.** A genuinely keyless public RSS/ATOM feed
exists on the same NAP, but its own page states explicitly it covers
"unplanned and safety-related traffic events," filed under "Road events
and conditions," not "Road work information" (the roadworks dataset's
own category) — confirmed live that this keyless route does not carry
roadworks. Unlike Italy's CCISS, there's no keyless shortcut for Austria.

**No hardcoded data URL, and no confirmed auth scheme — genuinely more
open than Vejdirektoratet in one sense, less confirmed in another.** The
dataset page states access requires registration via ASFINAG's own
Content Portal (`contentportal.asfinag.at`), but neither that page, its
licence terms, nor its JS bundle (read directly, the same technique that
found Roma's/Lisboa's/Oslo's real backends) state the real pull URL or
credential mechanism. `AsfinagClient` therefore takes `base_url` as a
required argument and accepts a pre-configured `httpx.Client` rather
than guessing a header name or auth scheme.

**Licence: CC-BY-4.0, confirmed live, with real supplementary conditions
beyond plain CC-BY.** Confirmed directly from ASFINAG's own licence page:
the base licence is unmodified CC BY 4.0, but registration requires
accepting real supplementary conditions — disclosing your own downstream
services built on this data back to ASFINAG, and ASFINAG reserving the
right to publicly reference your name when describing that it supplies
you data. Credentials: registration via the
[ASFINAG Content Portal](https://contentportal.asfinag.at/) (confirmed
live and reachable) — whether it's genuinely self-service or requires
manual approval is itself unconfirmed. See
[`docs/providers/index.md#credentials-wanted`](index.md#credentials-wanted)
for the condensed table entry.
