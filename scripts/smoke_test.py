#!/usr/bin/env python3
"""Connectivity smoke test for the streetworks SDK.

Unlike the unit tests (which are fully mocked), this script makes *real*
calls to the live test/sandbox systems using credentials from environment
variables. It verifies that each provider can authenticate and read - and,
just as usefully, tells you whether the SDK's endpoint/field assumptions
match reality for your account.

Every check is READ-ONLY and targets non-production (sandbox / integration)
environments by default. Nothing is created, updated, or deleted.

Set only the credentials for the services you want to test - each section is
skipped if its variables are absent.

    # Street Manager (SANDBOX)
    export SM_EMAIL="api-user@example.com"
    export SM_PASSWORD="..."
    export SM_ENV="sandbox"          # or "production"
    export SM_VERSION="v6"           # or "v7"

    # Geoplace DataVIA - Basic auth ...
    export DATAVIA_USER="..."
    export DATAVIA_PASSWORD="..."
    # ... or OAuth2 client credentials
    export DATAVIA_CLIENT_ID="..."
    export DATAVIA_CLIENT_SECRET="..."
    export DATAVIA_USRN="4401245"    # optional extra probe

    # D-TRO (INTEGRATION)
    export DTRO_CLIENT_ID="..."
    export DTRO_CLIENT_SECRET="..."
    export DTRO_APP_ID="..."         # your application UUID
    export DTRO_ENV="integration"    # or "production"

    python scripts/smoke_test.py

Exit code is 0 only if every attempted check passed (skipped services don't
count as failures).

By default this targets the TEST environments (Street Manager SANDBOX, D-TRO
integration). To point a service at PRODUCTION, set its ``*_ENV=production``
variable AND pass ``--allow-production`` - without that flag the script
refuses to touch production. All checks are read-only either way.
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable

from streetworks.exceptions import StreetworksError

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


class Reporter:
    def __init__(self) -> None:
        self.failures = 0
        self.ran = 0

    def result(self, service: str, status: str, detail: str = "") -> None:
        line = f"  [{status:4}] {service}"
        if detail:
            line += f" - {detail}"
        print(line)
        if status == FAIL:
            self.failures += 1
        if status in (PASS, FAIL):
            self.ran += 1

    def check(self, service: str, needed: list[str], fn: Callable[[], str]) -> None:
        missing = [v for v in needed if not os.environ.get(v)]
        if missing:
            self.result(service, SKIP, f"set {', '.join(missing)} to enable")
            return
        try:
            detail = fn()
            self.result(service, PASS, detail)
        except StreetworksError as exc:
            self.result(service, FAIL, f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001 - surface anything unexpected
            self.result(service, FAIL, f"{type(exc).__name__}: {exc}")
            traceback.print_exc()


# --------------------------------------------------------------------------- #
# Environment resolution
# --------------------------------------------------------------------------- #


def _is_prod(var: str, default: str = "sandbox") -> bool:
    return os.environ.get(var, default).lower().startswith("prod")


def target_environments() -> dict[str, str]:
    """Map each configured service to the environment it will hit."""
    envs: dict[str, str] = {}
    if os.environ.get("SM_EMAIL"):
        envs["Street Manager"] = "PRODUCTION" if _is_prod("SM_ENV") else "sandbox"
    if os.environ.get("DATAVIA_USER") or os.environ.get("DATAVIA_CLIENT_ID"):
        envs["DataVIA"] = "live"  # DataVIA has a single environment
    if os.environ.get("DTRO_CLIENT_ID"):
        envs["D-TRO"] = "PRODUCTION" if _is_prod("DTRO_ENV", "integration") else "integration"
    return envs


def production_targets(envs: dict[str, str]) -> list[str]:
    return [name for name, env in envs.items() if env == "PRODUCTION"]


# --------------------------------------------------------------------------- #
# Per-service checks
# --------------------------------------------------------------------------- #


def check_street_manager() -> str:
    from streetworks.streetmanager import ApiVersion, Environment, StreetManagerClient

    env = Environment.PRODUCTION if _is_prod("SM_ENV") else Environment.SANDBOX
    version = ApiVersion(os.environ.get("SM_VERSION", "v6"))
    with StreetManagerClient(
        os.environ["SM_EMAIL"],
        os.environ["SM_PASSWORD"],
        environment=env,
        version=version,
    ) as sm:
        org = sm.authenticate()
        return f"authenticated ({env.name.lower()}/{version.value}), organisation {org}"


def check_datavia() -> str:
    from streetworks.datavia import DataViaClient

    if os.environ.get("DATAVIA_CLIENT_ID"):
        client = DataViaClient(
            client_id=os.environ["DATAVIA_CLIENT_ID"],
            client_secret=os.environ["DATAVIA_CLIENT_SECRET"],
        )
        method = "OAuth2"
    else:
        client = DataViaClient(
            username=os.environ["DATAVIA_USER"], password=os.environ["DATAVIA_PASSWORD"]
        )
        method = "Basic"

    with client as dv:
        caps = dv.get_capabilities()
        detail = f"{method} auth, GetCapabilities returned {len(caps)} bytes"
        usrn = os.environ.get("DATAVIA_USRN")
        if usrn:
            result = dv.street_by_usrn(usrn)
            n = len(result.get("features", [])) if isinstance(result, dict) else 0
            detail += f"; USRN {usrn} -> {n} feature(s)"
        return detail


def check_dtro() -> str:
    from streetworks.dtro import DTROClient, Environment

    env = (
        Environment.PRODUCTION
        if _is_prod("DTRO_ENV", "integration")
        else Environment.INTEGRATION
    )
    with DTROClient(
        os.environ["DTRO_CLIENT_ID"],
        os.environ["DTRO_CLIENT_SECRET"],
        app_id=os.environ.get("DTRO_APP_ID"),
        environment=env,
    ) as dtro:
        events = dtro.search_events(pageSize=1)
        total = events.get("totalCount", "?") if isinstance(events, dict) else "?"
        return f"token acquired ({env.name.lower()}), events search -> totalCount {total}"


def check_opendata_parsing() -> str:
    """Open Data is a push model - real end-to-end needs a deployed HTTPS
    endpoint. What we *can* verify locally is that the parsing pipeline works
    on a well-formed SNS notification."""
    import json

    from streetworks.opendata import EventNotification, handle

    sample = json.dumps(
        {
            "Type": "Notification",
            "MessageId": "smoke-test",
            "TopicArn": "arn:aws:sns:eu-west-2:000000000000:street-manager",
            "Message": json.dumps(
                {"event_type": "WORK_START", "object_type": "PERMIT", "object_reference": "X-01"}
            ),
        }
    )
    payload = handle(sample, verify=False)
    event = EventNotification.model_validate(payload)
    return f"parsed sample notification ({event.event_type}) - deploy an endpoint for live push"


def main() -> int:
    allow_prod = "--allow-production" in sys.argv

    envs = target_environments()
    prod = production_targets(envs)

    print("=" * 64)
    print("streetworks connectivity smoke test")
    if not envs:
        print("(no services configured)")
    else:
        banner = "  ".join(f"{name}: {env}" for name, env in envs.items())
        print(f"TARGET  {banner}")
    print("All checks are READ-ONLY.")
    print("=" * 64)
    print()

    # Production is a deliberate act. Refuse to touch it without opt-in.
    if prod and not allow_prod:
        print(
            f"REFUSING to run: {', '.join(prod)} would hit PRODUCTION.\n"
            "Production is real live data. If you truly intend this, re-run with:\n"
            "    python scripts/smoke_test.py --allow-production\n"
            "Otherwise unset the *_ENV=production variable(s) to target the "
            "test environment."
        )
        return 2

    if prod:
        print(f"!! Running against PRODUCTION for: {', '.join(prod)} (read-only) !!\n")

    reporter = Reporter()
    reporter.check("Street Manager", ["SM_EMAIL", "SM_PASSWORD"], check_street_manager)
    if os.environ.get("DATAVIA_CLIENT_ID"):
        reporter.check(
            "DataVIA (OAuth2)", ["DATAVIA_CLIENT_ID", "DATAVIA_CLIENT_SECRET"], check_datavia
        )
    else:
        reporter.check("DataVIA (Basic)", ["DATAVIA_USER", "DATAVIA_PASSWORD"], check_datavia)
    reporter.check("D-TRO", ["DTRO_CLIENT_ID", "DTRO_CLIENT_SECRET"], check_dtro)
    # Open Data parsing always runs - it needs no credentials
    reporter.check("Open Data (parsing)", [], check_opendata_parsing)

    print()
    if reporter.ran == 0:
        print("No services configured - set credentials and re-run. See --help.")
        return 0
    if reporter.failures:
        print(f"{reporter.failures} of {reporter.ran} check(s) FAILED.")
        return 1
    print(f"All {reporter.ran} attempted check(s) passed.")
    return 0


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        raise SystemExit(0)
    raise SystemExit(main())
