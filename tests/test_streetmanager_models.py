"""Tests for the generated Street Manager v6 Pydantic models.

Skipped unless the models have been generated (they are produced from the DfT
swagger specs by ``scripts/generate_models.py`` and are not committed
upstream). ``CommentCreateRequest`` is a small, stable model: a required
string (``detail``), a required enum (``topic``), and ``extra="forbid"``.

The work fixture (tests/fixtures/streetmanager_work_asd_geometry_sandbox.json)
is a real sandbox ``GET /works/{wrn}`` response captured 2026-10-28, for a PAA
created 2026-10-09 - after V6.17.24 added ``asd_coordinate_geometry`` to ASD
rows. Contact names, emails and numbers are redacted; nothing else is changed.
Against the models generated before this release it fails with 15
``extra_forbidden`` errors - the key is present on every ASD row, null or not.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

pytest.importorskip("streetworks.streetmanager.models.v6.work")

from streetworks.streetmanager.models.v6.geojson import WorkFeature  # noqa: E402
from streetworks.streetmanager.models.v6.work import (  # noqa: E402
    CommentCreateRequest,
    CommentTopic,
    PermitASDResponse,
    SiteDetails,
    WorkResponse,
)

VALID_COMMENT = {"detail": "Access needed to the loading bay", "topic": "GENERAL"}
WORK_WITH_ASD_GEOMETRY = json.loads(
    (Path(__file__).parent / "fixtures" / "streetmanager_work_asd_geometry_sandbox.json").read_text(
        encoding="utf-8"
    )
)


def test_validates_comment_payload():
    comment = CommentCreateRequest.model_validate(VALID_COMMENT)
    assert comment.detail == "Access needed to the loading bay"
    assert comment.topic == CommentTopic.GENERAL


def test_rejects_unknown_topic():
    with pytest.raises(ValidationError):
        CommentCreateRequest.model_validate({**VALID_COMMENT, "topic": "NOT_A_TOPIC"})


def test_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        CommentCreateRequest.model_validate({"topic": "GENERAL"})


def test_rejects_unknown_field():
    with pytest.raises(ValidationError):
        CommentCreateRequest.model_validate({**VALID_COMMENT, "foo": "bar"})


def test_validates_real_work_with_asd_coordinate_geometry():
    work = WorkResponse.model_validate(WORK_WITH_ASD_GEOMETRY)
    asds = work.active_permit.permit_asds + work.active_permit.permit_not_selected_asds
    geometries = [a.asd_coordinate_geometry for a in asds if a.asd_coordinate_geometry]
    assert len(geometries) == 8
    # The spec gives the field no type; live it arrives as GeoJSON *text*.
    assert {json.loads(g)["type"] for g in geometries} == {"Point", "LineString", "Polygon"}


def test_response_models_keep_fields_added_by_later_releases():
    asd = PermitASDResponse.model_validate(
        {
            **WORK_WITH_ASD_GEOMETRY["active_permit"]["permit_asds"][0],
            "some_future_field": 1,
        }
    )
    assert asd.model_extra == {"some_future_field": 1}


def test_response_side_models_not_named_response_are_open_too():
    # Response-side by the spec's paths, not by name - a suffix rule would miss them.
    assert WorkFeature.model_config["extra"] == "allow"
    assert SiteDetails.model_config["extra"] == "allow"
