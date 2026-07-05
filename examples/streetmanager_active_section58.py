"""Check whether a USRN currently has a Section 58 restriction in force.

Reduces the Reporting API's ``/section-58s`` list for a single USRN to one
answer: the in-force restriction, else the next upcoming one, else nothing.

Raw Response:
{'pagination': {'has_next_page': False, 'total_rows': 4},
 'rows': [{'area': '',
           'date_created': '2026-07-03T09:03:26.435Z',
           'end_date': '2027-01-01T23:00:00.000Z',
           'ha_organisation_name': 'DURHAM COUNTY COUNCIL',
           'restriction_duration': 'six_months',
           'restriction_duration_string': 'six_months',
           'section_58_reference_number': 'S58-1355-06848964',
           'section_58_status': 'in_force',
           'section_58_status_string': 'in_force',
           'start_date': '2026-07-02T23:00:00.000Z',
           'street': 'CARR STREET',
           'town': 'SPENNYMOOR',
           'usrn': 33909869},
          {'area': '',
           'date_created': '2024-05-15T13:16:42.079Z',
           'end_date': '2024-11-13T23:00:00.000Z',
           'ha_organisation_name': 'DURHAM COUNTY COUNCIL',
           'restriction_duration': 'six_months',
           'restriction_duration_string': 'six_months',
           'section_58_reference_number': 'S58-1355-66208226',
           'section_58_status': 'closed',
           'section_58_status_string': 'closed',
           'start_date': '2024-05-14T23:00:00.000Z',
           'street': 'CARR STREET',
           'town': 'SPENNYMOOR',
           'usrn': 33909869},
          {'area': 'SPENNYMOOR',
           'date_created': '2023-08-09T14:49:47.276Z',
           'end_date': '2024-11-14T00:00:00.000Z',
           'ha_organisation_name': 'DURHAM COUNTY COUNCIL',
           'restriction_duration': 'one_year',
           'restriction_duration_string': 'one_year',
           'section_58_reference_number': 'S58-1355-65977366',
           'section_58_status': 'closed',
           'section_58_status_string': 'closed',
           'start_date': '2023-11-15T00:00:00.000Z',
           'street': 'CARR STREET',
           'town': 'SPENNYMOOR',
           'usrn': 33909869},
          {'area': 'SPENNYMOOR',
           'date_created': '2023-08-09T14:19:13.847Z',
           'end_date': '2024-11-12T00:00:00.000Z',
           'ha_organisation_name': 'DURHAM COUNTY COUNCIL',
           'restriction_duration': 'one_year',
           'restriction_duration_string': 'one_year',
           'section_58_reference_number': 'S58-1355-72509699',
           'section_58_status': 'closed',
           'section_58_status_string': 'closed',
           'start_date': '2023-11-13T00:00:00.000Z',
           'street': 'CARR STREET',
           'town': 'SPENNYMOOR',
           'usrn': 33909869}]}

Vs

Active section 58 response
{'active': True,
 'section_58': {'area': '',
                'date_created': '2026-07-03T09:03:26.435Z',
                'end_date': '2027-01-01T23:00:00.000Z',
                'ha_organisation_name': 'DURHAM COUNTY COUNCIL',
                'restriction_duration': 'six_months',
                'restriction_duration_string': 'six_months',
                'section_58_reference_number': 'S58-1355-06848964',
                'section_58_status': 'in_force',
                'section_58_status_string': 'in_force',
                'start_date': '2026-07-02T23:00:00.000Z',
                'street': 'CARR STREET',
                'town': 'SPENNYMOOR',
                'usrn': 33909869},
 'upcoming': False}
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
