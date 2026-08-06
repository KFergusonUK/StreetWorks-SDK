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

    # Statens vegvesen (Norway, DATEX II) - PHASE 2 CONFIRMED, see
    # streetworks.datex2.vegvesen. Provide either Basic or Bearer, not both.
    export VEGVESEN_USERNAME="..."
    export VEGVESEN_PASSWORD="..."
    # ... or:
    export VEGVESEN_TOKEN="..."

    # Trafikverket (Sweden) - PENDING LIVE VERIFICATION, see
    # streetworks.datex2.trafikverket. Free self-service registration.
    export TRAFIKVERKET_API_KEY="..."

    # Vejdirektoratet (Denmark) - PENDING LIVE VERIFICATION, see
    # streetworks.datex2.vejdirektoratet. Credentials + pull URL are both
    # issued per-dataset at registration - see module docstring.
    export VEJDIREKTORATET_URL="..."
    export VEJDIREKTORATET_USERNAME="..."
    export VEJDIREKTORATET_PASSWORD="..."

    # TfNSW Live Traffic (New South Wales, Australia) - PHASE 2 CONFIRMED,
    # see streetworks.au.nsw. Free self-service registration.
    export NSW_LIVETRAFFIC_API_KEY="..."

    # DTP Planned Disruptions (Victoria, Australia) - PHASE 2 CONFIRMED, see
    # streetworks.au.vic. Free subscription key.
    export VIC_DISRUPTIONS_API_KEY="..."

    # Main Roads WA WebEOC Roadworks (Western Australia) and QLDTraffic
    # Events (Queensland) both need NO credentials at all - see
    # streetworks.au.wa / streetworks.au.qld. QLD_QLDTRAFFIC_API_KEY below
    # is entirely optional - only set it if you've registered your own
    # private key rather than using the real, shared public one this
    # module already defaults to.
    export QLD_QLDTRAFFIC_API_KEY="..."

    # Traffic SA / DIT Roadworks (South Australia) - PENDING LIVE
    # VERIFICATION, genuinely blocked on two access gates (a token-gated
    # query endpoint, a geo-restricted host) - see streetworks.au.sa.
    export SA_TRAFFICSA_TOKEN="..."

    # ACT Temporary Traffic Management (Roads ACT) and Tasmania Roadworks
    # - State Roads (Dept of State Growth) both need NO credentials at
    # all - see streetworks.au.act / streetworks.au.tas. TAS ships with a
    # genuinely unconfirmed licence (not blocked - see module docstring).

    # NZTA Highway Information - Road Events and LINZ NZ Addresses both
    # need NO credentials at all - see streetworks.nzta / streetworks.linz.
    # LINZ NZ Addresses: Roads/Road Sections - PENDING LIVE VERIFICATION,
    # genuinely blocked on a real LINZ Data Service API key, free self-
    # service registration at data.linz.govt.nz.
    export LINZ_API_KEY="..."

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
    if os.environ.get("TRAFIKVERKET_API_KEY"):
        envs["Trafikverket (Sweden)"] = "live"  # single environment, no sandbox
    if os.environ.get("VEJDIREKTORATET_URL"):
        envs["Vejdirektoratet (Denmark)"] = "live"  # single environment, no sandbox
    if os.environ.get("NSW_LIVETRAFFIC_API_KEY"):
        envs["TfNSW Live Traffic (NSW, Australia)"] = "live"  # single environment, no sandbox
    if os.environ.get("VIC_DISRUPTIONS_API_KEY"):
        envs["DTP Planned Disruptions (VIC, Australia)"] = "live"  # single env, no sandbox
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


