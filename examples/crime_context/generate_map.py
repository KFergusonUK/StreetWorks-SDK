#!/usr/bin/env python3
"""Neighbourhood-level crime *context* map for one police force.

Builds a self-contained HTML map, banded by neighbourhood policing team
(NPT), for lone-worker and night-shift planning context. Everything it does
goes through :class:`~streetworks.police.PoliceClient` and
:data:`~streetworks.police.SAFETY_RELEVANT_CATEGORIES` - it does not reach
around the SDK, and it does not add property-crime categories the library
deliberately excludes (see ``SAFETY_RELEVANT_CATEGORIES``'s own comment).

Run: python examples/crime_context/generate_map.py --force leicestershire

See README.md in this directory for the method, its limitations, and what
this deliberately does not attempt - the same panel is embedded in the
output HTML itself, because a screenshot of the map should carry the
caveats with it.

-------------------------------------------------------------------------
Why a 3-month window, not something longer or shorter (read this before
changing DEFAULT_WINDOW_MONTHS)
-------------------------------------------------------------------------
Neighbourhood policing team boundaries are redrawn periodically - month to
month, in practice. Force boundaries are stable; NPT boundaries are not.
Querying many months of crime against *today's* boundary polygon silently
mixes geographies for any month where the boundary differed. The correct
fix is to fetch each month's crime against that month's own boundary, from
the historical boundary archive at
https://data.police.uk/data/boundaries/ - not implemented here. A shorter
window reduces that risk further (less time for a boundary to have moved
under the query), and this SDK's own good-API-citizenship principle favours
the smaller number of live calls a shorter window needs (a force's
neighbourhoods x 3 months, not x 12) - both real, deliberate reasons to
prefer 3 months over 12, not just a smaller default for its own sake.

The real cost: fewer months means fewer recorded crimes to sum per area,
which pushes more (especially rural, already-quiet) neighbourhoods below
MIN_COUNT_TO_BAND and into "too few crimes to band" - suppression is the
*correct* response to less data, not a defect, but it does mean a 3-month
run will show more grey than a 12-month one, most visibly in exactly the
low-crime areas a rural/urban contrast is trying to show. If that trade
stops being worth it, raise this back toward 12 (or pass
--window-months 12) rather than lowering MIN_COUNT_TO_BAND to compensate -
the count floor is about whether there's enough data to trust, not about
producing a target amount of colour on the map.

-------------------------------------------------------------------------
Why area (km^2), not population or address count
-------------------------------------------------------------------------
The Police API states neither. Area, from the boundary polygon this SDK
already has, is the *cheap and honest* denominator - not the *right* one.
An address count (from streetworks.openusrn or streetworks.datavia) or a
population figure would both make a better rate denominator, since crime
risk tracks people and footfall, not bare land area. A works-hours
denominator would be better again for this SDK's actual lone-worker
framing. None of those are wired up here - flagged, not solved.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

from streetworks.exceptions import ServerError
from streetworks.police import SAFETY_RELEVANT_CATEGORIES, PoliceClient

JSON = dict[str, Any]
Point = tuple[float, float]

# --------------------------------------------------------------------------- #
# Tunables - see the module docstring for why these specific values
# --------------------------------------------------------------------------- #

#: See the module docstring's "Why a 3-month window" section before changing.
DEFAULT_WINDOW_MONTHS = 3

#: The API publishes street-level crime in arrears; the most recent month or
#: two commonly comes back partial or empty, which would misleadingly read
#: as "safe". Always skipped, counted back from the API's own last_updated().
SKIP_RECENT_MONTHS = 2

#: Below this many safety-relevant crimes over the *whole* window, a
#: neighbourhood is rendered unshaded/"too few crimes to band" rather than
#: coloured - a handful of crimes in a small area is Poisson noise, not a
#: real signal, and shrinkage alone doesn't fully protect against that at
#: the low end. Five is a judgement call, not derived from anything.
MIN_COUNT_TO_BAND = 5

#: Ring vertex target before a neighbourhood boundary is used in a crimes
#: query - see decimate_ring().
TARGET_QUERY_VERTICES = 150

# --------------------------------------------------------------------------- #
# Banding tiers. Quintiles need enough bandable areas that each bin means
# something - a force with 6 neighbourhoods put into 5 quintile bins gives
# 1-2 areas per bin, which is a coin flip dressed up as a percentile. Below
# the quintile floor, fall back to terciles (3 bins - coarser, but each bin
# still holds a handful of areas); below the tercile floor, refuse to band
# at all rather than publish a map whose bins are statistically meaningless.
# A force the size of the City of London (6 real neighbourhoods) sits right
# at the tercile floor by design, not by coincidence - it's the real,
# smallest-force case this tier structure was built to handle honestly.
# --------------------------------------------------------------------------- #

#: At least 3 areas per bin, rounded down, for a 3-bin split to say anything.
MIN_AREAS_FOR_TERCILES = 6

#: At least 3 areas per bin, rounded down, for a 5-bin split to say anything.
MIN_AREAS_FOR_QUINTILES = 15

#: Relative, not absolute - see the module/README's own repeated point that
#: this is context, not a risk score. Never compared across forces.
BAND_LABELS_5 = [
    "well below force typical",
    "below force typical",
    "around force typical",
    "above force typical",
    "well above force typical",
]

#: A sequential single-hue (teal) ramp, light -> dark. Deliberately not
#: red/amber/green - RAG carries an action semantics this data cannot
#: support (see README.md).
BAND_COLORS_5 = ["#e3f3f1", "#a8dad4", "#69b8ae", "#2f8577", "#0b4f45"]

#: The tercile fallback - three labels, not five, over the same real
#: vocabulary the brief for this example specified in the first place.
BAND_LABELS_3 = ["below force typical", "around force typical", "above force typical"]

#: Three well-spaced steps from the same ramp as BAND_COLORS_5 - not a
#: different palette, just fewer stops on it.
BAND_COLORS_3 = ["#a8dad4", "#69b8ae", "#0b4f45"]

#: Grey, not a "band colour" at all - suppressed cells (and, when the whole
#: force can't be banded, every cell) are explicitly excluded from the
#: colour scale, not the lightest band on it.
SUPPRESSED_COLOR = "#d9d9d9"


# --------------------------------------------------------------------------- #
# Disk cache - a force's neighbourhoods x 3 months is still a few hundred
# real API calls; re-runs should be instant. Never caches a failed call (see
# fetch_month_counts) so a transient error doesn't get "stuck" as if it
# were a real empty result.
# --------------------------------------------------------------------------- #


def cached(cache_dir: Path, key: str, fetch: Any) -> Any:
    path = cache_dir / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    result = fetch()
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result), encoding="utf-8")
    return result


# --------------------------------------------------------------------------- #
# Month window
# --------------------------------------------------------------------------- #


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


def month_window(latest_available: str, *, window_months: int, skip_recent: int) -> list[str]:
    """``latest_available`` is ``PoliceClient.last_updated()``'s own
    ``YYYY-MM-DD`` - only year/month are used. Returns ``window_months``
    real ``"YYYY-MM"`` strings, oldest first, ending ``skip_recent`` months
    before the API's own latest."""
    year, month = (int(p) for p in latest_available.split("-")[:2])
    year, month = _shift_month(year, month, -skip_recent)
    months = []
    for _ in range(window_months):
        months.append(f"{year:04d}-{month:02d}")
        year, month = _shift_month(year, month, -1)
    return list(reversed(months))


