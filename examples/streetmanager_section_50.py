"""Apply for, start, and stop a Section 50 (S50) application in Street
Manager, submitted under the highway authority's own promoter account -
the applicant never touches Street Manager directly.

**Scope: apply / start / stop only.** Reinstatement (Cat C inspection, bond
release, guarantee period) is deliberately out of scope and stays
council-side - this is not the full S50 lifecycle, just the three verbs a
licence needs to get onto and off Street Manager's register.

**This submits a Section 50 application to Street Manager - where the
authority manages, grants or refuses it.** The applicant fills it in; it
lands as a submitted S50 under the authority's own promoter account, and
the highway authority then works it *in Street Manager* - reviews, grants
or refuses - and confirms the outcome to the applicant directly, by the
email/phone contact captured below (so ``secondary_contact_email`` is
load-bearing here, and required in the front-end, even though Street
Manager itself allows it empty). Supporting evidence (insurance,
accreditation, plans) is *attached to the record* - see ``apply()`` below,
a real, sandbox-callable upload via ``WorkAPI.upload_file``, not a mockup.
What it is *not* is the binding licence itself: the Section 50 licence,
with its conditions, bond and signed undertakings, is the separate legal
instrument the authority issues alongside, and this script does not
capture the licensee declarations, contractor identity, land title or
adoption logic (see ``s50-streetmanager-form-mapping-addendum.md``'s own
field-disposition table for the mapping vs the real Durham S50/01 form's
full field-by-field breakdown). Attaching evidence is not the same as it
being assessed - filing a document is not acceptance of it - so this
drives the workflow but does not grant the licence. The licence decision
remains with the Highway Authority. Remember this is just an example of
what you COULD do.

**Two real, evidenced additions layered onto that unchanged scope**:
``apply()`` uploads illustrative placeholder evidence files and includes
the real ``file_id``\\ s the sandbox returns on ``WorkCreateRequest.file_ids``
(a genuine field, confirmed against ``WorkCreateRequest``'s own model - see
``section_50_utils.py``'s docstring for why this needed no connector
change at all, ``file_ids`` already passes through like every other
applicant-stated field); and a real per-surface bond estimate is computed
from the drawn extent's own true ground area (a shoelace-formula
:func:`_polygon_area_m2` over the already-BNG-reprojected geometry - real
metres, not degrees) times illustrative council rates, folded into
``additional_info`` as a clearly-labelled note, never a structured SM
field. Both are demonstrated capability, not just documented ones - but
the bond *rates* and the *placeholder* evidence files are illustrative,
exactly like ``HA_SWA_CODE``/``WORKSTREAM_PREFIX`` below; only the upload
calls, the returned file ids, and the area arithmetic are real.

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
remains unexercised. The demo geometry below remains illustrative (a small
rectangular footprint near Bishop Auckland, not the real drawn extent from
the record referenced above) - a polygon rather than a bare point since a
real S50 excavation has a footprint, and the bond estimate needs one to
compute an area from.

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

# Illustrative WGS84 polygon (~8m x 4m) near Bishop Auckland - NOT the real
# drawn extent from UG05016064998-01 (unavailable to this example); replace
# with your own applicant-drawn geometry. A polygon rather than a point so
# the bond estimate below has a real footprint to compute an area from.
DEMO_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [
        [
            [-1.6645027687666911, 53.6119724337765],
            [-1.664381631233309, 53.6119724337765],
            [-1.664381631233309, 53.612008366223506],
            [-1.6645027687666911, 53.612008366223506],
            [-1.6645027687666911, 53.6119724337765],
        ]
    ],
}

# Synthetic placeholder evidence files - dummy content, never a real policy
# document or accreditation copy. Demonstrates the real upload-then-attach
# sequence (see apply()) that a real front end would run against real
# scanned copies of the applicant's own insurance certificate/accreditation.
DEMO_ATTACHMENTS = [
    ("insurance.pdf", b"%PDF-1.4\n% Placeholder only - not a real policy document.\n"),
    ("accreditation.pdf", b"%PDF-1.4\n% Placeholder only - not a real accreditation copy.\n"),
]

# Illustrative per-surface areas (m2) for the bond estimate below - applicant
# -apportioned, not derived from geometry (the drawn extent alone can't say
# which square metres are carriageway vs footway vs verge without a
# surfacing dataset). Consistent with this demo's own
# location_types=["verge", "footway"] and no carriageway incursion - real
# DEMO_GEOMETRY area is ~32.0m2, matched here so apply() doesn't print its
# own mismatch nudge on a stock run.
DEMO_SURFACE_AREAS = {"footway": 20.0, "verge": 12.0}

# Illustrative bond rates (GBP/m2) - council policy, not SDK data; varies by
# authority and changes annually. Durham's real schedule is not shipped
# here. Replace with your own highway authority's current rates, the same
# way HA_SWA_CODE/WORKSTREAM_PREFIX above are demo values to replace.
DEMO_BOND_RATES = {"footway": 15.0, "verge": 10.0}

DEMO_APPLICANT_FIELDS = {
    "secondary_contact": "J. Smith (licensee contact)",
    "secondary_contact_number": "01234 567890",
    # How the authority returns the grant/refuse decision. Street Manager
    # allows this empty, but the S50 workflow is: applicant submits, the HA
    # works it in Street Manager, then confirms the outcome to the applicant
    # here - so it's load-bearing, and required in the front-end. A genuine
    # (nullable) WorkCreateRequest field, confirmed against swagger V6.17.3,
    # so it passes straight through assembly like every other applicant-stated
    # field - no connector change. additional_contact_email is also available
    # if you ever need a correspondence address distinct from the licensee.
    "secondary_contact_email": "j.smith@example.com",
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


def _polygon_area_m2(bng_polygon: dict) -> float:
    """Shoelace-formula area of a BNG (EPSG:27700) GeoJSON Polygon's
    exterior ring, in real ground square metres - metres-accurate for free
    since the geometry is already reprojected to BNG, not degrees. Interior
    rings (holes) are ignored - an S50 excavation footprint doesn't have
    one. Pure, example-layer only - section_50_utils never computes an
    area, it only reprojects."""
    ring = bng_polygon["coordinates"][0]
    area = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def calculate_bond(
    area_by_surface: dict[str, float], rate_by_surface: dict[str, float]
) -> tuple[dict[str, float], float]:
    """Illustrative bond estimate, itemised per surface plus a total.
    Pure function, example-layer only - section_50_utils (the connector)
    never learns what a bond is, matching its own "transport plus identity
    injection only" scope. The carriageway/footway/verge split is
    applicant-apportioned (``area_by_surface``), never derived from
    geometry alone - a drawn extent can't say which of its own square
    metres are carriageway without a surfacing dataset. Never sent to
    Street Manager as a structured field; the caller folds the result into
    ``additional_info`` as a labelled note instead."""
    itemised = {
        surface: area * rate_by_surface[surface] for surface, area in area_by_surface.items()
    }
    return itemised, sum(itemised.values())


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

        # Real upload-then-attach sequence against the sandbox - not a
        # mockup. Non-fatal per file: a real front end shouldn't let one
        # bad upload block the whole application. See module docstring.
        file_ids = []
        for filename, content in DEMO_ATTACHMENTS:
            try:
                uploaded = sm.work.upload_file(filename, content)
                file_ids.append(uploaded["file_id"])
            except Exception as exc:  # noqa: BLE001 - evidence attachment is optional, never fatal
                print(f"Could not upload {filename} ({exc}); continuing without it.")
        if file_ids:
            print(f"Uploaded {len(file_ids)} evidence file(s), file_ids={file_ids}")

        applicant_fields = dict(DEMO_APPLICANT_FIELDS)
        if file_ids:
            applicant_fields["file_ids"] = file_ids

        payload, warnings = build_work_create_request(
            applicant_fields,
            ha_swa_code=HA_SWA_CODE,
            host_usrn=DEMO_USRN,
            geometry=DEMO_GEOMETRY,
            workstream_prefix=WORKSTREAM_PREFIX,
            host_usrn_geometry=usrn_geometry,
        )
        for warning in warnings:
            print(f"Warning: {warning}")

        # Real area, from the already-BNG-reprojected drawn extent - see
        # _polygon_area_m2's own docstring. The rates are illustrative; the
        # arithmetic and the area it's applied to are not.
        drawn_area = _polygon_area_m2(payload["works_coordinates"])
        surface_total = sum(DEMO_SURFACE_AREAS.values())
        if abs(surface_total - drawn_area) > max(2.0, drawn_area * 0.1):
            print(
                f"Note: illustrative per-surface areas ({surface_total:.1f}m²) don't "
                f"closely match the drawn extent's own area ({drawn_area:.1f}m²) - a real "
                "front end would flag this to the applicant, not silently bond the mismatch."
            )
        itemised, bond_total = calculate_bond(DEMO_SURFACE_AREAS, DEMO_BOND_RATES)
        bond_note = (
            f"Illustrative bond estimate (demo only, not enforced by Street Manager): "
            f"£{bond_total:,.2f} - "
            + ", ".join(f"{surface}: £{amount:,.2f}" for surface, amount in itemised.items())
        )
        existing_note = payload.get("additional_info")
        payload["additional_info"] = f"{existing_note} {bond_note}" if existing_note else bond_note

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
