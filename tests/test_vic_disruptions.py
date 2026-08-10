"""Tests for the Victoria (DTP Planned Disruptions - Road) adapter.

**Phase 2 confirmed (2026-07-30)** - see the module docstring in
``streetworks.au.vic``. The fixture (``vic_disruptions_planned.json``) is
**real**, trimmed from a real, credentialed pull (a tester ran
``scripts/smoke_test.py`` with their own subscription key) - the
LineString geometry is trimmed to 16 of its original 2000+ real vertices
to keep the fixture a reasonable size, but every kept vertex is real,
unedited. No longer synthetic, unlike this module's first-version
fixture.
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
    assert features[0]["properties"]["id"] == "Planned:OneView:IMP-0119747"


def test_from_vic_disruptions_prefers_point_over_linestring():
    """A real design correction: a GeometryCollection's LineString can
    span an entire route (~150km here, matching srns='M31,B400') rather
    than the disruption's own precise extent - the Point is the real
    disruption site, so it's preferred, and the LineString is never
    promoted to Coordinate.points. See module docstring in
    streetworks.au.vic ('A real design mistake this confirmed')."""
    features = parse_features(FIXTURE_JSON)
    works = from_vic_disruptions(features)
    assert len(works) == 1

    item = works[0]
    assert item.reference == "Planned:OneView:IMP-0119747"
    assert item.coordinate.value == (-36.700197, 145.653193)
    assert item.coordinate.crs == "EPSG:4326"
    assert item.coordinate.points is None  # LineString deliberately not used


def test_from_vic_disruptions_administrative_area_is_the_operator_not_the_lga():
    """A deliberate correction to the source investigation brief - see
    module docstring in streetworks.au.vic: administrative_area is data
    ownership (DTP), not geography (the LGA)."""
    features = parse_features(FIXTURE_JSON)
    item = from_vic_disruptions(features)[0]
    assert item.administrative_area == "Department of Transport and Planning"
    assert item.territory == "Australia"
    assert item.promoter == "OneView"  # real source.sourceName

    site = item.sites[0]
    assert "MITCHELL" in site.location_description  # the LGA lives here instead
    assert "METROPOLITAN RING" in site.location_description
    # endIntersection* - not in the OpenAPI spec's own schema, discovered
    # only in a real response, and confirmed common (92% of one real pull).
    assert "HARRIS ROAD" in site.location_description
    assert "GATEWAY ISLAND" in site.location_description


def test_from_vic_disruptions_maps_dates_and_impact():
    features = parse_features(FIXTURE_JSON)
    site = from_vic_disruptions(features)[0].sites[0]

    assert site.works_type == "Roadworks"
    assert site.status == "Pending"
    assert site.date_confidence == DateConfidence.ESTIMATED
    # Real duration.start/end are naive ISO-8601 - no UTC offset at all,
    # confirmed live (genuinely unusual - see module docstring). The
    # resulting datetime is timezone-naive, not assumed UTC/AEST.
    assert site.proposed_start.isoformat() == "2024-02-01T00:00:00"
    assert site.proposed_end.isoformat() == "2025-06-30T00:00:00"
    assert site.proposed_start.tzinfo is None
    assert site.actual_start is None and site.actual_end is None

    # string-typed "numeric" impact fields carried through as strings, not
    # coerced - confirmed correct by real data (delay is a real range, not
    # a bare number).
    assert "0 to 5 min" in site.traffic_management
    assert "Lanes blocked" in site.traffic_management
    # recurrences[].duration is a real ISO-8601 duration string (PT6H),
    # not free text - carried through as-is.
    assert "Monday 09:30 PT6H" in site.operating_window
    assert "Friday 09:30 PT6H" in site.operating_window


def test_client_requires_api_key():
    with pytest.raises(ValueError):
        VicDisruptionsClient(api_key="")


@respx.mock
def test_client_sends_keyid_header_not_the_openapi_advertised_scheme():
    """A live probe found the OpenAPI spec's own advertised auth scheme
    (Ocp-Apim-Subscription-Key) is wrong for the real gateway, which
    actually reads KeyID - confirmed twice now: once by the WWW-Authenticate
    probe, once by a real key succeeding via this exact header. See module
    docstring."""
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
