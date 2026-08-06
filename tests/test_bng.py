"""Tests for streetworks.common._bng - the WGS84<->BNG transform, verified
against Ordnance Survey's own published worked examples (not invented
numbers - see the module docstring for the source document), not just
internal round-trips."""

from __future__ import annotations

import math

import pytest

from streetworks.common._bng import (
    _latlon_to_national_grid,
    _national_grid_to_latlon,
    bng_to_wgs84,
    reproject_geojson_to_bng,
    wgs84_to_bng,
)


def _dms(degrees: float, minutes: float, seconds: float) -> float:
    return degrees + minutes / 60 + seconds / 3600


# --------------------------------------------------------------------------- #
# Annex C.1/C.2 - pure ellipsoidal Transverse Mercator, OSGB36 datum only,
# no Helmert step involved - the purest possible check of the projection
# maths in isolation, so tolerance is tight (millimetres: pure algebra, no
# datum uncertainty at all).
# --------------------------------------------------------------------------- #


def test_latlon_to_national_grid_matches_os_worked_example():
    lat = math.radians(_dms(52, 39, 27.2531))
    lon = math.radians(_dms(1, 43, 4.5177))
    easting, northing = _latlon_to_national_grid(lat, lon)
    assert easting == pytest.approx(651409.903, abs=0.001)
    assert northing == pytest.approx(313177.270, abs=0.001)


def test_national_grid_to_latlon_matches_os_worked_example():
    lat, lon = _national_grid_to_latlon(651409.903, 313177.270)
    assert math.degrees(lat) == pytest.approx(_dms(52, 39, 27.2531), abs=1e-7)
    assert math.degrees(lon) == pytest.approx(_dms(1, 43, 4.5177), abs=1e-7)


# --------------------------------------------------------------------------- #
# Annex D - the full WGS84 -> OSGB36 (Helmert) -> National Grid worked
# example, so this exercises the whole public wgs84_to_bng/bng_to_wgs84 path.
# --------------------------------------------------------------------------- #

_ANNEX_D_LAT = _dms(53, 36, 43.1653)
_ANNEX_D_LON = -_dms(1, 39, 51.9920)  # West
_ANNEX_D_HEIGHT = 299.800
_ANNEX_D_EASTING = 422297.792
_ANNEX_D_NORTHING = 412878.741


def test_wgs84_to_bng_matches_os_worked_example():
    easting, northing = wgs84_to_bng(_ANNEX_D_LON, _ANNEX_D_LAT, height=_ANNEX_D_HEIGHT)
    assert easting == pytest.approx(_ANNEX_D_EASTING, abs=0.05)
    assert northing == pytest.approx(_ANNEX_D_NORTHING, abs=0.05)


def test_bng_to_wgs84_approximates_os_worked_example():
    # Looser tolerance than the forward test - bng_to_wgs84 uses the
    # approximate (small-angle) inverse Helmert, not a true matrix inverse
    # (see _helmert_osgb36_to_wgs84's own docstring). abs=0.0005 degrees is
    # of the order of tens of metres, generous relative to the sub-cm
    # residual the approximation actually produces - this test is about
    # correctness (right point, right hemisphere/sign), not pinning the
    # approximation's exact residual.
    lon, lat = bng_to_wgs84(_ANNEX_D_EASTING, _ANNEX_D_NORTHING)
    assert lat == pytest.approx(_ANNEX_D_LAT, abs=0.0005)
    assert lon == pytest.approx(_ANNEX_D_LON, abs=0.0005)


# --------------------------------------------------------------------------- #
# Round trip - the real regression guard for a sign/axis-order bug. Done in
# BNG metres so the tolerance is direct and meaningful. A correct
# implementation's only error source is the approximate Helmert inverse,
# which is second-order in the (arcsecond/ppm-scale) rotation/scale
# parameters - true residual is sub-millimetre (confirmed directly against
# this implementation), so centimetre tolerance is tight enough to catch a
# real bug while leaving headroom.
# --------------------------------------------------------------------------- #


def test_wgs84_to_bng_round_trips_within_a_centimetre():
    # An arbitrary GB point (near Durham, matching this SDK's other worked
    # examples) - not a special-cased coordinate.
    easting, northing = 429000.0, 541000.0
    lon, lat = bng_to_wgs84(easting, northing)
    easting2, northing2 = wgs84_to_bng(lon, lat)
    assert easting2 == pytest.approx(easting, abs=0.01)
    assert northing2 == pytest.approx(northing, abs=0.01)


# --------------------------------------------------------------------------- #
# reproject_geojson_to_bng - shape-preserving, no "crs" key added (matches
# Street Manager's own implicit-BNG convention, mirroring the read-side
# _coordinate() in streetworks.common.from_streetmanager).
# --------------------------------------------------------------------------- #


def test_reproject_geojson_to_bng_point():
    point = {"type": "Point", "coordinates": [_ANNEX_D_LON, _ANNEX_D_LAT]}
    result = reproject_geojson_to_bng(point)
    assert result["type"] == "Point"
    assert "crs" not in result
    assert result["coordinates"][0] == pytest.approx(_ANNEX_D_EASTING, abs=0.05)
    assert result["coordinates"][1] == pytest.approx(_ANNEX_D_NORTHING, abs=0.05)


def test_reproject_geojson_to_bng_line_string():
    geometry = {
        "type": "LineString",
        "coordinates": [[_ANNEX_D_LON, _ANNEX_D_LAT], [_ANNEX_D_LON, _ANNEX_D_LAT]],
    }
    result = reproject_geojson_to_bng(geometry)
    assert result["type"] == "LineString"
    assert len(result["coordinates"]) == 2
    for x, y in result["coordinates"]:
        assert x == pytest.approx(_ANNEX_D_EASTING, abs=0.05)
        assert y == pytest.approx(_ANNEX_D_NORTHING, abs=0.05)


def test_reproject_geojson_to_bng_polygon():
    ring = [
        [_ANNEX_D_LON, _ANNEX_D_LAT],
        [_ANNEX_D_LON, _ANNEX_D_LAT],
        [_ANNEX_D_LON, _ANNEX_D_LAT],
        [_ANNEX_D_LON, _ANNEX_D_LAT],
    ]
    result = reproject_geojson_to_bng({"type": "Polygon", "coordinates": [ring]})
    assert result["type"] == "Polygon"
    assert len(result["coordinates"]) == 1
    assert len(result["coordinates"][0]) == 4


def test_reproject_geojson_to_bng_rejects_unsupported_geometry_type():
    with pytest.raises(ValueError, match="MultiPoint"):
        reproject_geojson_to_bng({"type": "MultiPoint", "coordinates": [[0.0, 0.0]]})
