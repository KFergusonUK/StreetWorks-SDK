import base64
import json
import time

import httpx
import respx

from streetworks.streetmanager import (
    ApiVersion,
    AsyncStreetManagerClient,
    Environment,
    StreetManagerClient,
)

SANDBOX = "https://api.sandbox.manage-roadworks.service.gov.uk"


def make_jwt(expires_in: float) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = (
        base64.urlsafe_b64encode(json.dumps({"exp": time.time() + expires_in}).encode())
        .rstrip(b"=")
        .decode()
    )
    return f"{header}.{payload}.sig"


def auth_response(expires_in: float = 3600, id_token: str | None = None) -> dict:
    return {
        "idToken": id_token or make_jwt(expires_in),
        "accessToken": "access",
        "refreshToken": "refresh",
        "organisationReference": "1234",
    }


@respx.mock
def test_forward_plans_hits_reporting_endpoint_with_filters():
    respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        return_value=httpx.Response(200, json=auth_response())
    )
    route = respx.get(f"{SANDBOX}/v6/reporting/forward-plans").mock(
        return_value=httpx.Response(200, json={"pagination": {"has_next_page": False}, "rows": []})
    )

    with StreetManagerClient("user@example.com", "pw") as sm:
        sm.reporting.forward_plans(usrn=12345)

    sent = route.calls[0].request
    assert sent.url.params["usrn"] == "12345"


@respx.mock
def test_authenticates_once_and_sends_token_header():
    auth_route = respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        return_value=httpx.Response(200, json=auth_response())
    )
    work_route = respx.get(f"{SANDBOX}/v6/work/works/ABC123").mock(
        return_value=httpx.Response(200, json={"work_reference_number": "ABC123"})
    )
    respx.get(f"{SANDBOX}/v6/reporting/permits").mock(
        return_value=httpx.Response(200, json={"rows": []})
    )

    with StreetManagerClient("user@example.com", "pw") as sm:
        work = sm.work.get_work("ABC123")
        sm.reporting.permits(status="submitted")

    assert work["work_reference_number"] == "ABC123"
    assert auth_route.call_count == 1  # token reused across APIs
    sent = work_route.calls[0].request
    assert sent.headers["token"]
    assert sm.organisation_reference == "1234"
    # auth body uses the documented field names
    auth_body = json.loads(auth_route.calls[0].request.content)
    assert auth_body == {"emailAddress": "user@example.com", "password": "pw"}


@respx.mock
def test_expired_token_refreshes_via_party_api():
    respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        return_value=httpx.Response(200, json=auth_response(expires_in=1))  # already stale
    )
    refresh_route = respx.post(f"{SANDBOX}/v6/party/refresh").mock(
        return_value=httpx.Response(200, json=auth_response(expires_in=3600))
    )
    respx.get(f"{SANDBOX}/v6/work/works/X").mock(return_value=httpx.Response(200, json={}))

    with StreetManagerClient("user@example.com", "pw") as sm:
        sm.work.get_work("X")  # triggers auth (stale token)
        sm.work.get_work("X")  # stale -> refresh

    assert refresh_route.call_count == 1
    refresh_body = json.loads(refresh_route.calls[0].request.content)
    assert refresh_body == {"refreshToken": "refresh"}


@respx.mock
def test_failed_refresh_falls_back_to_reauthentication():
    auth_route = respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        side_effect=[
            httpx.Response(200, json=auth_response(expires_in=1)),
            httpx.Response(200, json=auth_response(expires_in=3600)),
        ]
    )
    respx.post(f"{SANDBOX}/v6/party/refresh").mock(
        return_value=httpx.Response(401, json={"message": "Authentication failed"})
    )
    respx.get(f"{SANDBOX}/v6/work/works/X").mock(return_value=httpx.Response(200, json={}))

    with StreetManagerClient("user@example.com", "pw") as sm:
        sm.work.get_work("X")
        sm.work.get_work("X")

    assert auth_route.call_count == 2


@respx.mock
def test_v7_and_production_urls():
    respx.post("https://api.manage-roadworks.service.gov.uk/v7/work/authenticate").mock(
        return_value=httpx.Response(200, json=auth_response())
    )
    route = respx.get("https://api.manage-roadworks.service.gov.uk/v7/geojson/works").mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    with StreetManagerClient(
        "u@e.com", "pw", environment=Environment.PRODUCTION, version=ApiVersion.V7
    ) as sm:
        sm.geojson.works()
    assert route.call_count == 1


@respx.mock
async def test_async_client_roundtrip():
    respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        return_value=httpx.Response(200, json=auth_response())
    )
    respx.get(f"{SANDBOX}/v6/reporting/permits").mock(
        return_value=httpx.Response(200, json={"rows": [{"permit_status": "submitted"}]})
    )
    async with AsyncStreetManagerClient("u@e.com", "pw") as sm:
        permits = await sm.reporting.permits(status="submitted")
    assert permits["rows"][0]["permit_status"] == "submitted"


@respx.mock
def test_authenticate_returns_org_reference():
    auth_route = respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        return_value=httpx.Response(200, json=auth_response())
    )
    with StreetManagerClient("user@example.com", "pw") as sm:
        org = sm.authenticate()
    assert org == "1234"
    assert auth_route.call_count == 1


@respx.mock
def test_generic_escape_hatch_for_unwrapped_endpoints():
    respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        return_value=httpx.Response(200, json=auth_response())
    )
    route = respx.post(f"{SANDBOX}/v6/work/section-58s").mock(
        return_value=httpx.Response(200, json={"section_58_reference_number": "S58-1"})
    )
    with StreetManagerClient("u@e.com", "pw") as sm:
        result = sm.work.post("section-58s", json={"usrn": 123})
    assert result["section_58_reference_number"] == "S58-1"
    assert route.call_count == 1
