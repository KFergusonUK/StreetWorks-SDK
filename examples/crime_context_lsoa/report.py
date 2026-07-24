#!/usr/bin/env python3
"""Worksite-keyed, LSOA-level crime context.

Successor to ``examples/crime_context/`` (the neighbourhood-policing-team
version) - same purpose, finer geography, a real population denominator,
and reframed around a question a planner actually asks: "I'm sending a
crew here - what's the context?" rather than a force-wide ranking of areas.

Run: python -m examples.crime_context_lsoa.report \\
       --force durham --point 54.6109,-1.5568 --radius-m 300

See README.md in this directory for the full method, what changed from the
neighbourhood version and why, and what this deliberately still does not
attempt. The same method/limitations panel is embedded in the output HTML,
not behind a toggle, for the same reason the neighbourhood version does
that: a screenshot of the page should carry the caveats with it.

-------------------------------------------------------------------------
Why LSOA, not neighbourhood policing team (read this before assuming
"finer is just better")
-------------------------------------------------------------------------
A neighbourhood policing team map is, in effect, a population-density map -
crimes per km^2 rises with people per km^2, which tells a planner something
they already knew. LSOAs are built by ONS to hold a roughly equal ~1,500
residents each, so a town the size of Newton Aycliffe becomes fifteen to
twenty areas instead of one, and a population denominator (not area) says
something an area-based rate cannot.

-------------------------------------------------------------------------
Why 12 months by default now, having been 3 for the neighbourhood version
-------------------------------------------------------------------------
The neighbourhood-level example defaulted to a short window because its
ingestion cost was real: a live polygon query per neighbourhood per month,
several hundred sequential HTTP calls. This example's ingestion is a single
bulk CSV download per date range (confirmed live: a 12-month single-force
request is ready in seconds, a few MB). That cost is gone, so the
countervailing reason to keep the window long stands on its own: at ~1,500
residents an LSOA, a 3-month count is frequently single digits, and
small-number instability is *worse* here than at neighbourhood level, not
better - shrinkage helps but does not fully protect against it. Longer
window, more stable counts, same boundary-drift caveat as before (LSOA
boundaries are far more stable than NPT boundaries, but not literally
fixed - see README.md).

-------------------------------------------------------------------------
Why a worksite, not a whole-force map, as the primary output
-------------------------------------------------------------------------
The intended use is a planner asking about one place, not comparing
estates. The whole-force LSOA layer is still computed (bands are relative
to the whole force, which needs the whole force's data to mean anything)
and still rendered as map background - but the worksite is the visual and
textual subject, the answer this page leads with, and the ranked map is
context behind it, not the headline.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from streetworks.police import PoliceClient

from . import ingest, ons
from . import worksite as worksite_mod
from .stats import (
    SUPPRESSED_COLOR,
    LsoaMembershipError,
    check_lsoa_membership,
    compute_force_bands,
)

JSON = dict[str, Any]

#: See the module docstring's "Why 12 months" section before changing.
DEFAULT_WINDOW_MONTHS = 12

#: The API publishes in arrears; querying a month it hasn't published yet
#: returns an empty result that would read as falsely "safe" - see
#: examples/crime_context/generate_map.py's identical, live-verified fix
#: for the same problem at neighbourhood level. This module makes the same
#: choice: derive the window's end from PoliceClient.street_level_availability()
#: itself, never a fixed guess back from today.
_ = None  # (no separate constant needed - see _latest_available_month())

#: A tight buffer is false precision - see worksite.worksite_from_point's
#: own docstring on why. 300m is a reasonable default worksite-plus-margin
#: footprint, not a value this data justifies more precisely than that.
DEFAULT_RADIUS_M = 300.0


# --------------------------------------------------------------------------- #
# Disk cache - same convention as examples/crime_context/generate_map.py.
# Never caches a failed fetch, so a transient error doesn't get "stuck" as
# if it were a real (empty) result.
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
# Month window - duplicated in spirit from the neighbourhood example (same
# "derive from the API's own reported availability" fix), not imported
# across examples, so each stays independently runnable.
# --------------------------------------------------------------------------- #


def latest_available_month(availability: list[JSON]) -> str:
    """The most recent "YYYY-MM" PoliceClient.street_level_availability()
    reports data for."""
    return max(entry["date"] for entry in availability)


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


def month_range(latest_month: str, *, window_months: int) -> tuple[str, str]:
    """``(date_from, date_to)`` for bulk_download_csv - ``window_months``
    real months ending at ``latest_month``."""
    year, month = (int(p) for p in latest_month.split("-"))
    from_year, from_month = _shift_month(year, month, -(window_months - 1))
    return f"{from_year:04d}-{from_month:02d}", latest_month


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def build_force_lsoa_rows(
    police: PoliceClient, cache_dir: Path, force: str, date_from: str, date_to: str
) -> tuple[list[JSON], int]:
    """Downloads and aggregates ``force``'s crime CSVs for the window, joins
    in ONS 2021 population + boundary, and returns ``(lsoa_rows,
    window_months)`` - one row per LSOA the force's crime data actually
    references, each with ``code``, ``name``, ``utla``, ``count``,
    ``population``, ``rings``, ``by_category``.

    Raises :class:`~examples.crime_context_lsoa.stats.LsoaMembershipError`
    if too much of the crime data can't be matched to ONS's LSOA set - see
    that check's own docstring for why that's the real risk here, not
    silent 2011/2021 vintage skew (boundary and population share one ONS
    row, so they can't drift from each other - see ``ons.py``'s docstring).
    """
    window_key = f"{force}_{date_from}_{date_to}"

    per_lsoa, all_lsoa_row_counts = cached(
        cache_dir,
        f"{window_key}_crime",
        lambda: _fetch_and_aggregate(police, force, date_from, date_to),
    )
    per_lsoa = {
        code: {**v, "by_category": Counter(v["by_category"])} for code, v in per_lsoa.items()
    }
    all_lsoa_row_counts = Counter(all_lsoa_row_counts)

    candidate_codes = sorted(all_lsoa_row_counts)
    ons_stats = cached(
        cache_dir,
        f"{window_key}_ons",
        lambda: ons.fetch_lsoa_stats(candidate_codes),
    )

    check_lsoa_membership(all_lsoa_row_counts, set(ons_stats))

    lsoa_rows = []
    for code, ons_row in ons_stats.items():
        crime = per_lsoa.get(code, {"count": 0, "by_category": Counter()})
        lsoa_rows.append(
            {
                "code": code,
                "name": ons_row["name"],
                "utla": ons_row["utla"],
                "population": ons_row["population"],
                "rings": ons_row["rings"],
                "count": crime["count"],
                "by_category": crime["by_category"],
            }
        )

    year_from, month_from = (int(p) for p in date_from.split("-"))
    year_to, month_to = (int(p) for p in date_to.split("-"))
    window_months = (year_to - year_from) * 12 + (month_to - month_from) + 1
    return lsoa_rows, window_months


def _fetch_and_aggregate(
    police: PoliceClient, force: str, date_from: str, date_to: str
) -> tuple[dict[str, JSON], dict[str, int]]:
    per_lsoa, all_lsoa_row_counts = ingest.fetch_lsoa_crime_counts(
        police, force, date_from=date_from, date_to=date_to
    )
    # Counter isn't JSON-native - cached() round-trips through json.dumps,
    # so convert to plain dict/int here and back to Counter on read.
    per_lsoa_json = {
        code: {"count": v["count"], "by_category": dict(v["by_category"])}
        for code, v in per_lsoa.items()
    }
    return per_lsoa_json, dict(all_lsoa_row_counts)


# --------------------------------------------------------------------------- #
# HTML rendering
# --------------------------------------------------------------------------- #

_METHOD_PANEL_HTML = """
<div id="method-panel">
  <h2>What this page is</h2>
  <p>Recorded-crime <b>context</b> for one worksite, to inform a lone-worker
  deployment decision - two-person crew, check-in interval, lighting, vehicle
  positioning - not a yes/no on lone working, and not a risk score.</p>
  <h3>Method</h3>
  <ul>
    <li>Counts are {window} of recorded crime in the categories that bear on a
    lone worker's confrontation/threat/assault risk (violent crime, public
    order, anti-social behaviour, robbery, possession of weapons) - not
    property crime.</li>
    <li>The window always ends at the most recent month data.police.uk itself
    confirms it has published, never a fixed guess back from today.</li>
    <li>The denominator is each LSOA's 2021 Census usual-resident population,
    not land area - LSOAs are population-equal by design, so a rate per 1,000
    residents says something an area-based rate cannot.</li>
    <li>Rates are shrunk toward the force-wide average, more so for smaller
    populations, then compared in quintiles (or terciles below a floor, or not
    banded at all below a lower one) <b>within this force's own LSOAs only</b>.</li>
    <li>Grey areas had too few recorded crimes over the window to compare
    meaningfully - not "zero crime", just not enough data to say anything.</li>
  </ul>
  <h3>What this data cannot tell you</h3>
  <ul>
    <li><b>There is no time of day in this data.</b> It is month-level only.
    An area with high daytime public-order counts near a shopping precinct is
    a different proposition at 2am than the same count near a pub strip at
    closing time - the source cannot distinguish them, and this is probably
    the single most important limitation for a lone-worker decision.</li>
    <li><b>Anti-social behaviour is reporting-sensitive.</b> It is likely the
    most relevant category here for abuse directed at road crews, and it also
    reflects how readily an area's residents report things as much as what
    actually occurs - it should not be the swing factor on its own.</li>
    <li>Each LSOA is derived from crime locations already snapped to
    anonymised points, so it inherits that displacement - tolerable at LSOA
    size, least reliable for a worksite sitting near an LSOA's edge.</li>
    <li>No per-street or per-address figure is reported: a real map point
    covers at least eight postal addresses, or none, and the true coordinates
    are already replaced by the map point's - LSOA sits above that floor,
    nothing finer does.</li>
    <li>No comparison across forces or nationally - bands are quintiles within
    this force's own LSOAs only.</li>
    <li>LSOA boundaries are far more stable than the neighbourhood-policing
    boundaries the predecessor to this example used, but are not literally
    fixed; this aggregates the window's crime against today's boundary.</li>
  </ul>
  <p>This is one input among several a deployment decision should weigh:
  sightlines, egress, proximity to licensed premises, whether the crew works
  in hi-vis beside a lit vehicle or on foot after dark. It informs; it is not
  a lone-worker risk assessment and is not a substitute for one.</p>
  <p>Contains public sector information licensed under the
  <a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
  target="_blank" rel="noopener">Open Government Licence v3.0</a>.
  &copy; Crown copyright and database rights, data.police.uk and
  Office for National Statistics.</p>
