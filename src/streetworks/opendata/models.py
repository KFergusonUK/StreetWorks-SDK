"""Models for Street Manager Open Data (SNS) messages."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SnsMessageType(str, Enum):
    SUBSCRIPTION_CONFIRMATION = "SubscriptionConfirmation"
    NOTIFICATION = "Notification"
    UNSUBSCRIBE_CONFIRMATION = "UnsubscribeConfirmation"


class SnsMessage(BaseModel):
    """The SNS envelope wrapping every Open Data message."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: SnsMessageType = Field(alias="Type")
    message_id: str = Field(alias="MessageId")
    topic_arn: str | None = Field(default=None, alias="TopicArn")
    subject: str | None = Field(default=None, alias="Subject")
    message: str = Field(alias="Message")
    timestamp: str | None = Field(default=None, alias="Timestamp")
    signature_version: str | None = Field(default=None, alias="SignatureVersion")
    signature: str | None = Field(default=None, alias="Signature")
    signing_cert_url: str | None = Field(default=None, alias="SigningCertURL")
    subscribe_url: str | None = Field(default=None, alias="SubscribeURL")
    token: str | None = Field(default=None, alias="Token")

    # The raw dict is kept for signature canonicalisation.
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _capture_raw(cls, data: Any) -> Any:
        if isinstance(data, dict) and "raw" not in data:
            data = dict(data)
            data["raw"] = dict(data)
        return data

    def event_payload(self) -> dict[str, Any]:
        """Decode the Street Manager event JSON carried in ``Message``."""
        return json.loads(self.message)


class EventNotification(BaseModel):
    """A Street Manager event, loosely typed.

    Street Manager notifications carry an ``event_type`` (e.g. permit or
    activity lifecycle events), a ``timestamp``, an ``object_type`` /
    ``object_reference`` identifying the affected entity, and an
    ``object_data`` dict with entity details. Field sets vary by event type
    and API version, so unknown fields are preserved (``extra="allow"``) and
    available via ``model_extra``.
    """

    model_config = ConfigDict(extra="allow")

    event_reference: int | str | None = None
    event_type: str | None = None
    event_time: str | None = None
    object_type: str | None = None
    object_reference: str | None = None
    version: int | None = None
    object_data: dict[str, Any] | None = None

    @classmethod
    def from_sns(cls, message: SnsMessage) -> EventNotification:
        return cls.model_validate(message.event_payload())
