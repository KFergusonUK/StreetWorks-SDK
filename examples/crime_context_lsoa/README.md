# LSOA-level crime context, keyed to a worksite

Successor to [`examples/crime_context/`](../crime_context/) (the
neighbourhood-policing-team version). Same purpose - background context for
lone-worker and night-shift planning around street works, not a risk score,
not a risk assessment - but finer geography, a real population denominator,
and reframed around the question a planner actually asks: "I'm sending a
crew to this worksite - what's the context?" rather than a force-wide
ranking of areas.

```bash
python -m examples.crime_context_lsoa.report \
  --force durham --point 54.6109,-1.5568 --radius-m 300
```

Writes a self-contained `worksite_context.html` (default; override with
`--out`). Unlike the neighbourhood-level example, the first run for a force
is fast: ingestion is one bulk CSV download per date range (see "What
changed, and why" below), not hundreds of live queries - a full 12-month
Durham run, cold cache, took 13 seconds in testing. Results are still
cached to disk (`./cache/` by default, `--cache-dir` to change it).

## What changed from the neighbourhood-level version, and why

**LSOA instead of neighbourhood policing team.** A neighbourhood policing
team map is, in effect, a population-density map - crimes per km² rises
with people per km², which tells a planner something they already knew.
LSOAs are built by ONS to hold a roughly equal ~1,500 residents each, so a
town the size of Newton Aycliffe becomes fifteen to twenty areas instead of
one.

**A population denominator instead of area.** LSOAs are population-equal by
design; crimes per 1,000 residents per year says something crimes per km²
cannot, since crime exposure tracks people and footfall, not land area.

**A bulk CSV download instead of hundreds of polygon queries.** Verified
live: data.police.uk's "custom download" (https://data.police.uk/data/) is
a CSRF-protected HTML form plus an async job, not a JSON API endpoint, but
fully scriptable with a plain cookie jar and no browser - see
`PoliceClient.bulk_download_csv()`'s own docstring for the details and the
one real, live-verified caveat (a per-force export carries a small amount
of geographic cross-force contamination, handled by this package's
`ingest._in_force_rows`, not by the API). This is also why the default
window went back up to **12 months**, having been 3 for the neighbourhood
version: that shorter window existed specifically to bound a now-gone
cost (hundreds of sequential live polygon queries). At ~1,500 residents an
LSOA, a short window's count is frequently single digits - shrinkage helps
but doesn't fully protect against that, so a longer window is the better
trade once its only real cost is a few extra seconds of download.

**No separate category-mapping file needed.** The brief for this example
expected `police-uk-category-mappings.csv` would be required to translate
the CSV's human-readable `Crime type` column ("Violence and sexual
offences") into the JSON API's slugs (`violent-crime`) that
`SAFETY_RELEVANT_CATEGORIES` uses. Live-checked: that file maps something
else entirely (granular Home Office offence codes to a different category
scheme). The real mapping is already available for free from
`PoliceClient.crime_categories()`, whose `name`/`url` pairs match the CSV's
`Crime type` column exactly, confirmed character-for-character live.

**Keyed to a worksite, not a whole-force ranking.** Input is a point and a
radius (buffered, live-tested), or a USRN (see "USRN input" below). The
output leads with that one place's own numbers; the whole-force LSOA layer
is still computed - bands are relative to the whole force, which needs the
whole force's data to mean anything - and still rendered as map background,
but muted, with the worksite highlighted on top. The ranked map is context
behind the answer, not the answer itself.

## Architecture: why this isn't in `streetworks` itself

**`streetworks` is a street works and roadworks client library. It should
not grow a demographics or census-geography module because one example
needed a population denominator.** The split:

- `PoliceClient.bulk_download_csv()` lives in `streetworks.police` - it's
  real police data, reached through a real (if unusual) data.police.uk
  route, same as every other method on that client.
- ONS 2021 LSOA population and boundary handling (`ons.py`) is
  example-local, with its own dependency (none extra, in fact - it queries
  a public ArcGIS FeatureServer through the SDK's own general-purpose
  `streetworks.arcgis.ArcGISFeatureClient`, already used elsewhere in this
  SDK for Jersey's roadworks and US TIGERweb boundaries. One live discovery
  worth recording: ONS's own "Number of Usual Residents" (TS001) layer
  carries boundary geometry *and* population together in the same query -
  see `ons.py`'s own docstring for why that also removes the 2011/2021
  LSOA-vintage-mixing risk this brief was concerned about at the source,
  not just at a downstream check.
- Worksite geometry (`worksite.py`) is also example-local, and does need a
  real dependency: `shapely`, for buffering and polygon intersection -
  unlike the neighbourhood example, where shapely was a nicety with a
  stdlib fallback, it's the actual point here and isn't optional.

This ended up spanning enough (police ingestion, ONS integration, worksite
geometry, stats) that it's a small package, not a single script like the
neighbourhood example - `report.py` ties the others together and is the
CLI entry point.

## USRN input (implemented, not live-tested end-to-end)

```bash
python -m examples.crime_context_lsoa.report \
  --force durham --usrn 12345678 \
  --usrn-geopackage /path/to/osopenusrn.gpkg --radius-m 300
```

Resolves the USRN's geometry via `streetworks.openusrn.reader.UsrnDatabase`
against an **already-downloaded** OS Open USRN GeoPackage
(`OpenUSRNClient.download()`) - confirmed live to be a genuine ~300MB
product, too large to fetch as part of this example's own development and
verification. The point+radius path above is the one actually exercised
end-to-end against real Durham data; the USRN path follows `UsrnDatabase`'s
already-tested, documented behaviour faithfully; but it has not itself been
run against a real file in building this example. It also uses a different
coordinate system deliberately - see `worksite.py`'s own docstring for why
(the short version: the GeoPackage's native British National Grid, kept
native rather than reprojected, to avoid needing a real OSGB36 transform
this module doesn't implement).

## What this data cannot tell you

- **There is no time of day in this data.** It is month-level only. An area
  with high daytime public-order counts near a shopping precinct is a
  different proposition at 2am than the same count near a pub strip at
  closing time - the source cannot distinguish them. This is probably the
  single most important limitation for a lone-worker decision, and it is
  invisible unless named - so it's named, in the page's own always-visible
  panel, not just here.
- **Anti-social behaviour is reporting-sensitive.** It's likely the most
  relevant category here for abuse directed at road crews, and it also
  reflects how readily an area's residents report things as much as what
  actually occurs. It should not be the swing factor on its own.
- **Each LSOA is derived from crime locations already snapped to
  anonymised points**, so it inherits that displacement - tolerable at
  LSOA size, least reliable for a worksite sitting near an LSOA's edge.

## What this deliberately does not do

- **No per-street, per-address, or per-USRN crime figure.** A real map
  point covers at least eight postal addresses, or none, and the true
  coordinates are already replaced by the map point's - LSOA sits above
  that floor, nothing finer does.
- **No ranking of areas as a headline output.** The whole-force layer is
  computed and shown, but as map background behind the highlighted
  worksite, not the page's subject.
- **No cross-force or national comparison.** Bands are quintiles (or
  terciles, or refused entirely below a floor - see `stats.py`) within this
  force's own LSOAs only.
- **Nothing here is named "risk", "score", or "index".** It informs a
  deployment decision - two-person crew, check-in interval, lighting,
  vehicle positioning - it is not a lone-worker risk assessment and is not
  a substitute for one. Sightlines, egress, proximity to licensed premises,
  and whether the crew works in hi-vis beside a lit vehicle or on foot
  after dark all matter and none of them are in this data.

## Dependencies

`shapely` (required, not optional, unlike the neighbourhood example -
buffering and polygon intersection are this package's actual job) plus
`streetworks` itself.

## Attribution

Crime data © Crown copyright and database rights, data.police.uk. Population
and boundary data © Crown copyright and database rights, Office for
National Statistics. Both licensed under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
Credited on the generated page itself, in the method panel.
