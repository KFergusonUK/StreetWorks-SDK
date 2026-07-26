"""Compare active works across three providers, side by side - Street
Manager (England), DGT (Spain, national), and Consell de Mallorca
(Spain, insular), by default.

The actual point of this script isn't the specific areas - it's that all
three providers' output ends up in the *same*
streetworks.common.Works/WorksSite shape (from_streetmanager/from_datex2/
from_mallorca), so one bit of print/filter code works unmodified across
all of them, despite three structurally unrelated sources (Street
Manager: paginated REST, BNG coordinates, an explicit lifecycle status;
DGT: a DATEX II XML feed, WGS84 coordinates, no status field at all;
Consell de Mallorca: a GeoServer WFS, UTM31N coordinates, also no status
field).

**DGT vs. Consell de Mallorca is also the clearer, concrete point of
including both** - they cover the *same geographic area* (Alcúdia,
Mallorca), and their networks genuinely overlap rather than being cleanly
disjoint (corrected from an earlier "DGT doesn't include Consell-managed
island roads at all" claim - see docs/network-scope-audit.md: DGT's own
real data does reach Mallorca, and 2 of its Balearic records were checked
directly against Consell de Mallorca's own feed and matched almost
exactly on road, km-range and end-date - republication of the same real
works). Run this and you'll typically see DGT come back empty or
near-empty for Alcúdia while Consell de Mallorca shows real, current
works, since DGT's Balearic coverage is thin and Consell de Mallorca's is
rich - not a bug in either fetch, and **never a reason to deduplicate
matches between the two if both happen to return something** - see the
README's "Never deduplicate across providers" note.

Run: python examples/compare_active_works.py
Needs SM_EMAIL / SM_PASSWORD for the Street Manager third (SM_ENV=sandbox|
production, default sandbox - see .env.example); DGT and Consell de
Mallorca are both credential-free. Missing Street Manager credentials
degrade that third to a skip message, not a traceback - the other two
still run.

Areas are parameterised (--sm-town, --spain-point, --spain-radius-km)
rather than hardcoded; the defaults are the brief's own areas: Newton
Aycliffe (County Durham) and a 20km radius around Alcúdia, Mallorca -
shared between DGT and Consell de Mallorca so the comparison is
apples-to-apples, same centre and radius, two overlapping-but-not-
identical road networks.

Three honest, real findings from running this live, worth knowing before
reading the output as-is:

- The Street Manager sandbox account's "in_progress" permits often carry
  a proposed_end_date years in the past (test data isn't kept current) -
  real per the source's own explicit status field, so counted as active
  here regardless, not a bug in this script's date handling (which never
  looks at dates for the Street Manager side at all - see
  _street_manager_is_active).
- A 20km Alcúdia radius may genuinely return zero for DGT - its Balearic
  coverage is real but sparse (5 situations found live across the whole
  archipelago in one pull); a zero here is an honest result, not a broken
  query - see fetch_dgt_active's docstring / the brief's own "say so
  rather than erroring" instruction.
- Consell de Mallorca's coordinates are real UTM31N (EPSG:25831), not
  WGS84 like DGT's - the area filter therefore converts the *query
  point* (Alcúdia's lat/lon) to UTM31N via a standard WGS84/UTM forward
  transverse Mercator transform (see _latlon_to_utm31n), rather than
  reprojecting the *source data* - the data itself stays in its native
  CRS end to end, per this SDK's standing CRS policy. That transform was
  validated against a real point this SDK already confirmed live via the
  server's own reprojection (see streetworks.ogc.mallorca's module
  docstring): computed easting/northing were within ~0.3m of the
  server's own answer - negligible at a 20km radius.
"""

from __future__ import annotations

import argparse
import math
import os
from datetime import datetime, timezone

from streetworks.common import Works, WorksSite, from_datex2, from_mallorca, from_streetmanager

# --------------------------------------------------------------------------- #
# "Active" - honestly, per provider. Three different methods, not a forced
# common one:
#
#   - Street Manager states an explicit lifecycle field (work_status),
#     "in_progress" being its own real value for "under way now" - used
#     as-is, no date maths. Read off WorksSite.raw (the original permit
#     dict), since WorksSite.status on this converter surfaces the
#     *assessment* status_string (e.g. "granted"), not work_status - see
#     streetworks.common.from_streetmanager's own _to_site.
#   - DGT/Spain and Consell de Mallorca both have no lifecycle status
#     field anywhere in their feeds - "active" is INFERRED from whether
#     `now` falls inside the validity window (WorksSite.proposed_start/
#     proposed_end - for DGT these are the feed's own validity.overall_
#     start/overall_end; for Mallorca they're the feed's own inici/fin -
#     see streetworks.common.from_datex2/from_mallorca's own _to_site
#     functions). Open-ended (no proposed_end) counts as active once
#     started. Genuinely the same method for both, not a coincidence -
#     neither source states anything better to key off.
# --------------------------------------------------------------------------- #


