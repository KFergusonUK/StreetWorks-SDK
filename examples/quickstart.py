"""streetworks quickstart - one small call to every provider.

Copy `.env.example` to `.env`, fill in the credentials you have, then:

    python examples/quickstart.py

Providers without credentials are skipped; SRWR, OS Open USRN, WZDx,
TrafficWatchNI, Traffic Wales and UK Police need none.
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
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]  # strip surrounding quotes, dotenv-style
        os.environ.setdefault(key.strip(), value)


load_dotenv()


def section(title: str) -> None:
    print(f"\n=== {title} " + "=" * max(0, 56 - len(title)))


def attempt(label: str, fn) -> None:
    """Run a provider demo, degrading to a friendly line on any failure so one
    unreachable feed never sinks the whole tour."""
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - a demo should never hard-fail
        print(f"  ({label} unavailable: {type(exc).__name__} - {exc})")


# --- Street Manager: log in, list recent permits ------------------------------

section("Street Manager")
if os.environ.get("SM_EMAIL"):

    def _street_manager_demo() -> None:
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
            print(f"  logged in ({env.name.lower()}), organisation {org}")
            page = sm.reporting.permits()
            for permit in page.get("rows", [])[:3]:
                print(
                    "  ",
                    permit.get("permit_reference_number") or permit.get("work_reference_number"),
                    "-",
                    permit.get("street_name", "?"),
                )
            # For everything across all pages: sm.reporting.iter_permits(...)

    attempt("Street Manager", _street_manager_demo)
else:
    print("skipped - set SM_EMAIL / SM_PASSWORD in .env")

# --- DataVIA: look up one street by USRN --------------------------------------

section("Geoplace DataVIA")
if os.environ.get("DATAVIA_USER") or os.environ.get("DATAVIA_CLIENT_ID"):

    def _datavia_demo() -> None:
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
            print(f"  USRN {usrn}: {len(features)} feature(s)")
            if features:
                props = features[0].get("properties", {})
                print("  ", props.get("street_descriptor") or props)

    attempt("DataVIA", _datavia_demo)
else:
    print("skipped - set DATAVIA_USER / DATAVIA_PASSWORD in .env")

# --- D-TRO: search recent traffic-order events ---------------------------------

section("D-TRO")
if os.environ.get("DTRO_CLIENT_ID"):

    def _dtro_demo() -> None:
        from datetime import datetime, timezone

        from streetworks.dtro import DTROClient
        from streetworks.dtro import Environment as DtroEnv

        env = (
            DtroEnv.PRODUCTION
            if os.environ.get("DTRO_ENV", "").lower() == "production"
            else DtroEnv.INTEGRATION
        )
        if env is DtroEnv.PRODUCTION and not os.environ.get("STREETWORKS_ALLOW_PRODUCTION"):
            print("  skipped - DTRO_ENV=production also needs STREETWORKS_ALLOW_PRODUCTION=1")
            return
        with DTROClient(
            os.environ["DTRO_CLIENT_ID"],
            os.environ["DTRO_CLIENT_SECRET"],
            app_id=os.environ.get("DTRO_APP_ID"),
            environment=env,
        ) as dtro:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            events = dtro.search_events(page=1, pageSize=3, since="2024-01-01T00:00:00", to=now)
            info = dtro.token_info or {}
            print(f"  authenticated ({env.name.lower()}, scope={info.get('scope')})")
            for event in (events.get("events") or [])[:3]:
                print("  ", event.get("eventType"), "-", event.get("troName", ""))

    attempt("D-TRO", _dtro_demo)
else:
    print("skipped - set DTRO_CLIENT_ID / DTRO_CLIENT_SECRET in .env")

# --- National Highways: planned closures on the strategic road network ---------

section("National Highways (DATEX II)")
if os.environ.get("NH_SUBSCRIPTION_KEY"):

    def _nationalhighways_demo() -> None:
        from streetworks.datex2 import ClosureType, NationalHighwaysClient

        with NationalHighwaysClient(os.environ["NH_SUBSCRIPTION_KEY"]) as nh:
            payload, next_url = nh.get_closures(ClosureType.PLANNED)
            situations = payload.get("D2Payload", payload).get("situation", [])
            print(f"  {len(situations)} situations on page 1 (more pages: {bool(next_url)})")
            shown = 0
            for situation in nh.iter_roadworks(ClosureType.PLANNED, max_pages=1):
                works = situation.roadworks[0]
                print("  ", works.cause_type, "-", works.location.road_number or "?")
                shown += 1
                if shown == 3:
                    break

    attempt("National Highways", _nationalhighways_demo)
else:
    print("skipped - set NH_SUBSCRIPTION_KEY in .env")

# --- WZDx: US work zones, any agency's feed (no credentials) --------------------

section("WZDx (US Work Zone Data Exchange)")


def _wzdx_demo() -> None:
    from streetworks.wzdx import WZDxClient, list_feeds

    feeds = list_feeds()
    print(f"  {len(feeds)} active feeds in the USDOT registry")

    # Washington State DOT by default; set WZDX_FEED_URL to point at any
    # other agency's feed instead (see the feeds listed above).
    feed_url = os.environ.get("WZDX_FEED_URL", "https://wzdx.wsdot.wa.gov/api/v4/WorkZoneFeed")
    with WZDxClient() as wzdx:
        feed = wzdx.fetch(feed_url)
    print(f"  {feed.publisher} (WZDx v{feed.version}): {len(feed.road_events)} road events")
    shown = 0
    for event in feed.road_events:
        if not event.is_work_zone:
            continue
        print("  ", ", ".join(event.road_names) or "?", "-", event.vehicle_impact)
        shown += 1
        if shown == 3:
            break


attempt("WZDx", _wzdx_demo)

# --- SRWR Open Data: today's Scottish road works (no credentials) ---------------

section("SRWR Open Data (Scotland)")


def _srwr_demo() -> None:
    from streetworks.srwr import SRWRClient, describe

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


attempt("SRWR", _srwr_demo)

# --- OS Open USRN: national street lookup (no credentials) ----------------------

section("OS Open USRN")


def _openusrn_demo() -> None:
    from streetworks.openusrn import OpenUSRNClient, UsrnDatabase

    with OpenUSRNClient() as client:
        entry = client.downloads()[0]
        print(f"  product available: {entry['fileName']} ({entry['size']:,} bytes)")

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


attempt("OS Open USRN", _openusrn_demo)

# --- Northern Ireland: TrafficWatchNI roadworks RSS (no credentials) -------------

section("TrafficWatchNI (Northern Ireland)")


def _ni_demo() -> None:
    from streetworks.trafficwatchni import ATTRIBUTION as NI_ATTRIBUTION
    from streetworks.trafficwatchni import Feed as NIFeed
    from streetworks.trafficwatchni import TrafficWatchNIClient

    with TrafficWatchNIClient() as twni:
        ni_items = twni.fetch(NIFeed.ROADWORKS)
    for item in ni_items[:3]:
        print(f"  {item.closure_type or 'Roadworks'}: {item.road or '?'}, "
              f"{item.town or '?'} - {item.promoter or 'promoter n/a'}")
    print(f"  ({len(ni_items)} items; {NI_ATTRIBUTION})")


attempt("TrafficWatchNI", _ni_demo)

# --- Wales: Traffic Wales roadworks RSS (no credentials) -------------------------

section("Traffic Wales")


def _wales_demo() -> None:
    from streetworks.trafficwales import ATTRIBUTION as TW_ATTRIBUTION
    from streetworks.trafficwales import Feed as TWFeed
    from streetworks.trafficwales import TrafficWalesClient

    with TrafficWalesClient() as tw:
        tw_items = tw.fetch(TWFeed.ROADWORKS)
    for item in tw_items[:3]:
        roads = "/".join(item.roads) or "?"
        print(f"  {roads}: {item.title[:60]}")
    print(f"  ({len(tw_items)} items; {TW_ATTRIBUTION})")


attempt("Traffic Wales", _wales_demo)

# --- UK Police: crime near a worksite, as a safety signal (no credentials) -------

section("UK Police (worker-safety signal)")


def _police_demo() -> None:
    from streetworks.police import PoliceClient

    lat = float(os.environ.get("POLICE_LAT", "51.500617"))
    lng = float(os.environ.get("POLICE_LNG", "-0.124629"))
    with PoliceClient() as police:
        updated = police.last_updated()
        signal = police.safety_signal(lat, lng)
    print(f"  data current to {updated}")
    print(
        f"  ({lat}, {lng}): {signal['total_crimes']} crimes, "
        f"{signal['safety_relevant_count']} safety-relevant"
    )
    for category, count in signal["by_category"].items():
        print("  ", category, "-", count)


attempt("UK Police", _police_demo)

print("\ndone.")
