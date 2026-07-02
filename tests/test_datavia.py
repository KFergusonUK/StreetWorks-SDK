
import httpx
import pytest
import respx

from streetworks.datavia import (
    BASIC_SERVICE_URL,
    OIDC_SERVICE_URL,
    TOKEN_URL,
    DataViaClient,
    Layer,
    filters,
)

GEOJSON_EMPTY = {"type": "FeatureCollection", "features": []}


def make_client(**kwargs) -> DataViaClient:
    defaults = {"username": "user", "password": "pass"}
    defaults.update(kwargs)
    return DataViaClient(**defaults)


def test_requires_exactly_one_auth_method():
    with pytest.raises(ValueError):
        DataViaClient()
    with pytest.raises(ValueError):
        DataViaClient(username="u", password="p", client_id="c", client_secret="s")


@respx.mock
def test_street_by_usrn_posts_doc_shaped_getfeature():
    route = respx.post(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(200, json=GEOJSON_EMPTY)
    )
    with make_client() as dv:
        result = dv.street_by_usrn(4401245)

    assert result == GEOJSON_EMPTY
    request = route.calls[0].request
    assert request.headers["authorization"].startswith("Basic ")
    assert request.headers["content-type"] == "text/xml"
    body = request.content.decode()
    # Matches the documented POST example shape
    assert 'service="WFS" version="1.1.0"' in body
    assert 'outputFormat="geojson"' in body
    assert 'typeName="ms:StreetLines"' in body
    assert "<ogc:PropertyName>usrn</ogc:PropertyName>" in body
    assert "<ogc:Literal>4401245</ogc:Literal>" in body


@respx.mock
def test_oauth_client_credentials_flow():
    token_route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "tok123", "expires_in": 3600}
        )
    )
    service_route = respx.post(OIDC_SERVICE_URL).mock(
        return_value=httpx.Response(200, json=GEOJSON_EMPTY)
    )
    with DataViaClient(client_id="cid", client_secret="secret") as dv:
        dv.street_by_usrn(1)
        dv.street_by_usrn(2)

    assert token_route.call_count == 1  # token cached across calls
    token_body = token_route.calls[0].request.content.decode()
    assert "grant_type=client_credentials" in token_body
    assert "client_id=cid" in token_body  # DataVIA style: creds in body
    assert service_route.calls[0].request.headers["authorization"] == "Bearer tok123"


@respx.mock
def test_dwithin_and_combined_filters():
    route = respx.post(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(200, json=GEOJSON_EMPTY)
    )
    fragment = filters.and_(
        filters.dwithin_point(-0.138405, 50.825181, 100),
        filters.property_equals("special_designation_code", 2),
    )
    with make_client() as dv:
        dv.get_features(Layer.SPECIAL_DESIGNATION_LINES, filter_fragment=fragment)

    body = route.calls[0].request.content.decode()
    assert "<ogc:AND>" in body
    assert "<ogc:Distance units='m'>100</ogc:Distance>" in body
    assert "<ogc:Literal>2</ogc:Literal>" in body
    assert 'typeName="ms:StreetSpecialDesignationLines"' in body


@respx.mock
def test_kvp_get_with_paging_params():
    route = respx.get(BASIC_SERVICE_URL).mock(
        return_value=httpx.Response(200, json=GEOJSON_EMPTY)
    )
    with make_client() as dv:
        dv.get_features_kvp(Layer.ESU_STREETS, start_index=0, count=50)

    url = str(route.calls[0].request.url)
    assert "typenames=ms%3AESUStreets" in url
    assert "startIndex=0" in url
    assert "count=50" in url
    assert "srsName=EPSG%3A27700" in url


@respx.mock
def test_iter_features_pages_until_short_page():
    def page(request):
        body = request.content.decode()
        start = int(body.split("<wfs:StartIndex>")[1].split("<")[0])
        n = 2 if start == 0 else 1  # second page is short -> stop
        features = [{"type": "Feature", "properties": {"i": start + j}} for j in range(n)]
        return httpx.Response(
            200, json={"type": "FeatureCollection", "features": features}
        )

    respx.post(BASIC_SERVICE_URL).mock(side_effect=page)
    with make_client() as dv:
        collected = list(dv.iter_features(Layer.STREET_LINES, page_size=2))
    assert [f["properties"]["i"] for f in collected] == [0, 1, 2]


def test_polygon_ring_auto_closes_and_escapes():
    ring = [(-0.14, 50.82), (-0.14, 50.83), (-0.13, 50.83)]
    xml = filters.intersects_polygon(ring)
    coords = xml.split("<gml:coordinates>")[1].split("</gml:coordinates>")[0]
    pairs = coords.split(",")
    assert pairs[0] == pairs[-1]  # closed ring
    assert "&lt;" in filters.property_equals("usrn", "<evil>")