def check_vialietuva() -> str:
    """Via Lietuva (Lithuania) needs no credentials - confirmed live via
    the open data.gov.lt route (CC BY 4.0), not the agreement-gated RTTI
    NAP. Fetches the 'Remontas' (road repairs) table only - see
    streetworks.vialietuva's module docstring for why 'Kliutis'/'Renginys'
    aren't modelled. Coordinates are real LKS-94 (EPSG:3346), not WGS84."""
    from streetworks.common import from_vialietuva
    from streetworks.vialietuva import ViaLietuvaClient

    with ViaLietuvaClient() as lt:
        repairs = lt.road_repairs()
    works = from_vialietuva(repairs)
    with_coord = sum(1 for w in works if w.sites[0].coordinate is not None)
    with_line = sum(1 for w in works if w.sites[0].coordinate and w.sites[0].coordinate.parts)
    return (
        f"{len(works):,} road repairs, {with_coord}/{len(works)} with coordinates "
        f"({with_line} with a full line, the rest point-only)"
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


def check_euskadi() -> str:
    """Basque Country (DATEX II v1.0) needs no credentials - confirmed live
    (see streetworks.datex2.euskadi). Licence is explicitly absent, not
    unconfirmed - see the module docstring. Reports coordinate coverage,
    genuinely partial for this source unlike every other Spanish/DATEX
    adapter."""
    from streetworks.datex2.euskadi import EuskadiClient, provinces

    with EuskadiClient() as euskadi:
        situations = list(euskadi.iter_roadworks())
    works = [r for s in situations for r in s.roadworks]
    with_coord = sum(1 for r in works if r.location.points)
    distinct_provinces = len(set(provinces(situations).values()))
    return (
        f"{len(situations):,} roadworks situations ({len(works):,} works records), "
        f"{with_coord}/{len(works)} with coordinates, across {distinct_provinces} provinces"
    )


def check_mallorca() -> str:
    """Consell de Mallorca (IDEmallorca WFS) needs no credentials -
    confirmed live over plain HTTP (HTTPS doesn't connect at all - see
    streetworks.ogc.mallorca). Filters to Obres/Manteniment
    (excludes Altres) and reports the icon/tram join totality."""
    from streetworks.common import from_mallorca
    from streetworks.ogc.mallorca import MallorcaClient

    with MallorcaClient() as mallorca:
        icons = mallorca.fetch_roadworks_icons()
        trams = mallorca.fetch_trams()
    works = from_mallorca(icons, trams)
    with_line = sum(1 for w in works if w.sites[0].coordinate and w.sites[0].coordinate.parts)
    return f"{len(works):,} roadworks incidents ({with_line} with a joined tram line)"


def check_sct() -> str:
    """Servei Català de Trànsit (Catalonia) needs no credentials -
    confirmed live (see streetworks.sct). Filters to descripcio_tipus
    "Obres" and reports coordinate coverage."""
    from streetworks.common import from_sct
    from streetworks.sct import SCTClient

    with SCTClient() as sct:
        roadworks = list(sct.iter_roadworks())
    works = from_sct(roadworks)
    with_coord = sum(1 for w in works if w.sites[0].coordinate is not None)
    return f"{len(works):,} roadworks incidents ({with_coord}/{len(works)} with coordinates)"


def check_belgium() -> str:
    """Verkeerscentrum Vlaanderen (Belgium/Flanders, DATEX II v3) needs no
    credentials - confirmed live and reliably reachable (see
    streetworks.datex2.belgium). Coverage is Flanders only, not
    all-Belgium; coordinates are real EPSG:31370 (Lambert 72), not WGS84 -
    reports how many roadworks records came from each of the two real
    discriminator paths (dedicated xsi:type vs. the generic
    RoadOrCarriagewayOrLaneManagement/newRoadworksLayout signal)."""
    from streetworks.datex2 import BelgiumClient

    with BelgiumClient() as be:
        situations = list(be.iter_roadworks())
    works = [r for s in situations for r in s.roadworks]
    dedicated = sum(1 for r in works if r.record_type in {"MaintenanceWorks", "ConstructionWorks"})
    generic = len(works) - dedicated
    with_coord = sum(1 for r in works if r.location.points)
    return (
        f"{len(situations):,} roadworks situations ({len(works):,} works records: "
        f"{dedicated} dedicated xsi:type, {generic} generic/newRoadworksLayout), "
        f"{with_coord}/{len(works)} with Lambert 72 coordinates"
    )


def check_luxembourg() -> str:
    """Ponts et Chaussées/CITA (Luxembourg, DATEX II v2.3) needs no
    credentials - confirmed live and reliably reachable (see
    streetworks.datex2.luxembourg)."""
    from streetworks.datex2 import LuxembourgClient

    with LuxembourgClient() as lu:
        situations = list(lu.iter_roadworks())
    works = sum(len(s.roadworks) for s in situations)
    return f"{len(situations):,} roadworks situations ({works:,} works records)"


def check_bulgaria() -> str:
    """Road Infrastructure Agency/LIMA (Bulgaria, DATEX II v2.3) needs no
    credentials - confirmed live and reliably reachable via
    datasheet.api.bg, not the NAP-listed lima.api.bg (see
    streetworks.datex2.bulgaria). Fetches the 'Short-term Road
    Construction' (r03) dataset, confirmed a strict superset of the other
    two roadworks categories."""
    from streetworks.datex2 import BulgariaClient

    with BulgariaClient() as bg:
        situations = list(bg.iter_roadworks())
    works = sum(len(s.roadworks) for s in situations)
    return f"{len(situations):,} roadworks situations ({works:,} works records)"


#: Real diagnostic pass (2026-07-30, see streetworks.datex2.vegvesen module
#: docstring) found zero contradictions across 2,636 real coordinate
#: elements - srsName is a clean, trustworthy declaration for this feed,
#: never a mislabelling. A "corrected" result means resolve_coordinate_crs
#: had to override a declared srsName using value-range arbitration - real,
#: useful information if it ever fires, but never expected to; a run that
#: sees more than this many is worth investigating, not silently trusting.
_VEGVESEN_CORRECTED_THRESHOLD = 0


def check_vegvesen() -> str:
    """Statens vegvesen (Norway, DATEX II) - PHASE 2 CONFIRMED (2026-07-30),
    see streetworks.datex2.vegvesen. Requires credentials (HTTP Basic via
    VEGVESEN_USERNAME/VEGVESEN_PASSWORD - confirmed correct; or Bearer via
    VEGVESEN_TOKEN, untested). No IP allow-listing needed, confirmed live.

    **Real coordinates are genuinely mixed CRS within this feed** (~76%
    UTM zone 33N/EPSG:25833, ~24% WGS84) - resolved per-record via
    streetworks.common.from_vegvesen /
    streetworks.common._crs.resolve_coordinate_crs, not guessed at. This
    check classifies every roadworks record's real resolution status
    (declared/inferred/corrected/unresolved) and reports the actual split
    for this run - it's derived from live classification each time, never
    hardcoded - then fails loudly if any record needed "corrected"
    (declared srsName contradicted by its own values) beyond the expected
    near-zero threshold, since that would mean this feed's srsName
    declaration stopped being trustworthy."""
    from streetworks.common._crs import UTM33N_NORWAY, WGS84_NORWAY, resolve_coordinate_crs
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
    records = [record for situation in situations for record in situation.roadworks]

    counts = {"declared": 0, "inferred": 0, "corrected": 0, "unresolved": 0}
    for record in records:
        if not record.location.points:
            continue
        raw_a, raw_b = record.location.points[0]
        resolution = resolve_coordinate_crs(
            srs_name=record.location.srs_name,
            raw_a=raw_a,
            raw_b=raw_b,
            encoding_default="EPSG:4326",
            candidates=(WGS84_NORWAY, UTM33N_NORWAY),
        )
        counts[resolution.status] += 1

    if counts["corrected"] > _VEGVESEN_CORRECTED_THRESHOLD:
        raise RuntimeError(
            f"{counts['corrected']} record(s) needed CRS correction (declared "
            f"srsName contradicted by real coordinate values) - more than the "
            f"expected {_VEGVESEN_CORRECTED_THRESHOLD}, worth investigating "
            f"before trusting this run's geometry. Full split: {counts}"
        )

    return (
        f"{method} auth, {len(situations):,} roadworks situations "
        f"({len(records):,} works records) - CRS resolution: "
        f"{counts['declared']:,} declared, {counts['inferred']:,} inferred, "
        f"{counts['corrected']:,} corrected, {counts['unresolved']:,} unresolved"
    )


def check_trafikverket() -> str:
    """Trafikverket (Sweden) - PENDING LIVE VERIFICATION, see
    streetworks.datex2.trafikverket. Requires an API key
    (TRAFIKVERKET_API_KEY, free self-service registration). This is the
    first real authenticated pull this SDK will have made against
    Trafikverket - if you run this, please also compare
    Deviation.MessageType/MessageCode against the module docstring's open
    question about the real roadworks-discriminator value and report back
    (see the module docstring's linked issue)."""
    from streetworks.datex2 import TrafikverketClient

    with TrafikverketClient(api_key=os.environ["TRAFIKVERKET_API_KEY"]) as trafikverket:
        situations = list(trafikverket.iter_situations())
    roadworks = sum(1 for s in situations if s.roadworks)
    message_types = sorted({r.record_type for s in situations for r in s.records})
    return (
        f"{len(situations):,} situations ({roadworks:,} flagged roadworks by "
        f"the current, likely-incomplete filter) - real MessageType values "
        f"seen: {message_types[:10]!r} - first real Swedish data seen, "
        "compare against module docstring's open questions"
    )


def check_vejdirektoratet() -> str:
    """Vejdirektoratet (Denmark) - PENDING LIVE VERIFICATION, see
    streetworks.datex2.vejdirektoratet. Requires VEJDIREKTORATET_URL (the
    per-dataset pull address issued at registration - there is no public
    default) plus HTTP Basic VEJDIREKTORATET_USERNAME/
    VEJDIREKTORATET_PASSWORD."""
    from streetworks.datex2 import VejdirektoratetClient

    with VejdirektoratetClient(
        base_url=os.environ["VEJDIREKTORATET_URL"],
        username=os.environ["VEJDIREKTORATET_USERNAME"],
        password=os.environ["VEJDIREKTORATET_PASSWORD"],
    ) as vejdirektoratet:
        situations = list(vejdirektoratet.iter_roadworks())
    works = sum(len(s.roadworks) for s in situations)
    return (
        f"{len(situations):,} roadworks situations ({works:,} works "
        "records) - first real Danish data seen, compare against module "
        "docstring's open questions"
    )


def check_nsw_livetraffic() -> str:
    """TfNSW Live Traffic (New South Wales, Australia) - PHASE 2 CONFIRMED
    (2026-07-30), see streetworks.au.nsw. Requires an API Gateway key
    (NSW_LIVETRAFFIC_API_KEY, free self-service registration). Auth
    (`apikey <key>`) and endpoint paths (`roadwork/open`-style, a real
    bug fix from a Phase 1 guess) are both confirmed correct."""
    from streetworks.au import NswLiveTrafficClient

    with NswLiveTrafficClient(api_key=os.environ["NSW_LIVETRAFFIC_API_KEY"]) as nsw:
        roadworks = nsw.iter_roadworks()
        # majorevent has a smaller real sample behind it than roadwork - a
        # failure here is itself useful information, but shouldn't fail
        # the whole check when the better-confirmed roadwork layer just
        # succeeded.
        try:
            major_events_count = f"{len(nsw.iter_major_events()):,}"
        except StreetworksError as exc:
            major_events_count = f"FAILED ({type(exc).__name__})"
    return f"{len(roadworks):,} roadwork + {major_events_count} major-event features"


def check_vic_disruptions() -> str:
    """DTP Planned Disruptions (Victoria, Australia) - PHASE 2 CONFIRMED
    (2026-07-30), see streetworks.au.vic. Requires a Transport Victoria
    Open Data Hub subscription key (VIC_DISRUPTIONS_API_KEY, free) sent
    as a `KeyID` header (confirmed correct - not the OpenAPI spec's own
    advertised scheme)."""
    from streetworks.au import VicDisruptionsClient

    with VicDisruptionsClient(api_key=os.environ["VIC_DISRUPTIONS_API_KEY"]) as vic:
        features = vic.iter_planned_disruptions()
    return f"{len(features):,} planned-disruption features"


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


def check_jersey() -> str:
    """Jersey RoadWorkx needs no credentials - the ArcGIS REST API is
    reachable without authentication even though the human-facing site
    gates behind a login (see streetworks.arcgis.jersey's module
    docstring). Only fetches a small, filtered slice (one real WHERE
    clause), not the full 22,105-record layer - a full pull is exercised
    live in this session's own verification, not repeated here on every
    smoke-test run."""
    from streetworks.arcgis.jersey import JerseyRoadworksClient

    with JerseyRoadworksClient() as jersey:
        records = list(jersey.iter_roadworks(where="STATUS='In Progress'"))
    if not records:
        raise RuntimeError("query returned no in-progress roadworks - real data may have changed")
    sample = records[0]["properties"]
    return f"{len(records)} in-progress record(s), e.g. PROJID={sample.get('PROJID')!r}"


def check_tigerweb() -> str:
    """TIGERweb (US Census Bureau) needs no credentials. Queries a small
    real bounding box (downtown Washington DC) rather than the full
    national dataset (16.15M local-road features alone - see
    streetworks.arcgis.tigerweb's module docstring)."""
    from streetworks.arcgis.tigerweb import LOCAL_ROADS_LAYER, TIGERwebClient

    dc_bbox = (-77.05, 38.89, -77.03, 38.91)
    with TIGERwebClient() as tiger:
        roads = list(tiger.iter_roads(LOCAL_ROADS_LAYER, bbox=dc_bbox))
    if not roads:
        raise RuntimeError("bbox query returned no results for a known real area")
    named = [r for r in roads if r["properties"].get("NAME")]
    sample_name = named[0]["properties"]["NAME"]
    return f"{len(roads)} road(s) in bbox, {len(named)} named, e.g. {sample_name!r}"


def check_wa_mainroads() -> str:
    """Main Roads WA WebEOC Roadworks needs no credentials - see
    streetworks.au.wa. Fetches the whole layer (a real total of 227
    records, one live pull - small enough that a full pull is cheap here,
    unlike Jersey's 22,105). Reports the real local-road-sentinel split
    (Road=='LOCAL ROAD') and fails loudly if the runtime coordinate guard
    ever actually fires - it shouldn't, since outSR=4326 is confirmed
    honoured live, but a silent reprojection kicking in unexpectedly would
    mean that's stopped being true."""
    from streetworks.au.wa import WaMainRoadsClient

    with WaMainRoadsClient() as wa:
        features = list(wa.iter_roadworks())
    if not features:
        raise RuntimeError("query returned no roadworks - real data may have changed")

    # "LOCAL ROAD" is the real, confirmed sentinel value - see
    # streetworks.common.from_au_wa_mainroads._LOCAL_ROAD_SENTINEL.
    local_road = sum(1 for f in features if f.get("properties", {}).get("Road") == "LOCAL ROAD")
    guard_fired = 0
    for feature in features:
        coords = (feature.get("geometry") or {}).get("coordinates")
        if coords and (abs(coords[0]) > 180 or abs(coords[1]) > 90):
            guard_fired += 1
    if guard_fired:
        raise RuntimeError(
            f"{guard_fired} feature(s) needed the runtime coordinate guard to fire "
            "(outSR=4326 wasn't honoured for them) - real behaviour may have changed, "
            "see streetworks.au.wa's module docstring"
        )
    return f"{len(features):,} roadwork(s), {local_road:,} local-road ('LOCAL ROAD' sentinel)"


def check_qld_qldtraffic() -> str:
    """QLDTraffic Events (TMR, Queensland) needs no credentials - a real,
    globally-shared public API key is used by default (see
    streetworks.au.qld). Set QLD_QLDTRAFFIC_API_KEY to use a registered
    private key instead, if the shared key's 100 req/min global quota
    (contended by every anonymous consumer of the API, not just this
    session) is being exhausted by other traffic. Reports the real
    administrative_area diversity (source.provided_by) and the real
    geometry-shape split (Point vs LineString-only vs GeometryCollection)
    confirmed live 2026-08-01."""
    from streetworks.au.qld import PUBLIC_API_KEY, QldTrafficClient

    api_key = os.environ.get("QLD_QLDTRAFFIC_API_KEY", PUBLIC_API_KEY)
    with QldTrafficClient(api_key=api_key) as qld:
        roadworks = qld.iter_roadworks()
    if not roadworks:
        raise RuntimeError("query returned no roadworks - real data may have changed")

    administrative_areas = {
        f.get("properties", {}).get("source", {}).get("provided_by") for f in roadworks
    }
    geometry_kinds: dict[str, int] = {}
    for feature in roadworks:
        kind = (feature.get("geometry") or {}).get("type", "unknown")
        geometry_kinds[kind] = geometry_kinds.get(kind, 0) + 1

    return (
        f"{len(roadworks):,} roadworks, {len(administrative_areas):,} distinct real "
        f"administrative_area value(s), geometry shapes: {geometry_kinds}"
    )


def check_sa_trafficsa() -> str:
    """Traffic SA / DIT Roadworks (South Australia) - PENDING LIVE
    VERIFICATION, genuinely blocked on two access gates, see
    streetworks.au.sa. Requires an ArcGIS query token
    (SA_TRAFFICSA_TOKEN, from location.sa.gov.au/arcgis/tokens/ - whether
    that's self-service or gated is itself unresolved). If this succeeds,
    it's the first real feature this module will ever have seen - please
    also compare the real REC_TYPE value against the module docstring's
    open question, and whether ROAD_NO/GIS_LINK_ID are genuinely populated
    (see the module docstring's linked issue)."""
    from streetworks.au.sa import TrafficSaClient

    with TrafficSaClient(token=os.environ["SA_TRAFFICSA_TOKEN"]) as sa:
        features = list(sa.iter_roadworks())
    rec_types = sorted({f.get("properties", {}).get("REC_TYPE") for f in features})
    road_no_populated = sum(1 for f in features if f.get("properties", {}).get("ROAD_NO"))
    return (
        f"{len(features):,} layer-0 record(s) (unfiltered - REC_TYPE "
        f"values seen: {rec_types!r}), {road_no_populated:,} with a "
        "populated ROAD_NO - first real South Australian data seen, "
        "compare against module docstring's open questions"
    )


def check_act_ttm() -> str:
    """ACT Temporary Traffic Management (Roads ACT) needs no credentials -
    see streetworks.au.act. Confirmed live 2026-08-01 (98 real records,
    the whole real dataset). Reports the real type-value split - flags if
    a real value beyond the confirmed live enum ever shows up."""
    from streetworks.au.act import ActTtmClient

    with ActTtmClient() as act:
        closures = list(act.iter_closures())
    if not closures:
        raise RuntimeError("query returned no closures - real data may have changed")

    types: dict[str, int] = {}
    for feature in closures:
        kind = feature.get("properties", {}).get("type", "unknown")
        types[kind] = types.get(kind, 0) + 1
    roadworks = types.get("roadWorks", 0)
    return f"{len(closures):,} closure(s), type split: {types} ({roadworks:,} roadWorks)"


def check_tas_roadworks() -> str:
    """Tasmania Roadworks - State Roads (Department of State Growth) needs
    no credentials - see streetworks.au.tas. Licence is genuinely
    unconfirmed (not blocked - see module docstring). Confirmed live
    2026-08-01 (10 real records - genuinely this small). Fails loudly if
    any coordinate ever looks implausible - this module deliberately has
    no reprojection fallback (native CRS is GDA94/MGA zone 55, not Web
    Mercator, so WA/SA's closed-form guard would silently apply the wrong
    formula), so a real value out of range here means outSR=4326 stopped
    being honoured and needs real investigation, not a guess."""
    from streetworks.au.tas import TasRoadworksClient

    with TasRoadworksClient() as tas:
        features = list(tas.iter_roadworks())
    if not features:
        raise RuntimeError("query returned no roadworks - real data may have changed")

    implausible = []
    for feature in features:
        for lon, lat in (feature.get("geometry") or {}).get("coordinates", []):
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                implausible.append((feature["properties"].get("ID"), lon, lat))
    if implausible:
        raise RuntimeError(
            f"{len(implausible)} coordinate(s) outside plausible WGS84 range "
            f"(e.g. {implausible[0]}) - outSR=4326 may have stopped being "
            "honoured; see streetworks.au.tas's module docstring before "
            "adding a reprojection fallback"
        )
    return f"{len(features):,} roadworks (real line geometry, all coordinates plausible WGS84)"


def check_nzta() -> str:
    """NZTA (Waka Kotahi) Highway Information - Road Events needs no
    credentials - see streetworks.nzta. Confirmed live 2026-08-02 (104
    real records). Reports the real status/eventType split - flags if a
    real value beyond the confirmed live enum ever shows up."""
    from streetworks.nzta import NztaClient

    with NztaClient() as nzta:
        events = list(nzta.iter_roadworks())
    if not events:
        raise RuntimeError("query returned no roadworks - real data may have changed")

    statuses: dict[str, int] = {}
    for feature in events:
        status = feature.get("properties", {}).get("status", "unknown")
        statuses[status] = statuses.get(status, 0) + 1
    return f"{len(events):,} roadworks event(s), status split: {statuses}"


def check_linz_addresses() -> str:
    """LINZ NZ Addresses needs no credentials - a public ArcGIS mirror,
    see streetworks.linz.client. Confirmed live 2026-08-02 (2,421,642 real
    addresses total). Only fetches a small, filtered slice, not the full
    layer."""
    from streetworks.linz import LinzClient

    with LinzClient() as linz:
        addresses = list(linz.iter_addresses(where="territorial_authority='Auckland'"))
    if not addresses:
        raise RuntimeError("query returned no addresses for a known real territorial authority")
    sample = addresses[0]["properties"]
    return f"{len(addresses):,} Auckland address(es), e.g. {sample.get('full_road_name')!r}"


def check_gnaf_addresses() -> str:
    """G-NAF National Address Points needs no credentials - a real ArcGIS
    Feature Service over the Digital Atlas of Australia, see
    streetworks.gnaf.client. Confirmed live 2026-08-02 (15,901,249 real
    addresses total). Only fetches a small, filtered slice, not the full
    layer."""
    from streetworks.gnaf import GnafClient

    with GnafClient() as gnaf:
        addresses = list(gnaf.iter_addresses(where="STATE='ACT'"))
    if not addresses:
        raise RuntimeError("query returned no addresses for a known real state")
    sample = addresses[0]["properties"]
    return f"{len(addresses):,} ACT address(es), e.g. {sample.get('COMPLETE_ADDRESS')!r}"


def check_gnaf_roads() -> str:
    """National Roads (Australia) needs no credentials - the same Digital
    Atlas of Australia platform as G-NAF addresses, see
    streetworks.gnaf.client. Confirmed live 2026-08-02 (4,346,217 real
    segments total). Reports the real hierarchy split for the fetched
    slice - flags if a real value beyond the confirmed live enum ever
    shows up."""
    from streetworks.gnaf import GnafClient

    with GnafClient() as gnaf:
        roads = list(gnaf.iter_roads(where="state='ACT'"))
    if not roads:
        raise RuntimeError("query returned no roads for a known real state")

    hierarchy: dict[str, int] = {}
    for feature in roads:
        value = feature.get("properties", {}).get("hierarchy", "unknown")
        hierarchy[value] = hierarchy.get(value, 0) + 1
    return f"{len(roads):,} ACT road segment(s), hierarchy split: {hierarchy}"


def check_linz_roads() -> str:
    """LINZ NZ Addresses: Roads/Road Sections - PENDING LIVE VERIFICATION,
    see streetworks.linz.client. Requires a real LINZ Data Service API key
    (LINZ_API_KEY, free self-service registration at data.linz.govt.nz).
    This is the first real WFS pull this SDK will have made against LDS -
    if you run this, please also compare a real road_id value against a
    real LINZ Addresses road_id to help settle the module docstring's own
    open cross-reference question, and report back (see the module
    docstring's linked issue)."""
    from streetworks.linz import LinzClient

    with LinzClient(api_key=os.environ["LINZ_API_KEY"]) as linz:
        roads = list(linz.iter_roads())
        sections = list(linz.iter_road_sections())
    if not roads or not sections:
        raise RuntimeError("query returned no roads/road sections - real data may have changed")
    return (
        f"{len(roads):,} road(s), {len(sections):,} road section(s) - "
        "first real LDS pull seen, compare against module docstring's open questions"
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


def check_wzdx_registry() -> str:
    """The USDOT WZDx feed registry itself needs no credentials - see
    streetworks.wzdx.registry. Confirmed live 2026-08-02 (41 real rows).
    Exercises the full registry-to-feed pipeline against 511NY (NYSDOT),
    the first concrete verified US feed - list_feeds() -> find the NY row
    -> fetch its real URL, no key needed. Also reports the real CWZ/
    needs-key split among the credential-free candidates, so a change in
    those real proportions is visible here rather than silently."""
    from streetworks.wzdx import WZDxClient
    from streetworks.wzdx.registry import list_feeds

    feeds = list_feeds()
    if not feeds:
        raise RuntimeError("registry returned no active, supported WZDx feeds")
    needs_key = sum(1 for f in feeds if f.needapikey)

    nysdot = next((f for f in feeds if f.feed_name == "nysdot"), None)
    if nysdot is None:
        raise RuntimeError("511NY (nysdot) is no longer in the registry - real coverage changed")
    if nysdot.needapikey:
        raise RuntimeError("511NY now states needapikey=true - it was confirmed key-free")

    with WZDxClient() as wzdx:
        feed = wzdx.fetch(nysdot.url)
    return (
        f"registry: {len(feeds)} active WZDx feed(s) ({needs_key} need a key) - "
        f"511NY: {feed.publisher} (v{feed.version}), {len(feed.road_events)} road events"
    )


def check_nycdot() -> str:
    """NYC DOT Street Construction Permits needs no credentials - see
    streetworks.nycdot. Confirmed live 2026-08-02 (3,798,494 real rows
    total, the roadworks-filtered slice alone still 1.8M+) - only takes
    the first real page via iter_roadworks()'s own $where filter, never
    the whole register."""
    import itertools

    from streetworks.nycdot import NycDotClient

    with NycDotClient() as nycdot:
        permits = list(itertools.islice(nycdot.iter_roadworks(), 50))
    if not permits:
        raise RuntimeError("query returned no permits - real data may have changed")
    with_geometry = sum(1 for p in permits if p.get("wkt"))
    return f"{len(permits)} roadworks permit(s) sampled, {with_geometry} with real wkt geometry"


def check_chicagodot() -> str:
    """Chicago CDOT Street Closures needs no credentials - see
    streetworks.chicagodot. Confirmed live 2026-08-03 (466,829 real rows
    in the Street Closures view) - only takes the first real page via
    iter_roadworks()'s own $where filter, never the whole view."""
    import itertools

    from streetworks.chicagodot import ChicagoDotClient

    with ChicagoDotClient() as chicago:
        permits = list(itertools.islice(chicago.iter_roadworks(), 50))
    if not permits:
        raise RuntimeError("query returned no permits - real data may have changed")
    with_geometry = sum(1 for p in permits if p.get("location"))
    return f"{len(permits)} roadworks permit(s) sampled, {with_geometry} with real Point geometry"


def check_paris() -> str:
    """Paris Chantiers needs no credentials - see streetworks.paris.
    Confirmed live 2026-08-06 (4,707 real records total) - only takes
    the first real page via iter_roadworks()'s own where filter, never
    the whole register."""
    import itertools

    from streetworks.paris import ParisClient

    with ParisClient() as paris:
        records = list(itertools.islice(paris.iter_roadworks(), 50))
    if not records:
        raise RuntimeError("query returned no records - real data may have changed")
    with_geometry = sum(1 for r in records if r.get("geo_point_2d"))
    return f"{len(records)} roadworks record(s) sampled, {with_geometry} with real geometry"


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


def check_cciss() -> str:
    """CCISS RSS (Italy) needs no credentials - see streetworks.cciss.
    Confirmed live 2026-08-03 (100 real items, 78 real roadworks after
    classification). Unlike TrafficWatchNI/Traffic Wales, this one feed
    mixes roadworks with weather/breakdowns/accidents/demonstrations -
    reports the real is_roadworks split rather than assuming it."""
    from streetworks.cciss import CcissClient

    with CcissClient() as cciss:
        items = cciss.fetch()
    if not items:
        raise RuntimeError("feed returned no items - real data may have changed")
    roadworks = sum(1 for i in items if i.is_roadworks)
    return f"{len(items)} real item(s), {roadworks} classified as roadworks"


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
    reporter.check(
        "DATEX II (Trafikverket/Sweden)", ["TRAFIKVERKET_API_KEY"], check_trafikverket
    )
    reporter.check(
        "DATEX II (Vejdirektoratet/Denmark)",
        ["VEJDIREKTORATET_URL", "VEJDIREKTORATET_USERNAME", "VEJDIREKTORATET_PASSWORD"],
        check_vejdirektoratet,
    )
    reporter.check(
        "TfNSW Live Traffic (NSW/Australia)", ["NSW_LIVETRAFFIC_API_KEY"], check_nsw_livetraffic
    )
    reporter.check(
        "DTP Planned Disruptions (VIC/Australia)",
        ["VIC_DISRUPTIONS_API_KEY"],
        check_vic_disruptions,
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
    # Jersey RoadWorkx and TIGERweb (US) need no credentials
    reporter.check("Jersey RoadWorkx", [], check_jersey)
    reporter.check("TIGERweb (USA)", [], check_tigerweb)
    # Main Roads WA WebEOC Roadworks needs no credentials
    reporter.check("Main Roads WA (Australia)", [], check_wa_mainroads)
    # QLDTraffic Events needs no credentials (a real, shared public API key)
    reporter.check("QLDTraffic Events (Queensland, Australia)", [], check_qld_qldtraffic)
    reporter.check(
        "Traffic SA / DIT Roadworks (SA/Australia)", ["SA_TRAFFICSA_TOKEN"], check_sa_trafficsa
    )
    # ACT TTM and TAS Roadworks both need no credentials
    reporter.check("ACT Temporary Traffic Management (Australia)", [], check_act_ttm)
    reporter.check("TAS Roadworks - State Roads (Australia)", [], check_tas_roadworks)
    # NZTA Highway Information and LINZ NZ Addresses both need no credentials
    reporter.check("NZTA Highway Information (New Zealand)", [], check_nzta)
    reporter.check("LINZ NZ Addresses (New Zealand)", [], check_linz_addresses)
    reporter.check(
        "LINZ NZ Addresses: Roads/Road Sections (New Zealand)", ["LINZ_API_KEY"], check_linz_roads
    )
    # G-NAF National Address Points and National Roads both need no credentials
    reporter.check("G-NAF National Address Points (Australia)", [], check_gnaf_addresses)
    reporter.check("National Roads (Australia)", [], check_gnaf_roads)
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
    # Basque Country (Euskadi) needs no credentials
    reporter.check("DATEX II (Euskadi/Basque Country)", [], check_euskadi)
    # Consell de Mallorca (IDEmallorca) needs no credentials
    reporter.check("Consell de Mallorca (IDEmallorca)", [], check_mallorca)
    # Servei Català de Trànsit (Catalonia) needs no credentials
    reporter.check("Servei Català de Trànsit (Catalonia)", [], check_sct)
    # Verkeerscentrum Vlaanderen (Belgium/Flanders) needs no credentials
    reporter.check("DATEX II (Belgium/Flanders)", [], check_belgium)
    # Ponts et Chaussées/CITA (Luxembourg) needs no credentials
    reporter.check("DATEX II (Luxembourg)", [], check_luxembourg)
    # Road Infrastructure Agency/LIMA (Bulgaria) needs no credentials
    reporter.check("DATEX II (Bulgaria)", [], check_bulgaria)
    # Autobahn GmbH (Germany) needs no credentials
    reporter.check("Autobahn GmbH (Germany)", [], check_autobahn)
    # Via Lietuva (Lithuania) needs no credentials
    reporter.check("Via Lietuva (Lithuania)", [], check_vialietuva)
    # German state roadworks (Hamburg, Brandenburg) need no credentials
    reporter.check("German regional roadworks (OGC/WFS)", [], check_german_regional)
    # WZDx (US Work Zone Data Exchange) needs no credentials
    reporter.check("WZDx", [], check_wzdx)
    reporter.check("WZDx feed registry (511NY end-to-end)", [], check_wzdx_registry)
    reporter.check("NYC DOT Street Construction Permits", [], check_nycdot)
    reporter.check("Chicago CDOT Street Closures", [], check_chicagodot)
    reporter.check("Paris Chantiers", [], check_paris)
    # TrafficWatchNI (Northern Ireland) and Traffic Wales RSS need no credentials
    reporter.check("TrafficWatchNI", [], check_trafficwatchni)
    reporter.check("Traffic Wales", [], check_trafficwales)
    reporter.check("CCISS (Italy)", [], check_cciss)
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
