"""Tests for the Autobahn GmbH (Germany, national motorways) adapter.

Fixtures are real trimmed responses from a live 113-road fetch, 2026-07:
``autobahn_roads.json`` (the full real road list - carries both real road
list traps: ``"A60 "``, a genuinely separate always-empty duplicate of
``"A60"``, and the lowercase suffixes ``A64a``/``A99a``),
``autobahn_a1_roadworks.json`` (a long-term ``ROADWORKS`` item with real
``LineString`` geometry, one real example of each of the three
short-term date shapes this adapter parses, one genuinely unparseable
short-term item, and three of the five real records sharing works
``2023-000045``), and ``autobahn_a61_roadworks.json`` (the other two
records of that same works - a real junction project that Autobahn GmbH's
own API splits across the two connecting roads' responses).
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.autobahn import DISPLAY_TYPES, AutobahnClient, parse_roadworks

FIXTURES = Path(__file__).parent / "fixtures"
A1_PAYLOAD = json.loads((FIXTURES / "autobahn_a1_roadworks.json").read_text())
A61_PAYLOAD = json.loads((FIXTURES / "autobahn_a61_roadworks.json").read_text())
A12_PAYLOAD = json.loads((FIXTURES / "autobahn_a12_roadworks.json").read_text())
ROADS_PAYLOAD = json.loads((FIXTURES / "autobahn_roads.json").read_text())


def test_road_list_carries_the_real_traps():
    roads = ROADS_PAYLOAD["roads"]
    assert len(roads) == 113
    assert "A60" in roads
    assert "A60 " in roads  # a genuinely separate entry, not just A60 with noise
    assert "A64a" in roads and "A99a" in roads  # lowercase suffixes


def test_roadworks_long_term_fields():
    items = parse_roadworks(A1_PAYLOAD, "A1")
    item = next(i for i in items if i.identifier.endswith("_003.de1"))
    assert item.display_type == "ROADWORKS"
    assert item.is_start_verified is True  # from the real startTimestamp field
    assert str(item.start) == "2026-05-04 00:00:00+02:00"
    # "Ende:" text - no end-date field exists anywhere in the API, verified or not
    assert str(item.end) == "2026-08-31 00:00:00+02:00"
    assert str(item.overall_end) == "2026-08-31 00:00:00+02:00"
    assert item.is_blocked is False  # the string "false", not a bool, parsed
    assert item.road == "A1"
    # Real LineString, not a single point - the whole line survives.
    assert len(item.points) > 2
    assert item.points[0] != item.coordinate  # native axis order differs (lon,lat) vs (lat,long)
    assert item.coordinate == (49.346849707777814, 7.0145271289960665)


def test_short_term_has_no_start_timestamp_field_and_no_overall_end():
    items = parse_roadworks(A1_PAYLOAD, "A1")
    item = next(i for i in items if i.identifier.endswith("_06-00-00-000.de3"))
    assert item.display_type == "SHORT_TERM_ROADWORKS"
    assert item.is_start_verified is False
    assert item.overall_end is None
    assert str(item.start) == "2026-07-26 06:00:00+02:00"
    assert str(item.end) == "2026-07-26 12:00:00+02:00"


def test_short_term_overnight_bis_zum_shape():
    items = parse_roadworks(A1_PAYLOAD, "A1")
    item = next(i for i in items if "19-00-00-000_002" in i.identifier)
    # First matching line wins: 22.07.26 20:00 -> 23.07.26 05:00 (a second
    # overnight line for the following night is present too - not parsed,
    # per "first match wins", which is fine - it's the same works, and the
    # true multi-night pattern is preserved verbatim in .raw either way).
    assert str(item.start) == "2026-07-22 20:00:00+02:00"
    assert str(item.end) == "2026-07-23 05:00:00+02:00"


def test_short_term_recurring_jeden_zwischen_shape():
    items = parse_roadworks(A1_PAYLOAD, "A1")
    item = next(i for i in items if "07-21_09-00-00-000_003" in i.identifier)
    # Outer bounding window only - the weekday-recurrence detail (Tue/Wed/Thu)
    # is lost, same trade-off DATEX's Validity makes for multi-period validity.
    assert str(item.start) == "2026-07-21 09:00:00+02:00"
    assert str(item.end) == "2026-07-23 15:00:00+02:00"


def test_genuinely_unparseable_date_text_left_unset():
    items = parse_roadworks(A1_PAYLOAD, "A1")
    item = next(i for i in items if i.identifier.endswith("_001.de3"))
    assert item.start is None
    assert item.end is None
    # Never dropped - the raw text and full item both survive.
    assert any("gültig" in line for line in item.description)
    assert item.raw["identifier"] == item.identifier


def test_dst_offset_is_not_hardcoded():
    # Same record, two different real offsets: May (+02:00) vs. a real
    # +01:00 seen on the A12 fixture's November end - confirms DST is read
    # from zoneinfo, not assumed fixed.
    items = parse_roadworks(A12_PAYLOAD, "A12")
    item = items[0]
    assert str(item.start.utcoffset()) == "2:00:00"  # May
    assert str(item.end.utcoffset()) == "1:00:00"  # November


def test_cross_road_works_share_an_identifier_prefix():
    a1_items = parse_roadworks(A1_PAYLOAD, "A1")
    a61_items = parse_roadworks(A61_PAYLOAD, "A61")
    a1_group = [i for i in a1_items if i.identifier_prefix == "2023-000045"]
    a61_group = [i for i in a61_items if i.identifier_prefix == "2023-000045"]
    assert len(a1_group) == 3
    assert len(a61_group) == 2
    # All five agree on the works-level end date despite being split across
    # two roads' API responses - confirmed live across 599 real groups.
    ends = {i.overall_end for i in a1_group + a61_group}
    assert len(ends) == 1


def test_null_entries_in_impact_symbols_are_filtered():
    items = parse_roadworks(A12_PAYLOAD, "A12")
    assert None not in items[0].impact_symbols
    assert all(isinstance(s, str) for s in items[0].impact_symbols)


@respx.mock
def test_client_list_roads():
    respx.get("https://verkehr.autobahn.de/o/autobahn/").mock(
        return_value=httpx.Response(200, json=ROADS_PAYLOAD)
    )
    with AutobahnClient() as client:
        roads = client.list_roads()
    assert len(roads) == 113
    assert "A60 " in roads


@respx.mock
def test_client_roadworks_encodes_trailing_space_road_id():
    respx.get("https://verkehr.autobahn.de/o/autobahn/A60%20/services/roadworks").mock(
        return_value=httpx.Response(200, json={"roadworks": []})
    )
    with AutobahnClient() as client:
        result = client.roadworks("A60 ")
    assert result == []


@respx.mock
def test_client_iter_all_roadworks_across_explicit_roads():
    respx.get("https://verkehr.autobahn.de/o/autobahn/A1/services/roadworks").mock(
        return_value=httpx.Response(200, json=A1_PAYLOAD)
    )
    respx.get("https://verkehr.autobahn.de/o/autobahn/A61/services/roadworks").mock(
        return_value=httpx.Response(200, json=A61_PAYLOAD)
    )
    with AutobahnClient() as client:
        items = list(client.iter_all_roadworks(["A1", "A61"]))
    assert len(items) == 10
    assert {i.road for i in items} == {"A1", "A61"}


def test_display_types_constant():
    items = parse_roadworks(A1_PAYLOAD, "A1")
    assert {i.display_type for i in items} <= DISPLAY_TYPES
