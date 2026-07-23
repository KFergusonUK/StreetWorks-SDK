"""Tests for the generated D-TRO v4.0.0 data-model Pydantic models.

``VALID_SOURCE`` is a real DfT example payload ("suspension-one-way"), from
https://github.com/department-for-transport-public/D-TRO's own
``Latest version (v4.0.0)/Examples/`` directory - unwrapped to the bare
``{"source": ...}`` shape the JSON schema (and therefore ``Model``) itself
validates; the real file wraps it as ``{"schemaVersion": "4.0.0", "data":
{"source": ...}}``, an outer envelope the schema doesn't require or define.
"""

import copy

import pytest
from pydantic import ValidationError

pytest.importorskip("streetworks.dtro.models.v4_0_0")

from streetworks.dtro.models.v4_0_0 import Model  # noqa: E402

VALID_SOURCE = {
    "source": {
        "actionType": "new",
        "currentTraOwner": 9001,
        "comingIntoForceDate": "2025-01-01",
        "madeDate": "2025-01-01",
        "provision": [
            {
                "actionType": "new",
                "orderReportingPoint": "ttroTtmoNoticeAfterMaking",
                "provisionDescription": (
                    "Suspension of one way on Haydon Road, perhaps to be linked to "
                    "placement of temporary traffic signals"
                ),
                "reference": "b1618e6f-f65c-48c7-9cc7-45da9f45fbda",
                "comingIntoForceDate": "2025-01-01",
                "regulatedPlace": [
                    {
                        "description": "Haydon Road",
                        "linearGeometry": {
                            "version": 1,
                            "direction": "bidirectional",
                            "lateralPosition": "centreline",
                            "linestring": "SRID=27700;LINESTRING(323357 124578, 323338 124640)",
                            "representation": "representingZone",
                            "externalReference": [
                                {
                                    "lastUpdateDate": "2024-10-01T00:00:00",
                                    "uniqueStreetReferenceNumber": [{"usrn": 39605715}],
                                }
                            ],
                        },
                        "type": "regulationLocation",
                    }
                ],
                # Object, not a 1-item array - the real v4.0.0 breaking change
                # from v3.5.1 (see docs/DTRO_SCHEMAS.md).
                "regulation": {
                    "condition": {
                        "timeValidity": {
                            "start": "2024-10-23T08:00:00",
                            "end": "2024-10-23T20:00:00",
                            "isPlaceholderTro": False,
                        }
                    },
                    "generalRegulation": {"regulationType": "miscSuspensionOfOneWay"},
                    "isDynamic": False,
                    "timeZone": "Europe/London",
                },
            }
        ],
        "reference": "c962b51f-e1aa-416e-8f0b-aefe39a4c099",
        "section": "All sections",
        "traAffected": [9001],
        "traCreator": 9001,
        "troName": "DfT Example - TTRO road closure v2, Jan. 2025",
        "statementDescription": "Some description",
    }
}


def test_validates_real_source_payload():
    model = Model.model_validate(VALID_SOURCE)
    # RootModel: reach into the validated source
    source = model.root.source
    assert source.troName == "DfT Example - TTRO road closure v2, Jan. 2025"
    # regulation is a plain object here, not source.provision[0].regulation.root[0]
    # like v3.5.1 - the real array-to-object migration, confirmed by validating.
    regulation = source.provision[0].regulation
    assert regulation.generalRegulation.regulationType.value == "miscSuspensionOfOneWay"


def test_regulation_time_zone_is_now_a_fixed_value():
    # Real v4.0.0 change: regulation.timeZone is `"const": "Europe/London"`,
    # not a free string as in v3.5.1 - confirmed by round-tripping a bad value.
    bad = copy.deepcopy(VALID_SOURCE)
    bad["source"]["provision"][0]["regulation"]["timeZone"] = "America/New_York"
    with pytest.raises(ValidationError):
        Model.model_validate(bad)


def test_source_action_type_gained_full_revoke():
    # Real v4.0.0 addition: sourceActionType enum gained "fullRevoke".
    ok = copy.deepcopy(VALID_SOURCE)
    ok["source"]["actionType"] = "fullRevoke"
    Model.model_validate(ok)  # does not raise


def test_rejects_unknown_regulation_type():
    bad = copy.deepcopy(VALID_SOURCE)
    bad["source"]["provision"][0]["regulation"]["generalRegulation"]["regulationType"] = (
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


def test_client_validate_payload_helper_with_explicit_version():
    from streetworks.dtro import AsyncDTROClient, DTROClient

    assert DTROClient.validate_payload(VALID_SOURCE, version="v4_0_0") is VALID_SOURCE
    assert AsyncDTROClient.validate_payload(VALID_SOURCE, version="v4_0_0") is VALID_SOURCE

    with pytest.raises(ValidationError):
        bad = copy.deepcopy(VALID_SOURCE)
        del bad["source"]["troName"]
        DTROClient.validate_payload(bad, version="v4_0_0")
