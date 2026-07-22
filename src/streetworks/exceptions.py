"""Exception hierarchy shared by all streetworks provider modules."""

from __future__ import annotations

from typing import Any


class StreetworksError(Exception):
    """Base class for all errors raised by the streetworks SDK."""


class TransportError(StreetworksError):
    """A network-level failure (DNS, connection, timeout) after retries were exhausted."""


class APIError(StreetworksError):
    """An HTTP error response from a remote API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: Any = None,
        request_url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.request_url = request_url

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        base = super().__str__()
        if self.status_code is not None:
            return f"[{self.status_code}] {base}"
        return base


class AuthenticationError(APIError):
    """401 - invalid/expired token, or bad credentials on /authenticate."""


class AccountLockedError(AuthenticationError):
    """423 - account locked after repeated failed logins (auto-unlocks after 5 minutes)."""


class OrganisationSuspendedError(AuthenticationError):
    """412 - the user's organisation is suspended or disabled."""


class ForbiddenError(APIError):
    """403 - authenticated, but not permitted to perform this action."""


class NotFoundError(APIError):
    """404 - resource does not exist."""


class RequestValidationError(APIError):
    """400/422 - the request body or parameters were rejected."""


class RateLimitError(APIError):
    """429 - rate limited. ``retry_after`` holds the server hint in seconds, if given."""

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(APIError):
    """5xx - the remote service failed."""


class SignatureVerificationError(StreetworksError):
    """An SNS message failed signature verification (streetworks.opendata)."""


class TruncatedResultError(StreetworksError):
    """A query returned a truncated page (the server's own transfer limit
    was hit) and this SDK could not page past it - e.g. an ArcGIS layer
    that both hits ``maxRecordCount`` and doesn't genuinely support
    ``resultOffset``/``resultRecordCount`` paging despite what its own
    metadata claims (confirmed live for Jersey's RoadWorks layer - see
    :mod:`streetworks.arcgis`). Raised rather than silently returning a
    partial result, since a silently truncated national dataset would be
    the worst possible failure for a caller to discover after the fact."""


class ProviderNotFoundError(StreetworksError, LookupError):
    """streetworks.get_provider() received a key with no registry match.
    The message names the closest real keys, so a typo doesn't dead-end."""


class AmbiguousProviderError(StreetworksError, LookupError):
    """streetworks.get_provider() received a key matching more than one
    provider (e.g. a country with several providers) - resolved by raising,
    never by guessing. The message names every candidate key."""


_STATUS_MAP: dict[int, type[APIError]] = {
    400: RequestValidationError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    412: OrganisationSuspendedError,
    422: RequestValidationError,
    423: AccountLockedError,
    429: RateLimitError,
}


def error_for_status(status_code: int) -> type[APIError]:
    """Return the most specific exception class for an HTTP status code."""
    if status_code in _STATUS_MAP:
        return _STATUS_MAP[status_code]
    if status_code >= 500:
        return ServerError
    return APIError
