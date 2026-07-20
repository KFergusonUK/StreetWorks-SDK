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

    # Statens vegvesen (Norway, DATEX II) - PENDING LIVE VERIFICATION, see
    # streetworks.datex2.vegvesen. Provide either Basic or Bearer, not both.
    export VEGVESEN_USERNAME="..."
    export VEGVESEN_PASSWORD="..."
    # ... or:
    export VEGVESEN_TOKEN="..."

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
    if os.environ.get("VEGVESEN_TOKEN") or os.environ.get("VEGVESEN_USERNAME"):
        envs["Statens vegvesen (Norway)"] = "live"  # single environment, no sandbox
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
        detail = f"{method} auth, WFS caps {len(caps)} bytes, WMS caps {len(wms)} bytes"
        usrn = os.environ.get("DATAVIA_USRN")
        if usrn:
            result = dv.street_by_usrn(usrn)
            n = len(result.get("features", [])) if isinstance(result, dict) else 0
            detail += f"; USRN {usrn} -> {n} feature(s)"
        return detail


def check_dtro() -> str:
    from streetworks.dtro import DTROClient, Environment

    env = Environment.PRODUCTION if _is_prod("DTRO_ENV", "integration") else Environment.INTEGRATION
    with DTROClient(
        os.environ["DTRO_CLIENT_ID"],
        os.environ["DTRO_CLIENT_SECRET"],
        app_id=os.environ.get("DTRO_APP_ID"),
        environment=env,
    ) as dtro:
        # /events requires page, pageSize, since and to (all mandatory).
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        events = dtro.search_events(page=1, pageSize=1, since="2020-01-01T00:00:00", to=now)
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


def check_irca() -> str:
    """IRCA/Vegagerðin (Iceland, DATEX II) needs no credentials - confirmed
    live and reliably reachable (see streetworks.datex2.irca)."""
    from streetworks.datex2 import IcelandClient

    with IcelandClient() as irca:
        situations = list(irca.iter_roadworks())
    works = sum(len(s.roadworks) for s in situations)
    return f"{len(situations):,} roadworks situations ({works:,} works records)"


def check_bisonfute() -> str:
    """Bison Futé/the DIRs (France, DATEX II v2) needs no credentials -
    confirmed live and reliably reachable (see streetworks.datex2.bisonfute)."""
    from streetworks.datex2 import BisonFuteClient
    from streetworks.datex2.bisonfute import dir_regions

    with BisonFuteClient() as bf:
        situations = list(bf.iter_roadworks())
    works = sum(len(s.roadworks) for s in situations)
    distinct_regions = len(set(dir_regions(situations).values()))
    return (
        f"{len(situations):,} roadworks situations ({works:,} works records) "
        f"across {distinct_regions} DIR regions"
    )


def check_autobahn() -> str:
    """Autobahn GmbH (Germany, national motorways) needs no credentials -
    confirmed live. Fetches one representative road (AUTOBAHN_ROAD, default
    A1) rather than all ~113 - the full sweep is a one-off verification
    step, not something to repeat on every smoke-test run. Licence for
    this data is unconfirmed - see streetworks.autobahn's module docstring."""
    from streetworks.autobahn import AutobahnClient

    road = os.environ.get("AUTOBAHN_ROAD", "A1")
    with AutobahnClient() as autobahn:
        items = autobahn.roadworks(road)
    short_term = sum(1 for i in items if i.is_short_term)
    with_start = sum(1 for i in items if i.start is not None)
    return (
        f"{road}: {len(items)} roadworks ({short_term} short-term), "
        f"{with_start}/{len(items)} with a parsed start date"
    )


def check_german_regional() -> str:
    """German state (Bundesland) roadworks needs no credentials - confirmed
    live for Hamburg (Point, WFS), Brandenburg (LineString, WFS), and
    Saxony (LineString, direct GeoJSON download, UTM33N not WGS84).
    Mecklenburg-Vorpommern and Saxony-Anhalt were checked and parked
    (GML-only; Saxony-Anhalt's licence is also explicitly non-commercial)
    - see streetworks.ogc.germany's module docstring."""
    from streetworks.common import from_ogc_features
    from streetworks.ogc.germany import FIELD_MAPS, GermanRoadworksClient

    with GermanRoadworksClient() as germany:
        counts = {}
        for state, field_map in FIELD_MAPS.items():
            features = germany.fetch(state)
            works = from_ogc_features(features, field_map)
            with_coord = sum(1 for w in works if w.coordinate is not None)
            counts[state] = (len(works), with_coord)
    return ", ".join(f"{state}: {n} ({c} with coordinates)" for state, (n, c) in counts.items())


def check_dgt() -> str:
    """DGT (Spain, DATEX II v3) needs no credentials - confirmed live and
    reliably reachable (see streetworks.datex2.dgt). Coverage excludes
    Catalonia and the Basque Country."""
    from streetworks.datex2 import DGTClient
    from streetworks.datex2.dgt import provinces

    with DGTClient() as dgt:
        situations = list(dgt.iter_roadworks())
    works = sum(len(s.roadworks) for s in situations)
    distinct_provinces = len(set(provinces(situations).values()))
    return (
        f"{len(situations):,} roadworks situations ({works:,} works records) "
        f"across {distinct_provinces} provinces"
    )


