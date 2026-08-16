"""A small, visual "AV last-mile" demo: route a pickup -> dropoff hop
across Newton Aycliffe, then check that route against Street Manager's
own real, live, in-progress roadworks - and reroute around any that sit
too close to the road, using nothing fancier than one extra waypoint.

The point isn't a production routing engine - it's showing what this SDK
is *for*: real ground-truth works data feeding a real decision (which
route an autonomous/delivery vehicle should actually take today), not
just plotted on a map for its own sake.

Run: python examples/av_route_avoiding_works.py --map
Needs SM_EMAIL / SM_PASSWORD for Street Manager (SM_ENV=sandbox|production,
default sandbox - see .env.example). No credentials for routing.

**Real data, one honestly-labelled shortcut.** Pickup/dropoff points are
real Newton Aycliffe streets (Emerson Way, Van Mildert Road - geocoded
live via Nominatim, not guessed), and the roadworks are Street Manager's
real, live, in-progress permits for "NEWTON AYCLIFFE" (the same
server-side filter `compare_active_works.py` already established for
Durham City - see that module's own docstring for why
`street_descriptor`/`work_status` are the real, working params). Newton
Aycliffe - a planned post-war new town with a proper grid of residential
streets - was chosen deliberately over Durham City's own historic core:
live testing found Durham's peninsula (formed by a loop in the River
Wear) genuinely has too few road crossings for this script's simple
detour heuristic to ever find a clean alternative, whereas Newton
Aycliffe's grid offers real parallel streets a detour can actually use -
confirmed live, not assumed. The road-following route itself comes from
OSRM's **public demo server** (`router.project-osrm.org`) - free,
keyless, genuinely real routing over OpenStreetMap's road network, but
explicitly not licensed for production traffic (OSRM's own terms) - swap
in a self-hosted OSRM/GraphHopper/ORS instance for anything beyond this
kind of illustrative run.

**Conflict check is a planar distance approximation, not a lane-level
closure model - stated honestly, not overclaimed.** Street Manager gives
a permit's own extent as a point (or, on Coordinate.points, its stated
line), not which specific lane or carriageway side is actually blocked -
this script flags a real conflict when the route passes within
`--threshold-m` (default 40m) of a real active worksite's own stated
location, a reasonable proxy at street scale, not a precise
"is this lane closed" answer. Distance/offset maths uses a simple
equirectangular approximation (flat-earth, scaled by latitude) - accurate
enough at this route's ~1-2km scale, not geodesically exact.

**Rerouting is one bounded, honest heuristic, not a search algorithm.**
If the direct route conflicts with real active works, this script offsets
a waypoint sideways (perpendicular to the pickup->dropoff line) from the
conflicting works' own real centroid, tries both sides, and keeps
whichever real OSRM route clears every conflict - or, if neither does,
says so plainly and shows the least-bad option rather than pretending
success.
"""

from __future__ import annotations

import argparse
import itertools
import math
import os
from datetime import timedelta

import httpx

from streetworks.common import Works, WorksSite, from_streetmanager

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"

#: Real Newton Aycliffe streets, geocoded live via Nominatim
#: (OpenStreetMap) - not guessed. (lon, lat), matching this script's own
#: coordinate convention throughout (OSRM/GeoJSON order).
PICKUP = (-1.5778218, 54.6160118)  # Emerson Way
DROPOFF = (-1.5610720, 54.6170340)  # Van Mildert Road

DEFAULT_CONFLICT_THRESHOLD_M = 40.0
#: Tried smallest-first, both sides, first one that clears every real
#: conflict wins - a short escalating list rather than one fixed offset,
#: since a real 180m offset can still snap back onto the same road (OSRM
#: routes around the *waypoint*, not away from the conflict point itself)
#: while 200m clears it a street over - confirmed live in Durham's own
#: Newton Hall estate.
_DETOUR_OFFSETS_M = (150.0, 250.0, 400.0, 600.0, 900.0)
_METRES_PER_DEGREE_LAT = 111_320.0


# --------------------------------------------------------------------------- #
# Fetch real, live, in-progress Street Manager works - the same
# work_status/street_descriptor filters compare_active_works.py already
# established live against both sandbox and production.
# --------------------------------------------------------------------------- #


