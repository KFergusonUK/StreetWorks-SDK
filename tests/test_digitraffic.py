"""Tests for the Finland (Digitraffic) DATEX adapter.

The fixture (tests/fixtures/digitraffic_roadworks.json) is four real
features (lightly trimmed) from a live call to
GET /api/traffic-message/v2/roadworks (2026-07-11), covering: a Point
geometry situation, a 3-phase MultiLineString situation with genuinely
different per-phase road numbers/Alert-C names sharing one geometry, a
situation with a non-empty phase comment, and a situation in a different
province with multiple workTypes (exercising the "skip other" selection).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import respx

from streetworks.datex2 import DigitrafficClient
from streetworks.datex2.digitraffic import parse_situations, provinces

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "digitraffic_roadworks.json").read_text(
        encoding="utf-8"
    )
)


def _situation(situations, situation_id):
    return next(s for s in situations if s.id == situation_id)


def test_point_geometry_situation():
    situations = parse_situations(FIXTURE)
    s = _situation(situations, "GUID50467185")
    assert len(s.roadworks) == 1 and len(s.measures) == 0

    record = s.roadworks[0]
    assert record.id == "GUID50469963"
    assert record.record_type == "MaintenanceWorks"  # endpoint-derived, not a field
    assert record.source_name == "Fintraffic Tieliikennekeskus Tampere"
    assert record.road_maintenance_type == "measurement equipment"
    assert record.validity.status is None  # no lifecycle field in Digitraffic
    assert record.validity.overall_start == datetime(2026, 7, 10, 21, 0, tzinfo=timezone.utc)
    assert record.location.kind == "Point"
    assert len(record.location.points) == 1
    assert record.location.road_number == "9"
    assert record.location.alert_c_location == "Kaukajärven liittymä"

    # .raw preserves everything the typed fields leave out (severity,
    # workingHours[], restrictions[], the full workTypes[] list...) -
    # SituationRecord.raw is the specific phase, Situation.raw the whole
    # feature, matching WZDx's RoadEvent.raw / SRWR's Record.raw pattern.
    assert record.raw["id"] == "GUID50469963"
    assert record.raw["severity"] == "high"
    assert s.raw["properties"]["situationId"] == "GUID50467185"
    assert s.raw["geometry"]["type"] == "Point"


def test_multi_phase_situation_shares_geometry_but_not_location_text():
    situations = parse_situations(FIXTURE)
    s = _situation(situations, "GUID50465119")
    assert len(s.roadworks) == 3

    roads = [r.location.road_number for r in s.roadworks]
    assert roads == ["577", "582", "576"]  # genuinely different per phase
    alert_c = [r.location.alert_c_location for r in s.roadworks]
    assert alert_c == ["Ruukuntie", "Vartiala", "Varpaisjärvi"]

    # Geometry is the situation's, reused identically across every phase -
    # not phase-precise.
    geometries = {r.location.points for r in s.roadworks}
    assert len(geometries) == 1
    assert all(r.location.kind == "MultiLineString" for r in s.roadworks)


def test_comment_and_work_type_selection():
    situations = parse_situations(FIXTURE)
    s = _situation(situations, "GUID50467132")
    record = s.roadworks[0]
    assert record.comments == ("Jaksoittain etenevä työ",)


def test_road_maintenance_type_skips_other_when_a_real_type_exists():
    situations = parse_situations(FIXTURE)
    s = _situation(situations, "GUID50467130")
    record = s.roadworks[0]
    # workTypes here are [resurfacing, stabilization, other] - the first
    # non-"other" entry wins, not a joined composite string.
    assert record.road_maintenance_type == "resurfacing"


def test_provinces_maps_situation_id_to_region():
    provs = provinces(FIXTURE)
    assert provs["GUID50467185"] == "Pirkanmaa"
    assert provs["GUID50465119"] == "Pohjois-Savo"
    assert provs["GUID50467130"] == "Uusimaa"


@respx.mock
def test_client_fetches_and_parses():
    respx.get("https://tie.digitraffic.fi/api/traffic-message/v2/roadworks").mock(
        return_value=httpx.Response(200, json=FIXTURE)
    )
    with DigitrafficClient() as client:
        situations = list(client.iter_roadworks())
    assert len(situations) == 4
    assert {s.id for s in situations} == {
        "GUID50467185",
        "GUID50465119",
        "GUID50467132",
        "GUID50467130",
    }
