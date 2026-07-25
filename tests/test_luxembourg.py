"""Tests for the Luxembourg (Ponts et Chaussées/CITA) DATEX II v2.3 adapter.

The fixture (three real situations, trimmed) is from a live GET of
``chantierActuelDatex.xml`` on ``cita.lu``, 2026-07 - confirmed reachable
with no credentials/API key required, and licensed CC0 (confirmed via
data.public.lu's own dataset API record), so real trimmed data is used
directly, unlike Belgium's synthetic fixture. Covers a roadworks-only
situation, a situation with a roadworks record sharing a situation with a
non-roadworks ``GeneralNetworkManagement`` record (exercises the
roadworks/measures split), and a non-roadworks-only situation (exercises
the roadworks filter).
"""

from pathlib import Path

import httpx
import respx

from streetworks.common import from_datex2
from streetworks.datex2 import iter_roadworks_full, iter_situations_full
from streetworks.datex2.luxembourg import DATEX_PATH, LuxembourgClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "luxembourg_chantiers.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def test_parses_real_situations():
    situations = list(iter_situations_full(FIXTURE_PATH))
    assert [s.id for s in situations] == ["34246", "65473", "55751"]


def test_iter_roadworks_excludes_non_roadworks_only_situation():
    roadworks = list(iter_roadworks_full(FIXTURE_PATH))
    assert [s.id for s in roadworks] == ["34246", "65473"]


def test_maintenance_works_fields():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "34246")
    works = situation.roadworks[0]
    assert works.record_type == "MaintenanceWorks"
    assert works.road_maintenance_type == "maintenanceWork"
    assert works.location.kind == "Linear"
    assert works.location.points == (
        (49.69184807503533, 6.291867835775066),
        (49.714263979573154, 6.304287120879002),
    )
    # Real, live-confirmed gaps: no road number, no Alert-C name, and every
    # record shares the same placeholder comment text - see module docstring.
    assert works.location.road_number is None
    assert works.location.alert_c_location is None
    assert works.comments == ("Titre:Nouvelle tape",)
    assert works.source_name == "PCH"
    # validityStatus never maps to the SDK's verified/estimated vocabulary
    # for this source - real dates, unmapped status.
    assert works.validity.status == "definedByValidityTimeSpec"
    assert works.raw is not None  # non-streaming parser - .raw is populated


def test_mixed_situation_splits_roadworks_and_measures():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "65473")
    assert len(situation.roadworks) == 1
    assert len(situation.measures) == 1
    assert situation.roadworks[0].record_type == "MaintenanceWorks"
    assert situation.measures[0].record_type == "GeneralNetworkManagement"


def test_from_datex2_defaults_administrative_area_to_pch():
    situation = next(s for s in iter_situations_full(FIXTURE_PATH) if s.id == "34246")
    works = from_datex2(situation, territory="Luxembourg")
    assert works.territory == "Luxembourg"
    assert works.administrative_area == "PCH"
    assert works.coordinate.crs == "EPSG:4326"  # the default, unlike Belgium


@respx.mock
def test_client_fetches_and_parses():
    respx.get(f"https://www.cita.lu/{DATEX_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with LuxembourgClient() as lu:
        situations = list(lu.iter_situations())
    assert len(situations) == 3


@respx.mock
def test_client_iter_roadworks_filters():
    respx.get(f"https://www.cita.lu/{DATEX_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with LuxembourgClient() as lu:
        roadworks = list(lu.iter_roadworks())
    assert len(roadworks) == 2
