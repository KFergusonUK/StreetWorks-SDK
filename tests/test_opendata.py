import json

import httpx
import pytest
import respx

from streetworks.exceptions import SignatureVerificationError
from streetworks.opendata import (
    EventNotification,
    SnsMessageType,
    handle,
    parse_message,
)
from streetworks.opendata.sns import _validate_cert_url

EVENT = {
    "event_reference": 529770,
    "event_type": "WORK_START",
    "object_type": "PERMIT",
    "object_reference": "TSR1591199404915-01",
    "event_time": "2026-06-04T08:00:00.000Z",
    "object_data": {"work_reference_number": "TSR1591199404915"},
}


def notification_body(**overrides) -> str:
    body = {
        "Type": "Notification",
        "MessageId": "abc-123",
        "TopicArn": "arn:aws:sns:eu-west-2:111122223333:street-manager-topic",
        "Message": json.dumps(EVENT),
        "Timestamp": "2026-06-04T08:00:01.000Z",
        "SignatureVersion": "1",
        "Signature": "sig",
        "SigningCertURL": "https://sns.eu-west-2.amazonaws.com/cert.pem",
    }
    body.update(overrides)
    return json.dumps(body)


def test_parse_notification_and_extract_event():
    message = parse_message(notification_body())
    assert message.type is SnsMessageType.NOTIFICATION
    event = EventNotification.from_sns(message)
    assert event.event_type == "WORK_START"
    assert event.object_data["work_reference_number"] == "TSR1591199404915"


def test_handle_returns_event_payload_without_verification():
    payload = handle(notification_body(), verify=False)
    assert payload["event_reference"] == 529770


def test_handle_rejects_unexpected_topic_arn():
    with pytest.raises(SignatureVerificationError):
        handle(
            notification_body(),
            verify=False,
            expected_topic_arn="arn:aws:sns:eu-west-2:111122223333:other-topic",
        )


@respx.mock
def test_subscription_confirmation_auto_confirms():
    subscribe = respx.get("https://sns.eu-west-2.amazonaws.com/confirm?token=t").mock(
        return_value=httpx.Response(200)
    )
    body = json.dumps(
        {
            "Type": "SubscriptionConfirmation",
            "MessageId": "abc",
            "TopicArn": "arn:aws:sns:eu-west-2:111122223333:street-manager-topic",
            "Message": "You have chosen to subscribe...",
            "SubscribeURL": "https://sns.eu-west-2.amazonaws.com/confirm?token=t",
            "Token": "t",
            "Timestamp": "2026-06-04T08:00:01.000Z",
        }
    )
    assert handle(body, verify=False) is None
    assert subscribe.call_count == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://sns.eu-west-2.amazonaws.com/cert.pem",  # not https
        "https://evil.example.com/cert.pem",  # wrong host
        "https://notamazonaws.com/cert.pem",  # suffix trick
        "https://sns.eu-west-2.amazonaws.com/cert.txt",  # not a .pem
    ],
)
def test_signing_cert_url_validation(url):
    with pytest.raises(SignatureVerificationError):
        _validate_cert_url(url)
