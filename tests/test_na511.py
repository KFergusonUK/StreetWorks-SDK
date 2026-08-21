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
    ]
    assert all(j.needs_key for j in keyed)
    assert len(jurisdictions.JURISDICTIONS) == 8


def test_nevada_is_the_first_us_jurisdiction_on_this_platform():
    assert jurisdictions.NEVADA.territory == "USA"
    assert jurisdictions.NEVADA.needs_key is True
    assert jurisdictions.NEVADA.base_url == "https://www.nvroads.com"
