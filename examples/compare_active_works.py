"""Compare active works side by side across two providers on two
different continents - Street Manager (England, Durham City) and Paris
Chantiers (France, Paris), by default.

The actual point of this script isn't the specific areas, and it's
honestly not a fair like-for-like work count either - Durham City (a
small English cathedral city) and Paris (a major world capital) are
wildly different scales. The real point is that both providers' output
ends up in the *same* streetworks.common.Works/WorksSite shape
(from_streetmanager/from_paris), so one bit of print/filter code works
unmodified across two structurally unrelated sources: Street Manager is
a paginated REST permit register with British National Grid coordinates
and an explicit lifecycle status field (work_status); Paris Chantiers is
an OpenDataSoft REST register with native WGS84 coordinates and *no*
status field at all - "active" has to be inferred from whether `now`
falls inside the worksite's own date_debut/date_fin window instead, the
same date-window inference this script's own DGT/Mallorca predecessor
used for exactly the same honest reason (see git history for that
version if you need a three-provider or Spain-specific comparison).

Run: python examples/compare_active_works.py
Needs SM_EMAIL / SM_PASSWORD for the Street Manager side (SM_ENV=sandbox|
production, default sandbox - see .env.example); Paris is credential-free.
Missing Street Manager credentials degrade that side to a skip message,
not a traceback - Paris still runs.

**Real filter behaviour, checked against both sandbox and production, not
assumed - and not what the field names first suggest.** The Reporting
API's ``permits`` endpoint has no ``town``/``swa_code``/
``highway_authority`` parameter at all: every variant tried returned the
*identical* ``total_rows``/``has_next_page`` and the same mixed real
towns (Bishop Auckland, Ferryhill, Newton Aycliffe, ...) - it just scopes
to the authenticated account's own registration. Invisible against a
small sandbox account (~366 permits, paginates in ~3s); in production the
same unfiltered pull was traced past 2000 rows in 29s with no end in
sight, and a longer run had to be killed by its own 120s timeout - never
erroring, just never finishing. **This is what "the feed wasn't loading
anything" actually was.**

The real, *documented* parameter names (found in Street Manager's own
published `Reporting API resource guide
<https://department-for-transport-streetmanager.github.io/street-manager-docs/api-documentation/V6/resource-guides/reporting-api-guide>`_,
not guessed) behave better, checked one at a time:

- ``street_descriptor`` ("search by street, town or area, partial match")
  genuinely narrows - sandbox 366 -> 26 for ``"DURHAM"``, production
  366-ish -> 66, both in under a second. It's a real partial match across
  street/town/area *combined text*, not town alone, so bare ``"DURHAM"``
  also catches e.g. a "Durham Road" in an unrelated town (checked live:
  Chester-le-Street, Sedgefield, Bishop Auckland, ... all showed up) -
  **``"DURHAM CITY"`` (the real town value, not the shorter guess) is the
  default here specifically because it doesn't have that problem** -
  checked live in production: 66 -> 26, every single returned row
  genuinely ``town == "DURHAM CITY"``, none of the false-positive towns.
  Used as the server-side town filter, replacing the earlier
  client-side-only workaround.
- ``organisation`` is documented as a partial-match org-name filter but
  did **not** narrow anything when tried (identical 366/366) - a second
  real doc-vs-reality gap, noted and left unused.
- ``work_start_date_from``/``work_start_date_to`` are documented as
  "actual start date if available, otherwise proposed" - genuinely narrow
  (366 -> 9 for a 2-week-ago cutoff). **Genuinely inconclusive whether
  that's really what they filter on or not**: every attempt to construct a
  sandbox record where ``date_created`` and ``proposed_start_date``
  diverge (to tell them apart) found none in the real test data - they're
  too correlated in this dataset to distinguish empirically, so this is
  used under its documented name/intent, with that honest caveat, rather
  than either fully trusting or second-guessing the docs.
- ``work_status="in_progress"`` narrows sandbox 366 -> 51, production ->
  624, every returned row checked to genuinely be ``work_status_string ==
  "in_progress"`` - the real, primary filter this script applies.

Combined (``work_status="in_progress"`` + ``street_descriptor``), the
result is small and fast in both environments - this replaces the earlier
capped-pull-then-filter-everything-client-side approach entirely.
``--sm-since-days N`` is off by default: combined with
``work_status="in_progress"`` it can genuinely return few or none (an
in-progress permit's relevant date is often not "N days ago" by either
possible reading) - checked live, not assumed to be safe.

Paris needs no equivalent parameter - "Chantiers à Paris" is already a
comprehensively city-scoped register (see streetworks.paris.client's own
module docstring), so there's no geographic filter left to apply on top
of it, unlike a national/regional feed that needs narrowing to one area.

``--map [PATH]`` writes a side-by-side Plotly map (Street Manager left,
Paris right, each independently centred on its own real area, a count
caption under each panel) - opt-in, off by default, print-only output
otherwise unchanged.
"""

