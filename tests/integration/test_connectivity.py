"""Integration tests against the real test/sandbox street works systems.

These are the opposite of the mocked unit tests: they make live calls and
therefore need real credentials. Each test skips automatically unless the
relevant environment variables are set, so the default ``pytest`` run (and
CI) never touches a live service.

Run them explicitly with credentials in the environment::

    pytest -m integration -v

All checks here are read-only and target non-production environments by
default (Street Manager SANDBOX, D-TRO integration). See
``scripts/smoke_test.py`` for the same checks as a standalone script, and
``docs/INTEGRATION.md`` for the full variable list.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


def _require(*names: str) -> None:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        pytest.skip(f"set {', '.join(missing)} to run this integration test")


def _guard_production(env_var: str, default: str) -> None:
    """Skip a test targeting production unless explicitly opted in via
    ``STREETWORKS_ALLOW_PRODUCTION=1``. Protects live systems from a stray
    ``*_ENV=production`` secret."""
    if os.environ.get(env_var, default).lower().startswith("prod") and not os.environ.get(
        "STREETWORKS_ALLOW_PRODUCTION"
    ):
        pytest.skip(
            f"{env_var}=production but STREETWORKS_ALLOW_PRODUCTION is not set; "
            "refusing to hit production"
        )


def test_street_manager_authenticate() -> None:
    _require("SM_EMAIL", "SM_PASSWORD")
    _guard_production("SM_ENV", "sandbox")
    from streetworks.streetmanager import ApiVersion, Environment, StreetManagerClient

    env = (
        Environment.PRODUCTION
        if os.environ.get("SM_ENV", "sandbox").lower().startswith("prod")
        else Environment.SANDBOX
    )
    with StreetManagerClient(
        os.environ["SM_EMAIL"],
        os.environ["SM_PASSWORD"],
        environment=env,
        version=ApiVersion(os.environ.get("SM_VERSION", "v6")),
    ) as sm:
        org = sm.authenticate()
        assert org  # a non-empty organisation reference proves auth worked


def test_street_manager_reporting_read() -> None:
    _require("SM_EMAIL", "SM_PASSWORD")
    _guard_production("SM_ENV", "sandbox")
    from streetworks.streetmanager import Environment, StreetManagerClient

    with StreetManagerClient(
        os.environ["SM_EMAIL"], os.environ["SM_PASSWORD"], environment=Environment.SANDBOX
    ) as sm:
        # A filtered reporting read; an empty result set is still a success.
        result = sm.reporting.permits(status="submitted")
        assert isinstance(result, dict)


def test_datavia_get_capabilities() -> None:
    if os.environ.get("DATAVIA_CLIENT_ID"):
        _require("DATAVIA_CLIENT_ID", "DATAVIA_CLIENT_SECRET")
        kwargs = {
            "client_id": os.environ["DATAVIA_CLIENT_ID"],
            "client_secret": os.environ["DATAVIA_CLIENT_SECRET"],
        }
    else:
        _require("DATAVIA_USER", "DATAVIA_PASSWORD")
        kwargs = {
            "username": os.environ["DATAVIA_USER"],
            "password": os.environ["DATAVIA_PASSWORD"],
        }
    from streetworks.datavia import DataViaClient

    with DataViaClient(**kwargs) as dv:
        caps = dv.get_capabilities()
        assert "WFS_Capabilities" in caps or "FeatureType" in caps


def test_datavia_street_by_usrn() -> None:
    _require("DATAVIA_USRN")
    if os.environ.get("DATAVIA_CLIENT_ID"):
        _require("DATAVIA_CLIENT_ID", "DATAVIA_CLIENT_SECRET")
        kwargs = {
            "client_id": os.environ["DATAVIA_CLIENT_ID"],
            "client_secret": os.environ["DATAVIA_CLIENT_SECRET"],
        }
    else:
        _require("DATAVIA_USER", "DATAVIA_PASSWORD")
        kwargs = {
            "username": os.environ["DATAVIA_USER"],
            "password": os.environ["DATAVIA_PASSWORD"],
        }
    from streetworks.datavia import DataViaClient

    with DataViaClient(**kwargs) as dv:
        result = dv.street_by_usrn(os.environ["DATAVIA_USRN"])
        assert result.get("type") == "FeatureCollection"


def test_nationalhighways_get_closures() -> None:
    _require("NH_SUBSCRIPTION_KEY")
    from streetworks.datex2 import ClosureType, NationalHighwaysClient

    with NationalHighwaysClient(os.environ["NH_SUBSCRIPTION_KEY"]) as nh:
        payload, _next_url = nh.get_closures(ClosureType.PLANNED)
        situations = payload.get("D2Payload", payload).get("situation", [])
        assert isinstance(situations, list)


def test_dtro_events_search() -> None:
    _require("DTRO_CLIENT_ID", "DTRO_CLIENT_SECRET")
    _guard_production("DTRO_ENV", "integration")
    from streetworks.dtro import DTROClient, Environment

    env = (
        Environment.PRODUCTION
        if os.environ.get("DTRO_ENV", "integration").lower().startswith("prod")
        else Environment.INTEGRATION
    )
    with DTROClient(
        os.environ["DTRO_CLIENT_ID"],
        os.environ["DTRO_CLIENT_SECRET"],
        app_id=os.environ.get("DTRO_APP_ID"),
        environment=env,
    ) as dtro:
        # /events requires page, pageSize, since and to.
        events = dtro.search_events(
            page=1, pageSize=1, since="2020-01-01T00:00:00", to="2099-01-01T00:00:00"
        )
        assert isinstance(events, dict)
