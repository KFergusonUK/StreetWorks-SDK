"""Tests for streetworks.dfi_roads - Northern Ireland's DfI Roads
Highway Network centreline.

Credential-free, live-verified 2026-08-16 - see the module docstring in
``streetworks.dfi_roads.client``. ``dfi_roads_live_pull.json`` holds 4
REAL sections trimmed from a real, unauthenticated pull (71,596 total):
two typical single-path Adopted sections, one genuine multi-path Adopted
section (``7020U2252_17``, confirmed live - 2 of 10,000 sampled), and
one real Unadopted section.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.dfi_roads import BASE_URL, DfiRoadsClient
from streetworks.exceptions import TruncatedResultError

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "dfi_roads_live_pull.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text())
QUERY_URL = f"{BASE_URL}/query"


def _mock_single_page() -> respx.Route:
    return respx.get(QUERY_URL).mock(return_value=httpx.Response(200, json=FIXTURE))


@respx.mock
def test_iter_road_sections_needs_no_credentials():
    _mock_single_page()
    with DfiRoadsClient() as dfi:
        sections = list(dfi.iter_road_sections())
    assert len(sections) == len(FIXTURE["features"])


@respx.mock
def test_default_filters_to_adopted_only():
    route = _mock_single_page()
    with DfiRoadsClient() as dfi:
        list(dfi.iter_road_sections())
    assert route.calls[0].request.url.params["where"] == "ADOPTION_S='Adopted'"


@respx.mock
def test_adopted_only_false_requests_everything():
    route = _mock_single_page()
    with DfiRoadsClient() as dfi:
        list(dfi.iter_road_sections(adopted_only=False))
    assert route.calls[0].request.url.params["where"] == "1=1"


@respx.mock
def test_real_multi_path_section_becomes_coordinate_parts():
    _mock_single_page()
    with DfiRoadsClient() as dfi:
        sections = list(dfi.iter_road_sections())
    multi = next(s for s in sections if s.section_code == "7020U2252_17")
    assert multi.geometry.parts is not None
    assert len(multi.geometry.parts) == 2
    assert multi.geometry.points is None


@respx.mock
def test_typical_single_path_section_uses_points_not_parts():
    _mock_single_page()
    with DfiRoadsClient() as dfi:
        sections = list(dfi.iter_road_sections())
    typical = next(s for s in sections if s.section_code == "7065U9014_16")
    assert typical.geometry.points is not None
    assert typical.geometry.parts is None
    assert typical.geometry.crs == "EPSG:29902"


@respx.mock
def test_real_unadopted_section_is_preserved_in_the_fixture():
    _mock_single_page()
    with DfiRoadsClient() as dfi:
        sections = list(dfi.iter_road_sections(adopted_only=False))
    unadopted = [s for s in sections if s.adoption_status == "Unadopted"]
    assert len(unadopted) == 1
    assert unadopted[0].section_code == "7020U4087_15"


@respx.mock
def test_pagination_follows_exceeded_transfer_limit():
    page_one = {**FIXTURE, "features": FIXTURE["features"][:2], "exceededTransferLimit": True}
    page_two = {**FIXTURE, "features": FIXTURE["features"][2:], "exceededTransferLimit": False}
    calls = {"n": 0}

    def _dispatch(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        body = page_one if calls["n"] == 1 else page_two
        return httpx.Response(200, json=body)

    respx.get(QUERY_URL).mock(side_effect=_dispatch)

    with DfiRoadsClient() as dfi:
        sections = list(dfi.iter_road_sections(adopted_only=False))

    assert calls["n"] == 2
    assert len(sections) == len(FIXTURE["features"])


@respx.mock
def test_exceeded_transfer_limit_with_an_empty_page_raises_not_silently_truncates():
    empty_but_truncated = {**FIXTURE, "features": [], "exceededTransferLimit": True}
    respx.get(QUERY_URL).mock(return_value=httpx.Response(200, json=empty_but_truncated))

    with DfiRoadsClient() as dfi, pytest.raises(TruncatedResultError):
        list(dfi.iter_road_sections())