# --------------------------------------------------------------------------- #
# Ring geometry - area and decimation
# --------------------------------------------------------------------------- #


def ring_area_km2(ring: list[Point]) -> float:
    """Approximate polygon area in km^2: an equirectangular projection
    centred on the ring's own mean latitude, then the shoelace formula.
    Fine at neighbourhood scale (a few km across); would need a real
    projection for anything bigger. See the module docstring for why area,
    not population/address count, is this example's denominator at all."""
    if len(ring) < 3:
        return 0.0
    mean_lat = sum(p[0] for p in ring) / len(ring)
    km_per_deg_lat = 110.574
    km_per_deg_lng = 111.320 * math.cos(math.radians(mean_lat))
    xy = [(lng * km_per_deg_lng, lat * km_per_deg_lat) for lat, lng in ring]
    area = 0.0
    for i in range(len(xy) - 1):
        x1, y1 = xy[i]
        x2, y2 = xy[i + 1]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def decimate_ring(
    ring: list[Point], *, target_vertices: int = TARGET_QUERY_VERTICES
) -> list[Point]:
    """Reduce a ring to roughly ``target_vertices`` points before using it
    in a crimes query - both to keep the ``poly`` string manageable and
    because full rings carry redundant vertices
    (:meth:`PoliceClient.neighbourhood_boundary` itself documents that real
    rings aren't guaranteed simple - near-duplicate vertices, the odd
    spike). Uses ``shapely`` (``simplify()`` + ``buffer(0)`` repair,
    logging which rings needed repair) if it's installed; even-stride
    decimation otherwise, which is adequate for the query but does nothing
    about a genuinely self-intersecting ring."""
    if len(ring) <= target_vertices:
        return ring
    try:
        import shapely.geometry as geom
    except ImportError:
        stride = max(1, len(ring) // target_vertices)
        decimated = ring[::stride]
        if decimated[-1] != ring[-1]:
            decimated.append(ring[-1])
        return decimated

    polygon = geom.Polygon([(lng, lat) for lat, lng in ring])
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
        print("    (shapely: repaired a self-intersecting ring via buffer(0))", file=sys.stderr)
    simplified = polygon.simplify(0.0005, preserve_topology=True)
    return [(lat, lng) for lng, lat in simplified.exterior.coords]


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


def fetch_month_counts(
    police: PoliceClient,
    cache_dir: Path,
    force: str,
    neighbourhood_id: str,
    query_ring: list[Point],
    months: list[str],
) -> int:
    """Sum of SAFETY_RELEVANT_CATEGORIES crimes across ``months`` for one
    neighbourhood. A month that fails to fetch is skipped, logged, and
    never cached as if it were a real (empty) result - counting a failed
    query as zero crimes would render an unqueried area as safe."""
    total = 0
    for month in months:
        key = f"{force}_{neighbourhood_id}_{month}_crimes"
        try:
            crimes = cached(
                cache_dir,
                key,
                lambda ring=query_ring, month=month: police.street_level_crimes_in_area(
                    ring, date=month
                ),
            )
        except ServerError as exc:
            print(f"    ! {neighbourhood_id} {month}: {exc} - skipped, not counted as zero",
                  file=sys.stderr)
            continue
        total += sum(1 for c in crimes if c.get("category") in SAFETY_RELEVANT_CATEGORIES)
    return total


def build_stats(
    police: PoliceClient, cache_dir: Path, force: str, months: list[str]
) -> list[JSON]:
    teams = cached(cache_dir, f"{force}_neighbourhoods", lambda: police.neighbourhoods(force))
    stats = []
    for i, team in enumerate(teams, 1):
        nid = team["id"]
        print(f"  [{i}/{len(teams)}] {nid} {team['name']}", file=sys.stderr)
        raw_boundary = cached(
            cache_dir,
            f"{force}_{nid}_boundary",
            lambda nid=nid: [
                {"lat": lat, "lng": lng}
                for lat, lng in police.neighbourhood_boundary(force, nid)
            ],
        )
        boundary = [(p["lat"], p["lng"]) for p in raw_boundary]
        if len(boundary) < 3:
            print(f"    ! {nid}: fewer than 3 boundary points, skipping", file=sys.stderr)
            continue

        query_ring = decimate_ring(boundary)
        area_km2 = ring_area_km2(boundary)  # full ring - area shouldn't depend on decimation
        count = fetch_month_counts(police, cache_dir, force, nid, query_ring, months)
        stats.append(
            {
                "id": nid,
                "name": team["name"],
                "count": count,
                "area_km2": area_km2,
                "boundary": boundary,
            }
        )
    return stats


# --------------------------------------------------------------------------- #
# Shrinkage and banding
# --------------------------------------------------------------------------- #


def compute_bands(
    stats: list[JSON], *, min_count: int = MIN_COUNT_TO_BAND
) -> tuple[list[JSON], str | None]:
    """Shrink rates toward the force mean, then band into quintiles (or,
    below :data:`MIN_AREAS_FOR_QUINTILES` eligible areas, terciles; or,
    below :data:`MIN_AREAS_FOR_TERCILES`, not at all - see the constants'
    own comments for why). Returns ``(stats, banding_note)`` -
    ``banding_note`` is ``None`` when normal banding happened, otherwise a
    human-readable reason the whole force went unbanded, meant to be shown
    to the reader, not just logged.
    """
    for s in stats:
        area = s["area_km2"]
        s["raw_rate"] = s["count"] / area if area > 0 else None

    areas = [s["area_km2"] for s in stats if s["area_km2"] > 0]
    k = statistics.median(areas) if areas else 1.0
    total_count = sum(s["count"] for s in stats)
    total_area = sum(areas)
    force_rate = total_count / total_area if total_area else 0.0

    for s in stats:
        area = s["area_km2"]
        if area > 0:
            # Bayes-flavoured shrinkage toward the force-wide mean rate,
            # weighted by k (the median neighbourhood area) - a small area
            # contributes little evidence of its own and gets pulled hard
            # toward force_rate; a large one is barely shrunk. A fitted
            # Poisson-gamma model is the statistically proper version of
            # this; this is the fast, readable approximation, not that.
            s["adjusted_rate"] = (s["count"] + force_rate * k) / (area + k)
        else:
            s["adjusted_rate"] = None
        # This is the safety-critical branch: a suppressed area is rendered
        # unshaded/grey, deliberately never folded into the lightest real
        # band, so "not enough data" can never look identical to "genuinely
        # low crime" - see tests/test_examples_crime_context.py.
        s["suppressed"] = s["count"] < min_count or s["adjusted_rate"] is None

    bandable = sorted((s for s in stats if not s["suppressed"]), key=lambda s: s["adjusted_rate"])
    n = len(bandable)

    if n >= MIN_AREAS_FOR_QUINTILES:
        labels, colors, num_bands = BAND_LABELS_5, BAND_COLORS_5, 5
    elif n >= MIN_AREAS_FOR_TERCILES:
        labels, colors, num_bands = BAND_LABELS_3, BAND_COLORS_3, 3
    else:
        labels = colors = None
        num_bands = 0

    banding_note = None
    if num_bands:
        for i, s in enumerate(bandable):
            band_index = min(num_bands - 1, (i * num_bands) // n)
            s["band"] = band_index
            s["band_label"] = labels[band_index]
            s["band_color"] = colors[band_index]
    elif n > 0:
        # Enough non-suppressed areas to have real data, but too few to
        # split into even three meaningful bins - refuse rather than
        # publish a map whose colours are noise, per this branch's own
        # design intent above.
        banding_note = (
            f"This force has only {n} neighbourhood(s) with enough recorded crime "
            f"to compare (minimum {MIN_AREAS_FOR_TERCILES} needed for even a "
            "three-band split) - too few for a meaningful relative comparison, so "
            "no areas are banded or coloured on this map."
        )
        for s in bandable:
            s["band"] = None
            s["band_label"] = "too few neighbourhoods in this force to band"
            s["band_color"] = SUPPRESSED_COLOR

    for s in stats:
        if s["suppressed"]:
            s["band"] = None
            s["band_label"] = "too few crimes to band"
            s["band_color"] = SUPPRESSED_COLOR

    return stats, banding_note


# --------------------------------------------------------------------------- #
# HTML rendering
# --------------------------------------------------------------------------- #

_METHOD_PANEL_HTML = """
<div id="method-panel">
  <h2>What this map is</h2>
  <p>Recorded-crime <b>context</b> for lone-worker and night-shift planning, banded
  by neighbourhood policing team, within one police force. It is <b>not</b> a risk
  score or a risk assessment, and must not be read as one.</p>
  <h3>Method</h3>
  <ul>
    <li>Counts are {window} of recorded crime in the categories a lone worker's
    confrontation/threat/assault risk actually tracks (violent crime, public
    order, anti-social behaviour, robbery, possession of weapons) - not property
    crime.</li>
    <li>The two most recent months are always excluded - the API publishes in
    arrears and recent months read as falsely "safe".</li>
    <li>Rates are crimes per km&sup2; of the neighbourhood's boundary polygon -
    the API states no population or address count. An address count or
    population figure would be a better denominator; this is the honest cheap
    option, not the right one.</li>
    <li>Rates are shrunk toward the force-wide average, more so for smaller
    areas, so a handful of crimes in a small polygon doesn't dominate the map on
    statistical noise alone.</li>
    <li>Bands are <b>quintiles within this force only</b> - "above force typical"
    says nothing about how this force compares to any other.</li>
    <li>Grey areas had too few recorded crimes over the window to band
    meaningfully - not "zero crime", just not enough data to say anything.</li>
  </ul>
  <h3>What this deliberately does not do</h3>
  <ul>
    <li>No per-street or per-address scoring - crime locations are snapped to
    anonymised points, so a street-level figure would measure the snapping as
    much as the crime.</li>
    <li>No comparison across forces or nationally.</li>
    <li>Neighbourhood boundaries are redrawn over time; this map aggregates
    several months against today's boundaries as an approximation, not against
    each month's real boundary from the archive at
    <a href="https://data.police.uk/data/boundaries/" target="_blank" rel="noopener">
    data.police.uk/data/boundaries</a>.</li>
  </ul>
  <p>Contains public sector information licensed under the
  <a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
  target="_blank" rel="noopener">Open Government Licence v3.0</a>.
  &copy; Crown copyright and database rights, data.police.uk.</p>
</div>
"""


def render_html(
    *,
    force: str,
    months: list[str],
    stats: list[JSON],
    banding_note: str | None,
    out_path: Path,
) -> None:
    features = []
    for s in stats:
        popup_lines = [f"<b>{html.escape(s['name'])}</b> ({html.escape(s['id'])})"]
        popup_lines.append(f"Safety-relevant crimes ({len(months)} months): {s['count']}")
        popup_lines.append(f"Area: {s['area_km2']:.2f} km&sup2;")
        if s["raw_rate"] is not None:
            popup_lines.append(f"Raw rate: {s['raw_rate']:.2f} / km&sup2;")
        if s["adjusted_rate"] is not None:
            popup_lines.append(f"Adjusted rate: {s['adjusted_rate']:.2f} / km&sup2;")
        popup_lines.append(f"Band: {html.escape(s['band_label'])}")
        features.append(
            {
                "coords": [[lat, lng] for lat, lng in s["boundary"]],
                "color": s["band_color"],
                "popup": "<br>".join(popup_lines),
            }
        )

    window_desc = f"a rolling {len(months)}-month window ({months[0]} to {months[-1]})"
    method_panel = _METHOD_PANEL_HTML.format(window=window_desc)
    if banding_note:
        method_panel = (
            f'<div id="banding-note"><b>No areas banded:</b> {html.escape(banding_note)}</div>'
            + method_panel
        )

    # Build the legend from what's actually assigned in `stats`, not from a
    # fixed 5-band assumption - a force that fell back to terciles (or was
    # refused banding entirely) must not show a 5-swatch legend it never
    # used.
    seen: dict[str, str] = {}
    for s in sorted((x for x in stats if x["band"] is not None), key=lambda x: x["band"]):
        seen.setdefault(s["band_label"], s["band_color"])
    legend_items = "".join(
        f'<span style="background:{color}"></span> {html.escape(label)}<br>'
        for label, color in seen.items()
    )
    # band=None cells can carry two different real reasons (suppressed for
    # too few crimes in that one area, vs. the whole force going unbanded) -
    # show whichever of those actually occur, not just the first one found.
    unbanded_labels = dict.fromkeys(s["band_label"] for s in stats if s["band"] is None)
    legend_items += "".join(
        f'<span style="background:{SUPPRESSED_COLOR}"></span> {html.escape(label)}<br>'
        for label in unbanded_labels
    ).removesuffix("<br>")

    all_lats = [lat for s in stats for lat, _ in s["boundary"]]
    all_lngs = [lng for s in stats for _, lng in s["boundary"]]
    center = (
        [sum(all_lats) / len(all_lats), sum(all_lngs) / len(all_lngs)]
        if all_lats
        else [52.6, -1.1]
    )

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Crime context - {html.escape(force)}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body {{ margin: 0; height: 100%; font-family: system-ui, sans-serif; }}
  #map {{ position: absolute; top: 0; bottom: 0; left: 0; right: 340px; }}
  #method-panel {{
    position: absolute; top: 0; right: 0; bottom: 0; width: 340px;
    overflow-y: auto; box-sizing: border-box; padding: 16px;
    background: #fafafa; border-left: 1px solid #ccc; font-size: 13px; line-height: 1.4;
  }}
  #method-panel h2 {{ font-size: 16px; margin-top: 0; }}
  #method-panel h3 {{ font-size: 14px; }}
  #banding-note {{
    background: #fff3cd; border: 1px solid #f0ad4e; border-radius: 4px;
    padding: 10px; margin-bottom: 12px; font-size: 13px;
  }}
  #legend {{
    position: absolute; bottom: 16px; left: 16px; z-index: 1000;
    background: white; padding: 8px 12px; border-radius: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-size: 12px; line-height: 1.6;
  }}
  #legend span {{
    display: inline-block; width: 12px; height: 12px; margin-right: 6px;
    border: 1px solid #999; vertical-align: middle;
  }}
