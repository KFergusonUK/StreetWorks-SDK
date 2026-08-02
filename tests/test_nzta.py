"""Tests for the New Zealand (NZTA Highway Information) adapter.

Credential-free, live-verified from day one - see the module docstring in
``streetworks.nzta.client``. ``nzta_road_events_live_pull.json`` holds
five REAL features trimmed from a real, unauthenticated pull (2026-08-02):
a Scheduled/Road Closed record, an Active record, a Resolved record, and
two more Scheduled records with varied ``eventDescription`` - not
synthetic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import respx

from streetworks.common import DateConfidence, from_nzta
from streetworks.nzta import BASE_URL, ROAD_EVENTS_LAYER, NztaClient

LIVE_PULL_PATH = Path(__file__).parent / "fixtures" / "nzta_road_events_live_pull.json"
LIVE_PULL_JSON = json.loads(LIVE_PULL_PATH.read_text())
LIVE_FEATURES = LIVE_PULL_JSON["features"]


def _layer_info():
    return {
        "objectIdField": "OBJECTID",
        "maxRecordCount": 2000,
        "advancedQueryCapabilities": {"supportsPagination": True},
        "fields": [{"name": "OBJECTID"}],
    }


# --------------------------------------------------------------------------- #
# Client wiring
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_filters_to_the_confirmed_real_event_types():
    respx.get(f"{BASE_URL}/{ROAD_EVENTS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{ROAD_EVENTS_LAYER}/query").mock(
        return_value=httpx.Response(200, json=LIVE_PULL_JSON)
    )
    with NztaClient() as nzta:
        features = list(nzta.iter_roadworks())
    assert len(features) == 5
    assert query_route.calls[0].request.url.params.get("where") == (
        "eventType IN ('Road Work', 'Scheduled Road Work')"
    )


@respx.mock
def test_iter_road_events_defaults_to_every_event_type():
    respx.get(f"{BASE_URL}/{ROAD_EVENTS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{ROAD_EVENTS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with NztaClient() as nzta:
        list(nzta.iter_road_events())
    assert query_route.calls[0].request.url.params.get("where") == "1=1"


@respx.mock
def test_iter_roadworks_requests_outsr_4326():
    respx.get(f"{BASE_URL}/{ROAD_EVENTS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{ROAD_EVENTS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with NztaClient() as nzta:
        list(nzta.iter_roadworks())
    assert query_route.calls[0].request.url.params.get("outSR") == "4326"


def test_client_requires_no_credentials():
    NztaClient()


# --------------------------------------------------------------------------- #
# Converter - the real status/planned signal, and the sentinel handling
# --------------------------------------------------------------------------- #


def test_from_nzta_maps_the_real_scheduled_gillies_avenue_feature():
    works = from_nzta(LIVE_FEATURES)
    assert len(works) == 5

    gillies = next(w for w in works if w.reference == "556827")
    assert gillies.territory == "New Zealand"
    assert gillies.administrative_area == "Waka Kotahi NZ Transport Agency"
    assert gillies.coordinate.value == (174.773985779427, -36.8728584510707)
    assert gillies.coordinate.crs == "EPSG:4326"

    site = gillies.sites[0]
    assert site.works_type == "Maintenance"
    assert site.status == "Scheduled"
    assert site.location_description == "SH 1 Gillies Avenue southbound Off-Ramp"
    assert site.proposed_start == datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)
    assert site.proposed_end == datetime(2026, 8, 2, 17, 0, tzinfo=timezone.utc)
    # Scheduled -> ESTIMATED, never VERIFIED, and no actual_start inferred.
    assert site.date_confidence is DateConfidence.ESTIMATED
    assert site.actual_start is None
    # A real, non-sentinel alternativeRoute must be surfaced.
    assert "Alternative route: Follow posted detour" in site.traffic_management


def test_active_status_promotes_to_verified_with_actual_start():
    works = from_nzta(LIVE_FEATURES)
    active = next(w for w in works if w.reference == "526478")
    site = active.sites[0]
    assert site.status == "Active"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert site.actual_start == site.proposed_start
    assert site.actual_end is None  # never inferred, even when verified


def test_resolved_status_is_also_verified():
    """A completed roadwork's dates are real, not just planned - the same
    'suspended still counts as VERIFIED' precedent DATEX's own
    validityStatus handling uses."""
    works = from_nzta(LIVE_FEATURES)
    resolved = next(w for w in works if w.reference == "552234")
    assert resolved.sites[0].status == "Resolved"
    assert resolved.sites[0].date_confidence is DateConfidence.VERIFIED


def test_not_applicable_alternative_route_is_excluded_not_surfaced():
    """The real, confirmed-live sentinel - carrying it through as if it
    were a genuine routing instruction would be misleading."""
    works = from_nzta(LIVE_FEATURES)
    active = next(w for w in works if w.reference == "526478")
    assert active.sites[0].raw["properties"]["alternativeRoute"] == "Not Applicable"
    assert "Alternative route" not in active.sites[0].traffic_management


def test_street_ref_is_never_populated():
    """No structured road identifier is stated anywhere in this feed - see
    streetworks.nzta.client's module docstring for why this settles the
    NZ cluster's works-to-LINZ join question."""
    works = from_nzta(LIVE_FEATURES)
    assert all(w.sites[0].street_ref is None for w in works)