def fetch_active_works(town: str) -> list[tuple[Works, WorksSite]]:
    if not (os.environ.get("SM_EMAIL") and os.environ.get("SM_PASSWORD")):
        print("  (Street Manager skipped - set SM_EMAIL / SM_PASSWORD, see .env.example)")
        return []

    from streetworks.streetmanager import Environment, StreetManagerClient

    env = (
        Environment.PRODUCTION
        if os.environ.get("SM_ENV", "sandbox").lower() == "production"
        else Environment.SANDBOX
    )
    params = {"work_status": "in_progress", "street_descriptor": town}
    with StreetManagerClient(
        os.environ["SM_EMAIL"], os.environ["SM_PASSWORD"], environment=env
    ) as sm:
        permits = list(itertools.islice(sm.reporting.iter_permits(**params), 2000))

    works_list = from_streetmanager(permits)
    return [
        (works, site)
        for works in works_list
        for site in works.sites
        if site.raw.get("work_status_string") == "in_progress"
    ]


def _works_lonlat(site: WorksSite) -> tuple[float, float] | None:
    """(lon, lat) for a real WorksSite - Street Manager's own Coordinate
    is BNG (EPSG:27700), reprojected via the same
    streetworks.common._bng.bng_to_wgs84 compare_active_works.py already
    uses (see that module's own _lonlat for the full reasoning)."""
    coordinate = site.coordinate
    if coordinate is None:
        return None
    from streetworks.common._bng import bng_to_wgs84

    easting, northing = coordinate.value[0], coordinate.value[1]
    return bng_to_wgs84(easting, northing)


# --------------------------------------------------------------------------- #
# Real, simple planar geometry - equirectangular approximation, adequate
# at this route's ~1-2 km scale (see module docstring), not geodesic.
# --------------------------------------------------------------------------- #


def _metres_per_degree_lon(lat: float) -> float:
    return _METRES_PER_DEGREE_LAT * math.cos(math.radians(lat))


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    mean_lat = (lat1 + lat2) / 2
    dx = (lon2 - lon1) * _metres_per_degree_lon(mean_lat)
    dy = (lat2 - lat1) * _METRES_PER_DEGREE_LAT
    return math.hypot(dx, dy)


def _point_to_route_distance_m(
    point: tuple[float, float], route: list[tuple[float, float]]
) -> float:
    """Minimum distance from a real point to the route polyline -
    closest-vertex approximation (the real route has 100+ vertices at
    this scale, so segment interpolation isn't needed for a useful
    answer here)."""
    return min(_distance_m(point, vertex) for vertex in route)


def _offset_point(
    point: tuple[float, float], bearing_deg: float, distance_m: float
) -> tuple[float, float]:
    """A real point offset by a bearing/distance - the same planar
    approximation as `_distance_m`, inverted."""
    lon, lat = point
    bearing = math.radians(bearing_deg)
    dlat = (distance_m * math.cos(bearing)) / _METRES_PER_DEGREE_LAT
    dlon = (distance_m * math.sin(bearing)) / _metres_per_degree_lon(lat)
    return (lon + dlon, lat + dlat)


def _bearing_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    dx = (lon2 - lon1) * _metres_per_degree_lon((lat1 + lat2) / 2)
    dy = (lat2 - lat1) * _METRES_PER_DEGREE_LAT
    return math.degrees(math.atan2(dx, dy))


# --------------------------------------------------------------------------- #
# OSRM's real public demo server - one plain GET per route, GeoJSON out.
# --------------------------------------------------------------------------- #


def _osrm_route(waypoints: list[tuple[float, float]]) -> dict | None:
    coords = ";".join(f"{lon},{lat}" for lon, lat in waypoints)
    url = f"{OSRM_BASE_URL}/{coords}"
    try:
        response = httpx.get(
            url,
            params={"overview": "full", "geometries": "geojson"},
            timeout=20.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"  (OSRM request failed: {exc})")
        return None
    body = response.json()
    if body.get("code") != "Ok" or not body.get("routes"):
        return None
    route = body["routes"][0]
    return {
        "coordinates": [tuple(c) for c in route["geometry"]["coordinates"]],
        "distance_m": route["distance"],
        "duration_s": route["duration"],
    }


