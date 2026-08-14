"""Tests for the Austria (ASFINAG) DATEX II adapter.

**Pending live verification** - see the module docstring in
``streetworks.datex2.austria``. The fixture
(``austria_asfinag_situations.xml``) is synthetic, not real data: only
ASFINAG's own official dataset page (confirming the dataset, its DATEX II
Situations/SituationRecords format, and its CC-BY-4.0-with-supplementary-
conditions licence) has been verified live - the credential-gated data
pull itself has never been exercised, and even the real auth mechanism is
unconfirmed. It exists to exercise the parser-reuse hypothesis (genuine
DATEX II XML, parsed via the existing shared streaming parser) against
the simplest plausible real-world response shape (a bare XML document
body) - a real ConstructionWorks record, a real MaintenanceWorks record,
and a non-roadworks Accident record (to prove the roadworks filter
doesn't over-match).
"""

from pathlib import Path

import httpx
import pytest
import respx

from streetworks.datex2 import AsfinagClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "austria_asfinag_situations.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()

BASE_URL = "https://example-asfinag.at/data/plannedevents"


def test_client_requires_base_url():
    with pytest.raises(ValueError):
        AsfinagClient(base_url="")


@respx.mock
def test_client_fetches_and_parses_construction_and_maintenance_works():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with AsfinagClient(base_url=BASE_URL) as client:
        situations = list(client.iter_situations())

    assert [s.id for s in situations] == [
        "synthetic-at-0001",
        "synthetic-at-0002",
        "synthetic-at-0003",
    ]

    construction = situations[0].records[0]
    assert construction.record_type == "ConstructionWorks"
    assert construction.construction_work_type == "roadWideningWork"
    assert construction.location.point == (48.2244, 15.8896)

    maintenance = situations[1].records[0]
    assert maintenance.record_type == "MaintenanceWorks"
    assert maintenance.road_maintenance_type == "resurfacingWork"


@respx.mock
def test_client_iter_roadworks_excludes_non_roadworks_records():
    """Genuine DATEX vocabulary - ROADWORKS_TYPES matches
    ConstructionWorks/MaintenanceWorks directly, the Accident record is
    excluded, no Trafikverket-style discriminator gap."""
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with AsfinagClient(base_url=BASE_URL) as client:
        roadworks = list(client.iter_roadworks())
    assert len(roadworks) == 2
    assert {s.id for s in roadworks} == {"synthetic-at-0001", "synthetic-at-0002"}
