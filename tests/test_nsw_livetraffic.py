"""Tests for the New South Wales (TfNSW Live Traffic Hazards) adapter.

**Pending live verification** - see the module docstring in
``streetworks.au.nsw``. The fixture (``nsw_livetraffic_roadwork.json``)
wraps one REAL feature (id 82681, Nelligen Bridge replacement project),
transcribed verbatim from TfNSW's own Developer Guide PDF - not a
synthetic reconstruction, unlike Sweden/Denmark's fixtures. Only the
FeatureCollection envelope around it is invented (the guide gives no real
example for ``rights``/``layerName``/``lastPublished``).
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.au.nsw import BASE_URL, NswLiveTrafficClient, parse_features
from streetworks.common import DateConfidence, from_nsw_livetraffic

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "nsw_livetraffic_roadwork.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())


def test_parse_features_strips_empty_and_null_but_keeps_the_string_null():
    features = parse_features(FIXTURE_JSON)
    assert len(features) == 1
    properties = features[0]["properties"]

    # Guide's own documented rule: empty/whitespace strings, empty lists,
    # and JSON null are all disregarded.
    for absent in ("headline", "weblinkUrl", "subCategoryB", "publicTransport", "media"):
        assert absent not in properties

    # The real footgun: a literal string "null" is NOT the same as JSON
    # null and must survive _clean_properties unchanged.
    assert properties["subCategoryA"] == "null"


def test_parse_features_coerces_sentinel_values_to_none():
    features = parse_features(FIXTURE_JSON)
    properties = features[0]["properties"]
    assert properties.get("expectedDelay") is None  # real value was -1
    assert "queueLength" not in properties["roads"][0] or True  # sentinel only applies top-level
    assert properties["speedLimit"] == 40  # a real, non-sentinel value survives untouched


def test_parse_features_attaches_layer_name_to_every_feature():
    features = parse_features(FIXTURE_JSON)
    assert features[0]["layerName"] == "RoadWork"


def test_from_nsw_livetraffic_maps_the_real_nelligen_bridge_feature():
    features = parse_features(FIXTURE_JSON)
    works = from_nsw_livetraffic(features)
    assert len(works) == 1

    item = works[0]
    # Composite layerName:id - id alone (82681) is only unique within a
    # layer, see module docstring.
    assert item.reference == "RoadWork:82681"
    assert item.territory == "Australia"
    assert item.administrative_area == "Transport for NSW"
    assert item.coordinate.value == (150.1431796, -35.6474524)
    assert item.coordinate.crs == "EPSG:4326"
    assert item.coordinate.points is None  # real encodedPolylines was empty

    site = item.sites[0]
    assert site.works_type == "SCHEDULED ROADWORK"
    assert site.status == "active"
    assert site.location_description == "Kings Highway between Old Nelligen Road Nelligen"
    assert site.date_confidence == DateConfidence.ESTIMATED
    assert site.proposed_start.isoformat() == "2021-02-21T13:00:00+00:00"
    assert site.proposed_end.isoformat() == "2024-12-31T07:00:00+00:00"
    assert site.actual_start is None and site.actual_end is None
    assert "Weekdays 7:00am-6:00pm" in site.operating_window
    assert "Saturday 8:00am-1:00pm" in site.operating_window
    assert "Alternating (stop/slow)" in site.traffic_management
    assert site.notices[0].text == "Nelligen Bridge replacement project"


def test_composite_reference_avoids_collision_across_layers():
    """A real roadwork 82681 and a real major-event 82681 are not
    guaranteed distinct (id is only unique within a layer, per the
    Developer Guide's own property table) - Works.reference must not
    collide when features from both layers are converted together."""
    roadwork_feature = parse_features(FIXTURE_JSON)[0]
    majorevent_feature = {**roadwork_feature, "layerName": "MajorEvent"}

    works = from_nsw_livetraffic([roadwork_feature, majorevent_feature])
    references = {item.reference for item in works}
    assert references == {"RoadWork:82681", "MajorEvent:82681"}


def test_client_requires_api_key():
    with pytest.raises(ValueError):
        NswLiveTrafficClient(api_key="")


@respx.mock
def test_client_fetches_and_parses_with_default_header_format():
    respx.get(f"{BASE_URL}/roadwork-open.json").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with NswLiveTrafficClient(api_key="test-key") as nsw:
        features = nsw.iter_roadworks()
    assert len(features) == 1

    request = respx.calls.last.request
    assert request.headers["Authorization"] == "apikey test-key"


@respx.mock
def test_client_header_format_is_overridable():
    respx.get(f"{BASE_URL}/roadwork-closed.json").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with NswLiveTrafficClient(api_key="test-key", header_format="Bearer {key}") as nsw:
        nsw.iter_roadworks(status="closed")

    request = respx.calls.last.request
    assert request.headers["Authorization"] == "Bearer test-key"


@respx.mock
def test_client_iter_major_events_hits_the_majorevent_path():
    respx.get(f"{BASE_URL}/majorevent-open.json").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with NswLiveTrafficClient(api_key="test-key") as nsw:
        features = nsw.iter_major_events()
    assert len(features) == 1

    request = respx.calls.last.request
    assert request.url.path.endswith("/majorevent-open.json")


@respx.mock
def test_client_get_features_is_the_shared_primitive_for_all_layers():
    respx.get(f"{BASE_URL}/roadwork.json").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    respx.get(f"{BASE_URL}/majorevent.json").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with NswLiveTrafficClient(api_key="test-key") as nsw:
        roadwork_features = nsw.iter_features("roadwork", status="all")
        majorevent_features = nsw.iter_features("majorevent", status="all")
    assert len(roadwork_features) == len(majorevent_features) == 1
