"""Tests for the France (Bison Futé / DIRs) DATEX II v2 adapter.

The fixture (three real situations, trimmed) is from a live GET of
``content.xml`` on ``tipi.bison-fute.gouv.fr``, 2026-07 - confirmed
reachable with no credentials/API key required. Covers a TPEG linear
location (from/to endpoints, real Alert-C name), a Point location paired
with a non-roadworks record in the same situation (exercises the
roadworks/measures split), and a non-roadworks-only situation (exercises
the roadworks filter).
"""

from pathlib import Path

import httpx
import respx

from streetworks.datex2 import BisonFuteClient, iter_roadworks_full, iter_situations_full
from streetworks.datex2.bisonfute import CONTENT_PATH, dir_regions

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bisonfute_content.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def test_parses_real_situations():
    situations = list(iter_situations_full(FIXTURE_PATH))
    assert [s.id for s in situations] == ["260122-001686", "260317-001067", "260113-001342"]


def test_iter_roadworks_excludes_non_roadworks_only_situation():
    roadworks = list(iter_roadworks_full(FIXTURE_PATH))
    assert [s.id for s in roadworks] == ["260122-001686", "260317-001067"]


def test_tpeg_linear_maintenance_works_fields():
    situations = list(iter_situations_full(FIXTURE_PATH))
    works = next(s for s in situations if s.id == "260122-001686").roadworks[0]
    assert works.record_type == "MaintenanceWorks"
    assert works.road_maintenance_type == "maintenanceWork"
    assert works.location.kind == "Linear"
    # Both TPEG endpoints survive - not just whichever came first (to).
    assert works.location.points == ((42.92285, 0.68384415), (42.908493, 0.6984161))
    assert works.location.road_number == "N0125"
    # Human-readable Alert-C name, not the raw numeric code.
    assert works.location.alert_c_location == "Fos"
    assert works.raw is not None  # non-streaming parser - .raw is populated


def test_point_construction_works_shares_situation_with_non_roadworks_record():
    situations = list(iter_situations_full(FIXTURE_PATH))
    situation = next(s for s in situations if s.id == "260317-001067")
    assert len(situation.roadworks) == 1
    assert len(situation.measures) == 1  # the ReroutingManagement sibling record

    works = situation.roadworks[0]
    assert works.record_type == "ConstructionWorks"
    assert works.location.kind == "Point"
    assert works.location.point == (46.47351, 0.26909396)
    assert works.location.alert_c_location == "Vivonne"


def test_dir_regions_reads_source_identification_from_raw():
    situations = list(iter_roadworks_full(FIXTURE_PATH))
    regions = dir_regions(situations)
    assert regions == {
        "260122-001686": "Direction interdépartementale des routes/DIR Sud-Ouest",
        "260317-001067": "Direction interdépartementale des routes/DIR Atlantique",
    }


@respx.mock
def test_client_fetches_and_parses():
    respx.get(f"https://tipi.bison-fute.gouv.fr/{CONTENT_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with BisonFuteClient() as bf:
        situations = list(bf.iter_situations())
    assert len(situations) == 3


@respx.mock
def test_client_iter_roadworks_filters():
    respx.get(f"https://tipi.bison-fute.gouv.fr/{CONTENT_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with BisonFuteClient() as bf:
        roadworks = list(bf.iter_roadworks())
    assert len(roadworks) == 2
