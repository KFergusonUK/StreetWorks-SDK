"""Tests for streetworks.saarland and streetworks.common.from_saarland.

Fixture is real Saarland LfS roadworks data
(tests/fixtures/saarland_roadworks_live_pull.json), captured live
2026-08-20 from `baustellen.saarland`'s own real
``roadworks_line_geojson.geojson`` - found by reading the public map
app's own bundled JS, see streetworks.saarland.client's module
docstring. Three real records: "Kuchenbergstraße" (a real named road),
one with a genuinely blank ``roadname`` (the real route number stated
only inside the free-text ``description``), and "Merziger Straße".
Geometry (``MultiLineString``) trimmed to 4 real vertices per record.
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import DateConfidence, from_saarland
from streetworks.saarland import ROADWORKS_URL, SaarlandClient

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "saarland_roadworks_live_pull.json").read_text(
        encoding="utf-8"
    )
)
_FEATURES = {f["properties"]["recordid"]: f for f in FIXTURE["features"]}


@respx.mock
def test_iter_roadworks_yields_real_features():
    respx.get(ROADWORKS_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    with SaarlandClient() as saarland:
        features = list(saarland.iter_roadworks())
    assert len(features) == 3
    assert features[0]["properties"]["recordid"] == "290005362842-760924601"


def test_real_named_road_and_multilinestring_geometry():
    works = from_saarland([_FEATURES["290005362842-760924601"]])
    w = works[0]
    site = w.sites[0]
    assert w.territory == "Germany"
    assert w.administrative_area == "Saarland"
    assert site.location_description == "Kuchenbergstraße"
    assert w.coordinate.crs == "EPSG:4326"
    assert len(w.coordinate.points) == 4
    lat, lon = w.coordinate.value
    assert 49.0 < lat < 49.7  # real Saarland bounds
    assert 6.3 < lon < 7.5


def test_genuinely_blank_roadname_not_fabricated():
    # The real route number is stated only inside the free-text
    # description ("L 116 ..."), never extracted - see module docstring.
    works = from_saarland([_FEATURES["2900053631841952216676"]])
    site = works[0].sites[0]
    assert site.location_description is None
    assert "L 116" in site.works_type


def test_naive_dates_localised_to_europe_berlin():
    # No UTC offset stated at all in the real source - see module
    # docstring for why this differs from Baden-Württemberg's own
    # explicit-offset dates on the same shared cluster.
    works = from_saarland([_FEATURES["290005362842-760924601"]])
    site = works[0].sites[0]
    assert str(site.proposed_start) == "2022-11-28 00:00:00+01:00"
    assert str(site.proposed_end) == "2026-12-31 23:59:59+01:00"
    assert site.date_confidence is DateConfidence.VERIFIED


def test_roadclosed_string_false_maps_to_no_status():
    # roadclosed is a real string "false"/"true", not a JSON boolean -
    # confirmed live every real record at investigation time states
    # "false".
    works = from_saarland([_FEATURES["290005362842-760924601"]])
    assert works[0].sites[0].status is None
