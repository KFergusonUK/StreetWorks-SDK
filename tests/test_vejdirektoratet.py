"""Tests for the Denmark (Vejdirektoratet) DATEX II adapter.

**Pending live verification** - see the module docstring in
``streetworks.datex2.vejdirektoratet``. The fixture
(``vejdirektoratet_trafikmeldinger.json``) is synthetic, not real data: only
the open metadata catalogue (confirming the dataset, its DATEX-II-3.2
standard, and its CC BY 4.0 licence) has been verified live - the
credential-gated data pull itself has never been exercised. It exists to
exercise the parser-reuse hypothesis (genuine DATEX II XML, parsed via the
existing shared streaming parser) against the documented
"trafikmeldinger: [xml string, ...]" REST response shape.
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.datex2 import VejdirektoratetClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vejdirektoratet_trafikmeldinger.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())

BASE_URL = "https://example-du.vd.dk/dataset/222"


def test_client_requires_base_url_and_credentials():
    import pytest

    with pytest.raises(ValueError):
        VejdirektoratetClient(base_url="", username="u", password="p")
    with pytest.raises(ValueError):
        VejdirektoratetClient(base_url=BASE_URL, username="", password="")


@respx.mock
def test_client_fetches_and_parses_construction_and_maintenance_works():
    respx.get(f"{BASE_URL}/trafikmeldinger").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with VejdirektoratetClient(base_url=BASE_URL, username="u", password="p") as client:
        situations = list(client.iter_situations())

    assert [s.id for s in situations] == ["DK-VD-000123", "DK-VD-000456"]

    construction = situations[0].records[0]
    assert construction.record_type == "ConstructionWorks"
    assert construction.construction_work_type == "roadWideningWork"
    assert construction.location.point == (56.1629, 10.2039)
    assert construction.comments == ("Vejarbejde på motorvej E45 - højre vognbane spærret",)

    maintenance = situations[1].records[0]
    assert maintenance.record_type == "MaintenanceWorks"
    assert maintenance.road_maintenance_type == "resurfacingWork"

    request = respx.calls.last.request
    assert request.headers["Authorization"].startswith("Basic ")


@respx.mock
def test_client_iter_roadworks_recognises_genuine_datex_types():
    """Unlike Sweden, this is genuine DATEX vocabulary - ROADWORKS_TYPES
    matches directly, no discriminator gap."""
    respx.get(f"{BASE_URL}/trafikmeldinger").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with VejdirektoratetClient(base_url=BASE_URL, username="u", password="p") as client:
        roadworks = list(client.iter_roadworks())
    assert len(roadworks) == 2