from __future__ import annotations

import argparse
import itertools
import os
from datetime import datetime, timedelta

from streetworks.common import Works, WorksSite, from_paris, from_streetmanager

#: Safety cap on raw Street Manager permits pulled, on top of the real
#: work_status server-side filter (see module docstring) - defence in depth
#: in case a future account/filter combination is unexpectedly large again.
_LIMIT = 2000

# --------------------------------------------------------------------------- #
# "Active" - honestly, per provider. Two different methods, not a forced
# common one:
#
#   - Street Manager states an explicit lifecycle field (work_status),
#     "in_progress" being its own real value for "under way now" - used
#     as-is, no date maths. Read off WorksSite.raw (the original permit
#     dict), since WorksSite.status on this converter surfaces the
#     *assessment* status_string (e.g. "granted"), not work_status - see
#     streetworks.common.from_streetmanager's own _to_site.
#   - Paris Chantiers has no lifecycle status field anywhere in its
#     register - "active" is INFERRED from whether `now` falls inside the
#     validity window (WorksSite.proposed_start/proposed_end - the
#     feed's own date_debut/date_fin, see
#     streetworks.common.from_paris's own _to_site). Open-ended (no
#     proposed_end) counts as active once started.
# --------------------------------------------------------------------------- #


def _street_manager_is_active(site: WorksSite) -> bool:
    return site.raw.get("work_status_string") == "in_progress"


def _paris_is_active(site: WorksSite, *, now: datetime) -> bool:
    """``now`` must be tz-naive here - Paris's real date_debut/date_fin
    are bare ``YYYY-MM-DD`` dates with no time or timezone component, so
    parse_iso8601 leaves proposed_start/proposed_end tz-naive too (the
    same naive-dates outcome this SDK's NYC/Chicago converters document
    for their own real date fields). Comparing against an aware ``now``
    raises ``TypeError`` - see ``fetch_paris_active``."""
    if site.proposed_start is None or site.proposed_start > now:
        return False
    return site.proposed_end is None or now <= site.proposed_end


# --------------------------------------------------------------------------- #
# Fetch + filter, one function per provider - everything past this point is
# generic over Works/WorksSite.
# --------------------------------------------------------------------------- #


def fetch_street_manager_active(
    town: str, *, since_days: int | None = None
) -> list[tuple[Works, WorksSite]]:
    if not (os.environ.get("SM_EMAIL") and os.environ.get("SM_PASSWORD")):
        print("  (Street Manager skipped - set SM_EMAIL / SM_PASSWORD, see .env.example)")
        return []

    from streetworks.streetmanager import Environment, StreetManagerClient

    env = (
        Environment.PRODUCTION
        if os.environ.get("SM_ENV", "sandbox").lower() == "production"
        else Environment.SANDBOX
    )
    # work_status + street_descriptor are both real, working server-side
    # filters (live-verified against the documented Reporting API resource
    # guide, see module docstring) - town= itself genuinely isn't.
    params: dict[str, object] = {"work_status": "in_progress", "street_descriptor": town}
    if since_days is not None:
        cutoff = (datetime.now() - timedelta(days=since_days)).date().isoformat()  # noqa: DTZ005
        params["work_start_date_from"] = cutoff

    with StreetManagerClient(
        os.environ["SM_EMAIL"], os.environ["SM_PASSWORD"], environment=env
    ) as sm:
        permits = list(itertools.islice(sm.reporting.iter_permits(**params), _LIMIT))

    works_list = from_streetmanager(permits)
    return [
        (works, site)
        for works in works_list
        for site in works.sites
        if _street_manager_is_active(site)  # server-side already filtered; this asserts it held
    ]


