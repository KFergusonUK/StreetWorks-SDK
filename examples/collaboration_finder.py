"""Flag Street Manager works worth coordinating - same street, close in
time, at least one disruptive.

Run: python examples/collaboration_finder.py
Needs SM_EMAIL / SM_PASSWORD (SM_ENV=sandbox|production, default sandbox -
see .env.example). Prints a clear message and exits cleanly if unset,
rather than a traceback.
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
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
    are silently skipped - never guessed at.

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
        # history irrelevant to coordination.
        permits = [
            permit
            for status in ("planned", "in_progress")
            for permit in sm.reporting.iter_permits(work_status=status)
        ]

    print(f"{len(permits)} active/planned permit(s) fetched.\n")

    candidates = find_collaboration_candidates(permits)
    if not candidates:
        print("No collaboration candidates found.")
        return

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


if __name__ == "__main__":
    main()