def check_vegvesen() -> str:
    """Statens vegvesen (Norway, DATEX II) - PENDING LIVE VERIFICATION, see
    streetworks.datex2.vegvesen. Requires credentials (HTTP Basic via
    VEGVESEN_USERNAME/VEGVESEN_PASSWORD, or Bearer via VEGVESEN_TOKEN) and
    an IP allow-listed by Statens vegvesen - it's expected to fail/skip
    everywhere else, which is why this check is gated behind those env
    vars rather than run unconditionally like the credential-free DATEX
    adapters (NDW, Digitraffic)."""
    from streetworks.datex2 import VegvesenClient

    token = os.environ.get("VEGVESEN_TOKEN")
    if token:
        client = VegvesenClient(token=token)
        method = "Bearer"
    else:
        client = VegvesenClient(
            username=os.environ["VEGVESEN_USERNAME"],
            password=os.environ["VEGVESEN_PASSWORD"],
        )
        method = "Basic"

    with client as vegvesen:
        situations = list(vegvesen.iter_roadworks())
    works = sum(len(s.roadworks) for s in situations)
    return (
        f"{method} auth, {len(situations):,} roadworks situations "
        f"({works:,} works records) - first real Norwegian data seen, "
        "compare against module docstring's open questions"
    )


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


def check_ban() -> str:
    """France's BAN needs no credentials. Only exercises the geocoding API
    (search + reverse) - the bulk files are ~900 MB-1.4 GB, too big for a
    smoke test. Set BAN_TEST_DEPT (a département code, e.g. "48") to also
    verify a real bulk-file download+parse of that département."""
    from streetworks.ban import BANClient

    with BANClient() as ban:
        hits = ban.search("8 rue des halles paris")
        if not hits:
            raise RuntimeError("search returned no results for a known real address")
        first = hits[0]
        reverse_hits = ban.reverse(first.lon, first.lat)
        summary = (
            f"search -> {len(hits)} hit(s), top: {first.street!r} ({first.commune_nom}); "
            f"reverse -> {len(reverse_hits)} hit(s)"
        )

        dept = os.environ.get("BAN_TEST_DEPT")
        if dept:
            import tempfile

            from streetworks.ban import iter_addresses

            with tempfile.TemporaryDirectory() as tmp:
                path = ban.download_departement(dept, f"{tmp}/dept.csv.gz")
                addresses = list(iter_addresses(path))
                summary += f"; dept {dept} bulk file: {len(addresses):,} addresses"
    return summary


def check_bag() -> str:
    """Netherlands BAG needs no credentials. Exercises the Locatieserver
    (search + reverse) and the Atom feed's discovery of the current
    GeoPackage/extract URLs - not the bulk files themselves (~7.8 GB/
    ~3.6 GB, too big for a smoke test). Set BAG_GPKG to a local downloaded
    bag-light.gpkg to also verify a real table read."""
    from streetworks.bag import BAGClient

    with BAGClient() as bag:
        hits = bag.search("Dam 1 Amsterdam")
        if not hits:
            raise RuntimeError("search returned no results for a known real address")
        first = hits[0]
        reverse_hits = bag.reverse(first.lon, first.lat)
        downloads = bag.discover_downloads()
        summary = (
            f"search -> {len(hits)} hit(s), top: {first.weergavenaam!r}; "
            f"reverse -> {len(reverse_hits)} hit(s); "
            f"Atom feed -> {len(downloads)} download(s)"
        )

        local = os.environ.get("BAG_GPKG")
        if local:
            from streetworks.bag import BAGDatabase

            with BAGDatabase(local) as db:
                tables = db.tables()
                summary += f"; local gpkg: {len(tables)} table(s)"
    return summary


def check_kartverket() -> str:
    """Norway's Kartverket gazetteer needs no credentials (unlike the
    Vegvesen roadworks adapter, still blocked on credentials - see
    streetworks.kartverket's module docstring). Exercises the address API,
    SSR place-names API and the bulk Atom feed discovery - not the bulk
    files themselves. Set KARTVERKET_BULK_ZIP to a local downloaded
    MatrikkelenAdresse CSV zip to also verify a real bulk parse."""
    from streetworks.kartverket import KartverketClient

    with KartverketClient() as kv:
        hits = kv.search(sok="Karl Johans gate 1")
        if not hits:
            raise RuntimeError("search returned no results for a known real address")
        places = kv.search_places(sok="Karasjok")
        downloads = kv.discover_bulk_downloads()
        summary = (
            f"search -> {len(hits)} hit(s); "
            f"SSR -> {len(places)} place(s), "
            f"{len(places[0].names) if places else 0} name form(s); "
            f"bulk feed -> {len(downloads)} download(s)"
        )

        local = os.environ.get("KARTVERKET_BULK_ZIP")
        if local:
            from streetworks.kartverket import iter_addresses

            n = sum(1 for _ in iter_addresses(local))
            summary += f"; local bulk file: {n:,} addresses"
    return summary