# --------------------------------------------------------------------------- #
# Planning: direct route first, real conflicts against it, then a bounded
# left/right detour attempt - see module docstring.
# --------------------------------------------------------------------------- #


def _conflicts(
    route: list[tuple[float, float]],
    works_points: list[tuple[Works, WorksSite, tuple[float, float]]],
    threshold_m: float,
) -> list[tuple[Works, WorksSite, tuple[float, float]]]:
    return [
        entry
        for entry in works_points
        if _point_to_route_distance_m(entry[2], route) <= threshold_m
    ]


def plan_route(
    pickup: tuple[float, float],
    dropoff: tuple[float, float],
    works_points: list[tuple[Works, WorksSite, tuple[float, float]]],
    *,
    threshold_m: float = DEFAULT_CONFLICT_THRESHOLD_M,
) -> dict:
    direct = _osrm_route([pickup, dropoff])
    if direct is None:
        raise RuntimeError("OSRM could not find any route between pickup and dropoff")

    direct_conflicts = _conflicts(direct["coordinates"], works_points, threshold_m)
    if not direct_conflicts:
        return {
            "route": direct,
            "conflicts_avoided": [],
            "conflicts_remaining": [],
            "direct": direct,
            "rerouted": False,
        }

    # Offset a waypoint sideways from the conflicting works' own real
    # centroid, perpendicular to the pickup -> dropoff line - try both
    # sides at each offset, smallest first, keep whichever real route
    # clears every conflict.
    centroid_lon = sum(e[2][0] for e in direct_conflicts) / len(direct_conflicts)
    centroid_lat = sum(e[2][1] for e in direct_conflicts) / len(direct_conflicts)
    centroid = (centroid_lon, centroid_lat)
    base_bearing = _bearing_deg(pickup, dropoff)

    best: dict | None = None
    for offset_m in _DETOUR_OFFSETS_M:
        for side in (90.0, -90.0):
            waypoint = _offset_point(centroid, base_bearing + side, offset_m)
            candidate = _osrm_route([pickup, waypoint, dropoff])
            if candidate is None:
                continue
            remaining = _conflicts(candidate["coordinates"], works_points, threshold_m)
            if not remaining:
                return {
                    "route": candidate,
                    "conflicts_avoided": direct_conflicts,
                    "conflicts_remaining": [],
                    "direct": direct,
                    "rerouted": True,
                }
            # Only a genuine improvement over both the direct route and
            # any other detour tried counts as "best" - a detour that
            # makes things worse is never preferred just for being tried.
            if len(remaining) < len(direct_conflicts) and (
                best is None or len(remaining) < len(best["conflicts_remaining"])
            ):
                best = {
                    "route": candidate,
                    "conflicts_avoided": [c for c in direct_conflicts if c not in remaining],
                    "conflicts_remaining": remaining,
                    "direct": direct,
                    "rerouted": True,
                }

    if best is not None:
        return best
    # Neither detour genuinely helped - stay honest, use the direct
    # route rather than a longer detour that isn't actually better.
    return {
        "route": direct,
        "conflicts_avoided": [],
        "conflicts_remaining": direct_conflicts,
        "direct": direct,
        "rerouted": False,
    }


# --------------------------------------------------------------------------- #
# Map - reuses roadworks_world_map.py/compare_active_works.py's own
# Scattermap + CartoDB-tile conventions (free, no key).
# --------------------------------------------------------------------------- #