def fetch_paris_active() -> list[tuple[Works, WorksSite]]:
    from streetworks.paris import ParisClient

    with ParisClient() as paris:
        records = list(paris.iter_roadworks())
    works_list = from_paris(records)

    # Naive, deliberately - see _paris_is_active's own docstring.
    now = datetime.now()  # noqa: DTZ005
    return [
        (works, site)
        for works in works_list
        for site in works.sites
        if _paris_is_active(site, now=now)
    ]


# --------------------------------------------------------------------------- #
# Map - a side-by-side visual, independent of the print path above. Reuses
# roadworks_world_map.py's own conventions (bare lazy plotly import, no new
# pyproject.toml dependency) but this repo's first two-panel subplot layout -
# no prior make_subplots precedent existed anywhere in examples/ or docs/.
#
# Scattermap (Plotly's MapLibre-based map trace, not the older/deprecated
# Scattergeo used by roadworks_world_map.py) - real street-level tiles,
# free, no API key/token. Scattergeo only ever draws filled country/land
# shapes with no street detail at any zoom level, which is why the first
# version of this map looked too zoomed-out to be useful at city scale.
#
# style="carto-positron" (CartoDB's Positron/light basemap), not Plotly's
# other free "open-street-map" style - live-checked: raw tile.openstreetmap.org
# returned 403 Forbidden when hit this way (its own usage policy is strict
# about non-browser/bulk-looking traffic). CartoDB's basemap CDN is the
# same tile source examples/crime_context_lsoa/report.py's own Leaflet map
# already uses successfully in this repo (basemaps.cartocdn.com/light_all),
# so this reuses a source already proven to work here rather than guessing
# at another one.
# --------------------------------------------------------------------------- #

# Real area centres for the two independent map panels - not a shared world
# view, since the whole point is two genuinely different-scale places.
_DURHAM_CENTRE = {"lat": 54.78, "lon": -1.57}
_PARIS_CENTRE = {"lat": 48.86, "lon": 2.35}
_DURHAM_ZOOM = 12
_PARIS_ZOOM = 11  # Paris covers more ground - see module docstring's own scale caveat


def _lonlat(site: WorksSite) -> tuple[float, float] | None:
    """(lon, lat) for plotting, from whichever CRS this site's Coordinate
    actually carries. Street Manager's is BNG (EPSG:27700, easting/northing,
    unswapped per this SDK's own projected-CRS convention) - reprojected via
    the same streetworks.common._bng.bng_to_wgs84 the S50 connector's own
    wgs84_to_bng reverses. Paris's is already WGS84 (lat, lon)."""
    coordinate = site.coordinate
    if coordinate is None:
        return None
    if coordinate.crs == "EPSG:27700":
        from streetworks.common._bng import bng_to_wgs84

        easting, northing = coordinate.value[0], coordinate.value[1]
        # bng_to_wgs84 already returns (lon, lat) - GeoJSON axis order, see
        # its own docstring - so no further swap here.
        return bng_to_wgs84(easting, northing)
    lat, lon = coordinate.value[0], coordinate.value[1]
    return lon, lat


