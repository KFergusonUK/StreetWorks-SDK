"""Tests for the derived ``is_traffic_sensitive`` Street Lookup helper."""

import httpx
import pytest
import respx
from pydantic import ValidationError

# The reducer validates the response against the generated v6 models; skip if absent.
pytest.importorskip("streetworks.streetmanager.models.v6.lookup")

from streetworks.streetmanager import (  # noqa: E402
    AsyncStreetManagerClient,
    StreetManagerClient,
)
from streetworks.streetmanager.environments import Environment  # noqa: E402
from streetworks.streetmanager.utils.lookup_utils import (  # noqa: E402
    summarise_traffic_sensitive,
)

SANDBOX = "https://api.sandbox.manage-roadworks.service.gov.uk"
USRN = 11700550
STREET = f"{SANDBOX}/v6/lookup/nsg/streets/{USRN}"


def mock_auth() -> None:
    respx.post(f"{SANDBOX}/v6/work/authenticate").mock(
        return_value=httpx.Response(
            200, json={"idToken": "t", "refreshToken": "r", "organisationReference": 1}
        )
    )


def _asd(code: int, **overrides) -> dict:
    """A made-up AdditionalSpecialDesignationsResponse-shaped row."""
    row = {
        "street_special_desig_code": code,
        "special_desig_description": f"DESIGNATION {code}",
        "whole_road": True,
    }
    row.update(overrides)
    return row


def _street(traffic_sensitive: bool, asds: list[dict] | None = None) -> dict:
    """A StreetResponse-shaped street with all required fields."""
    return {
        "usrn": USRN,
        "street_descriptor": "EXAMPLE ROAD",
        "area": "EXAMPLE AREA",
        "town": "EXAMPLE TOWN",
        "authority": "EXAMPLE COUNCIL",
        "authority_swa_code": "1355",
        "road_category": 5,
        "reinstatement_types": [],
        "traffic_sensitive": traffic_sensitive,
        "primary_notice_authorities": [],
        "interest_authorities": [],
        "additional_special_designations_response": asds or [],
    }


def test_blanket_flag_is_sensitive():
    result = summarise_traffic_sensitive(_street(True))
    assert result["is_traffic_sensitive"] is True
    assert result["designations"] == []


def test_code_2_designation_is_sensitive_even_when_flag_false():
    ts = _asd(
        2,
        special_desig_description="TRAFFIC SENSITIVE - BUS ROUTE",
        special_desig_start_time=700,
        special_desig_end_time=1900,
    )
    result = summarise_traffic_sensitive(_street(False, [ts]))
    assert result["is_traffic_sensitive"] is True
    assert result["designations"] == [ts]  # raw row, time window preserved
    assert result["designations"][0]["special_desig_start_time"] == 700


def test_non_traffic_sensitive_designation_is_not_sensitive():
    result = summarise_traffic_sensitive(_street(False, [_asd(3)]))
    assert result["is_traffic_sensitive"] is False
    assert result["designations"] == []


def test_malformed_designation_is_rejected():
    """Each ASD entry is verified against the v6 model before reducing."""
    bad = _asd(2)
    del bad["street_special_desig_code"]  # required field
    with pytest.raises(ValidationError):
        summarise_traffic_sensitive(_street(False, [bad]))


@respx.mock
def test_is_traffic_sensitive_over_http():
    mock_auth()
    ts = _asd(2, special_desig_start_time=700, special_desig_end_time=1900)
    route = respx.get(STREET).mock(
        return_value=httpx.Response(200, json=_street(True, [ts, _asd(3)]))
    )
    with StreetManagerClient("e@x.com", "pw", environment=Environment.SANDBOX) as sm:
        result = sm.lookup.is_traffic_sensitive(USRN)

    assert result["is_traffic_sensitive"] is True
    assert result["designations"] == [ts]
    assert route.calls[0].request.url.path.endswith(f"/nsg/streets/{USRN}")


@respx.mock
async def test_async_is_traffic_sensitive_over_http():
    mock_auth()
    route = respx.get(STREET).mock(return_value=httpx.Response(200, json=_street(False, [_asd(3)])))
    async with AsyncStreetManagerClient("e@x.com", "pw", environment=Environment.SANDBOX) as sm:
        result = await sm.lookup.is_traffic_sensitive(USRN)

    assert result["is_traffic_sensitive"] is False
    assert result["designations"] == []
    assert route.calls[0].request.url.path.endswith(f"/nsg/streets/{USRN}")
