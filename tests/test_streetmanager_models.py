"""Tests for the generated Street Manager v6 Pydantic models.

Skipped unless the models have been generated (they are produced from the DfT
swagger specs by ``scripts/generate_models.py`` and are not committed
upstream). ``CommentCreateRequest`` is a small, stable model: a required
string (``detail``), a required enum (``topic``), and ``extra="forbid"``.
"""

import pytest
from pydantic import ValidationError

pytest.importorskip("streetworks.streetmanager.models.v6.work")

from streetworks.streetmanager.models.v6.work import (  # noqa: E402
    CommentCreateRequest,
    CommentTopic,
)

VALID_COMMENT = {"detail": "Access needed to the loading bay", "topic": "GENERAL"}


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
