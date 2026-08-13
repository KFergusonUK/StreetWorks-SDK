"""Flag Street Manager works worth coordinating - same street, close in
time, at least one disruptive.

Run: python examples/collaboration_finder.py
Needs SM_EMAIL / SM_PASSWORD (SM_ENV=sandbox|production, default sandbox -
see .env.example). Prints a clear message and exits cleanly if unset,
rather than a traceback.

**Both ``work_status`` values are pulled, each capped - live-verified this
was needed, not a precaution.** ``planned`` and ``in_progress`` are both
real, working server-side filters (see ``compare_active_works.py``'s own
docstring for how that was confirmed against the documented Reporting API
resource guide), but they're not equally sized: ``in_progress`` alone
paginated to 624 real rows in ~5s in production, while an *uncapped*
``planned`` pull was still going after 60s and had to be killed - future/
upcoming work genuinely outnumbers currently-active work by a wide margin
in a real account. ``_LIMIT`` (applied per status, via ``itertools.islice``)
keeps this script's own runtime bounded regardless of account size -
confirmed live: capped at 1000, the same ``planned`` pull that wouldn't
finish uncapped completes in ~12s.

**Only future-starting permits are considered a candidate pair, on either
side.** Coordinating around a permit whose work already happened is not
actionable - obviously, but real sandbox/production data both turned up
plenty of long-past pairs (2021-2022 examples) that would otherwise clutter
real output with historical noise. Filtered by comparing
:func:`_start_date` against ``datetime.now(timezone.utc)`` before pairing,
not after - a permit that already started is dropped entirely, not just
hidden from display, so it can't drag a genuinely-future partner into a
"pair" that isn't actionable either.

**The single most obviously-should-have-coordinated pair gets its own
callout** - ranked by (both permits disruptive) then (smallest day gap),
printed first, before the full per-street listing, and highlighted
separately on the map (``--map``) if generated. Not a statistical claim,
just the most immediately obvious "these two clearly needed to talk to
each other" case in this run.

``--map [PATH]`` writes an optional map (Plotly ``Scattermap``, free
CartoDB street tiles, no API key - see ``compare_active_works.py``'s own
module docstring for why CartoDB rather than Plotly's other free
``open-street-map`` style, which real testing found gets blocked) - one
line per coordination pair connecting the two real permit locations
(reprojected from Street Manager's native BNG), the "doh" pair highlighted
in red, everything else in a neutral colour.
"""

from __future__ import annotations

import itertools
import os
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from typing import Any

JSON = dict[str, Any]

#: Real Street Manager traffic-management values (TrafficManagementTypeResponse)
#: that visibly disrupt other traffic - the ones worth flagging a nearby
#: works over. Deliberately excludes lighter categories (give_and_take,
#: some/no_carriageway_incursion, stop_go_boards, ...) - a pair where
#: neither side does more than that isn't worth a human's time here.
DISRUPTIVE_TRAFFIC_MANAGEMENT = {"road_closure", "multi_way_signals", "two_way_signals"}

#: "Within one month" - the brief's own words, taken as 30 days.
MAX_GAP_DAYS = 30

#: Safety cap per work_status pull - "planned" alone is confirmed to not
#: terminate within 60s uncapped in a real production account; see module
#: docstring for the live timing behind this.
_LIMIT = 1000


# --------------------------------------------------------------------------- #
# The matching logic - the reusable part. Everything below main() is just
# fetching/printing.
# --------------------------------------------------------------------------- #


def _start_date(permit: JSON) -> datetime | None:
    """The best-known start date for a permit - actual over proposed, the
    same preference streetworks.common.from_streetmanager's date_confidence
    already uses, so "start date" here means the same thing it does
    elsewhere in this SDK."""
    value = permit.get("actual_start_date") or permit.get("proposed_start_date")
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _is_disruptive(permit: JSON) -> bool:
    return permit.get("traffic_management_type_string") in DISRUPTIVE_TRAFFIC_MANAGEMENT


def _promoter_code(permit: JSON) -> str:
    """First 5 characters of ``work_reference_number`` (e.g. ``"UG107"``),
    used as a stand-in for promoter identity. Real sandbox data confirmed
    ``promoter_organisation``/``promoter_swa_code`` are the same single
    value (``"DURHAM COUNTY COUNCIL"``/``"1355"``) across every permit in
    the account - not useful for telling promoters apart - while this
    prefix genuinely partitions the 226 real permits checked into 17
    differently-sized groups (89 under ``"UG107"`` alone), so it's a real
    signal here, not a guess."""
    return permit["work_reference_number"][:5]


