"""Tests for the Australian gazetteer adapter (G-NAF + National Roads,
over the Digital Atlas of Australia).

Credential-free, live-verified from day one - see the module docstring in
``streetworks.gnaf.client``. Both fixtures hold REAL features trimmed
from real, unauthenticated pulls (2026-08-02, ACT-scoped) - not
synthetic. ``gnaf_addresses_live_pull.json``: a plain address, a real
FLAT_TYPE/FLAT_NUMBER ("unit") example, and a real NUMBER_FIRST_SUFFIX
example. ``gnaf_roads_live_pull.json``: an unnamed local road, a named
local road, a PROPOSED (not yet built) collector road, and a national
highway with a real ``jurisdiction_control`` value.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.common import from_gnaf_address, from_gnaf_road
from streetworks.common.gazetteer import Name
from streetworks.gnaf import (
    ADDRESSES_BASE_URL,
    ADDRESSES_LAYER,
    ROADS_BASE_URL,
    ROADS_LAYER,
    GnafClient,
)

ADDRESSES_PATH = Path(__file__).parent / "fixtures" / "gnaf_addresses_live_pull.json"
ADDRESSES_JSON = json.loads(ADDRESSES_PATH.read_text())
ADDRESS_FEATURES = ADDRESSES_JSON["features"]

ROADS_PATH = Path(__file__).parent / "fixtures" / "gnaf_roads_live_pull.json"
ROADS_JSON = json.loads(ROADS_PATH.read_text())
ROAD_FEATURES = ROADS_JSON["features"]


def _layer_info():
    return {
        "objectIdField": "OBJECTID",
        "maxRecordCount": 2000,
        "advancedQueryCapabilities": {"supportsPagination": True},
        "fields": [{"name": "OBJECTID"}],
    }


# --------------------------------------------------------------------------- #
# Client wiring - both credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_addresses_needs_no_credentials():
    respx.get(f"{ADDRESSES_BASE_URL}/{ADDRESSES_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    respx.get(f"{ADDRESSES_BASE_URL}/{ADDRESSES_LAYER}/query").mock(
        return_value=httpx.Response(200, json=ADDRESSES_JSON)
    )
    with GnafClient() as gnaf:
        features = list(gnaf.iter_addresses(where="STATE='ACT'"))
    assert len(features) == 3


@respx.mock
def test_iter_addresses_requests_outsr_4326():
    respx.get(f"{ADDRESSES_BASE_URL}/{ADDRESSES_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{ADDRESSES_BASE_URL}/{ADDRESSES_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with GnafClient() as gnaf:
        list(gnaf.iter_addresses())
    assert query_route.calls[0].request.url.params.get("outSR") == "4326"
    assert query_route.calls[0].request.url.params.get("where") == "1=1"


@respx.mock
def test_iter_roads_needs_no_credentials():
    respx.get(f"{ROADS_BASE_URL}/{ROADS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    respx.get(f"{ROADS_BASE_URL}/{ROADS_LAYER}/query").mock(
        return_value=httpx.Response(200, json=ROADS_JSON)
    )
    with GnafClient() as gnaf:
        features = list(gnaf.iter_roads(where="state='ACT'"))
    assert len(features) == 4


@respx.mock
def test_iter_roads_requests_outsr_4326():
    respx.get(f"{ROADS_BASE_URL}/{ROADS_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{ROADS_BASE_URL}/{ROADS_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with GnafClient() as gnaf:
        list(gnaf.iter_roads())
    assert query_route.calls[0].request.url.params.get("outSR") == "4326"


def test_client_requires_no_credentials():
    GnafClient()


# --------------------------------------------------------------------------- #
# Converter - addresses (real fixture)
# --------------------------------------------------------------------------- #


def _by_pid(pid: str):
    return next(
        f for f in ADDRESS_FEATURES if f["properties"]["ADDRESS_DETAIL_PID"] == pid
    )


def test_from_gnaf_address_maps_a_real_plain_address():
    address = from_gnaf_address(_by_pid("GAACT714958506"))
    assert address.geometry.value == (-35.16709003099993, 149.13066859000003)
    assert address.geometry.crs == "EPSG:4326"
    assert address.identifiers[0].scheme == "address_detail_pid"
    assert address.identifiers[0].value == "GAACT714958506"
    assert address.housenumber == "6"
    assert address.suffix is None
    assert address.street_name == "WENLOCK STREET"
    assert address.territory == "Australia"
    assert address.administrative_area == "AMAROO"


def test_from_gnaf_address_maps_a_real_suffixed_number():
    address = from_gnaf_address(_by_pid("GAACT717940856"))
    assert address.housenumber == "53"
    assert address.suffix == "A"
    assert address.street_name == "ARDLETHAN STREET"


def test_from_gnaf_address_flat_stays_on_raw_only():
    """A real 'unit' concept (FLAT_TYPE/FLAT_NUMBER) - no canonical field,
    the same gap LINZ's `unit` field already established, now confirmed
    on a second source. See gazetteer.Address's own docstring."""
    address = from_gnaf_address(_by_pid("GAACT719451198"))
    assert address.raw["properties"]["FLAT_TYPE"] == "SHOP"
    assert address.raw["properties"]["FLAT_NUMBER"] == 83
    assert address.housenumber == "125"


