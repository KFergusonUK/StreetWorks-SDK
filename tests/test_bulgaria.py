"""Tests for the Bulgaria (Road Infrastructure Agency/LIMA) DATEX II v2.3
adapter.

The fixture is synthetic - real, live-confirmed shape (bare ``Roadworks``
xsi:type, three ``pointByCoordinates`` per location, the mislabelled
``encoding="UTF-16"`` XML declaration over actually-UTF-8 bytes), not
trimmed from a live pull, since the real licence terms live behind the
unreachable ``lima.api.bg`` and couldn't be confirmed directly - see the
module docstring in ``bulgaria.py``. Covers two roadworks situations and
one non-roadworks (``Accident``) situation, added purely for
discriminator-exclusion test coverage - the real feed's "Short-term Road
Construction" dataset was 100% ``Roadworks`` in the live pull that informed
this fixture.
"""

from __future__ import annotations

import io
from pathlib import Path

import httpx
import respx

from streetworks.common import from_datex2
from streetworks.datex2 import iter_roadworks_full, iter_situations_full
from streetworks.datex2.bulgaria import BASE_URL, CATALOGUE_PATH, BulgariaClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bulgaria_roadworks_r03.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()
# What BulgariaClient.get_situations() produces after fixing the real feed's
# mislabelled encoding declaration - see module docstring.
CORRECTED_BYTES = FIXTURE_BYTES.replace(b'encoding="UTF-16"', b'encoding="UTF-8"', 1)

CATALOGUE_HTML = (
    '<html><body><a href="/files/20260725_roadworks_r03.xml" target="_blank">'
    "download</a></body></html>"
)


def test_fixture_reproduces_the_real_mislabelled_encoding_declaration():
    # Documents the real quirk this fixture is built to exercise.
    assert FIXTURE_BYTES.startswith(b'<?xml version="1.0" encoding="UTF-16"?>')


def test_parses_situations():
    situations = list(iter_situations_full(io.BytesIO(CORRECTED_BYTES)))
    assert [s.id for s in situations] == [
        "synthetic-bg-0001",
        "synthetic-bg-0002",
        "synthetic-bg-0003",
    ]


def test_iter_roadworks_excludes_non_roadworks_type():
    roadworks = list(iter_roadworks_full(io.BytesIO(CORRECTED_BYTES)))
    assert [s.id for s in roadworks] == ["synthetic-bg-0001", "synthetic-bg-0002"]


def test_roadworks_record_uses_bare_roadworks_xsi_type():
    situation = next(
        s for s in iter_situations_full(io.BytesIO(CORRECTED_BYTES)) if s.id == "synthetic-bg-0001"
    )
    works = situation.roadworks[0]
    assert works.record_type == "Roadworks"
    # roadMaintenanceType sits three levels deep (roadworks/maintenanceWorks/
    # roadMaintenanceType) - one past the shared parser's direct-child lookup,
    # so this comes out None (see module docstring in bulgaria.py).
    assert works.road_maintenance_type is None


def test_location_captures_only_first_of_three_real_points():
    situation = next(
        s for s in iter_situations_full(io.BytesIO(CORRECTED_BYTES)) if s.id == "synthetic-bg-0001"
    )
    works = situation.roadworks[0]
    assert works.location.kind == "Point"
    assert works.location.points == ((42.334656341554, 23.952773925773),)
    assert works.location.road_number is None
    assert works.location.alert_c_location is None


def test_accident_record_is_not_roadworks():
    situation = next(
        s for s in iter_situations_full(io.BytesIO(CORRECTED_BYTES)) if s.id == "synthetic-bg-0003"
    )
    assert len(situation.roadworks) == 0
    assert len(situation.measures) == 1
    assert situation.measures[0].record_type == "Accident"


def test_from_datex2_works_type_falls_back_to_record_type():
    situation = next(
        s for s in iter_situations_full(io.BytesIO(CORRECTED_BYTES)) if s.id == "synthetic-bg-0001"
    )
    works = from_datex2(situation, territory="Bulgaria")
    assert works.territory == "Bulgaria"
    assert works.coordinate.crs == "EPSG:4326"
    assert works.sites[0].works_type == "Roadworks"


@respx.mock
def test_client_resolves_catalogue_then_fetches_file_and_fixes_encoding():
    respx.get(f"{BASE_URL}/{CATALOGUE_PATH}").mock(
        return_value=httpx.Response(200, text=CATALOGUE_HTML)
    )
    respx.get(f"{BASE_URL}/files/20260725_roadworks_r03.xml").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with BulgariaClient() as bg:
        raw = bg.get_situations()
    assert raw == CORRECTED_BYTES


@respx.mock
def test_client_iter_roadworks_filters():
    respx.get(f"{BASE_URL}/{CATALOGUE_PATH}").mock(
        return_value=httpx.Response(200, text=CATALOGUE_HTML)
    )
    respx.get(f"{BASE_URL}/files/20260725_roadworks_r03.xml").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with BulgariaClient() as bg:
        roadworks = list(bg.iter_roadworks())
    assert len(roadworks) == 2


@respx.mock
def test_client_raises_when_catalogue_link_missing():
    respx.get(f"{BASE_URL}/{CATALOGUE_PATH}").mock(
        return_value=httpx.Response(200, text="<html><body>no link here</body></html>")
    )
    with BulgariaClient() as bg:
        try:
            bg.get_situations()
        except ValueError as exc:
            assert "no roadworks file link found" in str(exc)
        else:
            raise AssertionError("expected ValueError")
