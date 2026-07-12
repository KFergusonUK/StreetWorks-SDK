"""Check whether a USRN currently has a Section 58 restriction in force.

Reduces the Reporting API's ``/section-58s`` list for a single USRN to one
answer: the in-force restriction, else the next upcoming one, else nothing.
"""

import os
from pprint import pprint

from streetworks.streetmanager import Environment, StreetManagerClient

USRN = 33909869

with StreetManagerClient(
    os.environ["SM_EMAIL"],
    os.environ["SM_PASSWORD"],
    environment=Environment.SANDBOX,
) as sm:
    # Raw endpoint: returns the full JSON section58 list unchanged (no validation).
    pprint(sm.reporting.section_58s(USRN))

    # Derived view: validates each row against Section58SummaryResponse, then
    # reduces to one answer as a plain dict.
    result = sm.reporting.active_section_58(USRN)
    pprint(result)

    s58 = result["section_58"]
    if s58 is None:
        print(f"USRN {USRN}: no Section 58 restriction in force or upcoming")
    elif result["active"]:
        print(f"USRN {USRN}: Section 58 IN FORCE ({s58['section_58_reference_number']})")
        print(f"  {s58['street']} - until {s58['end_date']}")
    else:  # upcoming
        ref = s58["section_58_reference_number"]
        print(f"USRN {USRN}: no restriction now, one UPCOMING ({ref})")
        print(f"  {s58['street']} - starts {s58['start_date']}")

    v2 = sm.lookup.is_traffic_sensitive(33909869)
    print(v2)
