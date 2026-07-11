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

    # National Highways (DATEX II closures) - a single live environment
    export NH_SUBSCRIPTION_KEY="..."

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
from datetime import datetime, timezone

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
    if os.environ.get("NH_SUBSCRIPTION_KEY"):
        envs["National Highways"] = "live"  # single environment, no sandbox
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
        wms = dv.wms_capabilities()
        detail = (
            f"{method} auth, WFS caps {len(caps)} bytes, WMS caps {len(wms)} bytes"
        )
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
        # /events requires page, pageSize, since and to (all mandatory).
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        events = dtro.search_events(
            page=1, pageSize=1, since="2020-01-01T00:00:00", to=now
        )
        total = events.get("totalCount", "?") if isinstance(events, dict) else "?"
        info = dtro.token_info or {}
        scope = info.get("scope")
        products = info.get("api_product_list")
        extra = f", scope={scope}, products={products}" if scope or products else ""
        return f"token acquired ({env.name.lower()}{extra}), events -> totalCount {total}"


def check_nationalhighways() -> str:
    """National Highways closures (DATEX II v3.4 JSON) - a single live
    environment, read-only. Fetches one page of planned closures."""
    from streetworks.datex2 import ClosureType, NationalHighwaysClient

    with NationalHighwaysClient(os.environ["NH_SUBSCRIPTION_KEY"]) as nh:
        payload, next_url = nh.get_closures(ClosureType.PLANNED)
        situations = payload.get("D2Payload", payload).get("situation", [])
    return f"{len(situations)} situations on page 1 (more pages: {bool(next_url)})"


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


def check_srwr() -> str:
    """SRWR Open Data needs no credentials. If SRWR_ARCHIVE points at a local
    .zip/.csv it is parsed; otherwise the latest daily extract is downloaded
    (a few MB) and parsed. Both paths are read-only."""
    import tempfile
    from pathlib import Path

    from streetworks.srwr import SRWRClient, iter_activities

    local = os.environ.get("SRWR_ARCHIVE")
    if local:
        path = Path(local)
        source_desc = f"local archive {path.name}"
    else:
        tmp = Path(tempfile.mkdtemp()) / "srwr-daily.zip"
        with SRWRClient() as srwr:
            path = srwr.download_daily(tmp)
        source_desc = f"downloaded daily extract ({path.stat().st_size:,} bytes)"

    count = with_phase = 0
    for activity in iter_activities(path):
        count += 1
        if activity.phases:
            with_phase += 1
    return f"{source_desc} -> {count} activities ({with_phase} with phases)"


def check_openusrn() -> str:
    """OS Open USRN needs no credentials. By default this only queries the
    Downloads API metadata (the GeoPackage itself is ~300 MB - too big for a
    smoke test). Set OPENUSRN_GPKG to a local extracted .gpkg to also verify
    a real lookup (set OPENUSRN_TEST_USRN to choose the USRN)."""
    from streetworks.openusrn import OpenUSRNClient, UsrnDatabase

    with OpenUSRNClient() as client:
        entries = client.downloads()
        if not entries:
            raise RuntimeError("Downloads API returned no GeoPackage entry")
        entry = entries[0]
        summary = f"API OK: {entry['fileName']} ({entry['size']:,} bytes)"

    local = os.environ.get("OPENUSRN_GPKG")
    if local:
        with UsrnDatabase(local) as db:
            total = db.count()
            usrn = os.environ.get("OPENUSRN_TEST_USRN")
            if usrn:
                street = db.get(usrn)
                found = "found" if street else "NOT FOUND"
                geom = " with geometry" if street and street.geometry else ""
                summary += f"; local db {total:,} USRNs, {usrn} {found}{geom}"
            else:
                summary += f"; local db {total:,} USRNs"
    return summary


def check_datex2_ndw() -> str:
    """NDW Open Data (Netherlands) needs no credentials. Set NDW_FEED to a
    local planned-works file to parse it locally; otherwise the live feed is
    downloaded (~15 MB gzipped)."""
    import tempfile
    from pathlib import Path

    from streetworks.datex2 import NDWClient, iter_roadworks

    local = os.environ.get("NDW_FEED")
    if local:
        path = Path(local)
        source_desc = f"local feed {path.name}"
    else:
        tmp = Path(tempfile.mkdtemp()) / "ndw-planned.xml.gz"
        with NDWClient() as ndw:
            path = ndw.download_planned_works(tmp)
        source_desc = f"downloaded planned-works feed ({path.stat().st_size:,} bytes)"

    situations = works = 0
    for situation in iter_roadworks(path):
        situations += 1
        works += len(situation.roadworks)
    return f"{source_desc} -> {situations:,} roadworks situations ({works:,} works records)"


