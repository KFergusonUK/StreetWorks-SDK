"""streetworks quickstart - one small call to every provider.

Copy `.env.example` to `.env`, fill in the credentials you have, then:

    python examples/quickstart.py

Providers without credentials are skipped; SRWR and OS Open USRN need none.
Everything here is read-only.
"""

from __future__ import annotations

import os
from pathlib import Path

# --- tiny .env loader (stdlib-only; python-dotenv works too) ----------------


def load_dotenv(path: str = ".env") -> None:
    file = Path(path)
    if not file.exists():
        return
    for line in file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv()


def section(title: str) -> None:
    print(f"\n=== {title} " + "=" * max(0, 56 - len(title)))


# --- Street Manager: log in, list recent permits ------------------------------

section("Street Manager")
if os.environ.get("SM_EMAIL"):
    from streetworks.streetmanager import Environment, StreetManagerClient

    env = (
        Environment.PRODUCTION
        if os.environ.get("SM_ENV", "sandbox").lower() == "production"
        else Environment.SANDBOX
    )
    with StreetManagerClient(
        os.environ["SM_EMAIL"], os.environ["SM_PASSWORD"], environment=env
    ) as sm:
        org = sm.authenticate()
        print(f"logged in ({env.name.lower()}), organisation {org}")
        page = sm.reporting.permits()
        for permit in page.get("rows", [])[:3]:
            print(
                " ",
                permit.get("permit_reference_number") or permit.get("work_reference_number"),
                "-",
                permit.get("street_name", "?"),
            )
        # For everything across all pages: sm.reporting.iter_permits(...)
else:
    print("skipped - set SM_EMAIL / SM_PASSWORD in .env")

# --- DataVIA: look up one street by USRN --------------------------------------

section("Geoplace DataVIA")
if os.environ.get("DATAVIA_USER") or os.environ.get("DATAVIA_CLIENT_ID"):
    from streetworks.datavia import DataViaClient

    if os.environ.get("DATAVIA_CLIENT_ID"):
        dv = DataViaClient(
            client_id=os.environ["DATAVIA_CLIENT_ID"],
            client_secret=os.environ["DATAVIA_CLIENT_SECRET"],
        )
    else:
        dv = DataViaClient(
            username=os.environ["DATAVIA_USER"],
            password=os.environ["DATAVIA_PASSWORD"],
        )
    with dv:
        usrn = os.environ.get("DATAVIA_USRN", "33909869")
        result = dv.street_by_usrn(usrn)
        features = result.get("features", []) if isinstance(result, dict) else []
        print(f"USRN {usrn}: {len(features)} feature(s)")
        if features:
            props = features[0].get("properties", {})
            print(" ", props.get("street_descriptor") or props)
else:
    print("skipped - set DATAVIA_USER / DATAVIA_PASSWORD in .env")

# --- D-TRO: search recent traffic-order events ---------------------------------

section("D-TRO")
if os.environ.get("DTRO_CLIENT_ID"):
    from datetime import datetime, timezone

    from streetworks.dtro import DTROClient
    from streetworks.dtro import Environment as DtroEnv

    env = (
        DtroEnv.PRODUCTION
        if os.environ.get("DTRO_ENV", "").lower() == "production"
        else DtroEnv.INTEGRATION
    )
    if env is DtroEnv.PRODUCTION and not os.environ.get("STREETWORKS_ALLOW_PRODUCTION"):
        print("skipped - DTRO_ENV=production also needs STREETWORKS_ALLOW_PRODUCTION=1")
    else:
        with DTROClient(
            os.environ["DTRO_CLIENT_ID"],
            os.environ["DTRO_CLIENT_SECRET"],
            app_id=os.environ.get("DTRO_APP_ID"),
            environment=env,
        ) as dtro:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            events = dtro.search_events(
                page=1, pageSize=3, since="2024-01-01T00:00:00", to=now
            )
            info = dtro.token_info or {}
            print(f"authenticated ({env.name.lower()}, scope={info.get('scope')})")
            for event in (events.get("events") or [])[:3]:
                print(" ", event.get("eventType"), "-", event.get("troName", ""))
else:
    print("skipped - set DTRO_CLIENT_ID / DTRO_CLIENT_SECRET in .env")

# --- SRWR Open Data: today's Scottish road works (no credentials) ---------------

section("SRWR Open Data (Scotland)")
from streetworks.srwr import SRWRClient, describe  # noqa: E402

with SRWRClient() as srwr:
    archive = os.environ.get("SRWR_ARCHIVE") or srwr.download_daily("srwr-daily.zip")
    shown = 0
    for activity in srwr.iter_activities(archive):
        if not activity.phases:
            continue
        phase = activity.phases[-1]
        print(
            f"  {activity.activity_id}:",
            describe("works_type", phase.works_type),
            "-",
            describe("activity_status", phase.activity_status),
            "@",
            (phase.location or "?")[:50],
        )
        shown += 1
        if shown == 3:
            break

# --- OS Open USRN: national street lookup (no credentials) ----------------------

section("OS Open USRN")
from streetworks.openusrn import OpenUSRNClient, UsrnDatabase  # noqa: E402

with OpenUSRNClient() as client:
    entry = client.downloads()[0]
    print(f"product available: {entry['fileName']} ({entry['size']:,} bytes)")

gpkg = os.environ.get("OPENUSRN_GPKG")
if gpkg and Path(gpkg).exists():
    with UsrnDatabase(gpkg) as db:
        usrn = os.environ.get("OPENUSRN_TEST_USRN", "33909869")
        street = db.get(usrn)
        if street and street.geometry:
            print(f"  USRN {street.usrn} -> {street.geometry[:60]}...")
        else:
            print(f"  USRN {usrn} not found in local file")
else:
    print("  (set OPENUSRN_GPKG to a downloaded GeoPackage for local lookups -")
    print("   see examples/openusrn_lookup.py for the one-off ~300 MB download)")

print("\ndone.")
