"""Tests for the Croatia (Hrvatske ceste / NPT) DATEX II adapter.

**Pending live verification** - see the module docstring in
``streetworks.datex2.croatia``. The fixture (``croatia_datex.xml``) is
synthetic, not real data: only the NAP's own public dataset-metadata page
(confirming the real pull URL, its DATEX-II-v3 standard, WGS84
georeferencing, and Otvorena dozvola open licence) and a live 401 on that
URL have been verified - the credential-gated data pull itself has never
been exercised.
"""

from pathlib import Path

import httpx
import pytest
import respx

from streetworks.datex2 import CroatiaClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "croatia_datex.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()

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