def find_collaboration_candidates(permits: list[JSON]) -> list[tuple[JSON, JSON, int]]:
    """Group permits by USRN, then flag every same-USRN pair whose start
    dates are within :data:`MAX_GAP_DAYS` of each other AND where at least
    one permit uses a disruptive traffic-management type. Two works on the
    same street around the same time, at least one of which will visibly
    block traffic, are worth a human checking for coordination (shared
    access, combined closure, sequencing) before both go ahead independently.

    A pair sharing one ``work_reference_number`` is **not** flagged - real
    Street Manager sandbox data confirmed this happens often (13/139 real
    candidate pairs in one live pull): it's a permit and its own amendment
    under the same work, not two separate works that need coordinating.
    Nor is a pair sharing the same :func:`_promoter_code` - coordinating a
    promoter with itself isn't the point; the value here is surfacing two
    *different* promoters' works that neither would otherwise know about.

    Permits missing a USRN or any start date can't be grouped/compared and
    are silently skipped - never guessed at. Callers are expected to have
    already dropped past-starting permits (see module docstring) - this
    function itself doesn't re-check that, it just pairs what it's given.

    Returns ``(permit_a, permit_b, day_gap)`` tuples, one per qualifying
    pair - a permit can appear in more than one pair if it has more than
    one near-in-time neighbour on the same street.
    """
    by_usrn: dict[Any, list[tuple[JSON, datetime]]] = defaultdict(list)
    for permit in permits:
        usrn = permit.get("usrn")
        start = _start_date(permit)
        if usrn is None or start is None:
            continue
        by_usrn[usrn].append((permit, start))

    candidates: list[tuple[JSON, JSON, int]] = []
    for group in by_usrn.values():
        for (a, a_start), (b, b_start) in combinations(group, 2):
            if a["work_reference_number"] == b["work_reference_number"]:
                continue
            if _promoter_code(a) == _promoter_code(b):
                continue
            gap_days = abs((a_start - b_start).days)
            if gap_days > MAX_GAP_DAYS:
                continue
            if not (_is_disruptive(a) or _is_disruptive(b)):
                continue
            candidates.append((a, b, gap_days))
    return candidates


def find_doh_candidate(
    candidates: list[tuple[JSON, JSON, int]],
) -> tuple[JSON, JSON, int] | None:
    """The single most obviously-should-have-coordinated pair - both
    permits disruptive (not just one), then smallest day gap. Not a
    statistical ranking, just "which one pair would make a human wince
    first" - see module docstring."""
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda c: (0 if (_is_disruptive(c[0]) and _is_disruptive(c[1])) else 1, c[2]),
    )


# --------------------------------------------------------------------------- #
# Map - independent of the print path above. Reuses compare_active_works.py's
# own conventions (Scattermap, carto-positron, bare lazy plotly import).
# --------------------------------------------------------------------------- #

_DURHAM_CENTRE = {"lat": 54.78, "lon": -1.57}
_DURHAM_ZOOM = 12


def _permit_lonlat(permit: JSON) -> tuple[float, float] | None:
    """(lon, lat) from a raw permit's own works_coordinates (BNG GeoJSON,
    Point or LineString - see streetworks.common.from_streetmanager's own
    _coordinate for the confirmed real shapes). The first vertex only, same
    "value is the representative point" convention used everywhere else in
    this SDK."""
    from streetworks.common._bng import bng_to_wgs84

    works_coordinates = permit.get("works_coordinates") or {}
    coordinates = works_coordinates.get("coordinates")
    geometry_type = works_coordinates.get("type")
    if geometry_type == "Point" and coordinates:
        easting, northing = coordinates[0], coordinates[1]
    elif geometry_type == "LineString" and coordinates:
        easting, northing = coordinates[0][0], coordinates[0][1]
    else:
        return None
    return bng_to_wgs84(easting, northing)


