"""Tests for streetworks.toronto.

Fixture is real trimmed Toronto Road Restrictions/Closures data
(tests/fixtures/toronto_road_restrictions.json), captured live
2026-08-21 - covers a real record whose description contains a literal
backslash (the same real character the source's own raw JSON export
leaves un-escaped - see test_repair_json_escapes_a_real_stray_backslash
for the raw-response defect itself), a clean workEventType value, a
real garbled placeholder value (a confirmed export defect - see
streetworks.toronto.client's own module docstring), a real ROAD_CLOSED
record, and a real no-contractor record.
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.toronto import BASE_URL, TorontoClient, parse_polyline
from streetworks.toronto.client import _repair_json

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "toronto_road_restrictions.json").read_text(
        encoding="utf-8"
    )
)


def test_repair_json_escapes_a_real_stray_backslash():
    # The exact real shape found live: a stray backslash inside a quoted
    # string, not part of any valid JSON escape sequence.
    raw = '{"Closure": [{"id": "x", "description": "WATER \\ SEWER"}]}'
    repaired = _repair_json(raw)
    parsed = json.loads(repaired)
    assert parsed["Closure"][0]["description"] == "WATER \\ SEWER"


def test_repair_json_is_a_no_op_on_valid_json():
    raw = '{"Closure": [{"id": "x", "description": "fine \\\\ already escaped"}]}'
    assert json.loads(_repair_json(raw)) == json.loads(raw)


def test_parse_polyline_extracts_real_lon_lat_pairs():
    points = parse_polyline("[-79.382090,43.727320],[-79.382070,43.727240]")
    assert points == ((-79.38209, 43.72732), (-79.38207, 43.72724))


def test_parse_polyline_handles_none_and_empty():
    assert parse_polyline(None) == ()
    assert parse_polyline("") == ()


@respx.mock
def test_iter_roadworks_yields_every_real_record():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    with TorontoClient() as toronto:
        records = list(toronto.iter_roadworks())
    assert len(records) == 5


@respx.mock
def test_iter_roadworks_repairs_a_real_malformed_response_body():
    # Simulates the real live defect: valid JSON except for one stray
    # backslash - respx serves the raw malformed text directly, not
    # re-encoded through httpx.Response(json=...), which would silently
    # fix it for us before this client ever sees the real defect.
    raw_body = (
        '{"Closure": [{"id": "Tor-RD52026-4929", '
        '"description": "Toronto-TMC: WATER \\ SEWER", '
        '"latitude": "43.7", "longitude": "-79.4"}]}'
    )
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, content=raw_body.encode("utf-8"))
    )
    with TorontoClient() as toronto:
        records = list(toronto.iter_roadworks())
    assert records[0]["description"] == "Toronto-TMC: WATER \\ SEWER"
