"""Tests for streetworks.caclr - CACLR (Luxembourg's national street
register).

``caclr_real_sample.zip`` holds 3 REAL RUE rows (Ale Wee - normal, Rue
du Fort Berlaimont - a real end-dated street, Château de Beggen - a
real provisional street), 1 REAL LOCALITE row (Luxembourg), and 2 REAL
COMMUALL rows sharing the same commune code (01) under two different
real cantons (00 = Luxembourg, 13 = Burmerange) - the real join trap
this SDK found live, see streetworks.caclr.client's own module
docstring for the full evidence.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from streetworks.caclr import DATASET_API_URL, CaclrStreetsClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "caclr_real_sample.zip"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()

ZIP_URL = "https://download.data.public.lu/resources/.../20260817-023002/caclr.zip"


def _mock_api_and_zip() -> None:
    respx.get(DATASET_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "resources": [
                    {"title": "caclr.xlsx", "url": "https://example.org/caclr.xlsx"},
                    {"title": "caclr.zip", "url": ZIP_URL},
                ]
            },
        )
    )
    respx.get(ZIP_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))


@respx.mock
def test_iter_streets_resolves_the_zip_url_from_the_live_api_first():
    api_route = respx.get(DATASET_API_URL).mock(
        return_value=httpx.Response(
            200, json={"resources": [{"title": "caclr.zip", "url": ZIP_URL}]}
        )
    )
    zip_route = respx.get(ZIP_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))
    with CaclrStreetsClient() as caclr:
        list(caclr.iter_streets())
    assert api_route.call_count == 1
    assert zip_route.call_count == 1


@respx.mock
def test_iter_streets_yields_every_real_row():
    _mock_api_and_zip()
    with CaclrStreetsClient() as caclr:
        rows = list(caclr.iter_streets())
    assert len(rows) == 3
    assert {r["NOM"] for r in rows} == {"Ale Wee", "Rue du Fort Berlaimont", "Château de Beggen"}


@respx.mock
def test_iter_streets_resolves_commune_via_the_real_composite_key():
    _mock_api_and_zip()
    with CaclrStreetsClient() as caclr:
        rows = list(caclr.iter_streets())
    ale_wee = next(r for r in rows if r["NUMERO"] == "00001")
    # The naive single-key join would land on "Burmerange" (also code 01,
    # a different canton) - the real composite key must resolve Luxembourg.
    assert ale_wee["COMMUNE_NOM"] == "Luxembourg"


@respx.mock
def test_missing_zip_resource_raises():
    respx.get(DATASET_API_URL).mock(return_value=httpx.Response(200, json={"resources": []}))
    with CaclrStreetsClient() as caclr, pytest.raises(LookupError, match="caclr.zip"):
        list(caclr.iter_streets())
