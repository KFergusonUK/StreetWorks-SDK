# Italy

> Migrated verbatim from README.md's `## Italy — CCISS (traffic bulletin
> RSS)` section (phase one, lossless restructure — see
> `docs/migration-mapping.md`).

## CCISS (traffic bulletin RSS)

Confirmed as Italy's own official RTTI/SRTI National Access Point (per
the European Commission's own October 2025 National Access Points
list), reached here via the real, public, **keyless** RSS route rather
than the registration-gated DATEX II one:

```python
from streetworks.cciss import CcissClient
from streetworks.common import from_cciss

with CcissClient() as cciss:
    roadworks = [i for i in cciss.fetch() if i.is_roadworks]
    works_list = [from_cciss(i) for i in roadworks]
```

**Genuinely different shape from TrafficWatchNI/Traffic Wales, despite
looking similar** — those two already serve roadworks-only feeds (see
[`docs/providers/uk.md`](uk.md)); CCISS
publishes one real, mixed stream (roadworks, weather, breakdowns,
accidents, demonstrations, debris/spill incidents), confirmed live 100
real items at a time, 78 of them real roadworks. Filtering happens via
`item.is_roadworks` — a real, evidenced classification (contains
`lavori`/`personale su strada`/`pulizia del manto stradale`), not a
closed enum, since the real event-type text is free Italian prose with
too much genuine variety to force into one (`manifestazione`, `veicolo
fermo o in avaria`, `tratto chiuso causa lavori`, `perdita di carico`,
...).

**No geometry** — the real feed carries only `title`/`description`/
`pubDate`/`dc:date`, confirmed directly against the live XML (an
earlier AI-summarised read of the CCISS homepage wrongly suggested items
were georeferenced; the real RSS feed isn't).

The registration-gated DATEX II route (same `cciss.it` domain, richer
structured data under RTTI) remains available as a separate, later
option if you register — not pursued here. **Licence unconfirmed** — no
reuse licence was found stated for this feed.

## Roma (Roma si trasforma)

Roma Capitale's own civic-interventions tracker, filtered to real,
currently in-progress street/infrastructure work — this SDK's second
Italy provider and first Rome-municipal source:

```python
from streetworks.roma import RomaClient
from streetworks.common import from_roma

with RomaClient() as roma:
    interventi = list(roma.iter_roadworks())  # Strade e infrastrutture + Cantiere only
works = from_roma(interventi)
```

**Built from `rome-athens-investigation.md`, but the brief's proposed
source doesn't exist as described.** The brief proposed Roma Servizi per
la Mobilità's (RSM) ArcGIS Hub (`data-rsm.opendata.arcgis.com`),
reasoning RSM "explicitly tracks cantieri" so a roadworks layer was
"very likely" present in its open data. Checked live before writing any
code: RSM's real DCAT feed lists 81 real datasets — ZTL zones, bike
infrastructure, metro/tram lines, bus lanes, traffic signals, parking,
mobility managers — and **not one is roadworks-related**. Roma
Capitale's own CKAN portal (`dati.comune.roma.it`, the brief's own named
fallback) was checked next — zero real results for "cantieri", "lavori",
"viabilità" or "opere" via its real search API. **The real source is a
third site the brief never named**: `romasitrasforma.it` ("Roma si
trasforma"), a Drupal-based civic-projects portal, found by reading its
own custom Drupal module's bundled JS
(`modules/custom/roma_api_mappa/assets/main.js`) — the same technique
that found Lisboa's and Road Report NT's real backends.

**A genuinely broader scope than "roadworks" — this is Rome's general
capital-projects tracker, not a dedicated register.** 1215 real records
span four macro-themes: Sostenibilità (sustainability — 624), Inclusione
(schools, housing — 285), Cultura (restorations, museums — 239),
Innovazione (digital infrastructure — 67). Street/road maintenance is
one sub-tag among many, confirmed via the portal's own `/api/filtri`
taxonomy endpoint, not guessed.

**Roadworks filter: `field_tag_temi` contains `"Strade e
infrastrutture"` AND `field_stato_lavori == "Cantiere"`** (a closed
project-lifecycle taxonomy — `Progettazione` → `Gara` → `Cantiere` →
`Fine lavori`). 252/1215 real records carry the "Strade e
infrastrutture" tag; only 69 of those are currently `Cantiere`
(in progress) rather than already finished, still in design, or out to
tender. **This is the thinnest real roadworks signal of any municipal
provider this SDK has built** — 69/1215 (5.7%) of the source feed, not
a dedicated roadworks feed — real titles confirm it's genuine street
work when filtered this way (`Manutenzione straordinaria di Via
Portuense`, `Riqualificazione pavimentazioni storiche...`), not noise.

**A real bug in the source, found and corrected, not reproduced.** The
`field_posizione` object's own key names are swapped relative to true
geography — what the source calls `"lon"` holds latitude-range values
(~41.7–42.1, Rome's real latitude band) and what it calls `"lat"` holds
longitude-range values (~12.2–12.8, Rome's real longitude band),
confirmed against every real coordinate in this pull. `from_roma` reads
them into their correct meaning rather than trusting the source's own
key names.

**No date fields exist anywhere in this schema** — a first for a
municipal provider in this SDK. `field_stato_lavori` is a project-
lifecycle category, not a calendar value; `date_confidence` is always
`UNKNOWN` and no `proposed_start`/`proposed_end` are populated.

**Geolocation is genuinely partial even within the filtered subset**:
35/69 real "Cantiere" + "Strade e infrastrutture" records carry a real
coordinate; the other 34 have only a district-level `field_municipio`
(Roman numeral, I–XV) and sometimes a free-text address, no point.

**Licence: genuinely unconfirmed** — checked the live site's page text,
footer, and common Italian open-data terms (licenza, IODL, riutilizzo,
copyright, note legali); none found stated anywhere.

## Athens — checked, off the board

Investigated alongside Rome (same brief) as a second Mediterranean-
capital municipal candidate — confirmed, not assumed, that no roadworks
open data exists for the City of Athens at any level. Beyond the checks
the investigation brief itself ran (`cityofathens.gr`, the Greek
national NAP — see [`docs/providers/index.md`](index.md#credentials-wanted)
and `streetworks.greece`'s own module docstring for the national-level
finding this repeats), a genuinely promising lead the brief hadn't found
was checked directly: Athens runs a real, live OGC API Features server
(`api.gis.cityofathens.gr`, `pygeoapi`) — but its real collection list
is exactly three layers (`lakes`, `geitonies` — neighbourhood
boundaries, `athens_ot` — building blocks), none of them roadworks. The
Greek national NAP (`data.nap.gov.gr`) was independently re-checked too
and still returns a live 502 from its own CKAN backend, matching this
SDK's existing Greece finding. Recorded here, not scaffolded as its own
module: this confirms and extends an existing finding
(`streetworks.greece`) rather than surfacing a new technical shape
worth its own package.