def build_map(plan: dict, works_points: list[tuple[Works, WorksSite, tuple[float, float]]]):
    import plotly.graph_objects as go

    fig = go.Figure()

    # Only draw the direct route separately when it actually differs
    # from the final one - if no detour helped, "route" already *is*
    # "direct" and a second, identical trace would just look redundant.
    if plan["rerouted"]:
        direct = plan["direct"]
        lons = [c[0] for c in direct["coordinates"]]
        lats = [c[1] for c in direct["coordinates"]]
        fig.add_trace(
            go.Scattermap(
                lon=lons,
                lat=lats,
                mode="lines",
                line={"width": 3, "color": "#999999"},
                name="Direct route (has conflicts)",
                hoverinfo="name",
            )
        )

    route = plan["route"]
    lons = [c[0] for c in route["coordinates"]]
    lats = [c[1] for c in route["coordinates"]]
    label = "Route (avoiding works)" if plan["rerouted"] else "Route (no conflicts)"
    fig.add_trace(
        go.Scattermap(
            lon=lons,
            lat=lats,
            mode="lines",
            line={"width": 5, "color": "#1a9850"},
            name=label,
            hoverinfo="name",
        )
    )

    avoided_refs = {id(c[1]) for c in plan["conflicts_avoided"]}
    remaining_refs = {id(c[1]) for c in plan["conflicts_remaining"]}
    for works, site, (lon, lat) in works_points:
        if id(site) in remaining_refs:
            colour, symbol, tag = "#d73027", "circle", "still blocking this route"
        elif id(site) in avoided_refs:
            colour, symbol, tag = "#fc8d59", "circle", "avoided"
        else:
            colour, symbol, tag = "#4575b4", "circle", "nearby, not on this route"
        fig.add_trace(
            go.Scattermap(
                lon=[lon],
                lat=[lat],
                mode="markers",
                marker={"size": 12, "color": colour, "symbol": symbol},
                name="Active works",
                showlegend=False,
                text=f"{works.reference or '?'} ({tag})<br>{site.works_type or '?'}"
                f"<br>{site.location_description or ''}",
                hoverinfo="text",
            )
        )

    for point, label, colour in (
        (PICKUP, "Pickup - Emerson Way", "#1a9850"),
        (DROPOFF, "Dropoff - Van Mildert Road", "#313695"),
    ):
        fig.add_trace(
            go.Scattermap(
                lon=[point[0]],
                lat=[point[1]],
                mode="markers",
                marker={"size": 18, "color": colour, "symbol": "circle"},
                name=label,
                text=label,
                hoverinfo="text",
            )
        )

    centre_lon = (PICKUP[0] + DROPOFF[0]) / 2
    centre_lat = (PICKUP[1] + DROPOFF[1]) / 2
    fig.update_layout(
        map={
            "style": "carto-positron",
            "center": {"lon": centre_lon, "lat": centre_lat},
            "zoom": 15,
        },
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        title="AV last-mile demo: Newton Aycliffe, avoiding real active roadworks",
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sm-town", default="NEWTON AYCLIFFE")
    parser.add_argument(
        "--threshold-m",
        type=float,
        default=DEFAULT_CONFLICT_THRESHOLD_M,
        help="how close a real worksite has to be to the route to count as a conflict",
    )
    parser.add_argument(
        "--map",
        nargs="?",
        const="av_route_avoiding_works.html",
        default=None,
        metavar="PATH",
        help="write the route map (default: av_route_avoiding_works.html); omit to skip",
    )
    args = parser.parse_args()

    print(f"Street Manager: active (in_progress) works in {args.sm_town}...")
    matches = fetch_active_works(args.sm_town)
    works_points = []
    for works, site in matches:
        point = _works_lonlat(site)
        if point is not None:
            works_points.append((works, site, point))
    print(f"  {len(works_points)} real active worksite(s) with a usable location")

    print(f"\nPlanning route: pickup {PICKUP} -> dropoff {DROPOFF} ...")
    plan = plan_route(PICKUP, DROPOFF, works_points, threshold_m=args.threshold_m)

    route = plan["route"]
    duration = timedelta(seconds=round(route["duration_s"]))
    print(f"  distance: {route['distance_m']:.0f} m, duration: {duration}")
    if plan["conflicts_avoided"]:
        print(f"  rerouted around {len(plan['conflicts_avoided'])} real worksite(s):")
        for works, site, _ in plan["conflicts_avoided"]:
            print(f"    - {works.reference or '?'}: {site.location_description or '?'}")
    if plan["conflicts_remaining"]:
        n = len(plan["conflicts_remaining"])
        t = args.threshold_m
        print(f"  {n} real worksite(s) still within {t:.0f}m - no detour clears them:")
        for works, site, _ in plan["conflicts_remaining"]:
            print(f"    - {works.reference or '?'}: {site.location_description or '?'}")
    if not plan["conflicts_avoided"] and not plan["conflicts_remaining"]:
        print("  no real active works within range of the direct route - clear run.")

    if args.map:
        fig = build_map(plan, works_points)
        fig.write_html(args.map)
        print(f"\nMap written to {args.map}")


if __name__ == "__main__":
    main()
