"""Tests for the Victoria (DTP Planned Disruptions - Road) adapter.

**Pending live verification, more speculative than NSW** - see the module
docstring in ``streetworks.au.vic``. The fixture
(``vic_disruptions_planned.json``) is **synthetic**: no real Planned
Disruptions payload has ever been obtained anywhere (the OpenAPI spec's
own Swagger UI can't preview it, and the linked technical documentation
PDF is not publicly accessible - confirmed live this session, not just
unfetched). Only the endpoint, auth header behaviour, rate limit,
pagination model, and full schema shape are confirmed, all directly from
the real OpenAPI 3.0.1 spec and a live gateway probe.
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.au.vic import BASE_URL, VicDisruptionsClient, parse_features
from streetworks.common import DateConfidence, from_vic_disruptions

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vic_disruptions_planned.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())


def test_parse_features_returns_the_feature_list():
    features = parse_features(FIXTURE_JSON)
    assert len(features) == 1
    assert features[0]["properties"]["id"] == "VIC-PD-100234"


def test_from_vic_disruptions_prefers_linestring_over_point():
    features = parse_features(FIXTURE_JSON)
    works = from_vic_disruptions(features)
    assert len(works) == 1

    item = works[0]
    assert item.reference == "VIC-PD-100234"
    assert item.coordinate.value == (145.0123, -37.8123)
    assert item.coordinate.points == ((145.0123, -37.8123), (145.0156, -37.8098))
    assert item.coordinate.crs == "EPSG:4326"


def test_from_vic_disruptions_administrative_area_is_the_operator_not_the_lga():
    """A deliberate correction to the source investigation brief - see
    module docstring in streetworks.au.vic: administrative_area is data
    ownership (DTP), not geography (the LGA)."""
    features = parse_features(FIXTURE_JSON)
    item = from_vic_disruptions(features)[0]
    assert item.administrative_area == "Department of Transport and Planning"
    assert item.territory == "Australia"
    assert item.promoter == "DTP Permits Team"

    site = item.sites[0]
    assert "Whitehorse" in site.location_description  # the LGA lives here instead
    assert "Springvale Road" in site.location_description


def test_from_vic_disruptions_maps_dates_and_impact():
    features = parse_features(FIXTURE_JSON)
    site = from_vic_disruptions(features)[0].sites[0]

    assert site.works_type == "Roadworks"
    assert site.status == "Active"
    assert site.date_confidence == DateConfidence.ESTIMATED
    assert site.proposed_start.isoformat() == "2026-08-03T07:00:00+10:00"
    assert site.proposed_end.isoformat() == "2026-08-28T17:00:00+10:00"
    assert site.actual_start is None and site.actual_end is None

    # string-typed "numeric" impact fields carried through as strings, not
    # coerced - see module docstring.
    assert "15" in site.traffic_management
    assert "Lane closure" in site.traffic_management
    assert "Monday" in site.operating_window
    assert "Saturday all day" in site.operating_window


def test_client_requires_api_key():
    with pytest.raises(ValueError):
        VicDisruptionsClient(api_key="")


@respx.mock
def test_client_sends_keyid_header_not_the_openapi_advertised_scheme():
    """A live probe found the OpenAPI spec's own advertised auth scheme
    (Ocp-Apim-Subscription-Key) is wrong for the real gateway, which
    actually reads KeyID - see module docstring."""
    respx.get(f"{BASE_URL}/planned/v1/").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with VicDisruptionsClient(api_key="test-key") as vic:
        vic.get_planned_disruptions()

    request = respx.calls.last.request
    assert request.headers["KeyID"] == "test-key"
    assert "Ocp-Apim-Subscription-Key" not in request.headers
    assert request.url.params["format"] == "GeoJson"


@respx.mock
def test_client_pages_until_has_more_records_is_false():
    page_one = {
        **FIXTURE_JSON,
        "nextPageDetails": {"nextPageToken": "page-2-token", "hasMoreRecords": True},
    }
    page_two = FIXTURE_JSON  # hasMoreRecords: false

    route = respx.get(f"{BASE_URL}/planned/v1/")
    route.side_effect = [
        httpx.Response(200, json=page_one),
        httpx.Response(200, json=page_two),
    ]

    with VicDisruptionsClient(api_key="test-key") as vic:
        features = vic.iter_planned_disruptions()

    assert len(features) == 2  # one feature per page, two pages
    assert route.call_count == 2
    second_request = route.calls[1].request
    assert second_request.headers["NextPageToken"] == "page-2-token"
