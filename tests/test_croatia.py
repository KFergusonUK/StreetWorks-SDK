"""Tests for the Croatia (Hrvatske ceste / NPT) DATEX II adapter.

**Confirmed live 2026-08-26** - see the module docstring in
``streetworks.datex2.croatia``. ``croatia_datex.xml`` is a synthetic
fixture (kept for its deliberate ConstructionWorks+MaintenanceWorks
coverage); ``croatia_datex_live_pull.xml`` holds 2 REAL situations
trimmed from a real authenticated pull (85 total, all real
MaintenanceWorks), proving the shared parser handles the genuine
response - a bare SituationPublication root - unchanged. Not synthetic.
"""

from pathlib import Path

import httpx
import pytest
import respx

from streetworks.datex2 import CroatiaClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "croatia_datex.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()

LIVE_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "croatia_datex_live_pull.xml"
LIVE_FIXTURE_BYTES = LIVE_FIXTURE_PATH.read_bytes()

BASE_URL = "https://b2b.promet-info.hr/dc/b2b.hc.roadworks.datex3"


def test_client_requires_a_credential():
    with pytest.raises(ValueError):
        CroatiaClient()


def test_client_rejects_both_basic_and_bearer_at_once():
    with pytest.raises(ValueError):
        CroatiaClient(username="u", password="p", bearer_token="t")


@respx.mock
def test_client_fetches_and_parses_with_basic_auth():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with CroatiaClient(username="u", password="p") as client:
        situations = list(client.iter_situations())

    assert [s.id for s in situations] == ["HR-HC-000789", "HR-HC-001042"]

    construction = situations[0].records[0]
    assert construction.record_type == "ConstructionWorks"
    assert construction.construction_work_type == "roadWideningWork"
    assert construction.location.point == (45.3271, 15.8756)
    assert "autocesti A1" in construction.comments[0]

    maintenance = situations[1].records[0]
    assert maintenance.record_type == "MaintenanceWorks"
    assert maintenance.road_maintenance_type == "vegetationManagementWork"

    request = respx.calls.last.request
    assert request.headers["Authorization"].startswith("Basic ")


@respx.mock
def test_client_fetches_with_bearer_token():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with CroatiaClient(bearer_token="test-token") as client:
        list(client.iter_situations())

    request = respx.calls.last.request
    assert request.headers["Authorization"] == "Bearer test-token"


@respx.mock
def test_client_iter_roadworks_recognises_genuine_datex_types():
    """Genuine DATEX vocabulary - ROADWORKS_TYPES matches directly, the
    same shape Vejdirektoratet already establishes."""
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with CroatiaClient(username="u", password="p") as client:
        roadworks = list(client.iter_roadworks())
    assert len(roadworks) == 2


@respx.mock
def test_client_parses_a_real_live_pull_unchanged():
    """The shared parser needed zero code changes against the real
    response - a bare SituationPublication root, real MaintenanceWorks
    records, real WGS84 coordinates."""
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=LIVE_FIXTURE_BYTES))
    with CroatiaClient(username="u", password="p") as client:
        situations = list(client.iter_situations())
    assert len(situations) == 2
    assert all(s.records[0].record_type == "MaintenanceWorks" for s in situations)
    lat, lon = situations[0].records[0].location.point
    # real Croatian latitude is ~45-46, longitude ~15-19.
    assert 44 < lat < 47
    assert 14 < lon < 20
