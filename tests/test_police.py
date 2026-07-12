"""Tests for the UK Police API (data.police.uk) adapter.

Fixtures are small hand-built samples shaped after the documented responses
at https://data.police.uk/docs/ (no auth, so nothing to verify beyond shape
and query parameters).
"""

import httpx
import respx

from streetworks.police import PoliceClient

BASE = "https://data.police.uk/api"

SAMPLE_CRIME = {
    "category": "anti-social-behaviour",
    "persistent_id": "",
    "location_subtype": "",
    "id": 87878965,
    "location": {
        "latitude": "51.500617",
        "longitude": "-0.124629",
        "street": {"id": 883407, "name": "On or near Parliament Street"},
    },
    "context": "",
    "month": "2026-05",
    "location_type": "Force",
    "outcome_status": None,
}


@respx.mock
def test_street_level_crimes_sends_point_and_parses_response():
    route = respx.get(f"{BASE}/crimes-street/all-crime").mock(
        return_value=httpx.Response(200, json=[SAMPLE_CRIME])
    )
    with PoliceClient() as police:
        crimes = police.street_level_crimes(51.500617, -0.124629, date="2026-05")

    assert crimes == [SAMPLE_CRIME]
    params = route.calls.last.request.url.params
    assert params["lat"] == "51.500617"
    assert params["lng"] == "-0.124629"
    assert params["date"] == "2026-05"


@respx.mock
def test_street_level_crimes_omits_date_when_not_given():
    route = respx.get(f"{BASE}/crimes-street/burglary").mock(
        return_value=httpx.Response(200, json=[])
    )
    with PoliceClient() as police:
        police.street_level_crimes(51.5, -0.1, category="burglary")

    assert "date" not in route.calls.last.request.url.params


@respx.mock
def test_street_level_crimes_in_area_sends_poly():
    route = respx.get(f"{BASE}/crimes-street/all-crime").mock(
        return_value=httpx.Response(200, json=[SAMPLE_CRIME])
    )
    points = [(52.268, 0.543), (52.794, 0.238), (52.130, 0.478)]
    with PoliceClient() as police:
        crimes = police.street_level_crimes_in_area(points)

    assert crimes == [SAMPLE_CRIME]
    assert route.calls.last.request.url.params["poly"] == (
        "52.268,0.543:52.794,0.238:52.13,0.478"
    )


@respx.mock
def test_safety_signal_filters_to_relevant_categories():
    mixed = [
        SAMPLE_CRIME,  # anti-social-behaviour - safety-relevant
        {**SAMPLE_CRIME, "id": 2, "category": "violent-crime"},
        {**SAMPLE_CRIME, "id": 3, "category": "public-order"},
        {**SAMPLE_CRIME, "id": 4, "category": "vehicle-crime"},  # not safety-relevant
        {**SAMPLE_CRIME, "id": 5, "category": "burglary"},  # not safety-relevant
    ]
    respx.get(f"{BASE}/crimes-street/all-crime").mock(
        return_value=httpx.Response(200, json=mixed)
    )
    with PoliceClient() as police:
        signal = police.safety_signal(51.500617, -0.124629, date="2026-05")

    assert signal["date"] == "2026-05"
    assert signal["total_crimes"] == 5
    assert signal["safety_relevant_count"] == 3
    assert signal["by_category"] == {
        "anti-social-behaviour": 1,
        "violent-crime": 1,
        "public-order": 1,
    }


@respx.mock
def test_crimes_at_location_by_lat_lng():
    route = respx.get(f"{BASE}/crimes-at-location").mock(
        return_value=httpx.Response(200, json=[SAMPLE_CRIME])
    )
    with PoliceClient() as police:
        crimes = police.crimes_at_location(date="2026-05", lat=51.5, lng=-0.1)

    assert crimes == [SAMPLE_CRIME]
    params = route.calls.last.request.url.params
    assert params["date"] == "2026-05"
    assert "location_id" not in params


@respx.mock
def test_crimes_no_location_requires_category_and_force():
    route = respx.get(f"{BASE}/crimes-no-location").mock(return_value=httpx.Response(200, json=[]))
    with PoliceClient() as police:
        police.crimes_no_location(category="all-crime", force="leicestershire", date="2026-01")

    params = route.calls.last.request.url.params
    assert params["category"] == "all-crime"
    assert params["force"] == "leicestershire"
    assert params["date"] == "2026-01"


@respx.mock
def test_crime_categories():
    respx.get(f"{BASE}/crime-categories").mock(
        return_value=httpx.Response(
            200, json=[{"url": "all-crime", "name": "All crime and ASB"}]
        )
    )
    with PoliceClient() as police:
        categories = police.crime_categories(date="2026-01")

    assert categories == [{"url": "all-crime", "name": "All crime and ASB"}]


@respx.mock
def test_last_updated_extracts_date_field():
    respx.get(f"{BASE}/crime-last-updated").mock(
        return_value=httpx.Response(200, json={"date": "2026-05-01"})
    )
    with PoliceClient() as police:
        assert police.last_updated() == "2026-05-01"


@respx.mock
def test_street_level_availability():
    respx.get(f"{BASE}/crimes-street-dates").mock(
        return_value=httpx.Response(
            200, json=[{"date": "2026-05", "stop-and-search": ["leicestershire"]}]
        )
    )
    with PoliceClient() as police:
        availability = police.street_level_availability()

    assert availability[0]["date"] == "2026-05"


@respx.mock
def test_forces():
    respx.get(f"{BASE}/forces").mock(
        return_value=httpx.Response(
            200, json=[{"id": "leicestershire", "name": "Leicestershire Police"}]
        )
    )
    with PoliceClient() as police:
        forces = police.forces()

    assert forces[0]["id"] == "leicestershire"


@respx.mock
def test_locate_neighbourhood_sends_combined_q_param():
    route = respx.get(f"{BASE}/locate-neighbourhood").mock(
        return_value=httpx.Response(
            200, json={"force": "metropolitan", "neighbourhood": "E05013806N"}
        )
    )
    with PoliceClient() as police:
        result = police.locate_neighbourhood(51.500617, -0.124629)

    assert result == {"force": "metropolitan", "neighbourhood": "E05013806N"}
    assert route.calls.last.request.url.params["q"] == "51.500617,-0.124629"
