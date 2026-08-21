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
    ``NH_SUBSCRIPTION_KEY``). WGS84 only: other CRS are reported and skipped,
    never silently reprojected (the SDK's ``Coordinate`` contract).

Usage
-----
    python roadworks_world_map.py                              # coverage map
    NH_SUBSCRIPTION_KEY=... python roadworks_world_map.py --live
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
    "Portugal": (-9.14, 38.72),
    "Finland": (25.7, 62.5), "Iceland": (-18.6, 64.9), "Bulgaria": (25.3, 42.7),
    "Lithuania": (23.9, 55.2), "Norway": (9.0, 61.0), "Sweden": (15.6, 62.2),
    "Denmark": (9.5, 56.1), "Ireland": (-8.0, 53.2), "Italy": (12.6, 42.5),
    "Greece": (23.7, 39.1),
    "Paris": (2.35, 48.86),
    # USA (federated WZDx — one national marker; per-state on live pull)
    "USA": (-98.5, 39.8), "New York City": (-74.0, 40.7), "Chicago": (-87.6, 41.9),
    # Canada (DriveBC/British Columbia; territory-scoped like Spain/Germany,
    # not province-scoped — see docs/providers/canada.md)
    "Canada": (-123.1, 49.25),
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
# streetmanager/dtro/opendata aren't here deliberately - see _fetch_works's own
# docstring for why their real interfaces don't fit "plot a point" at all.
CRED_ENV = {
    "nationalhighways": lambda: (
        {"subscription_key": os.environ["NH_SUBSCRIPTION_KEY"]}
        if os.environ.get("NH_SUBSCRIPTION_KEY") else None),
    "vegvesen": lambda: (
        {"username": os.environ["VEGVESEN_USERNAME"], "password": os.environ["VEGVESEN_PASSWORD"]}
        if os.environ.get("VEGVESEN_USERNAME") and os.environ.get("VEGVESEN_PASSWORD") else None),
    "nsw": lambda: (
        {"api_key": os.environ["NSW_LIVETRAFFIC_API_KEY"]}
        if os.environ.get("NSW_LIVETRAFFIC_API_KEY") else None),
    "vic": lambda: (
        {"api_key": os.environ["VIC_DISRUPTIONS_API_KEY"]}
        if os.environ.get("VIC_DISRUPTIONS_API_KEY") else None),
    "ab511": lambda: (
        {"api_key": os.environ["ALBERTA_511_API_KEY"]}
        if os.environ.get("ALBERTA_511_API_KEY") else None),
    "sk511": lambda: (
        {"api_key": os.environ["SASKATCHEWAN_511_API_KEY"]}
        if os.environ.get("SASKATCHEWAN_511_API_KEY") else None),
    "nb511": lambda: (
        {"api_key": os.environ["NEW_BRUNSWICK_511_API_KEY"]}
        if os.environ.get("NEW_BRUNSWICK_511_API_KEY") else None),
    "nl511": lambda: (
        {"api_key": os.environ["NEWFOUNDLAND_511_API_KEY"]}
        if os.environ.get("NEWFOUNDLAND_511_API_KEY") else None),
    "ns511": lambda: (
        {"api_key": os.environ["NOVA_SCOTIA_511_API_KEY"]}
        if os.environ.get("NOVA_SCOTIA_511_API_KEY") else None),
    "yt511": lambda: (
        {"api_key": os.environ["YUKON_511_API_KEY"]}
        if os.environ.get("YUKON_511_API_KEY") else None),
}

#: Cap on raw records pulled per provider before conversion - a coverage map
#: needs a representative sample, not the full register. Real registers here
#: range up to 1.8M+ rows (NYC DOT) even after each client's own server-side
#: roadworks filter - always capped, matching scripts/smoke_test.py's own
#: precedent for the same three large US/UK registers.
_LIMIT = 50

#: wzdx is registry-driven across dozens of independent state/city feeds -
#: every real keyless one is pulled for a genuine US-wide spread on the
#: map (see _fetch_works), each still capped at _LIMIT records, so one
#: bad/slow feed can't repeat today's original NYC DOT stall across a
#: whole sweep of feeds. No feed-*count* cap - an earlier fixed cap (25)
#: silently dropped whichever feeds sorted last once the real registry
#: grew past it (confirmed live: North Carolina and Mississippi never
#: appeared on the live map at all, a real "gap in the USA" rather than
#: a deliberate exclusion). Each feed is still independently
#: try/excepted, so a single hanging feed can't stall the rest - that
#: per-feed guard was always the real protection, not a feed-count cap.

#: DATEX II providers share one converter (from_datex2), called once per
#: Situation with kwargs that vary by source - collected here from the real,
#: tested invocations in tests/test_*.py (test_belgium.py, test_bulgaria.py,
#: test_common_datex2.py, ...), not re-derived from scratch.
_DATEX_TERRITORY: dict[str, dict[str, str]] = {
    "ndw": {"territory": "Netherlands"},
    "nationalhighways": {"territory": "England", "administrative_area": "National Highways"},
    "digitraffic": {"territory": "Finland"},
    "irca": {"territory": "Iceland"},
    "bisonfute": {"territory": "France"},
    "dgt": {"territory": "Spain"},
    "euskadi": {"territory": "Spain", "administrative_area": "Euskadi"},
    "belgium": {"territory": "Belgium", "crs": "EPSG:31370"},  # Lambert 72, confirmed live
    "luxembourg": {"territory": "Luxembourg"},
    "bulgaria": {"territory": "Bulgaria"},
}

#: streetworks.ogc.germany.GermanRoadworksClient is shared by all six states
#: - .fetch(state) takes the real FIELD_MAPS key (German name for Saxony).
_GERMAN_STATES = {
    "hamburg": "Hamburg", "brandenburg": "Brandenburg", "saxony": "Sachsen",
    "baden_wuerttemberg": "Baden-Württemberg", "schleswig_holstein": "Schleswig-Holstein",
    "rheinland_pfalz": "Rheinland-Pfalz",
}

#: streetworks.opendatasoft.france_departements.DepartementRoadworksClient is
#: shared by all five areas - .fetch(area) takes the real FIELD_MAPS key.
_FRANCE_AREAS = {
    "sarthe": "Sarthe", "loire_atlantique": "Loire-Atlantique",
    "hauts_de_seine": "Hauts-de-Seine", "toulouse": "Toulouse Métropole",
    "rennes": "Rennes Métropole",
}

#: streetworks.na511.NA511Client is shared by all three jurisdictions -
#: .fetch(jurisdiction) takes the real streetworks.na511.jurisdictions key.
_NA511_JURISDICTIONS = {
    "on511": "ontario", "ab511": "alberta", "sk511": "saskatchewan",
    "nb511": "new_brunswick", "nl511": "newfoundland_and_labrador",
    "ns511": "nova_scotia", "yt511": "yukon",
}

TIERS = {
    "keyless": dict(name="Live-capable (keyless)", color="#1b9e77", symbol="circle"),
    "login":   dict(name="Login required",         color="#e6a817", symbol="circle"),
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
    # Every EPSG:4326 Coordinate.value in this SDK is (lat, lon) - this SDK's
    # own stated convention, confirmed in three independent converters' own
    # docstrings (from_sct/from_wzdx/from_autobahn) and now enforced at the
    # source in every converter that used to store raw, unswapped GeoJSON
    # (lon, lat) instead (the ArcGIS-based Australian cluster plus NZTA -
    # confirmed live via a real Berlin point, (52.45, 13.32), and the
    # "Australia plotting in Antarctica" bug this fixed). Jersey/NYC DOT/Via
    # Lietuva's genuinely projected, non-4326 coordinates never reach this
    # line at all - the crs guard above already routes them to "skip".
    return float(c.value[1]), float(c.value[0])


def _fetch_works(key, client):
    """Fetch and convert one provider's current roadworks into real
    ``Works`` objects - the only shape ``_coord_lonlat`` can read a
    coordinate from.

    **A real fix, not the original design**: every provider's own
    ``iter_roadworks()``/``get_roadworks()`` returns its own raw/native
    type (a plain dict, or a provider-specific dataclass like SCT's
    ``Incident`` or DATEX's ``Situation``) - confirmed empirically against
    four different providers (Madrid, Paris, SCT, CCISS all checked live),
    none of which carry a ``.coordinate`` attribute directly. Getting from
    that native type to something ``_coord_lonlat`` can read is a separate
    ``from_<provider>()`` conversion step this function now does
    explicitly, which the script's original ``it()``-then-``_coord_lonlat``
    loop never did - so ``--live`` mode had never actually plotted a real
    point for any provider before this.

    Every raw pull is capped at :data:`_LIMIT` records (a coverage map
    needs a representative sample, not the full register - real registers
    here run past a million rows even after each client's own server-side
    roadworks filter).

    ``wzdx`` is registry-driven across dozens of independent feeds, so it's
    handled separately from every single-client provider below: every real
    keyless feed is pulled (each capped at :data:`_LIMIT` records - no
    feed-*count* cap, see that constant's own docstring for why a fixed one
    used to silently drop newly-added feeds).

    Returns ``None`` for providers with no converter wired below - not an
    error, just not yet covered. Not attempted at all: ``streetmanager``
    (a namespaced reporting API, not "plot a point" shaped), ``dtro`` (a
    legal-orders register, not a works-progress feed), ``opendata`` (a
    push-only SNS receiver, nothing to poll), ``srwr`` (needs a downloaded-
    and-extracted archive first, a genuinely different resource lifecycle
    from every HTTP-GET-shaped client here).
    """
    import itertools

    from streetworks.common import (
        from_amsterdam,
        from_au_act_ttm,
        from_au_nt_roadreport,
        from_au_qld_qldtraffic,
        from_au_tas_roadworks,
        from_au_wa_mainroads,
        from_autobahn,
        from_berlin,
        from_canton_zurich,
        from_cciss,
        from_chicagodot,
        from_copenhagen,
        from_datex2,
        from_dc,
        from_departement_roadworks,
        from_dortmund,
        from_drivebc,
        from_helsinki,
        from_jersey,
        from_lisboa,
        from_lyon,
        from_madrid,
        from_mallorca,
        from_milano,
        from_na511,
        from_nsw_livetraffic,
        from_nycdot,
        from_nzta,
        from_ogc_features,
        from_oslo,
        from_paris,
        from_quebec,
        from_roma,
        from_saarland,
        from_sct,
        from_tfl,
        from_trafficwales,
        from_trafficwatchni,
        from_vegvesen,
        from_vialietuva,
        from_vic_disruptions,
        from_vienna,
        from_wzdx,
        from_zurich,
    )

    if key in _DATEX_TERRITORY:
        situations = itertools.islice(client.iter_roadworks(), _LIMIT)
        return [from_datex2(s, **_DATEX_TERRITORY[key]) for s in situations]
    if key == "vegvesen":
        situations = itertools.islice(client.iter_roadworks(), _LIMIT)
        return [from_vegvesen(s) for s in situations]
    if key == "mallorca":
        return from_mallorca(client.fetch_roadworks_icons(), client.fetch_trams())
    if key in _GERMAN_STATES:
        from streetworks.ogc.germany import FIELD_MAPS

        state = _GERMAN_STATES[key]
        return from_ogc_features(client.fetch(state), FIELD_MAPS[state])
    if key in _FRANCE_AREAS:
        from streetworks.opendatasoft.france_departements import FIELD_MAPS as FR_FIELD_MAPS

        area = _FRANCE_AREAS[key]
        return from_departement_roadworks(client.fetch(area), FR_FIELD_MAPS[area])
    if key in _NA511_JURISDICTIONS:
        from streetworks.na511.jurisdictions import JURISDICTIONS as NA511_JURISDICTIONS

        jurisdiction = NA511_JURISDICTIONS[_NA511_JURISDICTIONS[key]]
        return from_na511(
            client.fetch(_NA511_JURISDICTIONS[key]),
            territory=jurisdiction.territory,
            administrative_area=jurisdiction.administrative_area,
        )
    if key == "vic":
        return from_vic_disruptions(client.iter_planned_disruptions())
    if key == "wzdx":
        from streetworks.wzdx.registry import list_feeds

        works: list = []
        feeds = [f for f in list_feeds() if not f.needapikey]
        for feed_entry in feeds:
            try:
                feed = client.fetch(feed_entry.url)
            except Exception:
                continue                  # one bad feed shouldn't drop the rest
            road_events = list(itertools.islice(feed.road_events, _LIMIT))
            works.extend(
                from_wzdx(
                    road_events,
                    territory=feed_entry.state or "USA",
                    administrative_area=feed_entry.organization,
                )
            )
        return works
    if key == "cciss":
        return [from_cciss(i) for i in client.fetch() if i.is_roadworks]
    if key == "trafficwatchni":
        from streetworks.trafficwatchni import Feed

        return [from_trafficwatchni(i) for i in client.fetch(Feed.ROADWORKS)]
    if key == "trafficwales":
        from streetworks.trafficwales import Feed

        return [from_trafficwales(i) for i in client.fetch(Feed.ROADWORKS)]
    if key == "vialietuva":
        # Not iter_roadworks() - Via Lietuva's real method is road_repairs(),
        # already the one real table this SDK models (see module docstring
        # for why Kliutis/Renginys aren't). Returns a plain list (~9,700
        # real rows), not an iterator - capped the same way, just sliced.
        return from_vialietuva(client.road_repairs()[:_LIMIT])
    if key == "autobahn":
        # roadworks(road) needs an explicit road - one representative road
        # (A1), not all ~113, matching scripts/smoke_test.py's own restraint
        # here (a full sweep is a one-off verification step, not a repeat).
        return from_autobahn(client.roadworks("A1"))

    if key == "nycdot":
        # Real finding: only ~87% of NYC DOT's own roadworks rows carry a
        # parseable wkt geometry at all (confirmed live against a 2000-row
        # sample) - and that's not evenly distributed, so the plain first
        # _LIMIT rows can come back with zero plottable points (a real,
        # observed run: 50/50 with no wkt). Pulling a larger raw sample and
        # keeping only the works that actually converted to a coordinate
        # (still capped at _LIMIT) gives the map a reliable NYC showing
        # without changing the SDK's own iter_roadworks() default at all.
        records = list(itertools.islice(client.iter_roadworks(), _LIMIT * 10))
        works = from_nycdot(records)
        return [w for w in works if w.coordinate is not None][:_LIMIT]

    simple = {
        "madrid": from_madrid, "drivebc": from_drivebc, "lisboa": from_lisboa,
        "roma": from_roma, "berlin": from_berlin, "sct": from_sct, "milano": from_milano,
        "jersey": from_jersey, "nzta": from_nzta,
        "wa": from_au_wa_mainroads,
        "qld": from_au_qld_qldtraffic, "act": from_au_act_ttm,
        "tas": from_au_tas_roadworks, "nsw": from_nsw_livetraffic,
        "paris": from_paris, "chicagodot": from_chicagodot,
        "copenhagen": from_copenhagen, "tfl": from_tfl,
        "saarland": from_saarland, "dortmund": from_dortmund, "lyon": from_lyon,
        "amsterdam": from_amsterdam, "nt": from_au_nt_roadreport, "dc": from_dc,
        "quebec": from_quebec,
        # oslo's, helsinki's, canton_zurich's and vienna's coordinates are
        # projected (EPSG:25832, EPSG:3879, EPSG:2056 and EPSG:31256
        # respectively), so _coord_lonlat's WGS84-only guard skips them on
        # the live-points layer today - still wired in so real Works are
        # fetched/counted honestly rather than silently omitted;
        # reprojecting for display is a separate decision.
        "oslo": from_oslo,
        "helsinki": from_helsinki,
        "canton_zurich": from_canton_zurich,
        "zurich": from_zurich,
        "vienna": from_vienna,
    }
    if key in simple:
        records = list(itertools.islice(client.iter_roadworks(), _LIMIT))
        return simple[key](records)

    return None


def live_points():
    """Current roadworks from keyless uniform providers, plus credential-gated
    ones whose key is in the environment. WGS84 only; others reported + skipped."""
    pts, skipped, unconverted = [], 0, 0
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
        try:
            works = _fetch_works(e.key, client)
        except Exception:
            continue                      # network/creds/shape -> degrade gracefully
        if works is None:
            unconverted += 1
            continue                      # no converter wired for this provider yet
        for w in works:
            ll = _coord_lonlat(w)
            if ll == "skip":
                skipped += 1
            elif ll:
                pts.append((ll[0], ll[1], e.key))
    if skipped:
        print(f"  (skipped {skipped} non-WGS84 points — reproject explicitly to include)")
    if unconverted:
        print(f"  ({unconverted} provider(s) attempted but not yet wired to a converter here)")
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
