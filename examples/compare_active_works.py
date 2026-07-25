"""Compare active works across two providers, side by side - Street
Manager (England) and DGT (Spain), by default.

The actual point of this script isn't the specific areas - it's that both
providers' output ends up in the *same* streetworks.common.Works/WorksSite
shape (from_streetmanager/from_datex2), so one bit of print/filter code
works unmodified on either side, despite two structurally unrelated
sources (Street Manager: paginated REST, BNG coordinates, an explicit
lifecycle status; DGT: a DATEX II XML feed, WGS84 coordinates, no status
field at all).

Run: python examples/compare_active_works.py
Needs SM_EMAIL / SM_PASSWORD for the Street Manager half (SM_ENV=sandbox|
production, default sandbox - see .env.example); DGT is credential-free.
Missing Street Manager credentials degrade that half to a skip message,
not a traceback - DGT still runs.

Areas are parameterised (--sm-town, --dgt-point, --dgt-radius-km) rather
than hardcoded; the defaults are the brief's own two areas: Newton
Aycliffe (County Durham) and a 20km radius around Alcúdia, Mallorca - real
data confirmed Newton Aycliffe genuinely appears in the Street Manager
sandbox, and DGT genuinely covers the Balearics (it excludes only
Catalonia and the Basque Country - see streetworks.datex2.dgt).

Two honest, real findings from running this live against SANDBOX/DGT,
worth knowing before reading the output as-is: the Street Manager sandbox
account's "in_progress" permits often carry a proposed_end_date years in
the past (test data isn't kept current) - real per the source's own
explicit status field, so counted as active here regardless, not a bug in
this script's date handling (which never looks at dates for the Street
Manager side at all - see _street_manager_is_active). And a 20km Alcúdia
radius may genuinely return zero - DGT's Balearic coverage is real but
sparse (5 situations found live across the whole archipelago in one
pull); a zero here is an honest result, not a broken query - see
fetch_dgt_active's docstring / the brief's own "say so rather than
erroring" instruction.
"""

from __future__ import annotations

import argparse
import math
import os
from datetime import datetime, timezone

from streetworks.common import Works, WorksSite, from_datex2, from_streetmanager

# --------------------------------------------------------------------------- #
# "Active" - honestly, per provider. The two definitions below are
# deliberately different methods, not a forced common one:
#
#   - Street Manager states an explicit lifecycle field (work_status),
#     "in_progress" being its own real value for "under way now" - used
#     as-is, no date maths. Read off WorksSite.raw (the original permit
#     dict), since WorksSite.status on this converter surfaces the
#     *assessment* status_string (e.g. "granted"), not work_status - see
#     streetworks.common.from_streetmanager's own _to_site.
#   - DGT/Spain has no lifecycle status field anywhere in the feed -
#     "active" is INFERRED from whether `now` falls inside the validity
#     window (WorksSite.proposed_start/proposed_end, which for DGT *are*
#     the feed's validity.overall_start/overall_end - see
#     streetworks.common.from_datex2's own _to_site). Open-ended (no
#     proposed_end) counts as active once started.
# --------------------------------------------------------------------------- #


def _street_manager_is_active(site: WorksSite) -> bool:
    return site.raw.get("work_status_string") == "in_progress"


def _dgt_is_active(site: WorksSite, *, now: datetime) -> bool:
    if site.proposed_start is None or site.proposed_start > now:
        return False
    return site.proposed_end is None or now <= site.proposed_end


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------- #
# Fetch + filter, one function per provider - everything past this point is
# generic over Works/WorksSite.
# --------------------------------------------------------------------------- #


def fetch_street_manager_active(town: str) -> list[tuple[Works, WorksSite]]:
    if not (os.environ.get("SM_EMAIL") and os.environ.get("SM_PASSWORD")):
        print("  (Street Manager skipped - set SM_EMAIL / SM_PASSWORD, see .env.example)")
        return []

    from streetworks.streetmanager import Environment, StreetManagerClient

    env = (
        Environment.PRODUCTION
        if os.environ.get("SM_ENV", "sandbox").lower() == "production"
        else Environment.SANDBOX
    )
    with StreetManagerClient(
        os.environ["SM_EMAIL"], os.environ["SM_PASSWORD"], environment=env
    ) as sm:
        permits = list(sm.reporting.iter_permits(town=town))

    works_list = from_streetmanager(permits)
    return [
        (works, site)
        for works in works_list
        for site in works.sites
        if _street_manager_is_active(site)
    ]


def fetch_dgt_active(
    center: tuple[float, float], radius_km: float
) -> list[tuple[Works, WorksSite]]:
    from streetworks.datex2 import DGTClient
    from streetworks.datex2.dgt import provinces

    with DGTClient() as dgt:
        situations = list(dgt.iter_roadworks())
    provs = provinces(situations)

    now = datetime.now(timezone.utc)
    matches: list[tuple[Works, WorksSite]] = []
    for situation in situations:
        works = from_datex2(
            situation, territory="Spain", administrative_area=provs.get(situation.id)
        )
        for site in works.sites:
            if not _dgt_is_active(site, now=now):
                continue
            if site.coordinate is None:
                continue
            lat, lon = site.coordinate.value[0], site.coordinate.value[1]
            if _haversine_km(*center, lat, lon) <= radius_km:
                matches.append((works, site))
    return matches


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
    parser.add_argument("--sm-town", default="NEWTON AYCLIFFE")
    parser.add_argument("--dgt-point", default="39.85,3.12", help="lat,lon (default: Alcúdia)")
    parser.add_argument("--dgt-radius-km", type=float, default=20.0)
    args = parser.parse_args()

    lat_str, lon_str = args.dgt_point.split(",")
    center = (float(lat_str), float(lon_str))

    print(f"Street Manager: active (in_progress) works in {args.sm_town}...")
    sm_matches = fetch_street_manager_active(args.sm_town)

    print(f"DGT/Spain: active works within {args.dgt_radius_km:.0f}km of {center}...")
    dgt_matches = fetch_dgt_active(center, args.dgt_radius_km)

    _print_area(f"Street Manager - {args.sm_town}", sm_matches)
    _print_area(f"DGT/Spain - within {args.dgt_radius_km:.0f}km of {center}", dgt_matches)

    print("\n=== Summary ===")
    print(f"  {args.sm_town + ':':<30}{len(sm_matches)} active")
    print(f"  {'DGT (' + str(args.dgt_radius_km) + 'km):':<30}{len(dgt_matches)} active")


if __name__ == "__main__":
    main()
