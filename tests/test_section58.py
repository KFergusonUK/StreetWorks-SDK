"""Tests for the derived ``active_section_58`` Reporting helper."""

import httpx
import pytest
import respx
from pydantic import ValidationError

# The reducer validates rows against the generated v6 models; skip if absent.
pytest.importorskip("streetworks.streetmanager.models.v6.reporting")

from streetworks.streetmanager import (  # noqa: E402
    AsyncStreetManagerClient,
    StreetManagerClient,
)
from streetworks.streetmanager.environments import Environment  # noqa: E402
from streetworks.streetmanager.utils.reporting_utils import (  # noqa: E402
    summarise_active_section_58,
)

SANDBOX = "https://api.sandbox.manage-roadworks.service.gov.uk"
SECTION_58S = f"{SANDBOX}/v6/reporting/section-58s"


def mock_auth() -> None:
    respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        return_value=httpx.Response(
            200, json={"idToken": "t", "refreshToken": "r", "organisationReference": 1}
        )
    )


def _page(rows: list[dict]) -> httpx.Response:
    return httpx.Response(200, json={"pagination": {"has_next_page": False}, "rows": rows})


def _row(status: str, ref: str = "S58-TEST-001") -> dict:
    """A made-up Section58SummaryResponse-shaped row with all required fields."""
    return {
        "date_created": "2025-01-01T00:00:00Z",
        "section_58_reference_number": ref,
        "street": "EXAMPLE ROAD",
        "section_58_status": status,
        "section_58_status_string": status,
        "start_date": "2025-01-01T00:00:00Z",
        "end_date": "2026-01-01T00:00:00Z",
        "restriction_duration": "one_year",
        "restriction_duration_string": "one_year",
        "usrn": 99999999,
        "ha_organisation_name": "EXAMPLE COUNCIL",
    }


def test_in_force_is_active():
    result = summarise_active_section_58([_row("in_force", ref="live"), _row("closed")])
    assert result["active"] is True
    assert result["upcoming"] is False
    assert result["section_58"]["section_58_reference_number"] == "live"


def test_proposed_is_upcoming():
    result = summarise_active_section_58([_row("proposed", ref="next")])
    assert result["active"] is False
    assert result["upcoming"] is True
    assert result["section_58"]["section_58_reference_number"] == "next"


def test_nothing_active_or_upcoming():
    assert summarise_active_section_58([_row("closed")]) == {
        "active": False,
        "upcoming": False,
        "section_58": None,
    }


def test_malformed_row_is_rejected():
    """Rows are verified against the v6 model before reducing."""
    bad = _row("in_force")
    del bad["street"]  # required field
    with pytest.raises(ValidationError):
        summarise_active_section_58([bad])


@respx.mock
def test_section_58s_raw_fetch_sends_usrn():
    """The raw GET /section-58s method returns the response unchanged and always
    sends the required usrn (plus any extra filters)."""
    mock_auth()
    row = _row("in_force", ref="live")
    route = respx.get(SECTION_58S).mock(return_value=_page([row]))
    with StreetManagerClient("e@x.com", "pw", environment=Environment.SANDBOX) as sm:
        raw = sm.reporting.section_58s(99999999, section_58_status="in_force")

    assert raw["rows"] == [row]
    params = route.calls[0].request.url.params
    assert params.get("usrn") == "99999999"
    assert params.get("section_58_status") == "in_force"


@respx.mock
def test_active_section_58_over_http():
    mock_auth()
    route = respx.get(SECTION_58S).mock(return_value=_page([_row("in_force", ref="live")]))
    with StreetManagerClient("e@x.com", "pw", environment=Environment.SANDBOX) as sm:
        result = sm.reporting.active_section_58(99999999)

    assert result["active"] is True
    assert result["section_58"]["section_58_reference_number"] == "live"
    assert route.calls[0].request.url.params.get("usrn") == "99999999"


@respx.mock
async def test_async_active_section_58_over_http():
    mock_auth()
    route = respx.get(SECTION_58S).mock(return_value=_page([_row("proposed", ref="next")]))
    async with AsyncStreetManagerClient("e@x.com", "pw", environment=Environment.SANDBOX) as sm:
        result = await sm.reporting.active_section_58(99999999)

    assert result["active"] is False
    assert result["upcoming"] is True
    assert result["section_58"]["section_58_reference_number"] == "next"
    assert route.calls[0].request.url.params.get("usrn") == "99999999"
