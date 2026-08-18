"""Tests for streetworks.bev - Austria's federal street-name register
(Österreichisches Adressregister, STRASSE.csv joined against
GEMEINDE.csv).

``bev_adressregister_real_sample.zip`` holds 2 REAL STRASSE.csv rows
trimmed from the real national bulk download (137,767 total, Stichtag
01.10.2025) plus their real GEMEINDE.csv municipality rows: a typical
entry, and one with a real STRASSENNAMENZUSATZ (name addition) - see
streetworks.bev.client's own module docstring for the live evidence
behind each.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from streetworks.bev import BASE_URL, BevStreetsClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bev_adressregister_real_sample.zip"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def _mock_feed() -> respx.Route:
    return respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))


@respx.mock
def test_iter_streets_needs_no_credentials():
    _mock_feed()
    with BevStreetsClient() as bev:
        rows = list(bev.iter_streets())
    assert len(rows) == 2


@respx.mock
def test_iter_streets_joins_real_gemeindename():
    _mock_feed()
    with BevStreetsClient() as bev:
        rows = list(bev.iter_streets())
    first = next(r for r in rows if r["SKZ"] == "000001")
    assert first["GEMEINDENAME"] == "Eisenstadt"
    second = next(r for r in rows if r["SKZ"] == "126290")
    assert second["GEMEINDENAME"] == "Donnerskirchen"


@respx.mock
def test_iter_streets_yields_real_shaped_fields():
    _mock_feed()
    with BevStreetsClient() as bev:
        rows = list(bev.iter_streets())
    named = [r["STRASSENNAME"] for r in rows]
    assert "Josef Stanislaus Albach-Gasse" in named
    assert "Reiterweg" in named
