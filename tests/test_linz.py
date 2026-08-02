"""Tests for the New Zealand (LINZ) gazetteer adapter.

Two genuinely different verification levels - see the module docstring in
``streetworks.linz.client``. ``linz_addresses_live_pull.json`` holds five
REAL features from a real, unauthenticated pull (2026-08-02, NZ Addresses,
layer 123113) - not synthetic. ``linz_roads_sample.json``/
``linz_road_sections_sample.json`` use real *attribute* values pulled from
LINZ's own public, keyless Koordinates metadata sample endpoint (real
``road_id``/name values, confirmed live) but an **illustrative-only
geometry**, since no real WFS query has ever been run (no LDS key) -
clearly not the same standing as the addresses fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.common import from_linz_address, from_linz_road, from_linz_road_section
from streetworks.common.gazetteer import GeometryGrade, Name
from streetworks.linz import (
    ADDRESSES_BASE_URL,
    ADDRESSES_LAYER,
    LDS_BASE_URL,
    ROADS_LAYER_ID,
    LinzClient,
)

ADDRESSES_PATH = Path(__file__).parent / "fixtures" / "linz_addresses_live_pull.json"
ADDRESSES_JSON = json.loads(ADDRESSES_PATH.read_text())
ADDRESS_FEATURES = ADDRESSES_JSON["features"]

ROADS_PATH = Path(__file__).parent / "fixtures" / "linz_roads_sample.json"
ROADS_JSON = json.loads(ROADS_PATH.read_text())

ROAD_SECTIONS_PATH = Path(__file__).parent / "fixtures" / "linz_road_sections_sample.json"
ROAD_SECTIONS_JSON = json.loads(ROAD_SECTIONS_PATH.read_text())


def _layer_info():
    return {
        "objectIdField": "OBJECTID",
        "maxRecordCount": 2000,
        "advancedQueryCapabilities": {"supportsPagination": True},
        "fields": [{"name": "OBJECTID"}],
    }


# --------------------------------------------------------------------------- #
# Client wiring - addresses (confirmed live, no key)
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_addresses_needs_no_credentials():
    respx.get(f"{ADDRESSES_BASE_URL}/{ADDRESSES_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    respx.get(f"{ADDRESSES_BASE_URL}/{ADDRESSES_LAYER}/query").mock(
        return_value=httpx.Response(200, json=ADDRESSES_JSON)
    )
    with LinzClient() as linz:
        features = list(linz.iter_addresses())
    assert len(features) == 5


@respx.mock
def test_iter_addresses_requests_outsr_4326():
    respx.get(f"{ADDRESSES_BASE_URL}/{ADDRESSES_LAYER}").mock(
        return_value=httpx.Response(200, json=_layer_info())
    )
    query_route = respx.get(f"{ADDRESSES_BASE_URL}/{ADDRESSES_LAYER}/query").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with LinzClient() as linz:
        list(linz.iter_addresses())
    assert query_route.calls[0].request.url.params.get("outSR") == "4326"


# --------------------------------------------------------------------------- #
# Client wiring - roads/road sections (needs a real LDS key, unverified)
# --------------------------------------------------------------------------- #


def test_iter_roads_requires_an_api_key():
    with LinzClient() as linz:
        with pytest.raises(ValueError, match="api_key is required"):
            list(linz.iter_roads())


def test_iter_road_sections_requires_an_api_key():
    with LinzClient() as linz:
        with pytest.raises(ValueError, match="api_key is required"):
            list(linz.iter_road_sections())


@respx.mock
def test_iter_roads_builds_the_real_lds_wfs_url_shape():
    """The API key lives in the URL path (;key=...), Koordinates' own
    convention - confirmed live from the layer's own /services/ listing,
    see module docstring. The query itself has never been run against a
    real key."""
    url = f"{LDS_BASE_URL}/services;key=test-key/wfs/"
    route = respx.get(url).mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with LinzClient(api_key="test-key") as linz:
        list(linz.iter_roads())
    assert route.called
    request = route.calls[0].request
    assert request.url.params.get("TYPENAMES") == f"layer-{ROADS_LAYER_ID}"
    assert request.url.params.get("startIndex") == "0"


@respx.mock
def test_iter_road_sections_pages_via_start_index():
    url = f"{LDS_BASE_URL}/services;key=test-key/wfs/"
    first_page = {
        "type": "FeatureCollection",
        "features": ROAD_SECTIONS_JSON["features"] * 500,  # exactly _PAGE_SIZE (1000)
    }
    second_page = {"type": "FeatureCollection", "features": ROAD_SECTIONS_JSON["features"]}
    route = respx.get(url).mock(
        side_effect=[httpx.Response(200, json=first_page), httpx.Response(200, json=second_page)]
    )
    with LinzClient(api_key="test-key") as linz:
        features = list(linz.iter_road_sections())
    assert len(features) == 1002
    assert route.calls[0].request.url.params.get("startIndex") == "0"
    assert route.calls[1].request.url.params.get("startIndex") == "1000"


# --------------------------------------------------------------------------- #
# Converter - addresses (real fixture)
# --------------------------------------------------------------------------- #


def test_from_linz_address_maps_a_real_unit_address():
    address = from_linz_address(ADDRESS_FEATURES[0])
    assert address.geometry.value == (-36.8868090715903, 174.899769829008)
    assert address.geometry.crs == "EPSG:4326"
    assert address.identifiers[0].scheme == "address_id"
    assert address.identifiers[0].value == "2453674"
    assert address.housenumber == "49"
    assert address.suffix is None
    assert address.street_name == "Pigeon Mountain Road"
    assert address.street_links[0].scheme == "road_id"
    assert address.street_links[0].value == "1828155"
    assert address.territory == "New Zealand"
    assert address.administrative_area == "Auckland"
    # The real "unit" concept (a genuine gap this SDK's own gazetteer model
    # docstring flags as absent from every source built so far) has no
    # canonical field - confirmed still reachable via raw.
    assert address.raw["properties"]["unit"] == "2"


def test_from_linz_address_decomposed_suffix_not_the_composite_string():
    address = from_linz_address(ADDRESS_FEATURES[1])
    assert address.housenumber == "2"
    assert address.suffix == "A"
    # full_address_number ("2A") is the composite the source also states,
    # but housenumber/suffix come from the separately-decomposed fields.
    assert address.raw["properties"]["full_address_number"] == "2A"


def test_from_linz_address_is_land_stays_on_raw_only():
    """A real, confirmed field-length quirk (is_land is esriFieldTypeString
    length 2, so real values are 'tr'/'fa') - no canonical field for it."""
    address = from_linz_address(ADDRESS_FEATURES[1])
    assert address.raw["properties"]["is_land"] == "fa"


def test_from_linz_address_raises_without_geometry():
    """Address.geometry is mandatory (unlike Street/Segment, which can be
    GeometryGrade.ABSENT) - mirrors from_linz_road_section's own discipline
    rather than silently constructing an invalid object."""
    feature = {"geometry": None, "properties": {"address_id": 1}}
    with pytest.raises(ValueError, match="no geometry"):
        from_linz_address(feature)


# --------------------------------------------------------------------------- #
# Converter - roads/road sections (real attributes, illustrative geometry)
# --------------------------------------------------------------------------- #


def test_from_linz_road_maps_real_attributes():
    street = from_linz_road(ROADS_JSON["features"][0])
    assert street.identifiers[0].scheme == "road_id"
    assert street.identifiers[0].value == "1771657"
    assert street.names == (Name(value="Dunvegan Street"),)
    assert street.street_type.label == "Street"
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry.points is not None
    assert len(street.geometry.points) == 3
    assert street.territory == "New Zealand"


def test_from_linz_road_section_maps_real_attributes_and_street_refs():
    segment = from_linz_road_section(ROAD_SECTIONS_JSON["features"][0])
    assert segment.identifiers[0].scheme == "road_section_id"
    assert segment.identifiers[0].value == "2907"
    assert segment.street_refs[0].scheme == "road_id"
    assert segment.street_refs[0].value == "1773601"
    assert segment.administrative_area == "Clutha District"
    assert segment.names == (Name(value="North Branch Road"),)


def test_from_linz_road_section_includes_secondary_and_tertiary_names_when_present():
    """secondary_road_name/tertiary_road_name are real fields the source
    can state (per the layer's own field list) - not present in the real
    sample rows checked, so exercised here with a small hand-built case."""
    feature = {
        "geometry": {"type": "LineString", "coordinates": [[172.0, -43.0], [172.01, -43.01]]},
        "properties": {
            "road_section_id": 99999,
            "road_id": 1234567,
            "full_road_name": "State Highway 1",
            "road_name_type": "Highway",
            "secondary_road_name": "SH1",
            "tertiary_road_name": None,
            "territorial_authority": "Wellington City",
        },
    }
    segment = from_linz_road_section(feature)
    assert segment.names == (Name(value="State Highway 1"), Name(value="SH1"))


def test_from_linz_road_section_raises_without_geometry():
    feature = {"geometry": None, "properties": {"road_section_id": 1, "road_id": 2}}
    with pytest.raises(ValueError, match="no geometry"):
        from_linz_road_section(feature)


def test_from_linz_road_multilinestring_becomes_parts():
    """The source's own documentation notes some aggregated centrelines
    are made of disjoint parts sharing one name - MultiLineString support
    is real, even though not present in the two real-attribute samples
    used elsewhere in this file."""
    feature = {
        "geometry": {
            "type": "MultiLineString",
            "coordinates": [
                [[172.0, -43.0], [172.01, -43.01]],
                [[173.0, -44.0], [173.01, -44.01]],
            ],
        },
        "properties": {"road_id": 555, "full_road_name": "Split Road"},
    }
    street = from_linz_road(feature)
    assert street.geometry.parts is not None
    assert len(street.geometry.parts) == 2
    assert street.geometry.value == street.geometry.parts[0][0]