</div>
"""


def render_html(
    *,
    force: str,
    window_desc: str,
    lsoa_rows: list[JSON],
    banding_note: str | None,
    worksite_lonlat: list[tuple[float, float]],
    worksite_codes: list[str],
    out_path: Path,
) -> None:
    features = []
    for s in lsoa_rows:
        for ring in s["rings"]:
            popup_lines = [f"<b>{html.escape(s['name'])}</b> ({html.escape(s['code'])})"]
            popup_lines.append(f"Population (2021 Census): {s['population']:,}")
            popup_lines.append(f"Safety-relevant crimes ({window_desc}): {s['count']}")
            if s["raw_rate_per_1000_per_year"] is not None:
                popup_lines.append(
                    f"Raw rate: {s['raw_rate_per_1000_per_year']:.1f} / 1,000 residents / year"
                )
            if s["adjusted_rate_per_1000_per_year"] is not None:
                popup_lines.append(
                    f"Adjusted rate: {s['adjusted_rate_per_1000_per_year']:.1f} / 1,000 / year"
                )
            popup_lines.append(f"Band: {html.escape(s['band_label'])}")
            features.append(
                {
                    "coords": [[lat, lng] for lng, lat in ring],
                    "color": s["band_color"],
                    "highlighted": s["code"] in worksite_codes,
                    "popup": "<br>".join(popup_lines),
                }
            )

    method_panel = _METHOD_PANEL_HTML.format(window=window_desc)
    if banding_note:
        method_panel = (
            f'<div id="banding-note"><b>No areas banded:</b> {html.escape(banding_note)}</div>'
            + method_panel
        )

    worksite_rows = [s for s in lsoa_rows if s["code"] in worksite_codes]
    worksite_panel = _render_worksite_panel(worksite_rows, window_desc)

    seen: dict[str, str] = {}
    for s in sorted((x for x in lsoa_rows if x["band"] is not None), key=lambda x: x["band"]):
        seen.setdefault(s["band_label"], s["band_color"])
    legend_items = "".join(
        f'<span style="background:{color}"></span> {html.escape(label)}<br>'
        for label, color in seen.items()
    )
    legend_items += (
        f'<span style="background:{SUPPRESSED_COLOR}"></span> too few crimes to band<br>'
    )
    if any(s["band_label"] == "too few LSOAs in this force to band" for s in lsoa_rows):
        legend_items += (
            f'<span style="background:{SUPPRESSED_COLOR}"></span> '
            "too few LSOAs in this force to band<br>"
        )
    legend_items = legend_items.removesuffix("<br>")

    all_coords = [c for f in features for c in f["coords"]]
    center = (
        [
            sum(c[0] for c in all_coords) / len(all_coords),
            sum(c[1] for c in all_coords) / len(all_coords),
        ]
        if all_coords
        else [52.6, -1.1]
    )
    worksite_latlng = [[lat, lng] for lng, lat in worksite_lonlat]

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Crime context - worksite in {html.escape(force)}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body {{ margin: 0; height: 100%; font-family: system-ui, sans-serif; }}
  #map {{ position: absolute; top: 0; bottom: 0; left: 0; right: 380px; }}
  #side-panel {{
    position: absolute; top: 0; right: 0; bottom: 0; width: 380px;
    overflow-y: auto; box-sizing: border-box; padding: 16px;
    background: #fafafa; border-left: 1px solid #ccc; font-size: 13px; line-height: 1.4;
  }}
  #worksite-panel {{
    background: #eef6f4; border: 1px solid #69b8ae; border-radius: 4px;
    padding: 12px; margin-bottom: 16px;
  }}
  #worksite-panel h2 {{ font-size: 16px; margin-top: 0; }}
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
<div id="side-panel">
{worksite_panel}
{method_panel}
</div>
<div id="legend">{legend_items}</div>
<script>
  const map = L.map('map').setView({json.dumps(center)}, 14);
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution: '&copy; OpenStreetMap contributors, &copy; CARTO',
    maxZoom: 19,
  }}).addTo(map);

  const features = {json.dumps(features)};
  const bounds = [];
  for (const f of features) {{
    const poly = L.polygon(f.coords, {{
      color: f.highlighted ? '#c0392b' : '#666',
      weight: f.highlighted ? 2.5 : 1,
      fillColor: f.color,
      fillOpacity: f.highlighted ? 0.55 : 0.35,
    }}).addTo(map);
    poly.bindPopup(f.popup);
    for (const c of f.coords) bounds.push(c);
  }}

  const worksite = {json.dumps(worksite_latlng)};
  if (worksite.length) {{
    L.polygon(worksite, {{
      color: '#c0392b', weight: 3, fillColor: '#c0392b', fillOpacity: 0.15,
      dashArray: '6 4',
    }}).addTo(map).bindPopup('Worksite (buffered)');
    for (const c of worksite) bounds.push(c);
  }}
  if (bounds.length) map.fitBounds(bounds);
</script>
</body>
</html>
"""
    out_path.write_text(doc, encoding="utf-8")


