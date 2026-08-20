"""Tests for streetworks.geosn - Saxony's statewide Hauskoordinaten
export, deduplicated to streets.

``geosn_hauskoordinaten_real_sample.zip`` holds 8 REAL address rows
trimmed from the real statewide export (990,090 total): 6 rows on 6
distinct real streets, plus 2 further real rows on the same street as
the first row (`Dolsenhainer Straße`, Stadt Frohburg) - a real
duplicate-street case, to exercise the client's own deduplication - see
streetworks.geosn.client's own module docstring for the live evidence
behind each.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from streetworks.geosn import BASE_URL, GeoSNStreetsClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "geosn_hauskoordinaten_real_sample.zip"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def _mock_feed() -> respx.Route:
    return respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE_BYTES))


@respx.mock
def test_iter_streets_needs_no_credentials():
    _mock_feed()
    with GeoSNStreetsClient() as geosn:
        rows = list(geosn.iter_streets())
    assert len(rows) > 0


@respx.mock
def test_iter_streets_deduplicates_real_repeated_street():
    _mock_feed()
    with GeoSNStreetsClient() as geosn:
        rows = list(geosn.iter_streets())
    # 8 real rows, but "Dolsenhainer Straße" (gmdschl=140, strschl=59992)
    # appears 3 times in the fixture - only the first should survive.
    dolsenhainer = [r for r in rows if r["str"] == "Dolsenhainer Straße"]
    assert len(dolsenhainer) == 1
    assert dolsenhainer[0]["hnr"] == "2"  # the real first row's own house number
    assert len(rows) == 6


@respx.mock
def test_iter_streets_yields_real_shaped_fields():
    _mock_feed()
    with GeoSNStreetsClient() as geosn:
        rows = list(geosn.iter_streets())
    names = {r["str"] for r in rows}
    assert "Bergstraße" in names
    assert "Veilchenweg" in names
