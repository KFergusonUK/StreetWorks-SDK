"""Tests for streetworks.brussels - wiring only. Converter behaviour is
tested in test_common_brussels.py against the same real fixture.

Fixture is real Brussels Road Events GeoJSON (tests/fixtures/
brussels_road_events.json), captured live 2026-08-23 from the genuinely
keyless, CC0-licensed https://data-mobility.brussels/mobiris/events/
?events=all feed - see streetworks.brussels.client's own module
docstring for the full investigation. The fixture's fourth record
(id "events.SYNTHETIC-NOT-OBSERVED-LIVE") is constructed, not real -
every live record pulled was datex_codes="RWK"; it exists only to
exercise iter_roadworks()'s own filter, since a real non-RWK example
wasn't observed.
"""

from pathlib import Path

import httpx
import respx

from streetworks.brussels import BASE_URL, BrusselsClient

FIXTURE = (Path(__file__).parent / "fixtures" / "brussels_road_events.json").read_bytes()


@respx.mock
def test_iter_events_yields_every_record_unfiltered():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE))
    with BrusselsClient() as client:
        records = list(client.iter_events())
    assert len(records) == 4
    assert {r["properties"]["datex_codes"] for r in records} == {"RWK", "ACC"}


@respx.mock
def test_iter_roadworks_filters_to_rwk():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, content=FIXTURE))
    with BrusselsClient() as client:
        records = list(client.iter_roadworks())
    assert len(records) == 3
    assert all(r["properties"]["datex_codes"] == "RWK" for r in records)
    assert "events.SYNTHETIC-NOT-OBSERVED-LIVE" not in {r["id"] for r in records}
