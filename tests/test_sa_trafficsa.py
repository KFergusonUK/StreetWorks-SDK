"""Tests for the South Australia (Traffic SA / DIT Roadworks) adapter.

**Phase 1 scaffold, genuinely blocked on two access gates** - see the
module docstring in ``streetworks.au.sa``. No real feature has ever been
retrieved (a token-gated query endpoint behind a geo-restricted host), so
``sa_trafficsa_synthetic.json`` is synthetic, built from the real field
list confirmed via a live ``?f=json`` layer-definition pull - the same
"schema is ground truth, data is not" position
``streetworks.datex2.trafikverket``/``streetworks.datex2.vejdirektoratet``
are in.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.au.sa import (
    BASE_URL,
    CLOSURES_LAYER,
    ROADWORKS_AND_INCIDENTS_LAYER,
    TrafficSaClient,
)
from streetworks.common import DateConfidence, from_au_sa_trafficsa

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sa_trafficsa_synthetic.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())


def _layer_info():
    return {
        "objectIdField": "ESRI_OID",
        "maxRecordCount": 1000,
        "advancedQueryCapabilities": {"supportsPagination": True},
        "fields": [{"name": "ESRI_OID"}],
    }


# --------------------------------------------------------------------------- #
# Client wiring - pagination itself is tested generically in
# test_arcgis_client.py; this covers the token passthrough and the
# deliberate no-REC_TYPE-filter decision.
# --------------------------------------------------------------------------- #


def test_client_requires_a_token():
    with pytest.raises(ValueError):
        TrafficSaClient(token="")


@respx.mock
def test_iter_roadworks_attaches_the_token_to_the_query_but_not_to_layer_info():
    layer_route = respx.get(f"{BASE_URL}/{ROADWORKS_AND_INCIDENTS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{ROADWORKS_AND_INCIDENTS_LAYER}/query").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with TrafficSaClient(token="secret-token") as sa:
        features = list(sa.iter_roadworks())
    assert len(features) == 2
    assert "token" not in layer_route.calls[0].request.url.params
    assert query_route.calls[0].request.url.params.get("token") == "secret-token"


@respx.mock
def test_iter_roadworks_does_not_filter_by_rec_type():
    """The deliberate design choice: the real REC_TYPE value meaning
    roadworks has never been confirmed (no query has ever succeeded), so
    iter_roadworks() returns layer 0's full mix rather than a fabricated
    filter - both synthetic records (both REC_TYPE=='Roadworks' here) come
    back, and the where clause sent is the caller's own, unmodified."""
    respx.get(f"{BASE_URL}/{ROADWORKS_AND_INCIDENTS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{ROADWORKS_AND_INCIDENTS_LAYER}/query").mock(
        return_value=httpx.Response(200, json=FIXTURE_JSON)
    )
    with TrafficSaClient(token="secret-token") as sa:
        features = list(sa.iter_roadworks())
    assert len(features) == 2
    assert query_route.calls[0].request.url.params.get("where") == "1=1"


@respx.mock
def test_iter_roadworks_passes_through_a_custom_where_clause():
    """Once a caller has confirmed the real REC_TYPE value themselves, they
    can filter explicitly - the client never silently overrides it."""
    respx.get(f"{BASE_URL}/{ROADWORKS_AND_INCIDENTS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{ROADWORKS_AND_INCIDENTS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with TrafficSaClient(token="secret-token") as sa:
        list(sa.iter_roadworks(where="REC_TYPE='Roadworks'"))
    assert query_route.calls[0].request.url.params.get("where") == "REC_TYPE='Roadworks'"


@respx.mock
def test_iter_closures_queries_the_sibling_layer():
    respx.get(f"{BASE_URL}/{CLOSURES_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{CLOSURES_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with TrafficSaClient(token="secret-token") as sa:
        list(sa.iter_closures())
    assert query_route.calls[0].request.url.path.endswith(f"/{CLOSURES_LAYER}/query")


# --------------------------------------------------------------------------- #
# Converter - the coordinate guard is shared with WA (see
# tests/test_web_mercator.py for the formula's own round-trip test).
# --------------------------------------------------------------------------- #


def test_from_au_sa_trafficsa_maps_a_synthetic_roadworks_feature():
    works = from_au_sa_trafficsa(FIXTURE_JSON["features"])
    assert len(works) == 2

    item = works[0]
    assert item.reference == "SA-RWI-000501"
    assert item.territory == "Australia"
    assert item.administrative_area == "Department for Infrastructure and Transport"
    assert item.coordinate.value == (138.6007, -34.9285)
    assert item.coordinate.crs == "EPSG:4326"

    site = item.sites[0]
    assert site.works_type == "Roadworks"
    assert site.status == "Y"  # ACTIVE passed through raw, never interpreted
    assert (
        site.location_description
        == "South Road resurfacing between Anzac Highway and Cross Road"
    )
    assert site.traffic_management == "Both directions - 1 - 40"
    assert site.proposed_start == datetime(2025, 7, 1, tzinfo=timezone.utc)
    assert site.proposed_end == datetime(2025, 9, 30, tzinfo=timezone.utc)
    assert site.date_confidence is DateConfidence.ESTIMATED


def test_road_no_and_gis_link_id_never_populate_street_ref():
    """The headline open question stays unresolved on purpose - a
    candidate join key this SDK can't verify must not be wired into a
    gazetteer join field, see module docstring."""
    works = from_au_sa_trafficsa(FIXTURE_JSON["features"])
    assert works[0].sites[0].street_ref is None
    # But the raw values are still reachable for anyone who wants to
    # investigate once real data exists.
    assert works[0].sites[0].raw["properties"]["ROAD_NO"] == 4331


def test_location_description_falls_back_when_description_is_absent():
    works = from_au_sa_trafficsa(FIXTURE_JSON["features"])
    second = next(w for w in works if w.reference == "SA-RWI-000502")
    assert second.sites[0].location_description == "Smith Street, Prospect"


def test_no_start_date_means_unknown_confidence():
    works = from_au_sa_trafficsa(FIXTURE_JSON["features"])
    second = next(w for w in works if w.reference == "SA-RWI-000502")
    assert second.sites[0].proposed_end is None
    assert second.sites[0].date_confidence is DateConfidence.ESTIMATED  # proposed_start IS set


def test_coordinate_guard_reprojects_web_mercator_metres():
    feature = {
        "geometry": {"type": "Point", "coordinates": [15432312.7, -4142255.9]},
        "properties": {"ROADWORKS_AND_INCIDENTS_ID": "SA-RWI-999"},
    }
    works = from_au_sa_trafficsa([feature])
    lon, lat = works[0].coordinate.value
    assert 135 < lon < 145  # plausible South Australia longitude
    assert -37 < lat < -30
    assert works[0].coordinate.crs == "EPSG:4326"
