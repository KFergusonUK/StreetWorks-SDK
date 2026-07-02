"""Fetch a work record and list submitted permits from the SANDBOX environment."""

import os

from streetworks.streetmanager import Environment, StreetManagerClient

with StreetManagerClient(
    os.environ["SM_EMAIL"],
    os.environ["SM_PASSWORD"],
    environment=Environment.SANDBOX,
) as sm:
    print("Authenticated as organisation:", sm.organisation_reference)

    submitted = sm.reporting.permits(status="submitted")
    print("Permits awaiting assessment:", submitted)
