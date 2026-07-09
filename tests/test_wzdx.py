"""Tests for the WZDx parser and client.

Fixtures are real feed excerpts (lightly trimmed - a couple of features
each), captured live 2026-07-09 from four agencies chosen to cover the
real cross-agency variation found before writing the parser: Hawaii DOT
(v4.1, LineString, boolean date-verified flags only), Ville de Québec
(v3.1, flat properties with no core_details wrapper, accuracy-enum dates,
relationship.parents linking a work-zone to a companion detour, French
description), Washington State DOT (v4.2, both feed_info key names at
once, both date-confidence encodings simultaneously, a verified-looking
placeholder end_date of 2028-12-30, and a 7-digit fractional-second
timestamp that breaks naive datetime.fromisoformat on Python < 3.11),
and NY511/TRANSCOM via Arcadis (v4.1, MultiPoint geometry,
core_details.related_road_events).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import respx

from streetworks.wzdx import WZDxClient
from streetworks.wzdx.parser import parse_road_events


def _fixture(name: str) -> dict:
    return json.loads(
        (Path(__file__).parent / "fixtures" / f"wzdx_{name}.json").read_text(encoding="utf-8")
    )


def test_hidot_v41_linestring_boolean_flags_only():
    events = parse_road_events(_fixture("hidot"))
    assert len(events) == 2
    e = events[0]
    assert e.event_type == "work-zone"
    assert e.is_work_zone is True
    assert e.geometry.kind == "LineString"
    assert e.geometry.point is not None
    # Native GeoJSON order: (longitude, latitude), not (latitude, longitude).
    lon, lat = e.geometry.point
    assert -160 < lon < -155  # Hawaii is west, small negative longitude
    assert 18 < lat < 23  # Hawaii is around 20N
    assert e.is_start_date_verified is False
    assert e.start_date_accuracy is None  # this feed only has the boolean flags
    assert e.start_date == datetime(2025, 11, 3, 23, 37, 22, 671000, tzinfo=timezone.utc)


def test_quebec_v31_flat_properties_accuracy_enums_and_relationship():
    events = parse_road_events(_fixture("quebec"))
    assert len(events) == 3
    work_zone = next(e for e in events if e.id == "ACL-20260708-DK-02-P1_1")
    assert work_zone.event_type == "work-zone"
    assert work_zone.start_date_accuracy == "estimated"
    assert work_zone.is_start_date_verified is None  # v3.1 feed has no boolean flags
    assert work_zone.relationship.parents == ("ACL-20260708-DK-02-WZP",)
    assert work_zone.road_names == ("Rue Gérard-Morisset",)  # French road name preserved
    # French description prose embeds a schedule - preserved as-is, never
    # parsed for dates (start/end_date are the real, structured fields).
    assert "travaux" in work_zone.description

    detour = next(e for e in events if e.event_type == "detour")
    assert detour.is_work_zone is False
    assert detour.relationship.parents

    plain = next(e for e in events if e.id == "20260423003-1")
    assert plain.relationship.parents == ()


def test_wsdot_v42_dual_feed_info_dual_encoding_and_placeholder_date():
    payload = _fixture("wsdot")
    assert "feed_info" in payload and "road_event_feed_info" in payload  # both present live
    events = parse_road_events(payload)
    placeholder = next(e for e in events if e.id == "40615-W")
    # A verified-looking placeholder: both encodings say "verified"/True, but
    # the end_date is a bare 2028-12-30 - exactly the data-quality trap the
    # design notes warned about.
    assert placeholder.start_date_accuracy == "verified"
    assert placeholder.is_start_date_verified is True
    assert placeholder.end_date == datetime(2028, 12, 30, tzinfo=timezone.utc)
    # 7-digit fractional seconds (would break datetime.fromisoformat on
    # Python < 3.11 without the shared streetworks._dt fix).
    assert placeholder.creation_date == datetime(
        2024, 5, 31, 21, 29, 32, 330869, tzinfo=timezone.utc
    )


def test_nysdot_transcom_v41_multipoint_and_related_road_events():
    events = parse_road_events(_fixture("nysdot"))
    with_related = next(e for e in events if e.related_road_events)
    assert with_related.geometry.kind == "MultiPoint"
    assert with_related.related_road_events == (
        {"type": "next-occurrence", "id": "8zRP1Tj5ZTchlsL+ihOhwHzBmbY="},
    )
    assert with_related.road_names == ("I-84",)


def test_parser_never_raises_on_garbage():
    garbage_payload = {
        "features": [
            {"properties": None, "geometry": None},
            {"properties": {"event_type": "work-zone"}, "geometry": {"type": "Polygon"}},
            {"properties": {"start_date": "not-a-date"}},
            "not-even-a-dict",
            {},
        ]
    }
    events = parse_road_events(garbage_payload)
    assert len(events) == 4  # the bare string is skipped, not crashed on
    assert all(e.start_date is None or isinstance(e.start_date, datetime) for e in events)


@respx.mock
def test_client_fetches_and_reports_feed_version():
    respx.get("https://example.test/wzdx").mock(
        return_value=httpx.Response(200, json=_fixture("wsdot"))
    )
    with WZDxClient() as client:
        feed = client.fetch("https://example.test/wzdx")

    assert feed.version == "4.2"
    assert feed.publisher == "Washington State DOT IT"
    assert len(feed.road_events) == 2
