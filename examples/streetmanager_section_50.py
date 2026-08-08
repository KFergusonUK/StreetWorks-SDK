"""Apply for, start, and stop a Section 50 (S50) licence works record in
Street Manager, submitted under the highway authority's own promoter
account - the applicant never touches Street Manager directly.

**Scope: apply / start / stop only.** Reinstatement (Cat C inspection, bond
release, guarantee period) is deliberately out of scope and stays
council-side - this is not the full S50 lifecycle, just the three verbs a
licence needs to get onto and off Street Manager's register.

The connector logic this script demonstrates (reprojection, request
assembly, identity stamping - see
``streetworks.streetmanager.utils.section_50_utils``) was designed against
live-sandbox findings from a real S50 record (``UG05016064998-01``,
Ferguson Court, Bishop Auckland, USRN 42820309) - see that module's own
docstring. **This *script* is verified against the Street Manager sandbox,
2026-08-06** - apply/start/stop all succeeded end-to-end against a real
sandbox record, per ``docs/concepts/write-path.md``'s own verification
record (the source of truth for this claim - check it before restating
this docstring, rather than assuming the date still holds). Production
remains unexercised. The demo geometry below remains illustrative (an
approximate point near Bishop Auckland), not the real drawn extent from
the record referenced above.

Run:
    python examples/streetmanager_section_50.py apply
    python examples/streetmanager_section_50.py start WRN12345678
    python examples/streetmanager_section_50.py stop WRN12345678

Needs SM_EMAIL / SM_PASSWORD (SM_ENV=sandbox|production, default sandbox -
see .env.example). Prints a clear message and exits cleanly if unset,
rather than a traceback.

**These must be Promoter-role credentials, not Highway Authority - live-
confirmed, not assumed.** A Street Manager login is registered under one
organisation with one role; a single account can't hold both HA and
Promoter registrations. Every *other* Street Manager example in this repo
(``collaboration_finder.py``, ``streetmanager_quickstart.py``, reporting/
permit reads) only ever reads, which an HA-role login covers - but
``work.create_work`` (what ``apply`` calls) requires a Promoter-role
account, since works are submitted by promoters. If your existing
``SM_EMAIL``/``SM_PASSWORD`` is HA-only (the DfT sandbox signup defaults to
one role per account), register a second sandbox account as Promoter and
point this script at that one specifically - the payload's own
``promoter_swa_code``/``highway_authority_swa_code`` (both stamped to the
same HA SWA code - see ``section_50_utils.py``) describe *whose identity
the work is filed under*, which is a separate thing from *which login's
role is allowed to call the endpoint*.

``start``/``stop`` each require the work reference number returned by
``apply`` as an explicit positional argument - neither can fire as a side
effect of just running this script, since both mutate a real record's
lifecycle state.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

# Demo config - replace with your own highway authority's values.
HA_SWA_CODE = "1355"  # Durham County Council
WORKSTREAM_PREFIX = "050"  # 3 digits only, no "UG" prefix
DEMO_USRN = 42820309  # Ferguson Court, Bishop Auckland - the real sandbox record (see docstring)

# Illustrative WGS84 point near Bishop Auckland - NOT the real drawn extent
# from UG05016064998-01 (unavailable to this example); replace with your
# own applicant-drawn geometry.
DEMO_GEOMETRY = {"type": "Point", "coordinates": [-1.6644422, 53.6119904]}

DEMO_APPLICANT_FIELDS = {
    "secondary_contact": "J. Smith (licensee contact)",
    "secondary_contact_number": "01234 567890",
    "proposed_start_date": "2026-09-01T00:00:00Z",
    "proposed_end_date": "2026-09-08T00:00:00Z",
    "description_of_work": "New private access - Section 50 licensed works",
    "works_location_description": "Verge and footway outside Ferguson Court",
    "excavation": True,
    "traffic_management_plan": False,
    "lane_rental_applicable": False,
    "collaborative_working": False,
    "traffic_management_type": "no_carriageway_incursion",
    "location_types": ["verge", "footway"],
    "close_footway": "no",
    "close_footpath": "no",
    # Required by Street Manager whenever work_type = "planned" (which this
    # connector always pins) - live-confirmed via a real sandbox rejection,
    # not assumed. No carriageway incursion here, so no TTRO is needed.
    "is_ttro_required": False,
    # Required whenever collaborative_working = false (also live-confirmed) -
    # and, in turn, reason_for_non_collaboration is required once this is
    # false. Chosen over the "true" branch, which would additionally require
    # collaboration_types and a collaboration contact - more than a single,
    # non-collaborative S50 licence needs.
    "others_can_collaborate_on_work": False,
    "reason_for_non_collaboration": (
        "Single licensed S50 works; no collaboration opportunity identified."
    ),
}


def _client_or_none():
    if not os.environ.get("SM_EMAIL") or not os.environ.get("SM_PASSWORD"):
        print("Set your Street Manager credentials first: SM_EMAIL / SM_PASSWORD")
        print("(SM_ENV=sandbox|production, default sandbox). See .env.example.")
        return None

    from streetworks.streetmanager import Environment, StreetManagerClient

    env = (
        Environment.PRODUCTION
        if os.environ.get("SM_ENV", "sandbox").lower() == "production"
        else Environment.SANDBOX
    )
    return StreetManagerClient(os.environ["SM_EMAIL"], os.environ["SM_PASSWORD"], environment=env)


def apply() -> None:
    from streetworks.streetmanager.utils.section_50_utils import build_work_create_request

    sm = _client_or_none()
    if sm is None:
        return

    with sm:
        try:
            usrn_geometry = sm.lookup.street_by_usrn(DEMO_USRN).get("geometry")
        except Exception as exc:  # noqa: BLE001 - the nudge check is optional, never fatal
            print(f"Could not fetch USRN geometry for the nudge check ({exc}); skipping it.")
            usrn_geometry = None

        payload, warnings = build_work_create_request(
            DEMO_APPLICANT_FIELDS,
            ha_swa_code=HA_SWA_CODE,
            host_usrn=DEMO_USRN,
            geometry=DEMO_GEOMETRY,
            workstream_prefix=WORKSTREAM_PREFIX,
            host_usrn_geometry=usrn_geometry,
        )
        for warning in warnings:
            print(f"Warning: {warning}")

        response = _call(sm.work.create_work, payload)
        print("Created:", response)
        print(
            "Persist both references - start/stop key off work_reference_number only, "
            "not permit_reference_number."
        )


def start(work_reference_number: str) -> None:
    from streetworks.streetmanager.utils.section_50_utils import build_work_start_update

    sm = _client_or_none()
    if sm is None:
        return

    with sm:
        payload = build_work_start_update(datetime.now(timezone.utc))
        response = _call(sm.work.start_work, work_reference_number, payload)
        print("Started:", response)


def stop(work_reference_number: str) -> None:
    from streetworks.streetmanager.utils.section_50_utils import build_work_stop_update

    sm = _client_or_none()
    if sm is None:
        return

    with sm:
        payload = build_work_stop_update(datetime.now(timezone.utc))
        response = _call(sm.work.stop_work, work_reference_number, payload)
        print("Stopped:", response)


def _call(fn, *args):
    """Runs a write call, printing Street Manager's own response body on a
    rejection before re-raising - APIError's default message (e.g. "[400]
    Bad Request") doesn't include SM's actual per-field validation detail,
    which lives in the exception's .body and is otherwise easy to miss."""
    from streetworks.exceptions import APIError

    try:
        return fn(*args)
    except APIError as exc:
        print(f"Street Manager rejected the request: {exc}")
        print("Response body:", exc.body)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("apply")
    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("work_reference_number")
    stop_parser = subparsers.add_parser("stop")
    stop_parser.add_argument("work_reference_number")

    args = parser.parse_args()
    if args.command == "apply":
        apply()
    elif args.command == "start":
        start(args.work_reference_number)
    elif args.command == "stop":
        stop(args.work_reference_number)


if __name__ == "__main__":
    main()
