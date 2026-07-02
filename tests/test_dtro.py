import json

import httpx
import respx

from streetworks.dtro import DTROClient, Environment

INTEGRATION = "https://dtro-integration.dft.gov.uk/v1"


def mock_token(expires_in: int = 1800) -> None:
    respx.post(f"{INTEGRATION}/oauth-generator").mock(
        return_value=httpx.Response(
            200, json={"access_token": "dtro-token", "expires_in": expires_in}
        )
    )


@respx.mock
def test_token_uses_basic_auth_and_is_cached():
    mock_token()
    token_route = respx.routes[0]
    respx.get(f"{INTEGRATION}/dtros/abc").mock(return_value=httpx.Response(200, json={"id": "abc"}))
    respx.get(f"{INTEGRATION}/dtros/def").mock(return_value=httpx.Response(200, json={"id": "def"}))

    with DTROClient("cid", "secret", app_id="app-uuid") as dtro:
        dtro.get_dtro("abc")
        dtro.get_dtro("def")

    assert token_route.call_count == 1  # cached for 30 minutes
    token_request = token_route.calls[0].request
    assert token_request.headers["authorization"].startswith("Basic ")  # D-TRO style
    assert "grant_type=client_credentials" in token_request.content.decode()


@respx.mock
def test_request_headers_include_app_id_correlation_and_bearer():
    mock_token()
    route = respx.get(f"{INTEGRATION}/dtros/abc").mock(
        return_value=httpx.Response(200, json={"id": "abc"})
    )
    with DTROClient("cid", "secret", app_id="app-uuid") as dtro:
        dtro.get_dtro("abc")
        dtro.get_dtro("abc")

    first, second = route.calls[0].request, route.calls[1].request
    assert first.headers["authorization"] == "Bearer dtro-token"
    assert first.headers["x-app-id"] == "app-uuid"
    assert first.headers["x-correlation-id"]
    # fresh correlation ID per request
    assert first.headers["x-correlation-id"] != second.headers["x-correlation-id"]


@respx.mock
def test_create_update_delete_and_events():
    mock_token()
    create = respx.post(f"{INTEGRATION}/dtros/createFromBody").mock(
        return_value=httpx.Response(201, json={"id": "new-id"})
    )
    respx.put(f"{INTEGRATION}/dtros/updateFromBody/new-id").mock(
        return_value=httpx.Response(200, json={"id": "new-id"})
    )
    respx.delete(f"{INTEGRATION}/dtros/new-id").mock(return_value=httpx.Response(204))
    events = respx.post(f"{INTEGRATION}/events").mock(
        return_value=httpx.Response(200, json={"events": [], "totalCount": 0})
    )

    payload = {"schemaVersion": "3.4.0", "data": {"source": {}}}
    with DTROClient("cid", "secret", app_id="app-uuid") as dtro:
        created = dtro.create_dtro(payload)
        dtro.update_dtro(created["id"], payload)
        dtro.search_events(since="2026-01-01T00:00:00", pageSize=50)
        dtro.delete_dtro(created["id"])

    assert json.loads(create.calls[0].request.content) == payload
    sent = json.loads(events.calls[0].request.content)
    assert sent == {"since": "2026-01-01T00:00:00", "pageSize": 50}


@respx.mock
def test_gzip_file_upload_compresses_content():
    mock_token()
    route = respx.post(f"{INTEGRATION}/dtros/createFromFile").mock(
        return_value=httpx.Response(201, json={"id": "new-id"})
    )
    raw = json.dumps({"schemaVersion": "3.4.0", "data": {}}).encode()
    with DTROClient("cid", "secret", app_id="app-uuid") as dtro:
        dtro.create_dtro_from_file(raw, gzip=True)

    body = route.calls[0].request.content
    assert b"dtro.json.gz" in body
    # gzip magic bytes appear in the multipart payload
    assert b"\x1f\x8b" in body


@respx.mock
def test_production_environment_url():
    respx.post("https://dtro.dft.gov.uk/v1/oauth-generator").mock(
        return_value=httpx.Response(200, json={"access_token": "t", "expires_in": 1800})
    )
    route = respx.get("https://dtro.dft.gov.uk/v1/dtros/all").mock(
        return_value=httpx.Response(200, json={"url": "https://signed.example/all.csv"})
    )
    with DTROClient("cid", "secret", environment=Environment.PRODUCTION) as dtro:
        result = dtro.get_all_dtros_url()
    assert "signed.example" in result["url"]
    assert route.call_count == 1
