"""Street Manager Open Data - AWS SNS webhook receiver toolkit.

Street Manager's Open Data service is a *push* model: you expose an HTTPS
endpoint, Street Manager (via AWS SNS) POSTs to it. This module handles the
fiddly parts every integrator has to get right:

1. **Parsing** the SNS envelope (``SubscriptionConfirmation``, ``Notification``,
   ``UnsubscribeConfirmation``).
2. **Verifying** the message signature (SignatureVersion 1 = SHA1-RSA,
   SignatureVersion 2 = SHA256-RSA) against the AWS signing certificate,
   including validating that the certificate really comes from an
   ``*.amazonaws.com`` host. Requires the ``cryptography`` package
   (``pip install streetworks[sns]``).
3. **Confirming** subscriptions automatically (GET the ``SubscribeURL``).
4. **Extracting** the Street Manager event payload from ``Message``.

The functions here are framework-agnostic: pass in the raw request body and
you get back structured objects. See ``examples/opendata_fastapi.py`` for a
ready-made FastAPI endpoint.
"""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import urlparse

import httpx

from ..exceptions import SignatureVerificationError, StreetworksError
from .models import SnsMessage, SnsMessageType

# Fields included in the canonical string-to-sign, in order, per message type.
# https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html
_SIGNED_FIELDS = {
    SnsMessageType.NOTIFICATION: (
        "Message",
        "MessageId",
        "Subject",  # only if present
        "Timestamp",
        "TopicArn",
        "Type",
    ),
    SnsMessageType.SUBSCRIPTION_CONFIRMATION: (
        "Message",
        "MessageId",
        "SubscribeURL",
        "Timestamp",
        "Token",
        "TopicArn",
        "Type",
    ),
    SnsMessageType.UNSUBSCRIBE_CONFIRMATION: (
        "Message",
        "MessageId",
        "SubscribeURL",
        "Timestamp",
        "Token",
        "TopicArn",
        "Type",
    ),
}


def parse_message(body: str | bytes) -> SnsMessage:
    """Parse a raw SNS request body into an :class:`SnsMessage`."""
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise StreetworksError(f"Request body is not valid JSON: {exc}") from exc
    return SnsMessage.model_validate(data)


def _validate_cert_url(cert_url: str) -> None:
    parsed = urlparse(cert_url)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or not (host == "amazonaws.com" or host.endswith(".amazonaws.com"))
        or not parsed.path.endswith(".pem")
    ):
        raise SignatureVerificationError(
            f"Refusing signing certificate from untrusted URL: {cert_url!r}"
        )


def _string_to_sign(message: SnsMessage) -> bytes:
    fields = _SIGNED_FIELDS.get(message.type)
    if fields is None:
        raise SignatureVerificationError(f"Unknown SNS message type: {message.type!r}")
    raw = message.raw
    parts: list[str] = []
    for field in fields:
        if field == "Subject" and raw.get("Subject") is None:
            continue
        value = raw.get(field)
        if value is None:
            raise SignatureVerificationError(f"SNS message missing signed field {field!r}")
        parts.append(field)
        parts.append(str(value))
    return ("\n".join(parts) + "\n").encode("utf-8")


def verify_signature(
    message: SnsMessage,
    *,
    fetch_certificate: httpx.Client | None = None,
) -> None:
    """Verify the SNS message signature. Raises :class:`SignatureVerificationError`.

    Certificates are fetched over HTTPS from the (validated) ``SigningCertURL``.
    Pass a shared ``httpx.Client`` via ``fetch_certificate`` to enable
    connection reuse and caching layers of your own.
    """
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.x509 import load_pem_x509_certificate
    except ImportError as exc:  # pragma: no cover
        raise StreetworksError(
            "Signature verification requires the 'cryptography' package. "
            "Install with: pip install streetworks[sns]"
        ) from exc

    if not message.signing_cert_url or not message.signature:
        raise SignatureVerificationError("SNS message missing Signature/SigningCertURL")
    _validate_cert_url(message.signing_cert_url)

    client = fetch_certificate or httpx.Client(timeout=10.0)
    try:
        pem = client.get(message.signing_cert_url).raise_for_status().content
    finally:
        if fetch_certificate is None:
            client.close()

    certificate = load_pem_x509_certificate(pem)
    public_key = certificate.public_key()
    signature = base64.b64decode(message.signature)
    digest = hashes.SHA1() if message.signature_version == "1" else hashes.SHA256()  # noqa: S303

    try:
        public_key.verify(signature, _string_to_sign(message), padding.PKCS1v15(), digest)
    except InvalidSignature as exc:
        raise SignatureVerificationError("SNS signature verification failed") from exc


def confirm_subscription(message: SnsMessage) -> None:
    """Confirm an SNS subscription by visiting its ``SubscribeURL``."""
    if message.type is not SnsMessageType.SUBSCRIPTION_CONFIRMATION:
        raise StreetworksError("Message is not a SubscriptionConfirmation")
    if not message.subscribe_url:
        raise StreetworksError("SubscriptionConfirmation missing SubscribeURL")
    httpx.get(message.subscribe_url, timeout=10.0).raise_for_status()


async def confirm_subscription_async(message: SnsMessage) -> None:
    """Async variant of :func:`confirm_subscription`."""
    if message.type is not SnsMessageType.SUBSCRIPTION_CONFIRMATION:
        raise StreetworksError("Message is not a SubscriptionConfirmation")
    if not message.subscribe_url:
        raise StreetworksError("SubscriptionConfirmation missing SubscribeURL")
    async with httpx.AsyncClient(timeout=10.0) as client:
        (await client.get(message.subscribe_url)).raise_for_status()


def handle(
    body: str | bytes,
    *,
    verify: bool = True,
    expected_topic_arn: str | None = None,
    auto_confirm: bool = True,
) -> dict[str, Any] | None:
    """One-call handler for an incoming Open Data POST.

    * Parses the envelope, optionally verifies the signature and topic ARN.
    * ``SubscriptionConfirmation`` -> confirms it (if ``auto_confirm``),
      returns ``None``.
    * ``Notification`` -> returns the Street Manager event payload as a dict.
    """
    message = parse_message(body)
    if verify:
        verify_signature(message)
    if expected_topic_arn is not None and message.topic_arn != expected_topic_arn:
        raise SignatureVerificationError(
            f"Unexpected TopicArn {message.topic_arn!r} (expected {expected_topic_arn!r})"
        )
    if message.type is SnsMessageType.SUBSCRIPTION_CONFIRMATION:
        if auto_confirm:
            confirm_subscription(message)
        return None
    if message.type is SnsMessageType.NOTIFICATION:
        return message.event_payload()
    return None
