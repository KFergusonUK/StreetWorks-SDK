"""Tests for streetworks.common._web_mercator - the shared closed-form
EPSG:3857 <-> EPSG:4326 helper used by the ArcGIS-family AU converters
(WA, SA). See that module's own docstring for why a closed-form formula is
used instead of pyproj.
"""

from __future__ import annotations

import pytest

from streetworks.common._web_mercator import reproject_if_projected, web_mercator_to_wgs84


def test_web_mercator_to_wgs84_round_trips_a_known_point():
    # Perth CBD (115.8605, -31.9505) forward-projected to EPSG:3857 via the
    # standard spherical Mercator formula.
    lon, lat = web_mercator_to_wgs84(12897531.863054074, -3756814.7353761178)
    assert lon == pytest.approx(115.8605, abs=1e-6)
    assert lat == pytest.approx(-31.9505, abs=1e-6)


def test_reproject_if_projected_reprojects_out_of_range_values():
    lon, lat = reproject_if_projected(12897531.863054074, -3756814.7353761178)
    assert 115 < lon < 117
    assert -33 < lat < -31


def test_reproject_if_projected_passes_through_genuine_wgs84():
    assert reproject_if_projected(115.8605, -31.9505) == (115.8605, -31.9505)


def test_reproject_if_projected_boundary_values_are_not_reprojected():
    # Exactly at the plausible-degree boundary - still treated as genuine
    # WGS84, not projected metres (the guard only fires strictly beyond).
    assert reproject_if_projected(180.0, 90.0) == (180.0, 90.0)
    assert reproject_if_projected(-180.0, -90.0) == (-180.0, -90.0)