</style>
</head>
<body>
<div id="map"></div>
{method_panel}
<div id="legend">{legend_items}</div>
<script>
  const map = L.map('map').setView({json.dumps(center)}, 11);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 18,
  }}).addTo(map);

  const features = {json.dumps(features)};
  const bounds = [];
  for (const f of features) {{
    const poly = L.polygon(f.coords, {{
      color: '#666', weight: 1, fillColor: f.color, fillOpacity: 0.7,
    }}).addTo(map);
    poly.bindPopup(f.popup);
    for (const c of f.coords) bounds.push(c);
  }}
  if (bounds.length) map.fitBounds(bounds);
</script>
</body>
</html>
"""
    out_path.write_text(doc, encoding="utf-8")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", required=True, help="Force id, e.g. 'leicestershire'")
    parser.add_argument("--out", type=Path, default=Path("crime_context.html"))
    parser.add_argument("--cache-dir", type=Path, default=Path(__file__).parent / "cache")
    parser.add_argument(
        "--window-months",
        type=int,
        default=DEFAULT_WINDOW_MONTHS,
        help="See the module docstring before changing this from 3.",
    )
    args = parser.parse_args()

    with PoliceClient() as police:
        latest = cached(args.cache_dir, "last_updated", police.last_updated)
        months = month_window(
            latest, window_months=args.window_months, skip_recent=SKIP_RECENT_MONTHS
        )
        print(f"Force: {args.force}", file=sys.stderr)
        print(f"Window: {months[0]} to {months[-1]} ({len(months)} months)", file=sys.stderr)
        stats = build_stats(police, args.cache_dir, args.force, months)

    stats, banding_note = compute_bands(stats)
    if banding_note:
        print(f"NOTE: {banding_note}", file=sys.stderr)
    render_html(
        force=args.force, months=months, stats=stats, banding_note=banding_note, out_path=args.out
    )
    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