def _street_manager_is_active(site: WorksSite) -> bool:
    return site.raw.get("work_status_string") == "in_progress"


def _active_by_date_window(site: WorksSite, *, now: datetime) -> bool:
    if site.proposed_start is None or site.proposed_start > now:
        return False
    return site.proposed_end is None or now <= site.proposed_end


def _dgt_is_active(site: WorksSite, *, now: datetime) -> bool:
    return _active_by_date_window(site, now=now)


def _mallorca_is_active(site: WorksSite, *, now: datetime) -> bool:
    return _active_by_date_window(site, now=now)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _latlon_to_utm31n(lat: float, lon: float) -> tuple[float, float]:
    """WGS84 -> UTM zone 31N forward transverse Mercator (standard
    formulas, WGS84 ellipsoid) - converts a *query point* only, never the
    source data itself, which Consell de Mallorca states natively in this
    CRS. Validated against a real point this SDK already confirmed live
    via the server's own reprojection (see module docstring): within
    ~0.3m of the server's own answer for the same point."""
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    k0 = 0.9996
    lon0 = math.radians(3.0)  # zone 31's central meridian
    lat_r, lon_r = math.radians(lat), math.radians(lon)
    n = a / math.sqrt(1 - e2 * math.sin(lat_r) ** 2)
    t = math.tan(lat_r) ** 2
    c = ep2 * math.cos(lat_r) ** 2
    coeff_a = (lon_r - lon0) * math.cos(lat_r)
    m = a * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * lat_r
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * lat_r)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * lat_r)
        - (35 * e2**3 / 3072) * math.sin(6 * lat_r)
    )
    easting = (
        k0 * n * (coeff_a + (1 - t + c) * coeff_a**3 / 6)
        + 500000.0
    )
    northing = k0 * (
        m + n * math.tan(lat_r) * (coeff_a**2 / 2 + (5 - t + 9 * c + 4 * c**2) * coeff_a**4 / 24)
    )
    return easting, northing


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


def fetch_mallorca_active(
    center: tuple[float, float], radius_km: float
) -> list[tuple[Works, WorksSite]]:
    from streetworks.ogc.mallorca import MallorcaClient

    with MallorcaClient() as mallorca:
        icons = mallorca.fetch_roadworks_icons()  # tipoinc-filtered - see module docstring
        trams = mallorca.fetch_trams()
    works_list = from_mallorca(icons, trams)

    # Query point only, converted once - the data itself is never
    # reprojected, see module docstring.
    center_easting, center_northing = _latlon_to_utm31n(*center)
    radius_m = radius_km * 1000.0

    now = datetime.now(timezone.utc)
    matches: list[tuple[Works, WorksSite]] = []
    for works in works_list:
        for site in works.sites:
            if not _mallorca_is_active(site, now=now):
                continue
            if site.coordinate is None:
                continue
            easting, northing = site.coordinate.value[0], site.coordinate.value[1]
            distance_m = math.hypot(easting - center_easting, northing - center_northing)
            if distance_m <= radius_m:
                matches.append((works, site))
    return matches


# --------------------------------------------------------------------------- #
# Print - identical code for all three providers, working only off the
# common Works/WorksSite fields.
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
    parser.add_argument(
        "--spain-point",
        default="39.85,3.12",
        help="lat,lon (default: Alcúdia) - shared by DGT and Consell de Mallorca",
    )
    parser.add_argument("--spain-radius-km", type=float, default=20.0)
    args = parser.parse_args()

    lat_str, lon_str = args.spain_point.split(",")
    center = (float(lat_str), float(lon_str))

    print(f"Street Manager: active (in_progress) works in {args.sm_town}...")
    sm_matches = fetch_street_manager_active(args.sm_town)

    print(f"DGT/Spain (national): active works within {args.spain_radius_km:.0f}km of {center}...")
    dgt_matches = fetch_dgt_active(center, args.spain_radius_km)

    print(
        f"Consell de Mallorca (insular): active works within "
        f"{args.spain_radius_km:.0f}km of {center}..."
    )
    mallorca_matches = fetch_mallorca_active(center, args.spain_radius_km)

    _print_area(f"Street Manager - {args.sm_town}", sm_matches)
    _print_area(
        f"DGT/Spain (national) - within {args.spain_radius_km:.0f}km of {center}", dgt_matches
    )
    _print_area(
        f"Consell de Mallorca (insular) - within {args.spain_radius_km:.0f}km of {center}",
        mallorca_matches,
    )

    print("\n=== Summary ===")
    print(f"  {args.sm_town + ':':<30}{len(sm_matches)} active")
    print(f"  {'DGT national (' + str(args.spain_radius_km) + 'km):':<30}{len(dgt_matches)} active")
    print(
        f"  {'Consell insular (' + str(args.spain_radius_km) + 'km):':<30}"
        f"{len(mallorca_matches)} active"
    )


if __name__ == "__main__":
    main()
