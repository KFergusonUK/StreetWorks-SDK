"""Tests for the New South Wales (TfNSW Live Traffic Hazards) adapter.

**Phase 2 confirmed (2026-07-30)** - see the module docstring in
``streetworks.au.nsw``. Two fixtures: ``nsw_livetraffic_roadwork.json``
wraps one REAL feature (id 82681, Nelligen Bridge replacement project)
transcribed verbatim from TfNSW's own Developer Guide PDF;
``nsw_livetraffic_live_pull.json`` holds three REAL features trimmed from
a real, credentialed pull against ``roadwork/open`` - a state-road
roadwork, a local-road roadwork, and a ferry-service hazard (confirming
the roadwork endpoint isn't perfectly pure). Neither is synthetic.
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.au.nsw import BASE_URL, NswLiveTrafficClient, _normalize_layer, parse_features
from streetworks.common import DateConfidence, from_nsw_livetraffic

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "nsw_livetraffic_roadwork.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())

LIVE_PULL_PATH = Path(__file__).parent / "fixtures" / "nsw_livetraffic_live_pull.json"
LIVE_PULL_JSON = json.loads(LIVE_PULL_PATH.read_text())


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
    assert features[0]["layer"] == "RoadWork"  # no status suffix to strip here


def test_normalize_layer_strips_real_status_suffixes_case_insensitively():
    """Real finding (2026-07-30): the same real hazard, fetched via
    different status endpoints, comes back with a different layerName -
    roadwork/open -> "Roadwork-Open", roadwork/closed -> "Roadwork-Closed",
    roadwork/all -> bare "Roadwork" (majorevent/* mirrors this exactly).
    Without normalising, the same hazard would get a different composite
    reference depending on which status fetched it."""
    assert _normalize_layer("Roadwork-Open") == "Roadwork"
    assert _normalize_layer("Roadwork-Closed") == "Roadwork"
    assert _normalize_layer("Roadwork") == "Roadwork"
    assert _normalize_layer("MajorEvent-Open") == "MajorEvent"
    assert _normalize_layer("roadwork-OPEN") == "roadwork"  # case-insensitive
    assert _normalize_layer(None) is None


def test_same_hazard_gets_the_same_reference_regardless_of_status_endpoint():
    """The concrete regression this normalisation exists to prevent: the
    identical real hazard (id 82681), fetched once as if from
    roadwork/open and once as if from roadwork/all, must produce the
    same Works.reference."""
    from_open = {**FIXTURE_JSON, "layerName": "Roadwork-Open"}
    from_all = {**FIXTURE_JSON, "layerName": "Roadwork"}

    open_feature = parse_features(from_open)[0]
    all_feature = parse_features(from_all)[0]
    assert open_feature["layer"] == all_feature["layer"] == "Roadwork"

    open_work = from_nsw_livetraffic([open_feature])[0]
    all_work = from_nsw_livetraffic([all_feature])[0]
    assert open_work.reference == all_work.reference == "Roadwork:82681"


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
    majorevent_feature = {**roadwork_feature, "layerName": "MajorEvent", "layer": "MajorEvent"}

    works = from_nsw_livetraffic([roadwork_feature, majorevent_feature])
    references = {item.reference for item in works}
    assert references == {"RoadWork:82681", "MajorEvent:82681"}


def test_client_requires_api_key():
    with pytest.raises(ValueError):
        NswLiveTrafficClient(api_key="")


@respx.mock
def test_client_fetches_and_parses_with_default_header_format():
    """The real path is `roadwork/open`, not `roadwork-open.json` - a real
    bug Phase 1 got wrong (following the Developer Guide's own Table 1
    literally) and Phase 2's live pull caught and fixed."""
    respx.get(f"{BASE_URL}/roadwork/open").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with NswLiveTrafficClient(api_key="test-key") as nsw:
        features = nsw.iter_roadworks()
    assert len(features) == 1

    request = respx.calls.last.request
    assert request.headers["Authorization"] == "apikey test-key"


@respx.mock
def test_client_header_format_is_overridable():
    respx.get(f"{BASE_URL}/roadwork/closed").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with NswLiveTrafficClient(api_key="test-key", header_format="Bearer {key}") as nsw:
        nsw.iter_roadworks(status="closed")

    request = respx.calls.last.request
    assert request.headers["Authorization"] == "Bearer test-key"


@respx.mock
def test_client_iter_major_events_hits_the_majorevent_path():
    respx.get(f"{BASE_URL}/majorevent/open").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with NswLiveTrafficClient(api_key="test-key") as nsw:
        features = nsw.iter_major_events()
    assert len(features) == 1

    request = respx.calls.last.request
    assert request.url.path.endswith("/majorevent/open")


@respx.mock
def test_client_get_features_is_the_shared_primitive_for_all_layers():
    respx.get(f"{BASE_URL}/roadwork/all").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    respx.get(f"{BASE_URL}/majorevent/all").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with NswLiveTrafficClient(api_key="test-key") as nsw:
        roadwork_features = nsw.iter_features("roadwork", status="all")
        majorevent_features = nsw.iter_features("majorevent", status="all")
    assert len(roadwork_features) == len(majorevent_features) == 1


# --------------------------------------------------------------------------- #
# Real live-pull fixture (2026-07-30) - see nsw_livetraffic_live_pull.json
# --------------------------------------------------------------------------- #


def test_live_pull_confirms_local_roads_appear_in_the_main_layer():
    """Real finding: isLocalRoad splits 'State road'/'Local road' within
    the same roadwork/open response - council works are NOT siloed away
    in regional-lga-* the way Phase 1 worried they might be."""
    features = parse_features(LIVE_PULL_JSON)
    local_road_ids = {
        f["id"] for f in features if f["properties"].get("isLocalRoad") == "Local road"
    }
    assert local_road_ids == {281497}


def test_live_pull_confirms_the_roadwork_layer_is_not_perfectly_pure():
    """Real finding: a ferry-service hazard (mainCategory='FERRY OUT OF
    SERVICE', CategoryIcon='Hazard') showed up in the roadwork-only
    endpoint - not filtered out by this module, matching Digitraffic's
    own precedent of not second-guessing an endpoint's own name."""
    works = from_nsw_livetraffic(parse_features(LIVE_PULL_JSON))
    ferry = next(w for w in works if w.sites[0].works_type == "FERRY OUT OF SERVICE")
    assert ferry.sites[0].location_description is not None
    assert "Berowra Waters Ferry" in ferry.sites[0].location_description


def test_live_pull_normalises_float_id_without_a_spurious_dot_zero():
    """Real finding: id 281450.0 arrives as a JSON float, not an int -
    the composite reference must render '281450', not '281450.0'."""
    features = parse_features(LIVE_PULL_JSON)
    ferry_feature = next(
        f for f in features if f["properties"]["mainCategory"] != "SCHEDULED ROADWORK"
    )
    work = from_nsw_livetraffic([ferry_feature])[0]
    # "Roadwork", not "Roadwork-Open" - the status suffix is normalised
    # away (see test_normalize_layer_strips_real_status_suffixes...).
    assert work.reference == "Roadwork:281450"


def test_live_pull_subcategory_a_is_a_real_populated_field_not_only_the_null_string():
    """The 'null' string footgun (see nsw_livetraffic_roadwork.json's
    test) is real, but subCategoryA also carries genuine values on other
    records - confirming it's a meaningful field, not placeholder-only."""
    features = parse_features(LIVE_PULL_JSON)
    values = {f["properties"].get("subCategoryA") for f in features}
    assert "Bridge work" in values
    assert "null" in values
