"""Tests for the Tasmania (Department of State Growth, Roadworks - State
Roads) adapter.

Credential-free, live-verified from day one, licence genuinely unconfirmed
- see the module docstring in ``streetworks.au.tas``.
``tas_roadworks_live_pull.json`` holds four REAL features trimmed from a
real, unauthenticated pull (2026-08-01, out of a real total of only 10) -
not synthetic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import respx

from streetworks.au.tas import BASE_URL, ROADWORKS_LAYER, TasRoadworksClient
from streetworks.common import DateConfidence, from_au_tas_roadworks

LIVE_PULL_PATH = Path(__file__).parent / "fixtures" / "tas_roadworks_live_pull.json"
LIVE_PULL_JSON = json.loads(LIVE_PULL_PATH.read_text())
LIVE_FEATURES = LIVE_PULL_JSON["features"]


def _layer_info():
    return {
        "objectIdField": "ID",
        "maxRecordCount": 2000,
        "advancedQueryCapabilities": {"supportsPagination": True},
        "fields": [{"name": "ID"}],
    }


# --------------------------------------------------------------------------- #
# Client wiring
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_queries_the_real_layer():
    respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}/query").mock(
        return_value=httpx.Response(200, json=LIVE_PULL_JSON)
    )
    with TasRoadworksClient() as tas:
        features = list(tas.iter_roadworks())
    assert len(features) == 4
    assert features[0]["properties"]["EVENT_TYPE"] == "Roadworks"


@respx.mock
def test_iter_roadworks_requests_outsr_4326():
    respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with TasRoadworksClient() as tas:
        list(tas.iter_roadworks())
    assert query_route.calls[0].request.url.params.get("outSR") == "4326"


def test_client_requires_no_credentials():
    TasRoadworksClient()


# --------------------------------------------------------------------------- #
# Converter - real line geometry, no reprojection fallback
# --------------------------------------------------------------------------- #


def test_from_au_tas_roadworks_maps_a_real_line_feature():
    works = from_au_tas_roadworks(LIVE_FEATURES)
    assert len(works) == 4

    leven = next(w for w in works if w.reference == "6177")
    assert leven.territory == "Australia"
    assert leven.administrative_area == "Department of State Growth"
    assert leven.coordinate.crs == "EPSG:4326"
    # Real line geometry - the whole thing is kept, not just the first vertex.
    assert leven.coordinate.points is not None
    assert len(leven.coordinate.points) == 5
    assert leven.coordinate.value == leven.coordinate.points[0]
    assert leven.coordinate.value == (146.15240038993386, -41.16203027859827)

    site = leven.sites[0]
    assert site.works_type == "Roadworks"
    assert site.location_description == "Bass Highway, Leven River Bridge Devonport Bound"
    assert site.proposed_start == datetime(2026, 3, 10, 11, 0, tzinfo=timezone.utc)
    assert site.proposed_end == datetime(2026, 9, 16, 10, 0, tzinfo=timezone.utc)
    assert site.date_confidence is DateConfidence.ESTIMATED


def test_site_contact_and_phone_fold_into_traffic_management():
    """SITE_CONTACT/SITE_CONTACT_PHONE have no canonical model field of
    their own - confirmed real, always-populated fields, appended rather
    than dropped, see module docstring."""
    works = from_au_tas_roadworks(LIVE_FEATURES)
    leven = next(w for w in works if w.reference == "6177")
    tm = leven.sites[0].traffic_management
    assert "Reduced Speed limit with frequent lane closures at all times" in tm
    assert "BridgePro" in tm
    assert "0460 933 483" in tm


def test_reference_is_the_only_available_identifier():
    """No separate GlobalID exists on this layer - ID (the real
    objectIdField) is the best available identifier, used honestly rather
    than pretending a more stable one exists. See module docstring."""
    works = from_au_tas_roadworks(LIVE_FEATURES)
    references = {w.reference for w in works}
    assert references == {"6177", "6366", "6367", "6112"}


def test_web_link_always_none_in_real_data():
    works = from_au_tas_roadworks(LIVE_FEATURES)
    for feature in LIVE_FEATURES:
        assert feature["properties"]["WEB_LINK"] is None
    # No canonical field maps WEB_LINK, but confirming it's real and
    # currently dead is worth pinning down with a regression test.
    assert works  # sanity - conversion still succeeds despite the null field


def test_coordinate_handles_missing_or_non_line_geometry():
    no_geometry = {"geometry": None, "properties": {}}
    point_geometry = {"geometry": {"type": "Point", "coordinates": []}, "properties": {}}
    assert from_au_tas_roadworks([no_geometry])[0].coordinate is None
    assert from_au_tas_roadworks([point_geometry])[0].coordinate is None
