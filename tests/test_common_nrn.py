"""Tests for streetworks.common.from_nrn.

Fixture is real National Road Network data
(tests/fixtures/nrn_roads_real.json), captured live 2026-08-16 against
the real ArcGIS REST service - Government of Canada open data (Open
Government Licence - Canada), so real records are committed here.
LineStrings are trimmed to their first 5 real vertices (fixture size
only - the converter carries every vertex given, it doesn't care how
many there are). Covers: five real downtown-Toronto local-road segments,
one real segment with the genuine "Unknown" name/place-name placeholder,
and one real segment on an actual administrative boundary (differing
left/right place names).
"""

import json
from pathlib import Path

from streetworks.common import from_nrn

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "nrn_roads_real.json").read_text(encoding="utf-8")
)

_FEATURES = {f["properties"]["OBJECTID"]: f for f in FIXTURE["features"]}


def test_real_street_name_and_type():
    segment = from_nrn(_FEATURES[26431])  # Wellington Street West
    assert len(segment.names) == 1
    assert segment.names[0].value == "Wellington Street West"
    assert segment.names[0].side is None  # l_stname_c == r_stname_c, no side split needed
    assert segment.street_type.label == "Collector"
    assert segment.administrative_area == "City of Toronto"


def test_geometry_is_wgs84_never_reprojected():
    segment = from_nrn(_FEATURES[26431])
    assert segment.geometry.crs == "EPSG:4326"
    assert segment.geometry.points is not None  # real multi-vertex LineString


def test_no_identifiers_ever_no_stable_id_exposed_by_this_service():
    segment = from_nrn(_FEATURES[26431])
    assert segment.identifiers == ()


def test_unknown_placeholder_becomes_no_name_and_no_admin_area():
    # A real record where l_stname_c/r_stname_c and l_placenam/r_placenam
    # are all NRN's own literal "Unknown" placeholder - never carried
    # through as a fabricated name or administrative area.
    segment = from_nrn(_FEATURES[3])
    assert segment.names == ()
    assert segment.administrative_area is None


def test_real_administrative_boundary_leaves_administrative_area_none():
    # A real segment between two different real townships - a single
    # field can't honestly state two different real values, so this
    # stays None rather than an arbitrary pick (same discipline
    # from_bdtopo established for its own real left/right admin split).
    segment = from_nrn(_FEATURES[242])
    assert segment.administrative_area is None
    assert segment.names[0].value == "Bar River Road East"
