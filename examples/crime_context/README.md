# Crime context map

A neighbourhood-level recorded-crime **context** map for one police force,
built entirely on `streetworks.police.PoliceClient` and
`streetworks.police.SAFETY_RELEVANT_CATEGORIES`. Intended as background
context for lone-worker and night-shift planning around street works - not a
risk score, not a risk assessment, and not a substitute for one.

```bash
python generate_map.py --force leicestershire
```

Writes a self-contained `crime_context.html` (default; override with
`--out`). First run for a force takes a few minutes (a force's
neighbourhoods across a 3-month window is still a few hundred real API
calls); results are cached to disk (`./cache/` by default, `--cache-dir`
to change it) so re-runs are near-instant. Be a good API citizen, per this
SDK's own design principle - don't delete the cache and re-run repeatedly
for no reason.

## Method, in brief

1. `PoliceClient.neighbourhoods(force)` for the area list;
   `neighbourhood_boundary()` for each team's polygon.
2. For each neighbourhood, `street_level_crimes_in_area()` once per month
   over a rolling 3-month window, filtered client-side to
   `SAFETY_RELEVANT_CATEGORIES` (violent crime, public order,
   anti-social behaviour, robbery, possession of weapons - **not** property
   crime, which this SDK's own `SAFETY_RELEVANT_CATEGORIES` deliberately
   excludes, see its own comment in `streetworks/police/client.py`).
3. The window always ends at the most recent month
   `PoliceClient.street_level_availability()` itself reports data for -
   never a fixed number of months guessed back from today. An earlier
   version guessed (`crime-last-updated`'s month minus a further 2-month
   buffer), which silently compounded into a 4-5 month lag rather than the
   ~2 months intended; querying a month the API hasn't published yet
   returns an empty result that reads as falsely "safe".
4. The denominator is the neighbourhood boundary's own area in km² (the API
   states no population or address count). Rates are shrunk toward the
   force-wide mean, more for smaller areas, then banded into quintiles
   **within the force only**.
5. Areas with too few recorded crimes over the whole window are shown
   unshaded, not coloured - not enough data to say anything, not "zero
   crime".

Full reasoning (why 3 months and not longer, why area and not
population, the exact shrinkage formula) is in `generate_map.py`'s own
module docstring and inline comments - read those before changing any of
the tunables at the top of the file. The same method/limitations summary is
also embedded directly in the output HTML's side panel, deliberately not
behind a toggle - if someone screenshots the map, the caveats travel with
it.

## What this deliberately does not do

- **No per-street or per-address scoring.** Recorded crime locations are
  snapped to anonymised points (often the middle of a street, sometimes
  100m+ off), so a street-level figure would measure the snapping as much
  as the crime. Neighbourhood-level area counts are the finest grain this
  is defensible at.
- **No national or cross-force comparison.** Bands are quintiles within one
  force's own neighbourhoods. A different force's "above force typical"
  band is not comparable to this one's - different force, different
  distribution, different quintile edges.
- **Nothing here is named "risk", "score", or "index".** It is context. A
  dark cell means "more recorded safety-relevant crime than most of this
  force's other neighbourhoods over the recent window," and nothing more
  specific than that.
- **Not a lone-worker risk assessment.** It can inform one; it is not one,
  and the output deliberately avoids any visual or textual framing (colour,
  wording) that would make it read like a finished judgement rather than
  one input among several.

## A real, acknowledged approximation

Neighbourhood policing team boundaries are redrawn from time to time - force
boundaries are stable, NPT boundaries are not. This tool aggregates several
months of crime against **today's** boundary polygon, which silently mixes
geographies for any month where the true boundary differed. The correct fix
is to fetch each month's crime against that month's own historical boundary,
published in the archive at
[data.police.uk/data/boundaries](https://data.police.uk/data/boundaries/) -
not implemented here. The short (3-month) window is a deliberate
approximation of that fix, not a considered trade-off against it - shorter
still reduces the risk further, at the real cost of more suppressed
(low-count) neighbourhoods; see `generate_map.py`'s own module docstring.

Likewise: an address count (from `streetworks.openusrn` or
`streetworks.datavia`) or a population figure would both be a better rate
denominator than bare polygon area, since crime risk tracks people and
footfall, not land area. A works-hours-weighted denominator would be
better again for this SDK's own lone-worker framing. None of those are
wired up here.

## Presentation choices, and why

- **A sequential single-hue (teal) ramp, not red/amber/green.** RAG carries
  an action semantics ("stop", "proceed with caution") this data cannot
  support - a red patch over a housing estate says something a dark-teal
  patch does not, and this data doesn't support saying it. This is the
  single choice that makes the rest of the map defensible.
- **Band labels are relative and say so** - "above force typical", not
  "high" - because the underlying banding *is* relative (quintiles within
  one force), and a label implying an absolute judgement would overstate
  what the data supports.
- **Every popup shows its own workings**: raw count, area, raw rate,
  shrunk/adjusted rate, band. Anyone looking at one cell can see exactly
  why it's shaded the way it is, not just trust the colour.
- **The legend always lists "too few crimes to band"**, whether or not a
  given run happened to suppress anything - a reader needs to be able to
  tell suppressed-grey from a real band the moment they see it, not only
  after the fact.
- **Basemap tiles are CARTO Positron, not the standard OSM style.** OSM's
  own tile usage policy excludes this kind of embedded/redistributed use,
  and the tiles 403 outright when this file is opened over `file://` (no
  `Referer` header to satisfy them). The muted grey basemap is also the
  better cartographic choice - a busier basemap competes with the
  choropleth for attention.

## Dependencies

Standard library, plus `streetworks` itself. `shapely` is used for proper
polygon simplification/repair if it happens to be installed, with
even-stride decimation as an always-available fallback - not a hard
dependency of this example.

## Attribution

Data © Crown copyright and database rights, contains public sector
information licensed under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/),
via [data.police.uk](https://data.police.uk/). Credited on the generated
page itself, in the method panel.

## Reference implementation note

The aggregation/shrinkage/banding/rendering logic here started from a
standalone prototype built directly against the raw API (no SDK, plain
`requests`). Two corrections were made porting it in: the prototype used the
wrong crime-category set (it included vehicle crime and criminal damage -
this version uses `SAFETY_RELEVANT_CATEGORIES` instead, per the point of
showcasing that constant), and its whole HTTP layer was replaced by
`PoliceClient`.