def test_from_gnaf_address_raises_without_geometry():
    feature = {"geometry": None, "properties": {"ADDRESS_DETAIL_PID": "X"}}
    with pytest.raises(ValueError, match="no geometry"):
        from_gnaf_address(feature)


# --------------------------------------------------------------------------- #
# Converter - roads (real fixture)
# --------------------------------------------------------------------------- #


def _by_road_id(road_id: str):
    return next(f for f in ROAD_FEATURES if f["properties"]["road_id"] == road_id)


def test_from_gnaf_road_maps_a_real_named_segment():
    segment = from_gnaf_road(_by_road_id("rds0dd303a0d423"))
    assert segment.identifiers[0].scheme == "road_id"
    assert segment.identifiers[0].value == "rds0dd303a0d423"
    assert segment.names == (Name(value="SHOOBRIDGE CIRCUIT"),)
    assert segment.street_type.code == "CIRCUIT"
    assert segment.street_type.label == "Circuit"
    assert segment.administrative_area == "ACT"
    assert segment.geometry.crs == "EPSG:4326"
    assert segment.geometry.points is not None


def test_from_gnaf_road_handles_a_real_unnamed_segment():
    """A genuine gap in the source, not a converter bug - some LOCAL ROAD
    segments carry no full_street_name at all."""
    segment = from_gnaf_road(_by_road_id("rdsf4cae148834a"))
    assert segment.names == ()
    assert segment.street_type is None
    assert segment.raw["properties"]["hierarchy"] == "LOCAL ROAD"


def test_from_gnaf_road_jurisdiction_control_stays_on_raw_only():
    """A real per-record authority (richer than a hardcoded value) - no
    canonical field for it on Segment."""
    segment = from_gnaf_road(_by_road_id("rds6c1a711dfd1d"))
    assert segment.names == (Name(value="PACIFIC HIGHWAY"),)
    assert (
        segment.raw["properties"]["jurisdiction_control"]
        == "Transport for New South Wales (controlled roads)"
    )


def test_from_gnaf_road_status_stays_on_raw_only_and_is_not_filtered():
    """PROPOSED (not yet built) roads are real, live data - iter_roads()
    is the raw network, not a curated 'built only' view. See module
    docstring."""
    segment = from_gnaf_road(_by_road_id("rdsSLl_zCdZ6oRI"))
    assert segment.raw["properties"]["status"] == "PROPOSED"


def test_from_gnaf_road_raises_without_geometry():
    feature = {"geometry": None, "properties": {"road_id": "x"}}
    with pytest.raises(ValueError, match="no geometry"):
        from_gnaf_road(feature)


def test_from_gnaf_road_multilinestring_becomes_parts():
    """No real sample pulled so far happens to be multi-part, but ArcGIS
    ``paths`` genuinely can carry more than one (see
    streetworks.arcgis.client) - exercised here with a hand-built case,
    the same precedent from_linz_road's own MultiLineString test sets."""
    feature = {
        "geometry": {
            "type": "MultiLineString",
            "coordinates": [
                [[149.0, -35.0], [149.01, -35.01]],
                [[149.1, -35.1], [149.11, -35.11]],
            ],
        },
        "properties": {"road_id": "rdsSPLIT0000001", "full_street_name": "SPLIT ROAD"},
    }
    segment = from_gnaf_road(feature)
    assert segment.geometry.parts is not None
    assert len(segment.geometry.parts) == 2
    assert segment.geometry.value == segment.geometry.parts[0][0]


def test_no_stated_join_between_addresses_and_roads():
    """The core finding this build settled: no address feature carries a
    road_id-shaped reference, and no road feature carries an address
    reference - confirmed by field-list inspection, not a live query gap.
    See streetworks.gnaf.client's module docstring."""
    address = from_gnaf_address(_by_pid("GAACT714958506"))
    assert address.street_links == ()
    segment = from_gnaf_road(_by_road_id("rds0dd303a0d423"))
    assert segment.street_refs == ()
