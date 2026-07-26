"""Tests for the Basque Country (Euskadi, Dirección de Tráfico del
Gobierno Vasco) DATEX II v1.0 adapter.

The fixture is synthetic - real, live-confirmed shape (DATEX II v1.0's
own namespace/envelope, the real ``tpeglinearLocation``/``tpegpointLocation``
lower-case spellings, Alert-C-only locations, the ``administrativeArea``
province nesting including the real ``"Desconocida"`` placeholder), not
trimmed from a live pull, since the publisher states "No licence - No
contract" - genuinely more restrictive than an unconfirmed licence, see
``streetworks/datex2/euskadi.py``'s module docstring. Four situations:
a ``ConstructionWorks`` with a real 2-point line (exercising the
``tpeglinearLocation`` parser fix), a ``MaintenanceWorks`` with a single
point, a ``ConstructionWorks`` with an Alert-C-only location (no
coordinates, real ``"Desconocida"`` province placeholder), and a
non-roadworks ``Activities`` record (a real bicycle-race closure,
confirming the discriminator excludes it).
"""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from streetworks.common import from_datex2
from streetworks.datex2 import iter_roadworks_full, iter_situations_full
from streetworks.datex2.euskadi import BASE_URL, SITUATION_PATH, EuskadiClient, provinces

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "euskadi_situations.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def test_parses_situations():
    situations = list(iter_situations_full(FIXTURE_PATH))
    assert [s.id for s in situations] == [
        "SYN_EUS_0001",
        "SYN_EUS_0002",
        "SYN_EUS_0003",
        "SYN_EUS_0004",
    ]


def test_iter_roadworks_excludes_activities():
    roadworks = list(iter_roadworks_full(FIXTURE_PATH))
    assert [s.id for s in roadworks] == ["SYN_EUS_0001", "SYN_EUS_0002", "SYN_EUS_0003"]


def test_lowercase_tpeglinearlocation_captures_both_points():
    """The real v1.0-specific parser fix: lower-case tpeglinearLocation
    (not the v2/v3 tpegLinearLocation) must still yield a real 2-point
    line, not fall through to a single-point fallback."""
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "SYN_EUS_0001")
    works = situation.roadworks[0]
    assert works.record_type == "ConstructionWorks"
    assert works.location.points == ((43.2824, -2.1528), (43.2866, -2.1762))
    assert works.location.road_number == "N-634"


def test_lowercase_tpegpointlocation_captures_single_point():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "SYN_EUS_0002")
    works = situation.roadworks[0]
    assert works.record_type == "MaintenanceWorks"
    assert works.location.points == ((43.1937, -2.4349),)
    assert works.location.road_number == "BI-636"
    assert works.road_maintenance_type == "roadworks"


def test_alert_c_only_record_has_no_coordinates():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "SYN_EUS_0003")
    works = situation.roadworks[0]
    assert works.location.points == ()
    assert works.location.road_number == "GI-631"
    assert works.location.alert_c_location == "19451"


def test_activities_record_is_not_roadworks():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "SYN_EUS_0004")
    assert len(situation.roadworks) == 0
    assert len(situation.measures) == 1
    assert situation.measures[0].record_type == "Activities"


def test_provinces_excludes_desconocida_placeholder():
    situations = list(iter_situations_full(FIXTURE_PATH))
    provs = provinces(situations)
    assert provs == {"SYN_EUS_0001": "GIPUZKOA", "SYN_EUS_0002": "Bizkaia"}
    # SYN_EUS_0003's real "Desconocida" placeholder is not a real province.
    assert "SYN_EUS_0003" not in provs


def test_from_datex2_crs_is_wgs84_default():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "SYN_EUS_0001")
    works = from_datex2(situation, territory="Spain", administrative_area="GIPUZKOA")
    assert works.coordinate.crs == "EPSG:4326"
    assert works.administrative_area == "GIPUZKOA"


@respx.mock
def test_client_fetches_and_parses():
    respx.get(f"{BASE_URL}/{SITUATION_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with EuskadiClient() as euskadi:
        situations = list(euskadi.iter_situations())
    assert len(situations) == 4


@respx.mock
def test_client_iter_roadworks_filters():
    respx.get(f"{BASE_URL}/{SITUATION_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with EuskadiClient() as euskadi:
        roadworks = list(euskadi.iter_roadworks())
    assert len(roadworks) == 3
