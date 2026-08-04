#!/usr/bin/env python3
"""
Roadworks on a world map — a streetworks SDK example.

Registry-driven: it reads ``streetworks.providers()`` at runtime, so **new
providers appear on the map automatically as they are released** — you never
edit this file to gain coverage. Each provider is sorted into its access tier
from the registry's own ``credentials`` field.

The one manual step
-------------------
A provider is only *plotted* if its territory has a display coordinate in
``TERRITORY_CENTROIDS`` below. Adding a provider in a brand-new territory means
adding **one line** there (e.g. ``"Singapore": (103.8, 1.35)``). The script
prints any registered territory that's missing a centroid, so you'll know.

Modes
-----
Coverage (default, offline)
    Plots every territory the SDK can pull roadworks from, coloured by tier:
      * Live-capable (keyless) — has >=1 credential-free provider; lights up on
        ``--live`` with no login.
      * Login required — every roadworks provider there is credential-gated
        (e.g. England: Street Manager / National Highways / D-TRO). Covered, but
        shows no live points without your credentials.

Live (``--live``, networked)
    Also pulls *current* roadworks from keyless providers exposing a uniform
    ``iter_roadworks()``, and from credential-gated providers **if** their key is
    in the environment (National Highways is the worked example — set
    ``NATIONAL_HIGHWAYS_KEY``). WGS84 only: other CRS are reported and skipped,
    never silently reprojected (the SDK's ``Coordinate`` contract).

Usage
-----
    python roadworks_world_map.py                              # coverage map
    NATIONAL_HIGHWAYS_KEY=... python roadworks_world_map.py --live
    python roadworks_world_map.py --inline -o map.html         # self-contained

Output: one self-contained HTML file (Plotly Scattergeo — offline coastlines,
no map tiles, no external calls unless ``--inline`` is omitted, in which case
plotly.js loads from a CDN).

Caveat that travels with the picture: marker size = provider count, not live
roadworks count. Coverage/freshness vary per provider; a demonstration of reach,
not an operational feed. Real data (c) each provider under its own licence.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

import streetworks as sw

# Display centroids (lon, lat). A provider is plotted only if its territory is
# here. New territory -> add one line. (Placement only; the *coverage* claim
# itself always comes from the live registry, never this table.)
TERRITORY_CENTROIDS: dict[str, tuple[float, float]] = {
    # UK + Crown Dependencies
    "England": (-1.5, 52.6), "Scotland": (-4.2, 56.8), "Wales": (-3.8, 52.3),
    "Northern Ireland": (-6.7, 54.6), "Jersey": (-2.1, 49.2),
    # Europe
    "Netherlands": (5.3, 52.2), "Belgium": (4.5, 50.6), "Luxembourg": (6.1, 49.8),
    "France": (2.4, 46.6), "Spain": (-3.7, 40.2), "Germany": (10.4, 51.2),
    "Finland": (25.7, 62.5), "Iceland": (-18.6, 64.9), "Bulgaria": (25.3, 42.7),
    "Lithuania": (23.9, 55.2), "Norway": (9.0, 61.0), "Sweden": (15.6, 62.2),
    "Denmark": (9.5, 56.1), "Ireland": (-8.0, 53.2), "Italy": (12.6, 42.5),
    "Greece": (23.7, 39.1),
    # USA (federated WZDx — one national marker; per-state on live pull)
    "USA": (-98.5, 39.8), "New York City": (-74.0, 40.7), "Chicago": (-87.6, 41.9),
    # Australia (per-state) + New Zealand
    "New South Wales": (147.0, -32.0), "Victoria": (144.5, -37.0),
    "Queensland": (146.0, -22.5), "Western Australia": (122.0, -25.0),
    "South Australia": (135.0, -30.0), "Tasmania": (146.6, -42.0),
    "Australian Capital Territory": (149.1, -35.3), "Northern Territory": (133.4, -19.5),
    "New Zealand": (172.5, -41.0),
}

WGS84 = {"EPSG:4326", "CRS:84", "urn:ogc:def:crs:EPSG::4326",
         "urn:ogc:def:crs:OGC:1.3:CRS84", "4326"}

# Worked example of pulling a credential-gated provider when its key is present.
# Extend as you wire more logins; each entry returns constructor kwargs or None.
CRED_ENV = {
    "nationalhighways": lambda: (
        {"subscription_key": os.environ["NATIONAL_HIGHWAYS_KEY"]}
        if os.environ.get("NATIONAL_HIGHWAYS_KEY") else None),
}

TIERS = {
    "keyless": dict(name="Live-capable (keyless)", color="#1b9e77", symbol="circle"),
    "login":   dict(name="Login required",         color="#e6a817", symbol="circle-open"),
}


def classify() -> dict[str, tuple[list, str]]:
    """territory -> (roadworks provider entries, tier). tier: 'keyless' | 'login'."""
    by_terr: dict[str, list] = defaultdict(list)
    for e in sw.providers():
        if e.kind.value == "roadworks":
            for t in e.territories:
                by_terr[t].append(e)
    return {t: (entries, "keyless" if any(not e.credentials for e in entries) else "login")
            for t, entries in by_terr.items()}


def _coord_lonlat(obj):
    c = getattr(obj, "coordinate", None)
    if c is None or getattr(c, "value", None) is None:
        return None
    if c.crs not in WGS84:
        return "skip"                     # needs explicit reprojection
    return float(c.value[0]), float(c.value[1])


def live_points():
    """Current roadworks from keyless uniform providers, plus credential-gated
    ones whose key is in the environment. WGS84 only; others reported + skipped."""
    pts, skipped = [], 0
    for e in sw.providers():
        if e.kind.value != "roadworks" or e.verified is False:
            continue
        kwargs = {}
        if e.credentials:
            factory = CRED_ENV.get(e.key)
            kwargs = factory() if factory else None
            if not kwargs:
                continue                  # gated, no key supplied
        try:
            client = sw.get_provider(e.key)(**kwargs)
        except Exception:
            continue
        it = getattr(client, "iter_roadworks", None) or getattr(client, "get_roadworks", None)
        if it is None:
            continue                      # non-uniform provider (its own converter)
        try:
            for w in it():
                ll = _coord_lonlat(w)
                if ll == "skip":
                    skipped += 1
                elif ll:
                    pts.append((ll[0], ll[1], e.key))
        except Exception:
            continue                      # network/creds/shape -> degrade gracefully
    if skipped:
        print(f"  (skipped {skipped} non-WGS84 points — reproject explicitly to include)")
    return pts


def build_figure(cls, live):
    import plotly.graph_objects as go
    fig = go.Figure()

    for tier in ("keyless", "login"):
        lons, lats, sizes, texts = [], [], [], []
        for terr, (entries, t) in sorted(cls.items()):
            if t != tier or terr not in TERRITORY_CENTROIDS:
                continue
            lon, lat = TERRITORY_CENTROIDS[terr]
            names = ", ".join(sorted(e.name for e in entries))
            note = ("keyless — lights up on --live" if tier == "keyless"
                    else "needs a login to show live works")
            lons.append(lon)
            lats.append(lat)
            sizes.append(9 + 4 * len(entries))
            texts.append(f"<b>{terr}</b> · {note}<br>{len(entries)} provider(s): {names}")
        s = TIERS[tier]
        fig.add_trace(go.Scattergeo(
            lon=lons, lat=lats, text=texts, hoverinfo="text", name=s["name"],
            marker=dict(size=sizes, color=s["color"], symbol=s["symbol"],
                        line=dict(width=1.4, color=s["color"] if tier == "login" else "white"),
                        opacity=0.9, sizemode="diameter")))

    if live:
        fig.add_trace(go.Scattergeo(
            lon=[p[0] for p in live], lat=[p[1] for p in live],
            text=[p[2] for p in live], hoverinfo="text", name=f"Live roadworks ({len(live)})",
            marker=dict(size=4, color="#2e5cb8", opacity=0.55)))

    n_terr = len([t for t in cls if t in TERRITORY_CENTROIDS])
    n_prov = sum(len(v[0]) for v in cls.values())
    sub = f"{n_prov} roadworks providers across {n_terr} territories"
    if live:
        sub += f" · {len(live)} live works"
    fig.update_layout(
        title=dict(text=f"<b>streetworks — roadworks coverage</b><br><sub>{sub}</sub>", x=0.5),
        geo=dict(projection_type="natural earth", showland=True, landcolor="#f4f1ec",
                 showcountries=True, countrycolor="#ddd8d0", showocean=True, oceancolor="#eef3f6",
                 coastlinecolor="#c9c3b8",
                 lataxis=dict(showgrid=True, gridcolor="#eae6df"),
                 lonaxis=dict(showgrid=True, gridcolor="#eae6df")),
        legend=dict(orientation="h", y=-0.02, x=0.5, xanchor="center"),
        margin=dict(l=0, r=0, t=70, b=64), paper_bgcolor="white",
        annotations=[dict(x=0.5, y=-0.15, xref="paper", yref="paper", showarrow=False,
            font=dict(size=10, color="#6b6459"),
            text=("Marker size = provider count, not live roadworks count. Amber territories "
                  "need a login to show live works. A demonstration of reach, not an "
                  "operational feed. Real data (c) each provider's licence."))],
    )
    return fig


def main():
    ap = argparse.ArgumentParser(description="Roadworks on a world map (streetworks example).")
    ap.add_argument("--live", action="store_true", help="pull live roadworks (networked)")
    ap.add_argument("-o", "--out", default="roadworks_world_map.html")
    ap.add_argument("--inline", action="store_true",
                    help="inline plotly.js — fully self-contained, larger file")
    args = ap.parse_args()

    cls = classify()
    print(f"Registry: {sum(len(v[0]) for v in cls.values())} roadworks providers, "
          f"{len(cls)} territories.")

    missing = sorted(t for t in cls if t not in TERRITORY_CENTROIDS)
    if missing:
        print("  Not shown (add a line to TERRITORY_CENTROIDS): " + ", ".join(missing))

    live = []
    if args.live:
        print("Pulling live roadworks…")
        live = live_points()
        print(f"  {len(live)} live points.")

    fig = build_figure(cls, live)
    fig.write_html(args.out, include_plotlyjs=(True if args.inline else "cdn"), full_html=True)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    sys.exit(main())
