"""Tests for the ACT (Temporary Traffic Management - Planned Road
Closures) adapter.

Credential-free, live-verified from day one - see the module docstring in
``streetworks.au.act``. ``act_ttm_live_pull.json`` holds five REAL
features trimmed from a real, unauthenticated pull (2026-08-01): a real
``roadWorks`` record with embedded HTML ``<br>`` in ``roadsClosed``, an
``other``-typed record (with ``describeActivity`` populated), a
``specialEvent`` record, a ``buildingConstruction`` record (whose
``suburb1`` is the literal value ``"OTHER"``), and a ``lightRail`` record
- not synthetic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import respx

from streetworks.au.act import BASE_URL, ROADWORKS_LAYER, ActTtmClient
from streetworks.common import DateConfidence, from_au_act_ttm

LIVE_PULL_PATH = Path(__file__).parent / "fixtures" / "act_ttm_live_pull.json"
LIVE_PULL_JSON = json.loads(LIVE_PULL_PATH.read_text())
LIVE_FEATURES = LIVE_PULL_JSON["features"]


def _layer_info():
    return {
        "objectIdField": "objectid",
        "maxRecordCount": 1000,
        "advancedQueryCapabilities": {"supportsPagination": True},
        "fields": [{"name": "objectid"}],
    }


# --------------------------------------------------------------------------- #
# Client wiring
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_roadworks_filters_to_the_confirmed_real_type_value():
    respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}/query").mock(
        return_value=httpx.Response(200, json=LIVE_PULL_JSON)
    )
    with ActTtmClient() as act:
        features = list(act.iter_roadworks())
    assert len(features) == 5
    assert query_route.calls[0].request.url.params.get("where") == "type='roadWorks'"


@respx.mock
def test_iter_closures_defaults_to_every_type():
    respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with ActTtmClient() as act:
        list(act.iter_closures())
    assert query_route.calls[0].request.url.params.get("where") == "1=1"


@respx.mock
def test_iter_roadworks_requests_outsr_4326():
    respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{BASE_URL}/{ROADWORKS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with ActTtmClient() as act:
        list(act.iter_roadworks())
    assert query_route.calls[0].request.url.params.get("outSR") == "4326"


# --------------------------------------------------------------------------- #
# Converter - real field-mapping findings
# --------------------------------------------------------------------------- #


def test_from_au_act_ttm_maps_the_real_watson_roadworks_feature():
    works = from_au_act_ttm(LIVE_FEATURES)
    assert len(works) == 5

    watson = next(w for w in works if w.reference == "28de4e5d-3e23-4e68-83d8-5bca5a510f2f")
    assert watson.territory == "Australia"
    assert watson.administrative_area == "Roads ACT"
    assert watson.coordinate.value == (149.159294347216, -35.2303907095075)
    assert watson.coordinate.crs == "EPSG:4326"

    site = watson.sites[0]
    assert site.works_type == "roadWorks"
    # The real embedded HTML <br> tag must survive unmodified.
    assert "<br>" in site.location_description
    assert "WATSON" in site.location_description
    assert site.traffic_management == (
        "Sewer works associated with the Watson Section 76 Block 2 redevelopment."
    )
    assert site.proposed_start == datetime(2025, 11, 18, 19, 30, tzinfo=timezone.utc)
    assert site.date_confidence is DateConfidence.ESTIMATED


def test_other_type_uses_describe_activity_as_works_type():
    """A real, deliberate improvement: type=='other' alone is
    uninformative - describeActivity (confirmed live to populate exactly
    the 'other' records) gives the real activity instead."""
    works = from_au_act_ttm(LIVE_FEATURES)
    other = next(w for w in works if w.reference == "c4de37ef-bbe3-44ad-a679-f3234ef47a96")
    # Real trailing whitespace in the source value - carried through
    # exactly as stated, never silently trimmed.
    assert other.sites[0].works_type == "Estate development - civil infrastructure. "


def test_non_other_types_keep_the_raw_type_value():
    works = from_au_act_ttm(LIVE_FEATURES)
    building = next(w for w in works if w.reference == "95ec2165-18d4-4c03-b83d-1656f9adce25")
    assert building.sites[0].works_type == "buildingConstruction"
    # A real suburb1 value happens to literally be "OTHER" - not a
    # sentinel, just carried through as real text.
    assert "OTHER" in building.sites[0].location_description


def test_client_requires_no_credentials():
    # Constructing the client at all must not require any argument.
    ActTtmClient()
