"""Tests for the generated D-TRO v3.5.1 data-model Pydantic models."""

import copy

import pytest
from pydantic import ValidationError

pytest.importorskip("streetworks.dtro.models.v3_5_1")

from streetworks.dtro.models.v3_5_1 import Model  # noqa: E402

VALID_SOURCE = {
    "source": {
        "actionType": "new",
        "currentTraOwner": 1585,
        "reference": "DUR-TRO-2026-001",
        "section": "1",
        "statementDescription": "No U-turn on the example road",
        "traAffected": [1585],
        "traCreator": 1585,
        "troName": "Durham Example Banned U-Turn Order 2026",
        "provision": [
            {
                "actionType": "new",
                "orderReportingPoint": "permanentNoticeOfMaking",
                "provisionDescription": "Banned U turn - example",
                "reference": "b1618e6f-f65c-48c7-9cc7-45da9f45fbdc",
                "comingIntoForceDate": "2026-01-01",
                "regulatedPlace": [
                    {
                        "description": "Example road segment",
                        "type": "regulationLocation",
                        "directedLinear": {
                            "version": 1,
                            "directedLineString": (
                                "SRID=27700;LINESTRING(524811 180305, 524804 180305)"
                            ),
                        },
                    }
                ],
                "regulation": [
                    {
                        "isDynamic": False,
                        "timeZone": "Europe/London",
                        "generalRegulation": {"regulationType": "bannedMovementNoUTurn"},
                        "condition": [
                            {
                                "timeValidity": {
                                    "start": "2026-01-01T00:00:00Z",
                                    "isPlaceholderTro": False,
                                }
                            }
                        ],
                    }
                ],
            }
        ],
    }
}


def test_validates_real_source_payload():
    model = Model.model_validate(VALID_SOURCE)
    # RootModel: reach into the validated source
    source = model.root.source
    assert source.troName == "Durham Example Banned U-Turn Order 2026"
    regulation = source.provision[0].regulation.root[0]
    assert regulation.generalRegulation.regulationType.value == "bannedMovementNoUTurn"


def test_rejects_unknown_regulation_type():
    bad = copy.deepcopy(VALID_SOURCE)
    bad["source"]["provision"][0]["regulation"][0]["generalRegulation"]["regulationType"] = (
        "notARealRegulationType"
    )
    with pytest.raises(ValidationError):
        Model.model_validate(bad)


def test_rejects_missing_required_field():
    bad = copy.deepcopy(VALID_SOURCE)
    del bad["source"]["troName"]
    with pytest.raises(ValidationError):
        Model.model_validate(bad)


def test_rejects_wrong_type():
    bad = copy.deepcopy(VALID_SOURCE)
    bad["source"]["currentTraOwner"] = "not-an-integer"
    with pytest.raises(ValidationError):
        Model.model_validate(bad)


def test_client_validate_payload_helper():
    from streetworks.dtro import AsyncDTROClient, DTROClient

    # VALID_SOURCE is v3.5.1-shaped (regulation as a 1-item array) - the
    # client's default is now v4.0.0 (see client.py), so this fixture must
    # name its version explicitly, exactly the trap the default's own
    # docstring warns about.
    assert DTROClient.validate_payload(VALID_SOURCE, version="v3_5_1") is VALID_SOURCE
    assert AsyncDTROClient.validate_payload(VALID_SOURCE, version="v3_5_1") is VALID_SOURCE

    with pytest.raises(ValidationError, match="v3_5_1 Model"):
        bad = copy.deepcopy(VALID_SOURCE)
        del bad["source"]["troName"]
        DTROClient.validate_payload(bad, version="v3_5_1")

    with pytest.raises(ValueError, match="No generated D-TRO models"):
        DTROClient.validate_payload(VALID_SOURCE, version="v9_9_9")
