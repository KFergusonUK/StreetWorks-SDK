"""Tests for the Spain (DGT) DATEX II v3 adapter.

The fixture (five real situations, trimmed) is from a live GET of the
DGT National Access Point's SituationPublication endpoint, 2026-07 -
confirmed reachable with no credentials/API key required (the well-known
``datex2_v36.xml`` path 301-redirects to ``datex2_v37.xml`` live; the fixture
itself carries ``profileVersion="3.7_1.0"``). Covers a
``SingleRoadLinearLocation`` (TPEG from/to), a ``PointLocation``, a
situation with two roadworks records of different xsi:types sharing one
situation (proves the cause-based discriminator isn't limited to
``RoadOrCarriagewayOrLaneManagement``), a situation with a real
province-boundary-crossing segment (exercises :func:`provinces`'s
first-found simplification), and a non-roadworks-only situation (same
xsi:type as the real roadworks ones, but a different cause - exercises
that the cause check, not just the xsi:type, is what discriminates).
"""

from pathlib import Path

import httpx
import respx

from streetworks.datex2 import DGTClient, iter_roadworks_full, iter_situations_full
from streetworks.datex2.dgt import SITUATION_PUBLICATION_PATH, provinces

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "dgt_situations.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def test_parses_real_situations():
    situations = list(iter_situations_full(FIXTURE_PATH))
    assert [s.id for s in situations] == [
        "2816645",
        "14845291",
        "14590355",
        "20268117",
        "13054089",
    ]


def test_iter_roadworks_excludes_non_roadmaintenance_cause():
    # 13054089's record is RoadOrCarriagewayOrLaneManagement too, but its
    # cause is infrastructureDamageObstruction - the same xsi:type as real
    # roadworks records, so this proves the cause check does the real work.
    roadworks = list(iter_roadworks_full(FIXTURE_PATH))
    assert [s.id for s in roadworks] == ["2816645", "14845291", "14590355", "20268117"]


def test_linear_location_roadworks_fields():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "2816645")
    works = situation.roadworks[0]
    assert works.record_type == "RoadOrCarriagewayOrLaneManagement"
    assert works.cause_type == "roadMaintenance"
    assert works.road_maintenance_type == "roadworks"
    assert works.location.kind == "SingleRoadLinearLocation"
    assert works.location.points == ((39.993732, -3.6074991), (39.994446, -3.6054852))
    # roadName fallback (Spain never states roadNumber)
    assert works.location.road_number == "N-400"
    assert works.raw is not None  # non-streaming parser - .raw is populated


def test_point_location_roadworks_fields():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "14845291")
    works = situation.roadworks[0]
    assert works.location.kind == "PointLocation"
    assert works.location.point == (40.917767, -1.3028483)
    assert works.location.road_number == "A-1507"


def test_speedmanagement_record_counts_as_roadworks():
    # Confirms the cause-based discriminator isn't hardcoded to one xsi:type.
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "14590355")
    assert len(situation.roadworks) == 2
    types = {r.record_type for r in situation.roadworks}
    assert types == {"SpeedManagement", "RoadOrCarriagewayOrLaneManagement"}


def test_provinces_reads_from_raw():
    roadworks = list(iter_roadworks_full(FIXTURE_PATH))
    result = provinces(roadworks)
    assert result == {
        "2816645": "Toledo",
        "14845291": "Teruel",
        "14590355": "Madrid",
        # Boundary-crossing segment (from/to endpoints in different
        # provinces) - takes the first one found, documented in the module.
        "20268117": "València/Valencia",
    }


@respx.mock
def test_client_fetches_and_parses():
    respx.get(f"https://nap.dgt.es/{SITUATION_PUBLICATION_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with DGTClient() as dgt:
        situations = list(dgt.iter_situations())
    assert len(situations) == 5


@respx.mock
def test_client_iter_roadworks_filters():
    respx.get(f"https://nap.dgt.es/{SITUATION_PUBLICATION_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with DGTClient() as dgt:
        roadworks = list(dgt.iter_roadworks())
    assert len(roadworks) == 4
