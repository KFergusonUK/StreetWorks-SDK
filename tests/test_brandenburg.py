"""Tests for streetworks.brandenburg - wiring only. See
streetworks.brandenburg.client's own module docstring for the live
evidence behind each real behaviour covered here (the real GML-only
WFS, and the confirmed non-exhaustive Berlin presence)."""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from streetworks.brandenburg import BASE_URL, BrandenburgStreetsClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "brandenburg_streets_real.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


@respx.mock
def test_iter_streets_needs_no_credentials():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with BrandenburgStreetsClient() as bb:
        records = list(bb.iter_streets())
    assert len(records) == 3


@respx.mock
def test_iter_streets_stops_on_a_short_page():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with BrandenburgStreetsClient(page_size=5000) as bb:
        records = list(bb.iter_streets())
    assert len(records) == 3
    # 3 real records is short of the 5000 page size - one request, not a loop.
    assert route.call_count == 1


@respx.mock
def test_iter_streets_parses_real_fields_and_land_codes():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with BrandenburgStreetsClient() as bb:
        records = list(bb.iter_streets())
    names = {r["strassenname"] for r in records}
    assert names == {"Am Feuerwerkslaboratorium", "Am Mariengrund", "Simmelstraße"}
    lands = {r["land"] for r in records}
    assert lands == {"12", "11"}


@respx.mock
def test_geographic_extent_is_captured_as_raw_gml():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with BrandenburgStreetsClient() as bb:
        records = list(bb.iter_streets())
    record = next(r for r in records if r["strassenname"] == "Am Feuerwerkslaboratorium")
    assert "gml:Polygon" in record["geographicExtent_gml"]
    assert "geographicExtent" not in record
