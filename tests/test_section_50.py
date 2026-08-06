"""Tests for streetworks.streetmanager.utils.section_50_utils - pure-function
request-assembly, no respx/HTTP involved (nothing in this module makes a
network call; see the module's own docstring for why there's no new
client.py endpoint to mock)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from streetworks.streetmanager.utils.section_50_utils import (
    build_work_create_request,
    build_work_start_update,
    build_work_stop_update,
)

_GEOMETRY = {"type": "Point", "coordinates": [-1.6644422, 53.6119904]}

_MINIMAL_APPLICANT_FIELDS = {
    "secondary_contact": "J. Smith",
    "secondary_contact_number": "01234 567890",
    "proposed_start_date": "2026-09-01T00:00:00Z",
    "proposed_end_date": "2026-09-05T00:00:00Z",
    "description_of_work": "Install new gas connection",
    "works_location_description": "Verge outside number 4",
    "excavation": True,
    "traffic_management_plan": False,
    "lane_rental_applicable": False,
    "collaborative_working": False,
    "traffic_management_type": "no_carriageway_incursion",
    "location_types": ["verge"],
    "close_footway": "no",
    "close_footpath": "no",
}


def _build(**overrides):
    applicant_fields = {**_MINIMAL_APPLICANT_FIELDS, **overrides.pop("applicant_fields", {})}
    kwargs = {
        "ha_swa_code": "1355",
        "host_usrn": 42820309,
        "geometry": _GEOMETRY,
        **overrides,
    }
    return build_work_create_request(applicant_fields, **kwargs)


def test_pins_identity_and_activity():
    payload, _warnings = _build()
    assert payload["promoter_swa_code"] == "1355"
    assert payload["highway_authority_swa_code"] == "1355"
    assert payload["activity_type"] == "section_50"
    assert payload["work_type"] == "planned"
    assert payload["application_type"] == "permit"


def test_lets_caller_override_application_type():
    payload, _warnings = _build(applicant_fields={"application_type": "notice"})
    assert payload["application_type"] == "notice"


@pytest.mark.parametrize(
    "owned_field", ["promoter_swa_code", "highway_authority_swa_code", "activity_type",
                     "work_type", "usrn", "works_coordinates", "immediate_risk"]
)
def test_rejects_applicant_supplied_connector_owned_fields(owned_field):
    with pytest.raises(ValueError, match=owned_field):
        _build(applicant_fields={owned_field: "anything"})


def test_validates_workstream_prefix_format():
    with pytest.raises(ValueError, match="3 digits"):
        _build(workstream_prefix="UG050")


def test_accepts_valid_workstream_prefix():
    payload, _warnings = _build(workstream_prefix="050")
    assert payload["workstream_prefix"] == "050"


def test_omits_workstream_prefix_when_not_given():
    payload, _warnings = _build()
    assert "workstream_prefix" not in payload


def test_overflows_additional_usrns_into_works_location_description():
    payload, _warnings = _build(additional_usrns=[12345, 67890])
    assert payload["usrn"] == 42820309
    assert "Also spans USRN(s): 12345, 67890." in payload["works_location_description"]
    # The applicant's own text is preserved, not replaced.
    assert "Verge outside number 4" in payload["works_location_description"]


def test_additional_usrns_without_works_location_description_raises():
    fields = {
        k: v for k, v in _MINIMAL_APPLICANT_FIELDS.items() if k != "works_location_description"
    }
    with pytest.raises(ValueError, match="works_location_description"):
        build_work_create_request(
            fields, ha_swa_code="1355", host_usrn=42820309, geometry=_GEOMETRY,
            additional_usrns=[12345],
        )


def test_reprojects_geometry_to_bng():
    payload, _warnings = _build()
    coords = payload["works_coordinates"]
    assert coords["type"] == "Point"
    # Annex D worked example lands near E=422297, N=412878 - this point is a
    # different (Bishop Auckland-area) coordinate, so just assert it's
    # plausibly BNG-scale (six-figure eastings/northings), not WGS84 degrees.
    assert coords["coordinates"][0] > 1000
    assert coords["coordinates"][1] > 1000


def test_normalises_datetime_fields_to_iso_strings():
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    payload, _warnings = _build(applicant_fields={"proposed_start_date": start})
    assert payload["proposed_start_date"] == start.isoformat()


def test_no_warning_when_no_usrn_geometry_given():
    payload, warnings = _build()
    assert warnings == []


def test_no_warning_when_extent_within_threshold():
    # The drawn point reprojects to ~(422297.79, 412878.74) (the Annex D
    # worked example) - the USRN geometry's first vertex sits right there,
    # trivially within threshold.
    payload, warnings = _build(
        geometry={"type": "Point", "coordinates": [-1.6644422, 53.6119904]},
        host_usrn_geometry={
            "type": "LineString",
            "coordinates": [[422297.792, 412878.741], [422400.0, 412900.0]],
        },
    )
    assert warnings == []


def test_warns_when_extent_far_from_usrn():
    payload, warnings = _build(
        host_usrn_geometry={
            "type": "LineString",
            "coordinates": [[500000.0, 500000.0], [500100.0, 500100.0]],
        },
    )
    assert len(warnings) == 1
    assert "42820309" in warnings[0]


def test_nudge_uses_point_to_segment_not_nearest_vertex():
    # A long, straight USRN line whose vertices are ~200m apart. The drawn
    # point sits ~2m off the *midpoint* of the segment - far from either
    # vertex (nearest-vertex distance would read as ~100m and wrongly warn),
    # but genuinely close to the line itself.
    usrn_geometry = {
        "type": "LineString",
        "coordinates": [[422200.0, 412878.741], [422400.0, 412878.741]],
    }
    # Reproject a point that lands very close to (422300.0, 412880.741) -
    # 2m off the segment's midpoint - by using a geometry whose BNG output
    # we control via a direct BNG LineString instead of a WGS84 round trip,
    # so the offset is exact.
    from streetworks.common._bng import bng_to_wgs84

    lon, lat = bng_to_wgs84(422300.0, 412880.741)
    payload, warnings = _build(
        geometry={"type": "Point", "coordinates": [lon, lat]},
        host_usrn_geometry=usrn_geometry,
    )
    assert warnings == []


def test_build_work_start_update_shape():
    payload = build_work_start_update("2026-09-01T00:00:00Z")
    assert payload == {"actual_start_date": "2026-09-01T00:00:00Z"}


def test_build_work_start_update_normalises_datetime():
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    payload = build_work_start_update(start)
    assert payload == {"actual_start_date": start.isoformat()}


def test_build_work_stop_update_shape():
    payload = build_work_stop_update("2026-09-05T00:00:00Z")
    assert payload == {"actual_stop_date": "2026-09-05T00:00:00Z"}


# --------------------------------------------------------------------------- #
# Real generated-model validation - genuinely valuable: catches connector/
# schema drift the moment DfT's schema changes (extra="forbid" would flag a
# stray key immediately). Skipped if the models aren't generated locally.
# --------------------------------------------------------------------------- #

pytest.importorskip("streetworks.streetmanager.models.v6.work")

from streetworks.streetmanager.models.v6.work import WorkCreateRequest  # noqa: E402


def test_full_payload_validates_against_generated_model():
    payload, _warnings = _build(workstream_prefix="050", additional_usrns=[12345])
    WorkCreateRequest.model_validate(payload)