def build_collaboration_map(
    candidates: list[tuple[JSON, JSON, int]],
    doh: tuple[JSON, JSON, int] | None,
):
    import plotly.graph_objects as go

    fig = go.Figure()
    for a, b, gap in candidates:
        is_doh = doh is not None and (a, b, gap) == doh
        point_a = _permit_lonlat(a)
        point_b = _permit_lonlat(b)
        if point_a is None or point_b is None:
            continue
        street = a.get("street") or b.get("street") or f"USRN {a.get('usrn')}"
        fig.add_trace(
            go.Scattermap(
                lon=[point_a[0], point_b[0]],
                lat=[point_a[1], point_b[1]],
                mode="lines+markers",
                line=dict(width=4 if is_doh else 2, color="#d4351c" if is_doh else "#1b70b8"),
                marker=dict(size=12 if is_doh else 8, color="#d4351c" if is_doh else "#1b70b8"),
                text=[
                    f"<b>{a.get('permit_reference_number', '?')}</b><br>{street}",
                    f"<b>{b.get('permit_reference_number', '?')}</b><br>{street}",
                ],
                hoverinfo="text",
                name=("🤦 " if is_doh else "") + f"{street} ({gap}d apart)",
                showlegend=False,
            )
        )

    fig.update_maps(style="carto-positron", center=_DURHAM_CENTRE, zoom=_DURHAM_ZOOM)
    fig.update_layout(
        title=dict(
            text=f"Coordination candidates - {len(candidates)} pair(s)"
            + (" (🤦 doh pair in red)" if doh else ""),
            x=0.5,
        ),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


# --------------------------------------------------------------------------- #
# Fetch + print
# --------------------------------------------------------------------------- #


def _describe(permit: JSON) -> str:
    ref = permit.get("permit_reference_number", "?")
    promoter = permit.get("promoter_organisation", "?")
    work_type = permit.get("traffic_management_type_string", "?")
    start = permit.get("actual_start_date") or permit.get("proposed_start_date") or "?"
    return f"{ref} - {promoter}, {work_type}, starts {start[:10]}"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--map",
        nargs="?",
        const="collaboration_finder.html",
        default=None,
        metavar="PATH",
        help="write a map of coordination pairs (default: collaboration_finder.html); omit to skip",
    )
    args = parser.parse_args()

    if not os.environ.get("SM_EMAIL") or not os.environ.get("SM_PASSWORD"):
        print("Set your Street Manager credentials first: SM_EMAIL / SM_PASSWORD")
        print("(SM_ENV=sandbox|production, default sandbox). See .env.example.")
        return

    from streetworks.streetmanager import Environment, StreetManagerClient

    env = (
        Environment.PRODUCTION
        if os.environ.get("SM_ENV", "sandbox").lower() == "production"
        else Environment.SANDBOX
    )

    print(f"Fetching active/planned Street Manager permits ({env.name.lower()})...")
    with StreetManagerClient(
        os.environ["SM_EMAIL"], os.environ["SM_PASSWORD"], environment=env
    ) as sm:
        # "Active/planned" = Street Manager's own work_status values
        # "in_progress" and "planned" - excludes completed/cancelled/
        # historical/etc. Two calls (server-side filtered) rather than one
        # unfiltered pull, since the account can hold plenty of closed-out
        # history irrelevant to coordination. Each capped independently -
        # see module docstring for why that's needed, not just cautious.
        permits = [
            permit
            for status in ("planned", "in_progress")
            for permit in itertools.islice(sm.reporting.iter_permits(work_status=status), _LIMIT)
        ]

    print(f"{len(permits)} active/planned permit(s) fetched.")

    # Only future-starting permits are actionable - see module docstring.
    now = datetime.now(timezone.utc)
    permits = [p for p in permits if (start := _start_date(p)) is not None and start >= now]
    print(f"{len(permits)} of those start now or in the future.\n")

    candidates = find_collaboration_candidates(permits)
    if not candidates:
        print("No collaboration candidates found.")
        return

    doh = find_doh_candidate(candidates)
    if doh is not None:
        doh_a, doh_b, doh_gap = doh
        street = doh_a.get("street") or doh_b.get("street") or f"USRN {doh_a.get('usrn')}"
        print(f"🤦 DOH - {street}, {doh_gap} day(s) apart, both disruptive:")
        print(f"  {_describe(doh_a)}")
        print(f"  {_describe(doh_b)}\n")

    by_street: dict[str, list[tuple[JSON, JSON, int]]] = defaultdict(list)
    for a, b, gap in candidates:
        street = a.get("street") or b.get("street") or f"USRN {a.get('usrn')}"
        by_street[street].append((a, b, gap))

    print(f"{len(candidates)} potential coordination pair(s) across {len(by_street)} street(s):\n")
    for street, pairs in sorted(by_street.items()):
        print(street)
        for a, b, gap in pairs:
            print(f"  {_describe(a)}")
            print(f"  {_describe(b)}")
            print(f"  -> {gap} day(s) apart\n")

    if args.map:
        fig = build_collaboration_map(candidates, doh)
        fig.write_html(args.map)
        print(f"Map written to {args.map}")


if __name__ == "__main__":
    main()