def check_nwb() -> str:
    """Netherlands NWB (road network) needs no credentials. Exercises the
    WFS (a filtered query + a count) and the two-hop Atom feed discovery -
    not the ~1 GB bulk GeoPackage itself. Set NWB_GPKG to a local
    downloaded nwb_wegen.gpkg to also verify a real table read."""
    from streetworks.nwb import NWBClient

    with NWBClient() as nwb:
        segments = nwb.query(cql_filter="gme_naam='Harlingen'", count=5)
        if not segments:
            raise RuntimeError("query returned no results for a known real municipality")
        total = nwb.count(cql_filter="gme_naam='Harlingen'")
        entry = nwb.discover_download()
        summary = (
            f"query -> {len(segments)} hit(s), top: {segments[0].stt_naam!r}; "
            f"count(Harlingen) -> {total}; bulk download -> {entry.title!r}"
        )

        local = os.environ.get("NWB_GPKG")
        if local:
            from streetworks.nwb import NWBDatabase

            with NWBDatabase(local) as db:
                tables = db.tables()
                summary += f"; local gpkg: {len(tables)} table(s)"
    return summary


def check_bdtopo() -> str:
    """France BD TOPO (IGN) needs no credentials. Exercises the
    Géoplateforme WFS (a filtered query, a count, and a voie_nommee
    lookup) - there is no bulk download route built (see the package
    docstring for why)."""
    from streetworks.bdtopo import BDTopoClient

    with BDTopoClient() as bdtopo:
        troncons = bdtopo.query_troncons(cql_filter="insee_commune_gauche='01004'", count=5)
        if not troncons:
            raise RuntimeError("query returned no results for a known real commune")
        total = bdtopo.count_troncons(cql_filter="insee_commune_gauche='01004'")
        voies = bdtopo.query_voies_nommees(cql_filter="insee_commune='01004'", count=5)
        return (
            f"troncons -> {len(troncons)} hit(s), top: {troncons[0].nom_voie_ban_gauche!r}; "
            f"count(01004) -> {total}; voies_nommees -> {len(voies)} hit(s)"
        )


def check_nvdb() -> str:
    """Norway NVDB needs no credentials, just an X-Client header (see
    streetworks.nvdb's module docstring - confirmed live, not gated the
    way streetworks.datex2.vegvesen's DATEX feed is)."""
    from streetworks.nvdb import NVDBClient

    with NVDBClient(client_name="streetworks-sdk-smoke-test") as nvdb:
        sequences = nvdb.veglenkesekvenser(kommune=4201, count=3)
        if not sequences:
            raise RuntimeError("query returned no results for a known real municipality")
        addresses = nvdb.adresser(kommune=4201, count=3)
        return (
            f"veglenkesekvenser -> {len(sequences)} hit(s); "
            f"adresser -> {len(addresses)} hit(s), top: {addresses[0].adressenavn!r}"
        )


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
    if os.environ.get("VEGVESEN_TOKEN"):
        reporter.check("DATEX II (Vegvesen/Norway, Bearer)", ["VEGVESEN_TOKEN"], check_vegvesen)
    else:
        reporter.check(
            "DATEX II (Vegvesen/Norway, Basic)",
            ["VEGVESEN_USERNAME", "VEGVESEN_PASSWORD"],
            check_vegvesen,
        )
    # Open Data parsing always runs - it needs no credentials
    reporter.check("Open Data (parsing)", [], check_opendata_parsing)
    # SRWR Open Data needs no credentials either (set SRWR_ARCHIVE to use a
    # local file instead of downloading)
    reporter.check("SRWR Open Data", [], check_srwr)
    # OS Open USRN needs no credentials (metadata check only by default)
    reporter.check("OS Open USRN", [], check_openusrn)
    reporter.check("BAN (France)", [], check_ban)
    reporter.check("BAG (Netherlands)", [], check_bag)
    reporter.check("Kartverket (Norway)", [], check_kartverket)
    reporter.check("NWB (Netherlands)", [], check_nwb)
    reporter.check("BD TOPO (France)", [], check_bdtopo)
    reporter.check("NVDB (Norway)", [], check_nvdb)
    # NDW DATEX II (Netherlands) needs no credentials
    reporter.check("DATEX II (NDW)", [], check_datex2_ndw)
    # Digitraffic (Finland) needs no credentials
    reporter.check("DATEX II (Digitraffic/Finland)", [], check_digitraffic)
    # IRCA (Iceland) needs no credentials
    reporter.check("DATEX II (IRCA/Iceland)", [], check_irca)
    # Bison Fute (France) needs no credentials
    reporter.check("DATEX II (Bison Fute/France)", [], check_bisonfute)
    # DGT (Spain) needs no credentials
    reporter.check("DATEX II (DGT/Spain)", [], check_dgt)
    # Autobahn GmbH (Germany) needs no credentials
    reporter.check("Autobahn GmbH (Germany)", [], check_autobahn)
    # German state roadworks (Hamburg, Brandenburg) need no credentials
    reporter.check("German regional roadworks (OGC/WFS)", [], check_german_regional)
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
