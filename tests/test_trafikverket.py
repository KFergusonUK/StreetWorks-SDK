"""Tests for the Sweden (Trafikverket) adapter.

**Pending live verification** - see the module docstring in
``streetworks.datex2.trafikverket``. The fixture
(``trafikverket_situations.json``) is synthetic, not real data: only the
endpoint, auth-failure shape, ``Situation`` object name, and schema version
have been confirmed live (an invalid-key probe). It exists to exercise the
bespoke request/parse path onto the shared ``Situation``/``SituationRecord``
models, and - deliberately - to demonstrate that ``iter_roadworks()``
returns nothing even for a deviation a human would recognise as roadworks
(``MessageType: "Vägarbete"``), since the real roadworks-identifying
``MessageType``/``MessageCode`` value is genuinely unconfirmed (see module
docstring).
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.datex2 import TrafikverketClient
from streetworks.datex2.trafikverket import BASE_URL, DATA_PATH, build_request, parse_situations

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "trafikverket_situations.json"
FIXTURE_JSON = json.loads(FIXTURE_PATH.read_text())


def test_build_request_embeds_api_key_and_schema_version():
    body = build_request("my-key")
    assert 'authenticationkey="my-key"' in body
    assert 'objecttype="Situation"' in body
    assert 'schemaversion="1.5"' in body


def test_parse_situations_maps_deviations_to_situation_records():
    situations = parse_situations(FIXTURE_JSON)
    assert [s.id for s in situations] == ["SE-TV-SIT-1001", "SE-TV-SIT-2002"]

    roadwork = situations[0].records[0]
    assert roadwork.id == "SE-TV-DEV-1001"
    assert roadwork.record_type == "Vägarbete"  # MessageType, preserved verbatim
    assert roadwork.source_name == "Vägarbete"
    assert roadwork.location.point == (59.3293, 18.0686)
    assert roadwork.location.road_number == "E4"
    assert roadwork.validity.overall_start.isoformat() == "2026-07-10T05:00:00+02:00"
    assert roadwork.validity.overall_end.isoformat() == "2026-09-01T18:00:00+02:00"
    assert roadwork.raw["MessageCode"] == "roadWork"


def test_is_roadworks_is_honestly_false_for_unconfirmed_message_type():
    """Core documented gap: MessageType "Vägarbete" is exactly what a real
    Swedish roadworks deviation would carry, but since the real DATEX-style
    discriminator value is unconfirmed, record_type isn't in
    ROADWORKS_TYPES, so is_roadworks is False - honestly, not silently
    guessed. See module docstring."""
    situations = parse_situations(FIXTURE_JSON)
    assert situations[0].records[0].is_roadworks is False
    assert situations[0].roadworks == []


def test_iter_roadworks_returns_nothing_pending_phase_2():
    situations = parse_situations(FIXTURE_JSON)
    assert all(not s.roadworks for s in situations)


def test_client_requires_api_key():
    with pytest.raises(ValueError):
        TrafikverketClient(api_key="")


@respx.mock
def test_client_fetches_and_parses():
    respx.post(f"{BASE_URL}/{DATA_PATH}").mock(return_value=httpx.Response(200, json=FIXTURE_JSON))
    with TrafikverketClient(api_key="test-key") as trafikverket:
        situations = list(trafikverket.iter_situations())
    assert len(situations) == 2

    request = respx.calls.last.request
    assert 'authenticationkey="test-key"' in request.content.decode()


@respx.mock
def test_client_iter_roadworks_empty_pending_phase_2():
    respx.post(f"{BASE_URL}/{DATA_PATH}").mock(return_value=httpx.Response(200, json=FIXTURE_JSON))
    with TrafikverketClient(api_key="test-key") as trafikverket:
        assert list(trafikverket.iter_roadworks()) == []
