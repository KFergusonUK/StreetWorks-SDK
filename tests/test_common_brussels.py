"""Tests for streetworks.common.from_brussels.

Fixture is real Brussels Road Events GeoJSON
(tests/fixtures/brussels_road_events.json) - see test_brussels.py's own
docstring for provenance, including the one synthetic (non-live)
record used only for the roadworks filter in test_brussels.py, not
used here.
"""

import json
from datetime import datetime
from pathlib import Path

from streetworks.common import DateConfidence, from_brussels

FEATURES = json.loads(
    (Path(__file__).parent / "fixtures" / "brussels_road_events.json").read_text()
)["features"]
ROADWORKS = [f for f in FEATURES if f["properties"]["datex_codes"] == "RWK"]


def _by_id(works_list):
    return {w.reference: w for w in works_list}


def test_coordinate_reads_lon_lat_geojson_order_into_lat_lon():
    works = _by_id(from_brussels(ROADWORKS))["events.095C592874E6DECE108EC92CAF2EEA33"]
    coordinate = works.coordinate
    assert coordinate.crs == "EPSG:4326"
    assert coordinate.value == (50.83923815617798, 4.340479167927325)


def test_works_type_is_stripped_of_the_real_trailing_space():
    works = _by_id(from_brussels(ROADWORKS))["events.095C592874E6DECE108EC92CAF2EEA33"]
    assert works.sites[0].works_type == "Travaux"


def test_location_description_combines_location_and_direction():
    works = _by_id(from_brussels(ROADWORKS))["events.095C592874E6DECE108EC92CAF2EEA33"]
    assert works.sites[0].location_description == "Boulevard Poincaré → PTE DE HAL"


def test_location_description_drops_indefini_direction():
    works = _by_id(from_brussels(ROADWORKS))["events.1FB737EDAC23DB78CF50DB10F4329F89"]
    assert works.sites[0].location_description == "Square Sainctelette"


def test_real_start_and_end_dates_parsed():
    works = _by_id(from_brussels(ROADWORKS))["events.095C592874E6DECE108EC92CAF2EEA33"]
    site = works.sites[0]
    assert site.proposed_start == datetime(2023, 6, 16, 9, 21)
    assert site.proposed_end == datetime(2026, 12, 31, 23, 59)


def test_html_entities_in_consequences_are_unescaped():
    works = _by_id(from_brussels(ROADWORKS))["events.33983005CFFFB5C8D02A3D6CB11763BF"]
    assert works.sites[0].traffic_management == "Bande d'arrêt d'urgence obstruée"


def test_date_confidence_is_uniformly_estimated():
    for works in from_brussels(ROADWORKS):
        assert works.sites[0].date_confidence is DateConfidence.ESTIMATED


def test_territory_and_administrative_area():
    works_list = from_brussels(ROADWORKS)
    assert all(w.territory == "Belgium" for w in works_list)
    assert all(w.administrative_area == "Brussels-Capital Region" for w in works_list)
