"""Tests for the Queensland (QLDTraffic Events, TMR) adapter.

Credential-free (a real, globally-shared public API key) and confirmed
live 2026-08-01 - see the module docstring in ``streetworks.au.qld``.
``qld_qldtraffic_live_pull.json`` holds seven real features trimmed from a
real, unauthenticated pull (458 total events that day): six real
``Roadworks`` events covering every real geometry shape found (a typical
single-segment ``MultiLineString``, a six-segment ``MultiLineString``, a
``MultiPoint``, a ``GeometryCollection`` mixing three Points with a
LineString, a non-TMR/Guardian-sourced record, and an Asignit-sourced
record) plus the one real ``area_alert=true`` event in that pull (a
``Special event``, not Roadworks - the exclusion mechanism is generic
across every ``event_type``, see module docstring). Not synthetic.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import respx

from streetworks.au.qld import BASE_URL, PUBLIC_API_KEY, QldTrafficClient
from streetworks.common import DateConfidence, from_au_qld_qldtraffic
from streetworks.common.from_au_qld_qldtraffic import _coordinate, _geometries

LIVE_PULL_PATH = Path(__file__).parent / "fixtures" / "qld_qldtraffic_live_pull.json"
LIVE_PULL_JSON = json.loads(LIVE_PULL_PATH.read_text())
LIVE_FEATURES = LIVE_PULL_JSON["features"]

_AEST = timezone(timedelta(hours=10))


def _feature(id_: int):
    return next(f for f in LIVE_FEATURES if f["properties"]["id"] == id_)


# --------------------------------------------------------------------------- #
# Client wiring
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_filters_client_side_by_event_type():
    """No server-side event_type filter exists (confirmed from the API
    spec's own query-parameter list) - iter_roadworks() must filter the
    mixed feed itself."""
    respx.get(f"{BASE_URL}/events").mock(return_value=httpx.Response(200, json=LIVE_PULL_JSON))
    with QldTrafficClient() as qld:
        roadworks = qld.iter_roadworks()
    assert len(roadworks) == 6  # the live pull's one Special event is excluded
    assert all(f["properties"]["event_type"] == "Roadworks" for f in roadworks)


@respx.mock
def test_iter_events_with_no_filter_returns_every_type():
    respx.get(f"{BASE_URL}/events").mock(return_value=httpx.Response(200, json=LIVE_PULL_JSON))
    with QldTrafficClient() as qld:
        events = qld.iter_events()
    assert len(events) == 7


@respx.mock
def test_default_client_uses_the_real_public_api_key():
    route = respx.get(f"{BASE_URL}/events").mock(
        return_value=httpx.Response(200, json=LIVE_PULL_JSON)
    )
    with QldTrafficClient() as qld:
        qld.get_events()
    assert route.calls[0].request.url.params.get("apikey") == PUBLIC_API_KEY


@respx.mock
def test_client_accepts_a_registered_private_key_instead():
    route = respx.get(f"{BASE_URL}/events").mock(
        return_value=httpx.Response(200, json=LIVE_PULL_JSON)
    )
    with QldTrafficClient(api_key="my-registered-key") as qld:
        qld.get_events()
    assert route.calls[0].request.url.params.get("apikey") == "my-registered-key"


# --------------------------------------------------------------------------- #
# Real doc-vs-reality mismatch #1: geometry.type isn't always
# GeometryCollection - _geometries() must handle all three real shapes.
# --------------------------------------------------------------------------- #


def test_geometries_handles_bare_multilinestring():
    points, lines = _geometries(_feature(548467))
    assert points == []
    assert len(lines) == 1
    assert lines[0][0] == (-28.0589968, 152.4066739)
    assert len(lines[0]) == 100


def test_geometries_handles_bare_multilinestring_with_several_segments():
    """Real finding: a MultiLineString can carry several genuinely
    non-contiguous real segments for one event (up to 8 seen live)."""
    points, lines = _geometries(_feature(754821))
    assert points == []
    assert len(lines) == 6
    assert lines[0][0] == (-23.364429, 150.4777976)
    assert lines[3][0] == (-23.3631926, 150.4766852)


def test_geometries_handles_bare_multipoint():
    points, lines = _geometries(_feature(725992))
    assert lines == []
    assert len(points) == 1


def test_geometries_handles_genuine_geometrycollection():
    """Real, rare (0.8% of real Roadworks events) shape: several Points
    alongside a LineString in one collection."""
    points, lines = _geometries(_feature(796576))
    assert len(points) == 3
    assert points[0] == (-28.1018383, 153.109563)
    assert len(lines) == 1
    assert lines[0][0] == (-28.1052752, 153.1054761)


# --------------------------------------------------------------------------- #
# area_alert exclusion
# --------------------------------------------------------------------------- #


def test_area_alert_polygon_is_excluded_from_real_geometry():
    """The one real area_alert=true event in the pull (a Special event,
    not Roadworks - the mechanism is generic, see module docstring):
    geometries = [Point, Polygon], area_alert=true. The Polygon must not
    surface as either a point or a line."""
    feature = _feature(818007)
    assert feature["properties"]["area_alert"] is True
    points, lines = _geometries(feature)
    assert points == [(-26.6751286, 153.1141787)]
    assert lines == []


def test_area_alert_exclusion_matters_even_when_the_last_entry_would_otherwise_parse():
    """A synthetic case beyond what the one real example proves: if a
    future area_alert's own geometry were ever typed Point/LineString
    (the spec doesn't guarantee Polygon), the exclusion slice must still
    drop it - not rely on type-filtering alone to save us."""
    feature = {
        "properties": {"area_alert": True},
        "geometry": {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "LineString", "coordinates": [[153.0, -27.0], [153.1, -27.1]]},
                {"type": "Point", "coordinates": [999.0, 999.0]},  # the "alert" entry
            ],
        },
    }
    points, lines = _geometries(feature)
    assert points == []  # the bogus alert point must not leak through
    assert lines == [[(-27.0, 153.0), (-27.1, 153.1)]]


# --------------------------------------------------------------------------- #
# Coordinate - the deliberate departure from Victoria's precedent
# --------------------------------------------------------------------------- #


def test_coordinate_uses_the_line_when_no_point_exists():
    """The dominant real shape (88.5% of real Roadworks events) - carried
    through, not dropped, unlike Victoria's own LineString handling."""
    coordinate = _coordinate(_feature(548467))
    assert coordinate is not None
    assert coordinate.crs == "EPSG:7844"
    assert coordinate.value == (-28.0589968, 152.4066739)
    assert coordinate.points is not None
    assert coordinate.points[0] == coordinate.value
    assert coordinate.parts is None


def test_coordinate_uses_parts_for_several_real_non_contiguous_segments():
    coordinate = _coordinate(_feature(754821))
    assert coordinate.parts is not None
    assert len(coordinate.parts) == 6
    assert coordinate.value == coordinate.parts[0][0]
    assert coordinate.points is None


def test_coordinate_prefers_the_point_when_one_exists():
    coordinate = _coordinate(_feature(725992))
    assert coordinate.value == (-27.2739148, 153.0183826)
    assert coordinate.points is None
    assert coordinate.parts is None


def test_coordinate_uses_the_first_point_when_several_and_a_line_coexist():
    """Real, rare shape (796576): three Points plus a LineString. The
    co-present line isn't promoted onto Coordinate - see module docstring
    for why guessing which point/line relationship applies from one
    2-record sample would be worse than leaving it on .raw."""
    coordinate = _coordinate(_feature(796576))
    assert coordinate.value == (-28.1018383, 153.109563)
    assert coordinate.points is None
    assert coordinate.parts is None


def test_coordinate_is_none_when_neither_point_nor_line_present():
    feature = {"geometry": {"type": "Polygon", "coordinates": []}, "properties": {}}
    assert _coordinate(feature) is None


# --------------------------------------------------------------------------- #
# Full converter mapping
# --------------------------------------------------------------------------- #


def test_from_au_qld_qldtraffic_maps_the_real_cunningham_highway_event():
    works = from_au_qld_qldtraffic([_feature(548467)])[0]
    assert works.reference == "548467"
    assert works.territory == "Australia"
    assert works.administrative_area == "Department of Transport and Main Roads"
    assert works.promoter == "EPS"
    assert works.coordinate.crs == "EPSG:7844"

    site = works.sites[0]
    assert site.works_type == "Planned roadworks"
    assert site.status == "Published"
    assert site.date_confidence is DateConfidence.ESTIMATED
    assert site.proposed_start == datetime(2023, 4, 11, 6, 0, 0, tzinfo=_AEST)
    assert site.proposed_end == datetime(2026, 10, 30, 17, 0, 0, tzinfo=_AEST)
    assert site.actual_start is None and site.actual_end is None
    assert "Cunningham Highway" in site.location_description
    assert "Tregony" in site.location_description
    assert "Lanes affected" in site.traffic_management
    assert "Changed traffic conditions" in site.traffic_management
    assert site.operating_window == "From Monday 6 AM to Friday 6 PM"
    assert site.notices[0].raw == (
        "https://www.tmr.qld.gov.au/projects/cunningham-highway-ipswich-warwick-2020-"
        "disaster-recovery-funding-arrangements-reconstruction-works"
    )
    assert site.notices[0].text is None  # no real label field exists for this - honest, not guessed


def test_administrative_area_is_per_record_from_provided_by_not_hardcoded():
    """The real, deliberate departure from every other AU converter: TMR,
    a council, and a republishing platform's own council all get their
    own real administrative_area, not one fixed operator string."""
    works = from_au_qld_qldtraffic(
        [_feature(548467), _feature(738661), _feature(791832)]
    )
    tmr, council, ipswich = works
    assert tmr.administrative_area == "Department of Transport and Main Roads"
    assert council.administrative_area == "Somerset Regional Council"
    assert council.promoter == "Guardian"
    assert ipswich.administrative_area == "Ipswich City Council"
    assert ipswich.promoter == "Asignit"


def test_real_empty_string_delay_is_treated_as_absent_not_a_literal_value():
    """Real finding: impact.delay is sometimes a genuine empty string, not
    null (a real Guardian/Somerset Regional Council record) - must not
    render as a stray ' - ' in traffic_management."""
    site = from_au_qld_qldtraffic([_feature(738661)])[0].sites[0]
    assert site.traffic_management is not None
    assert " -  - " not in site.traffic_management
    assert "Diversions are in place" in site.traffic_management


def test_reference_is_globally_unique_not_composited():
    """Unlike NSW, id is confirmed globally unique across the whole real
    feed (every event_type, not just Roadworks) - no composite key
    needed."""
    works = from_au_qld_qldtraffic(LIVE_FEATURES)
    assert {w.reference for w in works} == {str(f["properties"]["id"]) for f in LIVE_FEATURES}


def test_works_type_reflects_the_real_event_subtype():
    works = from_au_qld_qldtraffic([_feature(818007)])[0]
    assert works.sites[0].works_type == "N/A"  # the real event_subtype for this Special event
