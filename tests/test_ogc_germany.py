"""Tests for the generic OGCFeaturesClient and the German state field-map
registry.

Fixtures are real trimmed WFS GeoJSON responses, 2026-07: Hamburg (3
features - the original 130-feature sample's first record, one
future-dated record, and one missing an optional property), Brandenburg
(5 features - all three real records sharing works ID prefix "267201193"
- a `Sperrung` plus two `Bauabschnitt` segments - one record missing
`Anzahl_Fahrstreifen`, and the real 390-vertex LineString found in the
live feed), and Saxony (6 features - three real segments of one closure
sharing `ID` "LRABZ2026B00285", a real past-dated closure, a real
`"DD.MM.YYYY HH Uhr"`-formatted record, and one missing optional
properties).
"""

import io
import json
import zipfile
from pathlib import Path

import httpx
import respx

from streetworks.ogc import OGCFeaturesClient
from streetworks.ogc.germany import (
    BRANDENBURG,
    GERMANY_LAT_RANGE,
    GERMANY_LON_RANGE,
    HAMBURG,
    SAXONY,
    SAXONY_EASTING_RANGE,
    SAXONY_NORTHING_RANGE,
    GermanRoadworksClient,
)

FIXTURES = Path(__file__).parent / "fixtures"
HAMBURG_PAYLOAD = json.loads((FIXTURES / "ogc_hamburg_baustellen.json").read_text())
BRANDENBURG_PAYLOAD = json.loads(
    (FIXTURES / "ogc_brandenburg_baustelleninfo.json").read_text()
)
SAXONY_PAYLOAD = json.loads((FIXTURES / "ogc_saxony_sperrungen.json").read_text())


def _zipped(payload: dict, member: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, json.dumps(payload))
    return buffer.getvalue()


def _coords(feature):
    geometry = feature["geometry"]
    if geometry["type"] == "Point":
        return [geometry["coordinates"]]
    return geometry["coordinates"]


def test_hamburg_and_brandenburg_fixtures_are_within_germany_bounds():
    # The mandatory axis-order sanity check: a swapped-axis feed would put
    # coordinates in the Indian Ocean, not Germany.
    for payload in (HAMBURG_PAYLOAD, BRANDENBURG_PAYLOAD):
        for feature in payload["features"]:
            for lon, lat in _coords(feature):
                assert GERMANY_LON_RANGE[0] <= lon <= GERMANY_LON_RANGE[1], (lon, lat)
                assert GERMANY_LAT_RANGE[0] <= lat <= GERMANY_LAT_RANGE[1], (lon, lat)


def test_hamburg_field_map_has_no_road_field():
    # Genuinely absent from the real data (checked all 130 live features),
    # not an oversight - see streetworks.ogc.germany's module docstring.
    assert HAMBURG.road_field is None
    assert HAMBURG.status_field is None


def test_brandenburg_field_map_road_field_matches_real_typo():
    # The real property name has a typo (double "n") - confirmed live.
    assert BRANDENBURG.road_field == "Straßenummner"
    assert BRANDENBURG.road_field in BRANDENBURG_PAYLOAD["features"][0]["properties"]


def test_saxony_field_map_uses_utm33n_not_wgs84():
    # No WGS84 source exists for Saxony at all - see module docstring.
    assert SAXONY.crs == "EPSG:25833"
    assert SAXONY.access_mode == "zipped_geojson"
    assert SAXONY.zip_member is not None


def test_saxony_fixture_is_within_utm_bounds():
    # The UTM equivalent of the Germany-wide lon/lat bounds check - the
    # real feed's coordinates are metres (easting/northing), not degrees.
    for feature in SAXONY_PAYLOAD["features"]:
        for easting, northing in feature["geometry"]["coordinates"]:
            assert SAXONY_EASTING_RANGE[0] <= easting <= SAXONY_EASTING_RANGE[1]
            assert SAXONY_NORTHING_RANGE[0] <= northing <= SAXONY_NORTHING_RANGE[1]


@respx.mock
def test_ogc_features_client_requests_geojson_and_explicit_crs():
    route = respx.get("https://example.test/wfs").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with OGCFeaturesClient() as ogc:
        ogc.get_wfs_features("https://example.test/wfs", type_name="ns:thing")

    request = route.calls.last.request
    params = dict(httpx.QueryParams(request.url.query))
    assert params["OUTPUTFORMAT"] == "application/geo+json"
    assert params["SRSNAME"] == "EPSG:4326"
    assert params["TYPENAMES"] == "ns:thing"
    assert params["SERVICE"] == "WFS"


@respx.mock
def test_german_roadworks_client_fetch_hamburg():
    respx.get(HAMBURG.base_url).mock(return_value=httpx.Response(200, json=HAMBURG_PAYLOAD))
    with GermanRoadworksClient() as germany:
        features = germany.fetch("Hamburg")
    assert len(features) == 3
    assert features[0]["properties"]["titel"]


@respx.mock
def test_german_roadworks_client_iter_all():
    respx.get(HAMBURG.base_url).mock(return_value=httpx.Response(200, json=HAMBURG_PAYLOAD))
    respx.get(BRANDENBURG.base_url).mock(
        return_value=httpx.Response(200, json=BRANDENBURG_PAYLOAD)
    )
    with GermanRoadworksClient() as germany:
        results = list(germany.iter_all(["Hamburg", "Brandenburg"]))
    assert len(results) == 3 + 5
    assert {state for state, _ in results} == {"Hamburg", "Brandenburg"}


@respx.mock
def test_ogc_features_client_unzips_direct_geojson_download():
    zip_bytes = _zipped(SAXONY_PAYLOAD, "Baustelleninfo_Sperrungen_Sachsen.geojson")
    respx.get("https://example.test/download.zip").mock(
        return_value=httpx.Response(200, content=zip_bytes)
    )
    with OGCFeaturesClient() as ogc:
        payload = ogc.get_zipped_geojson(
            "https://example.test/download.zip", member="Baustelleninfo_Sperrungen_Sachsen.geojson"
        )
    assert len(payload["features"]) == 6


@respx.mock
def test_german_roadworks_client_fetch_saxony_via_zip():
    zip_bytes = _zipped(SAXONY_PAYLOAD, SAXONY.zip_member)
    respx.get(SAXONY.base_url).mock(return_value=httpx.Response(200, content=zip_bytes))
    with GermanRoadworksClient() as germany:
        features = germany.fetch("Sachsen")
    assert len(features) == 6
    assert features[0]["properties"]["Sperrung_Art_Klartext"]
