"""Tests for streetworks.swisstopo - Switzerland's federal street-name
register (Amtliches Verzeichnis der Strassen).

``swisstopo_strassenverzeichnis_real_sample.zip`` holds 6 REAL rows
trimmed from the real national bulk download (224,985 total), captured
live 2026-08-18: one typical Street row, one Area row, one Place row,
one real STR_STATUS="planned" row, one real STR_OFFICIAL="false" row,
and one row with a real STR_PARENT reference - see
streetworks.swisstopo.client's own module docstring for the live
evidence behind each.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from streetworks.swisstopo import BASE_URL, SwisstopoStreetsClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "swisstopo_strassenverzeichnis_real_sample.zip"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def _mock_feed() -> respx.Route:
    return respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))


@respx.mock
def test_iter_streets_needs_no_credentials():
    _mock_feed()
    with SwisstopoStreetsClient() as swisstopo:
        rows = list(swisstopo.iter_streets())
    assert len(rows) == 6


@respx.mock
def test_iter_streets_decodes_real_accented_utf8_content():
    _mock_feed()
    with SwisstopoStreetsClient() as swisstopo:
        rows = list(swisstopo.iter_streets())
    accented = next(r for r in rows if r["STR_ESID"] == "10078330")
    assert accented["STN_LABEL"] == "Bügl Grond"


@respx.mock
def test_iter_streets_yields_every_real_status_and_type():
    _mock_feed()
    with SwisstopoStreetsClient() as swisstopo:
        rows = list(swisstopo.iter_streets())
    statuses = {r["STR_STATUS"] for r in rows}
    types = {r["STR_TYPE"] for r in rows}
    assert statuses == {"real", "planned"}
    assert types == {"Street", "Area", "Place"}
