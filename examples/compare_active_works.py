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

The Durham City area is parameterised (--sm-town) rather than hardcoded.
Paris needs no equivalent parameter - "Chantiers à Paris" is already a
comprehensively city-scoped register (see streetworks.paris.client's own
module docstring), so there's no geographic filter left to apply on top
of it, unlike a national/regional feed that needs narrowing to one area.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime

from streetworks.common import Works, WorksSite, from_paris, from_streetmanager

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
    parser.add_argument("--sm-town", default="DURHAM")
    args = parser.parse_args()

    print(f"Street Manager: active (in_progress) works in {args.sm_town}...")
    sm_matches = fetch_street_manager_active(args.sm_town)

    print("Paris Chantiers: active works (date_debut/date_fin window) across Paris...")
    paris_matches = fetch_paris_active()

    _print_area(f"Street Manager - {args.sm_town}", sm_matches)
    _print_area("Paris Chantiers - Paris", paris_matches)

    print("\n=== Summary ===")
    print(f"  {args.sm_town + ':':<30}{len(sm_matches)} active")
    print(f"  {'Paris:':<30}{len(paris_matches)} active")


if __name__ == "__main__":
    main()
