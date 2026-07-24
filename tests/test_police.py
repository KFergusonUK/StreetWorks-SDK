"""Tests for the UK Police API (data.police.uk) adapter.

Most fixtures are small hand-built samples shaped after the documented
responses at https://data.police.uk/docs/ (no auth, so nothing to verify
beyond shape and query parameters). The neighbourhood fixtures
(``police_leicestershire_*.json``) are real captured responses - saved
because the boundary endpoint's real shape (string coordinates, a closed
but non-simple ring) matters for what :meth:`PoliceClient.neighbourhood_boundary`
must do with it, and a hand-built sample would risk hiding exactly that.

The ``police_data_*`` fixtures (download form HTML, fetch-page HTML, a
small real zip) are real captures too, trimmed to a handful of genuine rows
in the zip's case - the custom CSV download's real shape (a CSRF-protected
HTML form, an async job, a small real zip) is exactly the thing worth
testing against real bytes rather than a hand-built stand-in.
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.exceptions import ServerError
from streetworks.police import PoliceClient

BASE = "https://data.police.uk/api"
DATA_BASE = "https://data.police.uk/data"
FIXTURES = Path(__file__).parent / "fixtures"
FETCH_UUID = "6d051463-2288-4672-9b37-229350f91007"


def _fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _mock_download_flow(zip_url: str, *, post_response: httpx.Response | None = None) -> None:
    """Wires up the full custom-CSV-download flow's respx mocks: GET the
    form (real HTML), POST it (302 to a real-shaped fetch URL, or a caller-
    supplied response for testing failure paths), GET the fetch page
    (follow_redirects=True means httpx issues this automatically), GET the
    progress endpoint (ready immediately), GET the zip itself."""
    respx.get(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_download_form.html"))
    )
    respx.post(f"{DATA_BASE}/").mock(
        return_value=post_response
        or httpx.Response(302, headers={"Location": f"/data/fetch/{FETCH_UUID}/"})
    )
    respx.get(f"{DATA_BASE}/fetch/{FETCH_UUID}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_fetch_page.html"))
    )
    respx.get(f"{DATA_BASE}/progress/{FETCH_UUID}/").mock(
        return_value=httpx.Response(200, json={"status": "ready", "url": zip_url})
    )
    respx.get(zip_url).mock(
        return_value=httpx.Response(200, content=_fixture_bytes("police_durham_2026-05_small.zip"))
    )

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
    # 5 decimal places (~1m precision) - see test_short_polygon_still_uses_get
    # for why: it's both plenty precise and cuts the poly string length.
    assert route.calls.last.request.url.params["poly"] == (
        "52.26800,0.54300:52.79400,0.23800:52.13000,0.47800"
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


# --------------------------------------------------------------------------- #
# Neighbourhood catalogue - real fixtures, see module docstring
# --------------------------------------------------------------------------- #


@respx.mock
def test_neighbourhoods_lists_teams_for_a_force():
    fixture = _fixture("police_leicestershire_neighbourhoods.json")
    respx.get(f"{BASE}/leicestershire/neighbourhoods").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    with PoliceClient() as police:
        teams = police.neighbourhoods("leicestershire")

    assert teams == fixture
    assert {"id": "NC04", "name": "City Centre"} in teams


@respx.mock
def test_neighbourhood_returns_real_team_details():
    fixture = _fixture("police_leicestershire_NC04.json")
    respx.get(f"{BASE}/leicestershire/NC04").mock(return_value=httpx.Response(200, json=fixture))
    with PoliceClient() as police:
        team = police.neighbourhood("leicestershire", "NC04")

    assert team["name"] == "City Centre"
    # Real API: centre is itself {"latitude": ..., "longitude": ...} as strings -
    # this method does not coerce it (unlike neighbourhood_boundary), so a
    # caller reaching into .centre gets exactly what the API stated.
    assert team["centre"] == {"latitude": "52.6389", "longitude": "-1.13619"}


@respx.mock
def test_neighbourhood_boundary_coerces_strings_to_floats():
    fixture = _fixture("police_leicestershire_NC04_boundary.json")
    respx.get(f"{BASE}/leicestershire/NC04/boundary").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    with PoliceClient() as police:
        boundary = police.neighbourhood_boundary("leicestershire", "NC04")

    assert len(boundary) == len(fixture)
    assert all(isinstance(lat, float) and isinstance(lng, float) for lat, lng in boundary)
    assert boundary[0] == (float(fixture[0]["latitude"]), float(fixture[0]["longitude"]))


@respx.mock
def test_neighbourhood_boundary_ring_is_closed():
    fixture = _fixture("police_leicestershire_NC04_boundary.json")
    respx.get(f"{BASE}/leicestershire/NC04/boundary").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    with PoliceClient() as police:
        boundary = police.neighbourhood_boundary("leicestershire", "NC04")

    assert boundary[0] == boundary[-1]


@respx.mock
def test_neighbourhood_boundary_preserves_near_duplicate_vertices_unrepaired():
    # Real NC04 ring has near-duplicate consecutive vertices (confirmed live) -
    # this method must not silently dedupe/simplify them.
    fixture = _fixture("police_leicestershire_NC04_boundary.json")
    respx.get(f"{BASE}/leicestershire/NC04/boundary").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    with PoliceClient() as police:
        boundary = police.neighbourhood_boundary("leicestershire", "NC04")

    def dist(a, b):
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

    near_duplicates = sum(
        1 for i in range(len(boundary) - 1) if dist(boundary[i], boundary[i + 1]) < 1e-6
    )
    assert near_duplicates >= 1  # real, unrepaired data - not silently cleaned up
    assert len(boundary) == len(fixture)  # nothing dropped


# --------------------------------------------------------------------------- #
# street_level_crimes_in_area - GET/POST switchover, 503, and the 10k cap
# --------------------------------------------------------------------------- #


@respx.mock
def test_short_polygon_still_uses_get():
    route = respx.get(f"{BASE}/crimes-street/all-crime").mock(
        return_value=httpx.Response(200, json=[SAMPLE_CRIME])
    )
    points = [(52.268, 0.543), (52.794, 0.238), (52.130, 0.478)]
    with PoliceClient() as police:
        crimes = police.street_level_crimes_in_area(points)

    assert crimes == [SAMPLE_CRIME]
    assert route.calls.last.request.method == "GET"
    # 5 decimal places, per the brief - not the raw float repr.
    assert route.calls.last.request.url.params["poly"] == (
        "52.26800,0.54300:52.79400,0.23800:52.13000,0.47800"
    )


@respx.mock
def test_long_polygon_switches_to_post():
    route = respx.post(f"{BASE}/crimes-street/all-crime").mock(
        return_value=httpx.Response(200, json=[SAMPLE_CRIME])
    )
    # A real rural neighbourhood ring is hundreds of vertices - synthesise
    # enough points to cross the URL-length threshold; the exact coordinates
    # don't matter for this test, only the count/length.
    points = [(52.0 + i * 0.0001, 0.5 + i * 0.0001) for i in range(200)]
    with PoliceClient() as police:
        crimes = police.street_level_crimes_in_area(points)

    assert crimes == [SAMPLE_CRIME]
    assert route.calls.last.request.method == "POST"
    sent = dict(httpx.QueryParams(route.calls.last.request.content.decode()))
    assert sent["poly"].startswith("52.00000,0.50000:")


@respx.mock
def test_503_raises_server_error_not_empty_list():
    respx.get(f"{BASE}/crimes-street/all-crime").mock(
        return_value=httpx.Response(503, text="Service Unavailable")
    )
    points = [(52.268, 0.543), (52.794, 0.238), (52.130, 0.478)]
    with PoliceClient() as police:
        with pytest.raises(ServerError, match="too complex"):
            police.street_level_crimes_in_area(points)


@respx.mock
def test_non_503_server_error_is_not_rewritten():
    respx.get(f"{BASE}/crimes-street/all-crime").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    points = [(52.268, 0.543), (52.794, 0.238), (52.130, 0.478)]
    with PoliceClient() as police:
        with pytest.raises(ServerError) as exc_info:
            police.street_level_crimes_in_area(points)
    assert "too complex" not in str(exc_info.value)


@respx.mock
def test_exactly_10000_results_warns_about_possible_truncation():
    respx.get(f"{BASE}/crimes-street/all-crime").mock(
        return_value=httpx.Response(200, json=[SAMPLE_CRIME] * 10_000)
    )
    points = [(52.268, 0.543), (52.794, 0.238), (52.130, 0.478)]
    with PoliceClient() as police:
        with pytest.warns(UserWarning, match="10,000"):
            crimes = police.street_level_crimes_in_area(points)
    assert len(crimes) == 10_000


@respx.mock
def test_fewer_than_10000_results_does_not_warn():
    respx.get(f"{BASE}/crimes-street/all-crime").mock(
        return_value=httpx.Response(200, json=[SAMPLE_CRIME])
    )
    points = [(52.268, 0.543), (52.794, 0.238), (52.130, 0.478)]
    with PoliceClient() as police:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            police.street_level_crimes_in_area(points)  # must not raise/warn


# --------------------------------------------------------------------------- #
# bulk_download_csv - the custom CSV download (CSRF form + async job), not
# a JSON endpoint like everything else tested above.
# --------------------------------------------------------------------------- #


@respx.mock
def test_bulk_download_csv_parses_a_real_zip():
    zip_url = "https://policeuk-data.s3.amazonaws.com/download/test-happy-path.zip"
    _mock_download_flow(zip_url)

    with PoliceClient() as police:
        rows = police.bulk_download_csv("durham", date_from="2026-05", date_to="2026-05")

    assert len(rows) == 15
    assert rows[0] == {
        "Crime ID": "165128013480a16b1995eb3b523eda7b92db96a67fd4c6cbc10fa3f127f301ac",
        "Month": "2026-05",
        "Reported by": "Durham Constabulary",
        "Falls within": "Durham Constabulary",
        "Longitude": "-3.363793",
        "Latitude": "54.891441",
        "Location": "On or near Dick Trod Lane",
        "LSOA code": "E01019127",
        "LSOA name": "Allerdale 001B",
        "Crime type": "Other crime",
        "Last outcome category": "Investigation complete; no suspect identified",
        "Context": "",
    }
    # Real, varied categories from the fixture - confirms the zip's multi-
    # category content survives parsing, not just row 0.
    types = {row["Crime type"] for row in rows}
    assert {"Violence and sexual offences", "Anti-social behaviour", "Burglary"} <= types


@respx.mock
def test_bulk_download_csv_sends_repeated_forces_correctly():
    zip_url = "https://policeuk-data.s3.amazonaws.com/download/test-multi-force.zip"
    respx.get(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_download_form.html"))
    )
    post_route = respx.post(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(302, headers={"Location": f"/data/fetch/{FETCH_UUID}/"})
    )
    respx.get(f"{DATA_BASE}/fetch/{FETCH_UUID}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_fetch_page.html"))
    )
    respx.get(f"{DATA_BASE}/progress/{FETCH_UUID}/").mock(
        return_value=httpx.Response(200, json={"status": "ready", "url": zip_url})
    )
    respx.get(zip_url).mock(
        return_value=httpx.Response(200, content=_fixture_bytes("police_durham_2026-05_small.zip"))
    )

    with PoliceClient() as police:
        police.bulk_download_csv(
            ["durham", "leicestershire"], date_from="2026-05", date_to="2026-05"
        )

    # httpx form-encodes list values as repeated keys - both forces must
    # appear, not just the last one silently overwriting the first.
    body = post_route.calls.last.request.content.decode()
    assert "forces=durham" in body
    assert "forces=leicestershire" in body


@respx.mock
def test_bulk_download_csv_retries_a_transient_403(monkeypatch):
    import streetworks.police.client as client_module

    monkeypatch.setattr(client_module.time, "sleep", lambda _seconds: None)

    zip_url = "https://policeuk-data.s3.amazonaws.com/download/test-retry.zip"
    get_route = respx.get(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_download_form.html"))
    )
    respx.post(f"{DATA_BASE}/").mock(
        side_effect=[
            httpx.Response(403, text="CSRF verification failed. Request aborted."),
            httpx.Response(302, headers={"Location": f"/data/fetch/{FETCH_UUID}/"}),
        ]
    )
    respx.get(f"{DATA_BASE}/fetch/{FETCH_UUID}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_fetch_page.html"))
    )
    respx.get(f"{DATA_BASE}/progress/{FETCH_UUID}/").mock(
        return_value=httpx.Response(200, json={"status": "ready", "url": zip_url})
    )
    respx.get(zip_url).mock(
        return_value=httpx.Response(200, content=_fixture_bytes("police_durham_2026-05_small.zip"))
    )

    with PoliceClient() as police:
        rows = police.bulk_download_csv("durham", date_from="2026-05", date_to="2026-05")

    assert len(rows) == 15
    # Confirmed the retry actually happened, not that the first attempt
    # secretly succeeded some other way.
    assert get_route.calls.call_count == 2  # two GETs (one per attempt)


@respx.mock
def test_bulk_download_csv_403_persists_past_retries(monkeypatch):
    import streetworks.police.client as client_module

    monkeypatch.setattr(client_module.time, "sleep", lambda _seconds: None)

    respx.get(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_download_form.html"))
    )
    respx.post(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(403, text="CSRF verification failed. Request aborted.")
    )

    with PoliceClient() as police:
        with pytest.raises(ServerError):
            police.bulk_download_csv("durham", date_from="2026-05", date_to="2026-05")


@respx.mock
def test_bulk_download_csv_missing_csrf_token_raises():
    respx.get(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(200, text="<html><body>no token here</body></html>")
    )

    with PoliceClient() as police:
        with pytest.raises(ServerError, match="CSRF token"):
            police.bulk_download_csv("durham", date_from="2026-05", date_to="2026-05")


@respx.mock
def test_bulk_download_csv_unexpected_redirect_shape_raises():
    respx.get(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_download_form.html"))
    )
    # Redirects somewhere that isn't a /data/fetch/<uuid>/ page - simulates
    # the download flow changing shape.
    respx.post(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(302, headers={"Location": "/data/"})
    )
    respx.get(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_download_form.html"))
    )

    with PoliceClient() as police:
        with pytest.raises(ServerError, match="fetch"):
            police.bulk_download_csv("durham", date_from="2026-05", date_to="2026-05")


@respx.mock
def test_bulk_download_csv_poll_timeout_raises(monkeypatch):
    import streetworks.police.client as client_module

    monkeypatch.setattr(client_module.time, "sleep", lambda _seconds: None)

    respx.get(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_download_form.html"))
    )
    respx.post(f"{DATA_BASE}/").mock(
        return_value=httpx.Response(302, headers={"Location": f"/data/fetch/{FETCH_UUID}/"})
    )
    respx.get(f"{DATA_BASE}/fetch/{FETCH_UUID}/").mock(
        return_value=httpx.Response(200, text=_fixture_text("police_data_fetch_page.html"))
    )
    # Never reports ready - the job hung, or the flow changed shape.
    respx.get(f"{DATA_BASE}/progress/{FETCH_UUID}/").mock(
        return_value=httpx.Response(200, json={"status": "pending", "url": ""})
    )

    with PoliceClient() as police:
        with pytest.raises(ServerError, match="didn't finish"):
            police.bulk_download_csv(
                "durham",
                date_from="2026-05",
                date_to="2026-05",
                poll_interval=0.01,
                poll_timeout=0.05,
            )
