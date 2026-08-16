"""Tests for streetworks.osni - Northern Ireland's OSNI Open Data -
Gazetteer - Streetnames.

Credential-free, live-verified 2026-08-16 - see the module docstring in
``streetworks.osni.client``. ``osni_streetnames_live_pull.geojson`` holds
5 REAL features trimmed from a real, unauthenticated pull (25,643
total): one real road-number entry (``A0002``, a genuine content quirk,
not filtered), and a duplicate-name pair (``ABBEY CLOSE`` twice, two
genuinely distinct real streets with different USRNs/locations).
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.osni import BASE_URL, OsniStreetnamesClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "osni_streetnames_live_pull.geojson"
FEATURE_COLLECTION = json.loads(FIXTURE_PATH.read_text())


def _mock_feed() -> respx.Route:
    return respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=FEATURE_COLLECTION))


@respx.mock
def test_iter_streetnames_needs_no_credentials():
    _mock_feed()
    with OsniStreetnamesClient() as osni:
        streets = list(osni.iter_streetnames())
    assert len(streets) == len(FEATURE_COLLECTION["features"])


@respx.mock
def test_iter_streetnames_uses_x_y_coord_not_reprojected_geometry():
    _mock_feed()
    with OsniStreetnamesClient() as osni:
        streets = list(osni.iter_streetnames())

    a0002 = next(s for s in streets if s.streetname == "A0002")
    # The real X_Coord/Y_Coord (Irish Grid), not the geometry.coordinates
    # field (reprojected to WGS84 by this download route) - see module
    # docstring.
    assert a0002.easting == 334186.0
    assert a0002.northing == 377179.0


@respx.mock
def test_iter_streetnames_keeps_real_road_number_entries():
    _mock_feed()
    with OsniStreetnamesClient() as osni:
        streets = list(osni.iter_streetnames())
    # A real content quirk (STREETNAME sometimes a road number) - never
    # filtered out.
    assert any(s.streetname == "A0002" for s in streets)


@respx.mock
def test_iter_streetnames_usrn_is_populated_and_distinct_per_real_row():
    _mock_feed()
    with OsniStreetnamesClient() as osni:
        streets = list(osni.iter_streetnames())
    usrns = [s.usrn for s in streets]
    assert all(isinstance(u, int) for u in usrns)
    assert len(set(usrns)) == len(usrns)  # confirmed live: always distinct


@respx.mock
def test_duplicate_streetname_stays_two_distinct_real_records():
    _mock_feed()
    with OsniStreetnamesClient() as osni:
        streets = list(osni.iter_streetnames())
    abbey_close = [s for s in streets if s.streetname == "ABBEY CLOSE"]
    assert len(abbey_close) == 2
    assert abbey_close[0].usrn != abbey_close[1].usrn
    assert (abbey_close[0].easting, abbey_close[0].northing) != (
        abbey_close[1].easting,
        abbey_close[1].northing,
    )
