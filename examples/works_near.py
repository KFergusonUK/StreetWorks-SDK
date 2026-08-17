"""Works near a WGS84 point and/or a UK USRN.

Queries the v1 subset documented on streetworks.query: Traffic Wales
always (keyless); National Highways if --nh-key / NH_SUBSCRIPTION_KEY is
set; Street Manager if SM_EMAIL / SM_PASSWORD are set *and* --usrn is
given; SRWR if --srwr points at a local extract.

This will not download the SRWR daily zip or the Open USRN GeoPackage,
will not query TrafficWatchNI (no geometry), and will not pretend to
cover every registered provider.

Default point is the Raglan / A40 location from this SDK's own live-
verified Traffic Wales fixture (51.78344, -2.939548) so a no-credentials
run still has a real chance of printing current trunk-road works.

Run: python examples/works_near.py
     python examples/works_near.py --lat 51.48 --lon -3.18 --radius-m 10000
     python examples/works_near.py --usrn 33909869   # needs SM_* in the env
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from streetworks.query import v1_providers, works_near


def load_dotenv(path: str = ".env") -> None:
    file = Path(path)
    if not file.exists():
        return
    for line in file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lat", type=float, default=51.78344)
    parser.add_argument("--lon", type=float, default=-2.939548)
    parser.add_argument("--radius-m", type=float, default=5_000.0)
    parser.add_argument("--usrn", default=None)
    parser.add_argument(
        "--usrn-only",
        action="store_true",
        help="do not send the default lat/lon (USRN path only)",
    )
    parser.add_argument("--nh-key", default=os.environ.get("NH_SUBSCRIPTION_KEY"))
    parser.add_argument("--srwr", default=None, help="path to a local SRWR extract")
    args = parser.parse_args()

    lat = None if args.usrn_only else args.lat
    lon = None if args.usrn_only else args.lon
    if args.usrn_only and not args.usrn:
        parser.error("--usrn-only needs --usrn")

    street_manager = None
    if args.usrn and os.environ.get("SM_EMAIL") and os.environ.get("SM_PASSWORD"):
        from streetworks.streetmanager import Environment, StreetManagerClient

        env = (
            Environment.PRODUCTION
            if os.environ.get("SM_ENV", "sandbox").lower() == "production"
            else Environment.SANDBOX
        )
        street_manager = StreetManagerClient(
            os.environ["SM_EMAIL"], os.environ["SM_PASSWORD"], environment=env
        )

    planned = v1_providers(
        lat=lat,
        lon=lon,
        usrn=args.usrn,
        street_manager=street_manager,
        national_highways_key=args.nh_key,
        srwr_source=args.srwr,
    )
    where = f"{lat},{lon}" if lat is not None else f"USRN {args.usrn}"
    print(f"works_near {where}  radius_m={args.radius_m:g}")
    print(f"v1 providers for this call: {', '.join(planned) or '(none)'}")
    if "nationalhighways" not in planned:
        print("  (National Highways skipped - pass --nh-key or NH_SUBSCRIPTION_KEY)")
    if args.usrn and "streetmanager" not in planned:
        print("  (Street Manager skipped - set SM_EMAIL / SM_PASSWORD)")
    if args.usrn and "srwr" not in planned:
        print("  (SRWR skipped - pass --srwr /path/to/extract)")

    try:
        hits = works_near(
            lat,
            lon,
            usrn=args.usrn,
            radius_m=args.radius_m,
            street_manager=street_manager,
            national_highways_key=args.nh_key,
            srwr_source=args.srwr,
        )
    finally:
        if street_manager is not None:
            street_manager.close()

    print(f"{len(hits)} hit(s), not deduplicated across providers:\n")
    for hit in hits:
        works = hit.works
        site = works.sites[0] if works.sites else None
        where_txt = (
            (site.location_description if site else None)
            or works.location_usrn
            or "?"
        )
        dist = f"{hit.distance_m:,.0f} m" if hit.distance_m is not None else hit.match
        print(
            f"  [{hit.provider}] {works.reference or '?'}  {dist}  "
            f"{works.territory or '?'}  {where_txt}"
        )


if __name__ == "__main__":
    main()