def build_comparison_map(
    sm_matches: list[tuple[Works, WorksSite]],
    paris_matches: list[tuple[Works, WorksSite]],
    sm_town: str,
):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "map"}, {"type": "map"}]],
    )

    for col, (label, matches, centre, zoom, color) in enumerate(
        [
            (f"Street Manager - {sm_town}", sm_matches, _DURHAM_CENTRE, _DURHAM_ZOOM, "#1b9e77"),
            ("Paris Chantiers - Paris", paris_matches, _PARIS_CENTRE, _PARIS_ZOOM, "#e6a817"),
        ],
        start=1,
    ):
        # One pass, keeping (lon, lat, works, site) together - filtering by
        # coordinate presence must not desync the parallel lon/lat/text
        # lists Scattermap expects.
        plottable = [
            (*ll, works, site) for works, site in matches if (ll := _lonlat(site)) is not None
        ]
        lons = [p[0] for p in plottable]
        lats = [p[1] for p in plottable]
        texts = [
            f"<b>{works.reference or '?'}</b><br>{site.works_type or '?'}"
            for _, _, works, site in plottable
        ]
        fig.add_trace(
            go.Scattermap(
                lon=lons,
                lat=lats,
                text=texts,
                hoverinfo="text",
                name=label,
                marker=dict(size=12, color=color, opacity=0.85),
            ),
            row=1,
            col=col,
        )
        # style="carto-positron" - real street-level tiles, free, no
        # token/API key required (see module comment above this function
        # for why not Plotly's other free "open-street-map" style).
        fig.update_maps(row=1, col=col, style="carto-positron", center=centre, zoom=zoom)
        # Count "underneath" - paper-coordinate annotation below this
        # panel's own horizontal domain, not a subplot_title (which
        # renders above).
        x_centre = 0.225 if col == 1 else 0.775
        fig.add_annotation(
            x=x_centre,
            y=-0.06,
            xref="paper",
            yref="paper",
            showarrow=False,
            text=f"<b>{len(matches)}</b> active works",
            font=dict(size=14),
        )

    fig.update_layout(
        title=dict(text="Active works - Street Manager vs Paris Chantiers", x=0.5),
        showlegend=False,
        margin=dict(l=10, r=10, t=60, b=60),
    )
    return fig


# --------------------------------------------------------------------------- #
# Print - identical code for both providers, working only off the common
# Works/WorksSite fields.
# --------------------------------------------------------------------------- #


def _print_area(label: str, matches: list[tuple[Works, WorksSite]]) -> None:
    print(f"\n=== {label} ===")
    if not matches:
        print("  No active works found.")
        return
    for works, site in matches:
        where = site.location_description or works.location_usrn or "?"
        who = works.promoter or works.administrative_area or "?"
        print(f"  {works.reference or '?'}: {site.works_type or '?'} - {where}")
        print(f"    {who}, {site.proposed_start} -> {site.proposed_end}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sm-town",
        default="DURHAM CITY",
        help=(
            "real server-side filter (street_descriptor) - partial match across "
            "street/town/area combined, so a bare town name (e.g. 'DURHAM') can "
            "also match unrelated towns with a similarly-named street; the real "
            "town value is more precise, see module docstring"
        ),
    )
    parser.add_argument(
        "--sm-since-days",
        type=int,
        default=None,
        metavar="N",
        help=(
            "real server-side filter (work_start_date_from), documented as actual/"
            "proposed work start date - off by default, since combined with "
            "work_status=in_progress it can genuinely return few/none, see module "
            "docstring"
        ),
    )
    parser.add_argument(
        "--map",
        nargs="?",
        const="compare_active_works.html",
        default=None,
        metavar="PATH",
        help="write a side-by-side map (default: compare_active_works.html); omit to skip",
    )
    args = parser.parse_args()

    print(f"Street Manager: active (in_progress) works in {args.sm_town}...")
    sm_matches = fetch_street_manager_active(args.sm_town, since_days=args.sm_since_days)

    print("Paris Chantiers: active works (date_debut/date_fin window) across Paris...")
    paris_matches = fetch_paris_active()

    _print_area(f"Street Manager - {args.sm_town}", sm_matches)
    _print_area("Paris Chantiers - Paris", paris_matches)

    print("\n=== Summary ===")
    print(f"  {args.sm_town + ':':<30}{len(sm_matches)} active")
    print(f"  {'Paris:':<30}{len(paris_matches)} active")

    if args.map:
        fig = build_comparison_map(sm_matches, paris_matches, args.sm_town)
        fig.write_html(args.map)
        print(f"\nMap written to {args.map}")


if __name__ == "__main__":
    main()
