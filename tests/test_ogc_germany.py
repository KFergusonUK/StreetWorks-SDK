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

Baden-Württemberg (2026-08-20, `tests/fixtures/ogc_bw_roadworks.json`) -
3 real trimmed GeoJSON features from MobiData BW's direct download: a
real `ROAD_CLOSED`/`L154`, and two real `CONSTRUCTION`/`ONE_DIRECTION`
records on `K1077`/`K1055`. Schleswig-Holstein
(`tests/fixtures/ogc_sh_baustellen.xml`) - 3 real trimmed GML `wfs:member`
elements off LBV.SH's own WFS (posList trimmed to 5 coordinate pairs
each): a real `L281`, a real `B5`, and a real `G`-prefixed record (a
genuine, if uninformative, real value - see
:mod:`streetworks.ogc.germany`'s module docstring for what "G" means).
"""

import io
import json
import zipfile
from pathlib import Path

import httpx
import respx

from streetworks.ogc import OGCFeaturesClient
from streetworks.ogc.germany import (
    BADEN_WUERTTEMBERG,
    BRANDENBURG,
    GERMANY_LAT_RANGE,
    GERMANY_LON_RANGE,
    HAMBURG,
    SAXONY,
    SAXONY_EASTING_RANGE,
    SAXONY_NORTHING_RANGE,
    SCHLESWIG_HOLSTEIN,
    GermanRoadworksClient,
)

FIXTURES = Path(__file__).parent / "fixtures"
HAMBURG_PAYLOAD = json.loads((FIXTURES / "ogc_hamburg_baustellen.json").read_text())
BRANDENBURG_PAYLOAD = json.loads(
    (FIXTURES / "ogc_brandenburg_baustelleninfo.json").read_text()
)
SAXONY_PAYLOAD = json.loads((FIXTURES / "ogc_saxony_sperrungen.json").read_text())
BW_PAYLOAD = json.loads((FIXTURES / "ogc_bw_roadworks.json").read_text())
SH_XML = (FIXTURES / "ogc_sh_baustellen.xml").read_bytes()


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


def test_bw_field_map_uses_direct_geojson_and_iso_datetime():
    assert BADEN_WUERTTEMBERG.access_mode == "direct_geojson"
    assert BADEN_WUERTTEMBERG.start.format == "iso_datetime"
    assert BADEN_WUERTTEMBERG.crs == "EPSG:4326"


def test_bw_fixture_is_within_germany_bounds():
    for feature in BW_PAYLOAD["features"]:
        for lon, lat in feature["geometry"]["coordinates"]:
            assert GERMANY_LON_RANGE[0] <= lon <= GERMANY_LON_RANGE[1], (lon, lat)
            assert GERMANY_LAT_RANGE[0] <= lat <= GERMANY_LAT_RANGE[1], (lon, lat)


@respx.mock
def test_german_roadworks_client_fetch_baden_wuerttemberg():
    respx.get(BADEN_WUERTTEMBERG.base_url).mock(
        return_value=httpx.Response(200, json=BW_PAYLOAD)
    )
    with GermanRoadworksClient() as germany:
        features = germany.fetch("Baden-Württemberg")
    assert len(features) == 3
    assert features[0]["properties"]["street"] == "L154 Albbruck-St. Blasien"


def test_sh_field_map_uses_gml_wfs_and_split_date_fields():
    assert SCHLESWIG_HOLSTEIN.access_mode == "gml_wfs"
    assert SCHLESWIG_HOLSTEIN.start.field == "_start_iso"
    assert SCHLESWIG_HOLSTEIN.end.field == "_end_iso"
    # Already reprojected client-side from the service's real EPSG:25832 -
    # see streetworks.ogc.germany's module docstring.
    assert SCHLESWIG_HOLSTEIN.crs == "EPSG:4326"


@respx.mock
def test_german_roadworks_client_fetch_schleswig_holstein_parses_gml():
    respx.get(SCHLESWIG_HOLSTEIN.base_url).mock(
        return_value=httpx.Response(200, content=SH_XML)
    )
    with GermanRoadworksClient() as germany:
        features = germany.fetch("Schleswig-Holstein")
    assert len(features) == 3
    names = {f["properties"]["Straßenname"] for f in features}
    assert names == {"L281", "B5", "G"}
    # Real GML MultiCurve/curveMember/LineString, reprojected to genuine
    # WGS84 (EPSG:25832 -> 4326) and within Germany's own bounds.
    l281 = next(f for f in features if f["properties"]["Straßenname"] == "L281")
    assert l281["geometry"]["type"] == "LineString"
    for lon, lat in l281["geometry"]["coordinates"]:
        assert GERMANY_LON_RANGE[0] <= lon <= GERMANY_LON_RANGE[1], (lon, lat)
        assert GERMANY_LAT_RANGE[0] <= lat <= GERMANY_LAT_RANGE[1], (lon, lat)
    # The real combined "X bis Y" field, split into synthetic properties.
    assert l281["properties"]["_start_iso"] == "2026-08-03T23:00:00+02:00"
    assert l281["properties"]["_end_iso"] == "2026-09-11T22:59:00+02:00"
    assert l281["properties"]["Dauer_der_Bauphase"] == (
        "2026-08-03 23:00:00 bis 2026-09-11 22:59:00"
    )
