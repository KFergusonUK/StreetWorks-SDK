"""Tests for the Consell de Mallorca (IDEmallorca) roadworks adapter.

Fixtures are synthetic - real, live-confirmed shape (the real
``incidencies_icon``/``incidencies_tram`` field names, EPSG:25831
coordinates in the real value range, the real three ``tipoinc`` values,
a genuine 2-part ``MultiLineString`` matching the real
``codi=19528`` finding, and a point-only incident with no matching tram),
not trimmed from a live pull, since the licence is unconfirmed - see
``streetworks/ogc/mallorca.py``'s module docstring. Four icons: two
``Obres``, one ``Manteniment``, one ``Altres`` (must be excluded by
:meth:`~streetworks.ogc.mallorca.MallorcaClient.fetch_roadworks_icons`);
three trams (``90001``: 1 part, ``90002``: 2 parts, ``90003``: 1 part) -
``90004`` has no matching tram, exercising the point-only case.
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.common import from_mallorca
from streetworks.ogc.mallorca import (
    BASE_URL,
    CRS,
    ICON_TYPE_NAME,
    ROADWORKS_TIPOINC,
    TRAM_TYPE_NAME,
    MallorcaClient,
)

FIXTURES = Path(__file__).parent / "fixtures"
ICON_PAYLOAD = json.loads((FIXTURES / "ogc_mallorca_incidencies_icon.json").read_text())
TRAM_PAYLOAD = json.loads((FIXTURES / "ogc_mallorca_incidencies_tram.json").read_text())


def _mock_wfs():
    def side_effect(request: httpx.Request) -> httpx.Response:
        params = dict(httpx.QueryParams(request.url.query))
        # Not the SDK default (application/geo+json) - see module docstring.
        assert params["OUTPUTFORMAT"] == "application/json"
        assert params["SRSNAME"] == CRS
        if params["TYPENAMES"] == ICON_TYPE_NAME:
            return httpx.Response(200, json=ICON_PAYLOAD)
        if params["TYPENAMES"] == TRAM_TYPE_NAME:
            return httpx.Response(200, json=TRAM_PAYLOAD)
        raise AssertionError(f"unexpected TYPENAMES {params['TYPENAMES']!r}")

    respx.get(BASE_URL).mock(side_effect=side_effect)


def test_roadworks_tipoinc_excludes_altres():
    assert ROADWORKS_TIPOINC == {"Obres", "Manteniment"}


@respx.mock
def test_client_fetches_icons_requesting_application_json_not_geo_json():
    _mock_wfs()
    with MallorcaClient() as mallorca:
        icons = mallorca.fetch_icons()
    assert len(icons) == 4


@respx.mock
def test_client_fetch_roadworks_icons_excludes_altres():
    _mock_wfs()
    with MallorcaClient() as mallorca:
        icons = mallorca.fetch_roadworks_icons()
    codes = {f["properties"]["codi"] for f in icons}
    assert codes == {90001, 90002, 90004}
    assert all(f["properties"]["tipoinc"] != "Altres" for f in icons)


@respx.mock
def test_client_rejects_xml_error_body_masked_as_http_200():
    # The real, live-confirmed failure mode this server has for a bad
    # output_format - HTTP 200 wrapping an XML exception, not an error
    # status. json() itself fails loudly here (not valid JSON at all).
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(
            200,
            content=b"<ows:ExceptionReport><ows:Exception>bad outputFormat"
            b"</ows:Exception></ows:ExceptionReport>",
        )
    )
    with MallorcaClient() as mallorca:
        with pytest.raises(json.JSONDecodeError):
            mallorca.fetch_icons()


@respx.mock
def test_client_validates_json_that_is_not_a_feature_collection():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json={"error": "nope"}))
    with MallorcaClient() as mallorca:
        with pytest.raises(ValueError, match="FeatureCollection"):
            mallorca.fetch_icons()


def test_from_mallorca_joins_icon_and_tram_by_codi():
    icons = ICON_PAYLOAD["features"]
    trams = TRAM_PAYLOAD["features"]
    roadworks_icons = [f for f in icons if f["properties"]["tipoinc"] in ROADWORKS_TIPOINC]
    works_list = from_mallorca(roadworks_icons, trams)
    assert len(works_list) == 3

    by_ref = {w.reference: w for w in works_list}
    assert by_ref["90001"].sites[0].coordinate.parts is not None
    assert len(by_ref["90001"].sites[0].coordinate.parts) == 1
    # The real multi-part case (codi=19528 live) - 90002's tram has 2 parts.
    assert len(by_ref["90002"].sites[0].coordinate.parts) == 2


def test_from_mallorca_handles_point_only_incident_honestly():
    icons = ICON_PAYLOAD["features"]
    trams = TRAM_PAYLOAD["features"]
    roadworks_icons = [f for f in icons if f["properties"]["tipoinc"] in ROADWORKS_TIPOINC]
    works_list = from_mallorca(roadworks_icons, trams)
    by_ref = {w.reference: w for w in works_list}

    site = by_ref["90004"].sites[0]
    assert site.coordinate is not None  # the point itself is never fabricated away
    assert site.coordinate.value == (530000.0, 4430000.0)
    assert site.coordinate.parts is None  # no tram match - never invented


def test_from_mallorca_crs_is_labelled_not_reprojected():
    icons = ICON_PAYLOAD["features"]
    works_list = from_mallorca(icons[:1], [])
    coordinate = works_list[0].sites[0].coordinate
    assert coordinate.crs == "EPSG:25831"
    # Real UTM31N magnitude, not WGS84 degrees.
    assert coordinate.value[0] > 100_000


def test_from_mallorca_territory_and_authority():
    icons = ICON_PAYLOAD["features"]
    works_list = from_mallorca(icons, TRAM_PAYLOAD["features"])
    for works in works_list:
        assert works.territory == "Spain"
        assert works.administrative_area == "Consell de Mallorca"


def test_from_mallorca_location_description_combines_road_and_km_range():
    icons = ICON_PAYLOAD["features"]
    works_list = from_mallorca(icons, [])
    by_ref = {w.reference: w for w in works_list}
    assert by_ref["90001"].sites[0].location_description == "Ma-15 (km 3.5-6.2)"
    # pkfin is null on 90004 - only pkinici stated.
    assert by_ref["90004"].sites[0].location_description == "Ma-13 (km 50.0)"


def test_from_mallorca_dates_parsed_as_europe_madrid():
    icons = ICON_PAYLOAD["features"]
    works_list = from_mallorca(icons[:1], [])
    site = works_list[0].sites[0]
    assert site.proposed_start.isoformat() == "2026-08-01T09:00:00+02:00"
    assert site.date_confidence.value == "verified"
