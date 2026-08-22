"""Tests for streetworks.na511 - wiring only. Converter behaviour is
tested in test_common_na511.py against the same real fixture.

Fixture is real Ontario 511 event data (tests/fixtures/na511_ontario_events.json),
captured live 2026-08-21 from the genuinely keyless
https://511on.ca/api/v2/get/event endpoint - see streetworks.na511.client's
module docstring for the full investigation, including why Alberta/
Saskatchewan (the same platform, key-gated) are trusted to parse
identically.
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.na511 import EVENT_PATH, NA511Client, jurisdictions

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "na511_ontario_events.json").read_text(
        encoding="utf-8"
    )
)
ALBERTA_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "na511_alberta_events.json").read_text(
        encoding="utf-8"
    )
)
NEVADA_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "na511_nevada_events.json").read_text(
        encoding="utf-8"
    )
)
ALASKA_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "na511_alaska_events.json").read_text(
        encoding="utf-8"
    )
)


@respx.mock
def test_iter_events_yields_every_real_event_keyless():
    respx.get(f"{jurisdictions.ONTARIO.base_url}/{EVENT_PATH}").mock(
        return_value=httpx.Response(200, json=FIXTURE)
    )
    with NA511Client() as client:
        events = list(client.iter_events("ontario"))
    assert len(events) == 5
    assert events[0]["ID"] == 225175


@respx.mock
def test_iter_roadworks_filters_to_the_real_event_type():
    respx.get(f"{jurisdictions.ONTARIO.base_url}/{EVENT_PATH}").mock(
        return_value=httpx.Response(200, json=FIXTURE)
    )
    with NA511Client() as client:
        roadworks = list(client.iter_roadworks("ontario"))
    assert len(roadworks) == 4
    assert all(e["EventType"] == "roadwork" for e in roadworks)


@respx.mock
def test_no_key_sent_when_none_supplied():
    route = respx.get(f"{jurisdictions.ONTARIO.base_url}/{EVENT_PATH}").mock(
        return_value=httpx.Response(200, json=[])
    )
    with NA511Client() as client:
        list(client.iter_events("ontario"))
    assert "key" not in route.calls.last.request.url.params


@respx.mock
def test_key_sent_when_supplied_for_a_gated_jurisdiction():
    route = respx.get(f"{jurisdictions.ALBERTA.base_url}/{EVENT_PATH}").mock(
        return_value=httpx.Response(200, json=[])
    )
    with NA511Client(api_key="secret") as client:
        list(client.iter_events("alberta"))
    assert route.calls.last.request.url.params["key"] == "secret"


@respx.mock
def test_fetch_returns_a_plain_list_of_roadworks():
    respx.get(f"{jurisdictions.ONTARIO.base_url}/{EVENT_PATH}").mock(
        return_value=httpx.Response(200, json=FIXTURE)
    )
    with NA511Client() as client:
        roadworks = client.fetch("ontario")
    assert isinstance(roadworks, list)
    assert len(roadworks) == 4


def test_ontario_is_the_only_keyless_jurisdiction():
    assert jurisdictions.ONTARIO.needs_key is False
    keyed = [
        jurisdictions.ALBERTA,
        jurisdictions.SASKATCHEWAN,
        jurisdictions.NEW_BRUNSWICK,
        jurisdictions.NEWFOUNDLAND_AND_LABRADOR,
        jurisdictions.NOVA_SCOTIA,
        jurisdictions.YUKON,
        jurisdictions.NEVADA,
        jurisdictions.GEORGIA,
        jurisdictions.ALASKA,
        jurisdictions.LOUISIANA,
    ]
    assert all(j.needs_key for j in keyed)
    assert len(jurisdictions.JURISDICTIONS) == 11


def test_nevada_is_the_first_us_jurisdiction_on_this_platform():
    assert jurisdictions.NEVADA.territory == "USA"
    assert jurisdictions.NEVADA.needs_key is True
    assert jurisdictions.NEVADA.base_url == "https://www.nvroads.com"


def test_georgia_is_a_second_us_jurisdiction_on_this_platform():
    assert jurisdictions.GEORGIA.territory == "USA"
    assert jurisdictions.GEORGIA.needs_key is True
    assert jurisdictions.GEORGIA.base_url == "https://511ga.org"


def test_alaska_is_a_third_us_jurisdiction_on_this_platform():
    assert jurisdictions.ALASKA.territory == "USA"
    assert jurisdictions.ALASKA.needs_key is True
    assert jurisdictions.ALASKA.base_url == "https://511.alaska.gov"


def test_louisiana_is_a_fourth_us_jurisdiction_on_this_platform():
    assert jurisdictions.LOUISIANA.territory == "USA"
    assert jurisdictions.LOUISIANA.needs_key is True
    assert jurisdictions.LOUISIANA.base_url == "https://www.511la.org"


@respx.mock
def test_alberta_authenticated_response_parses_identically_to_ontario():
    """Real, trimmed Alberta 511 events (tests/fixtures/na511_alberta_events.json),
    captured live 2026-08-22 from a real authenticated pull against
    https://511.alberta.ca/api/v2/get/event - the first key-gated
    jurisdiction on this platform confirmed to round-trip through the
    exact same parsing Ontario's own keyless response already proved.
    Also the real source of the EventType enum correction documented in
    streetworks.na511.client's own module docstring: this fixture
    includes a real "closures" event (Alberta's own real population has
    EventType values Ontario's sample never showed)."""
    respx.get(f"{jurisdictions.ALBERTA.base_url}/{EVENT_PATH}").mock(
        return_value=httpx.Response(200, json=ALBERTA_FIXTURE)
    )
    with NA511Client(api_key="real-key") as client:
        roadworks = list(client.iter_roadworks("alberta"))
    assert len(roadworks) == 2
    assert {e["ID"] for e in roadworks} == {18, 30}
    assert all(e["EventType"] == "roadwork" for e in roadworks)


@respx.mock
def test_nevada_authenticated_response_parses_identically_to_ontario():
    """Real, trimmed Nevada 511 events (tests/fixtures/na511_nevada_events.json),
    captured live 2026-08-22 from a real authenticated pull against
    https://www.nvroads.com/api/v2/get/event - the second key-gated
    jurisdiction on this platform confirmed with a real key, same day as
    Alberta. Also a real cross-check that Alberta's own EventType/field-set
    findings aren't one-jurisdiction flukes: this fixture's own non-roadwork
    record is "accidentsAndIncidents", not one of Alberta's extra values -
    genuine per-jurisdiction variation, not a contradiction."""
    respx.get(f"{jurisdictions.NEVADA.base_url}/{EVENT_PATH}").mock(
        return_value=httpx.Response(200, json=NEVADA_FIXTURE)
    )
    with NA511Client(api_key="real-key") as client:
        roadworks = list(client.iter_roadworks("nevada"))
    assert len(roadworks) == 2
    assert {e["ID"] for e in roadworks} == {125464, 75}
    assert all(e["EventType"] == "roadwork" for e in roadworks)


@respx.mock
def test_alaska_authenticated_response_parses_identically_to_ontario():
    """Real, trimmed Alaska 511 events (tests/fixtures/na511_alaska_events.json),
    captured live 2026-08-22 from a real authenticated pull against
    https://511.alaska.gov/api/v2/get/event - the third key-gated
    jurisdiction on this platform confirmed with a real key. Also the
    real source of two genuine converter bugs found and fixed the same
    day: a .NET DateTime.MinValue placeholder on StartDate/Reported
    (47/57 real Alaska events, the majority shape) and a real "Null
    Island" (0.0, 0.0) placeholder coordinate with no polyline fallback -
    see streetworks.common.from_na511's own module docstring."""
    respx.get(f"{jurisdictions.ALASKA.base_url}/{EVENT_PATH}").mock(
        return_value=httpx.Response(200, json=ALASKA_FIXTURE)
    )
    with NA511Client(api_key="real-key") as client:
        roadworks = list(client.iter_roadworks("alaska"))
    assert len(roadworks) == 2
    assert {e["ID"] for e in roadworks} == {32138, 36958}
    assert all(e["EventType"] == "roadwork" for e in roadworks)
