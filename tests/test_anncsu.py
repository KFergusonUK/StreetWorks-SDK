"""Tests for streetworks.anncsu - Italy's national ANNCSU street-name
registry.

Credential-free, live-verified 2026-08-16 - see the module docstring in
``streetworks.anncsu.client``. ``anncsu_odonimi_live_pull.zip`` holds 4
REAL rows trimmed from the real national bulk download (1,219,990 total):
two typical entries sharing one municipality, one with an empty
``CODICE_COMUNALE`` (a real, genuine gap - not fabricated), and one with
a real accented character (``LOCALITÀ CASTELLUCCIO``) to exercise the
UTF-8 handling.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from streetworks.anncsu import BASE_URL, AnncsuClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "anncsu_odonimi_live_pull.zip"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def _mock_feed() -> respx.Route:
    return respx.get(f"{BASE_URL}?STRAD_ITA").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )


@respx.mock
def test_iter_odonimi_needs_no_credentials():
    _mock_feed()
    with AnncsuClient() as anncsu:
        streets = list(anncsu.iter_odonimi())
    assert len(streets) == 4


@respx.mock
def test_iter_odonimi_uses_the_real_bare_flag_query_param():
    route = _mock_feed()
    with AnncsuClient() as anncsu:
        list(anncsu.iter_odonimi())
    # A plain params dict would send "?STRAD_ITA=" (real server rejects
    # that with "no content associated") - confirm the bare-flag form.
    assert route.calls[0].request.url.query == b"STRAD_ITA"


@respx.mock
def test_iter_odonimi_decodes_real_accented_utf8_content():
    _mock_feed()
    with AnncsuClient() as anncsu:
        streets = list(anncsu.iter_odonimi())
    accented = next(s for s in streets if s.progressivo_nazionale == 1339708)
    assert accented.odonimo == "LOCALITÀ CASTELLUCCIO"


@respx.mock
def test_iter_odonimi_preserves_a_real_empty_codice_comunale():
    _mock_feed()
    with AnncsuClient() as anncsu:
        streets = list(anncsu.iter_odonimi())
    gap = next(s for s in streets if s.progressivo_nazionale == 375692)
    assert gap.codice_comunale is None  # a real, genuine gap - not fabricated


@respx.mock
def test_iter_odonimi_carries_both_real_municipality_codes():
    _mock_feed()
    with AnncsuClient() as anncsu:
        streets = list(anncsu.iter_odonimi())
    first = streets[0]
    assert first.codice_comune == "A008"  # Belfiore code
    assert first.codice_istat == "068001"  # ISTAT code
    assert first.totale_accessi == 1
