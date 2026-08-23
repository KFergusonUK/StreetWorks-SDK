"""Tests for streetworks.necompass - wiring only. Converter behaviour is
tested in test_common_necompass.py against the same real fixtures.

Fixtures are real New England Compass C2C XML (tests/fixtures/necompass_*.xml),
captured live 2026-08-23 from the genuinely keyless
https://nec-por.ne-compass.com/NEC.XmlDataPortal/api/c2c endpoint - see
streetworks.necompass.client's own module docstring for the full
investigation, including why laneClosureData and incidentData are both
needed for complete coverage.
"""

from pathlib import Path

import httpx
import respx

from streetworks.necompass import BASE_URL, NECompassClient

LANE_CLOSURES_FIXTURE = (
    Path(__file__).parent / "fixtures" / "necompass_maine_lane_closures.xml"
).read_bytes()
INCIDENTS_FIXTURE = (
    Path(__file__).parent / "fixtures" / "necompass_newhampshire_incidents.xml"
).read_bytes()


@respx.mock
def test_iter_lane_closures_yields_every_real_record_unfiltered():
    respx.get(BASE_URL, params={"networks": "Maine", "dataTypes": "laneClosureData"}).mock(
        return_value=httpx.Response(200, content=LANE_CLOSURES_FIXTURE)
    )
    with NECompassClient() as client:
        records = list(client.iter_lane_closures("Maine"))
    assert len(records) == 3
    assert {r["id"] for r in records} == {"ME26-002917", "ME26-002801", "ME26-002895"}
    # The real SpecialEvent record is included here - iter_lane_closures
    # doesn't filter, unlike iter_roadworks.
    assert {r["type"] for r in records} == {"RoadMaintenance", "SpecialEvent"}


@respx.mock
def test_iter_incidents_yields_every_real_record_unfiltered():
    respx.get(
        BASE_URL, params={"networks": "NewHampshire", "dataTypes": "incidentData"}
    ).mock(return_value=httpx.Response(200, content=INCIDENTS_FIXTURE))
    with NECompassClient() as client:
        records = list(client.iter_incidents("NewHampshire"))
    assert len(records) == 1
    assert records[0]["id"] == "NH24-003127"
    assert records[0]["type"] == "Construction"
    assert records[0]["kind"] == "incident"


@respx.mock
def test_iter_roadworks_combines_both_resources_filtered():
    respx.get(BASE_URL, params={"networks": "Maine", "dataTypes": "laneClosureData"}).mock(
        return_value=httpx.Response(200, content=LANE_CLOSURES_FIXTURE)
    )
    # Maine has no real incidentData records in this trimmed fixture set -
    # an empty real response is a genuine possible shape.
    respx.get(BASE_URL, params={"networks": "Maine", "dataTypes": "incidentData"}).mock(
        return_value=httpx.Response(
            200,
            content=b'<status xmlns="http://its.gov/c2c_icd">'
            b'<incidentData><net id="Maine" name="Maine"/></incidentData></status>',
        )
    )
    with NECompassClient() as client:
        roadworks = list(client.iter_roadworks("Maine"))
    # SpecialEvent (ME26-002895) is excluded; only the two real roadworks
    # records remain.
    assert {r["id"] for r in roadworks} == {"ME26-002917", "ME26-002801"}
    assert all(r["type"] in ("Construction", "RoadMaintenance", "BridgeMaintenance", "BridgeOut")
               for r in roadworks)