def check_digitraffic() -> str:
    """Digitraffic (Finland) needs no credentials. Its Simple-JSON schema
    isn't DATEX-shaped itself (see streetworks.datex2.digitraffic), but
    still produces the same Situation/SituationRecord models."""
    from streetworks.datex2.digitraffic import DigitrafficClient, provinces

    with DigitrafficClient() as digitraffic:
        payload = digitraffic.get_roadworks()
        situations = digitraffic.parse(payload)
    works = sum(len(s.roadworks) for s in situations)
    distinct_provinces = len(set(provinces(payload).values()))
    return (
        f"{len(situations):,} situations ({works:,} works records) across "
        f"{distinct_provinces} provinces"
    )


def check_wzdx() -> str:
    """WZDx (US Work Zone Data Exchange) needs no credentials. Points at
    Washington State DOT's feed by default; set WZDX_FEED_URL to point at a
    different agency's feed instead (see streetworks.wzdx.list_feeds() for
    the full USDOT registry)."""
    from streetworks.wzdx import WZDxClient

    feed_url = os.environ.get("WZDX_FEED_URL", "https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed")
    with WZDxClient() as wzdx:
        feed = wzdx.fetch(feed_url)
    work_zones = sum(1 for e in feed.road_events if e.is_work_zone)
    return (
        f"{feed.publisher} (WZDx v{feed.version}): {len(feed.road_events)} road "
        f"events ({work_zones} work zones)"
    )


def check_trafficwatchni() -> str:
    """TrafficWatchNI RSS (Northern Ireland) needs no credentials."""
    from streetworks.trafficwatchni import Feed, TrafficWatchNIClient

    with TrafficWatchNIClient() as twni:
        items = twni.fetch(Feed.ROADWORKS)
    extracted = sum(1 for i in items if i.closure_type or i.promoter)
    return f"{len(items)} roadworks items ({extracted} with extracted fields)"


def check_trafficwales() -> str:
    """Traffic Wales RSS needs no credentials."""
    from streetworks.trafficwales import Feed, TrafficWalesClient

    with TrafficWalesClient() as tw:
        items = tw.fetch(Feed.ROADWORKS)
    with_roads = sum(1 for i in items if i.roads)
    return f"{len(items)} roadworks items ({with_roads} with road numbers)"


def check_police() -> str:
    """UK Police API (data.police.uk) needs no credentials. Not a street-works
    feed - a worker-safety signal (see README for the historical/area-level
    caveats). POLICE_LAT/POLICE_LNG override the default probe point
    (Westminster, London)."""
    from streetworks.police import PoliceClient

    lat = float(os.environ.get("POLICE_LAT", "51.500617"))
    lng = float(os.environ.get("POLICE_LNG", "-0.124629"))
    with PoliceClient() as police:
        updated = police.last_updated()
        signal = police.safety_signal(lat, lng)
    return (
        f"data current to {updated}; {signal['total_crimes']} crimes near "
        f"({lat}, {lng}), {signal['safety_relevant_count']} safety-relevant"
    )


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
    reporter.check("National Highways", ["NH_SUBSCRIPTION_KEY"], check_nationalhighways)
    # Open Data parsing always runs - it needs no credentials
    reporter.check("Open Data (parsing)", [], check_opendata_parsing)
    # SRWR Open Data needs no credentials either (set SRWR_ARCHIVE to use a
    # local file instead of downloading)
    reporter.check("SRWR Open Data", [], check_srwr)
    # OS Open USRN needs no credentials (metadata check only by default)
    reporter.check("OS Open USRN", [], check_openusrn)
    # NDW DATEX II (Netherlands) needs no credentials
    reporter.check("DATEX II (NDW)", [], check_datex2_ndw)
    # Digitraffic (Finland) needs no credentials
    reporter.check("DATEX II (Digitraffic/Finland)", [], check_digitraffic)
    # WZDx (US Work Zone Data Exchange) needs no credentials
    reporter.check("WZDx", [], check_wzdx)
    # TrafficWatchNI (Northern Ireland) and Traffic Wales RSS need no credentials
    reporter.check("TrafficWatchNI", [], check_trafficwatchni)
    reporter.check("Traffic Wales", [], check_trafficwales)
    # UK Police (data.police.uk) needs no credentials
    reporter.check("UK Police (crime safety signal)", [], check_police)

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