def _render_worksite_panel(worksite_rows: list[JSON], window_desc: str) -> str:
    if not worksite_rows:
        return (
            '<div id="worksite-panel"><h2>This worksite</h2>'
            "<p>The buffered worksite area does not intersect any LSOA in this "
            "force's dataset - check the point/radius or USRN given.</p></div>"
        )

    parts = ['<div id="worksite-panel"><h2>This worksite</h2>']
    if len(worksite_rows) > 1:
        parts.append(
            f"<p>The worksite buffer spans {len(worksite_rows)} LSOAs - context "
            "for each is below.</p>"
        )
    for s in worksite_rows:
        parts.append(f"<p><b>{html.escape(s['name'])}</b> ({html.escape(s['code'])})<br>")
        parts.append(f"Population (2021 Census): {s['population']:,}<br>")
        parts.append(f"Safety-relevant crimes ({window_desc}): {s['count']}<br>")
        if s["adjusted_rate_per_1000_per_year"] is not None:
            parts.append(
                f"Adjusted rate: {s['adjusted_rate_per_1000_per_year']:.1f} / 1,000 "
                "residents / year<br>"
            )
        parts.append(f"Band: <b>{html.escape(s['band_label'])}</b></p>")
        if s["by_category"]:
            parts.append("<p>By category:<ul>")
            for category, count in sorted(s["by_category"].items(), key=lambda x: -x[1]):
                parts.append(f"<li>{html.escape(category)}: {count}</li>")
            parts.append("</ul></p>")
    parts.append("</div>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", required=True, help="Force id, e.g. 'durham'")
    parser.add_argument("--out", type=Path, default=Path("worksite_context.html"))
    parser.add_argument("--cache-dir", type=Path, default=Path(__file__).parent / "cache")
    parser.add_argument(
        "--window-months",
        type=int,
        default=DEFAULT_WINDOW_MONTHS,
        help="See the module docstring before changing this from 12.",
    )
    parser.add_argument("--point", help="Worksite centre as 'lat,lng'")
    parser.add_argument("--radius-m", type=float, default=DEFAULT_RADIUS_M)
    parser.add_argument("--usrn", help="Worksite USRN (needs --usrn-geopackage)")
    parser.add_argument(
        "--usrn-geopackage",
        type=Path,
        help="Path to an already-downloaded OS Open USRN GeoPackage "
        "(streetworks.openusrn.OpenUSRNClient.download()) - the USRN path "
        "is not live-tested end-to-end, see worksite.py's docstring.",
    )
    args = parser.parse_args()

    if bool(args.point) == bool(args.usrn):
        parser.error("give exactly one of --point lat,lng or --usrn (with --usrn-geopackage)")
    if args.usrn and not args.usrn_geopackage:
        parser.error("--usrn needs --usrn-geopackage")

    with PoliceClient() as police:
        availability = cached(
            args.cache_dir, "availability", police.street_level_availability
        )
        latest_month = latest_available_month(availability)
        date_from, date_to = month_range(latest_month, window_months=args.window_months)
        print(f"Force: {args.force}", file=sys.stderr)
        print(f"Window: {date_from} to {date_to}", file=sys.stderr)

        try:
            lsoa_rows, window_months = build_force_lsoa_rows(
                police, args.cache_dir, args.force, date_from, date_to
            )
        except LsoaMembershipError as exc:
            print(f"error: {exc}", file=sys.stderr)
            raise SystemExit(1) from None

    print(f"{len(lsoa_rows)} LSOAs in force dataset", file=sys.stderr)
    lsoa_rows, banding_note = compute_force_bands(lsoa_rows, window_months=window_months)
    if banding_note:
        print(f"NOTE: {banding_note}", file=sys.stderr)

    if args.point:
        lat_str, lng_str = args.point.split(",")
        worksite_polygon = worksite_mod.worksite_from_point(
            float(lat_str), float(lng_str), args.radius_m
        )
    else:
        worksite_polygon = worksite_mod.worksite_from_usrn(
            args.usrn, str(args.usrn_geopackage), args.radius_m
        )

    lsoa_lookup = {s["code"]: s for s in lsoa_rows}
    ring_lookup = {code: s["rings"] for code, s in lsoa_lookup.items()}
    worksite_codes = worksite_mod.find_intersecting_lsoas(
        worksite_polygon, {code: {"rings": rings} for code, rings in ring_lookup.items()}
    )
    print(f"Worksite intersects {len(worksite_codes)} LSOA(s): {worksite_codes}", file=sys.stderr)

    window_desc = f"a rolling {window_months}-month window ({date_from} to {date_to})"
    render_html(
        force=args.force,
        window_desc=window_desc,
        lsoa_rows=lsoa_rows,
        banding_note=banding_note,
        worksite_lonlat=list(worksite_polygon.exterior.coords),
        worksite_codes=worksite_codes,
        out_path=args.out,
    )
    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
