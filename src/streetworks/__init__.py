"""streetworks - an open SDK for UK street works APIs.

Providers:
    streetworks.streetmanager - DfT Street Manager (V6/V7, sandbox + production)
    streetworks.opendata      - Street Manager Open Data (AWS SNS push notifications)
    streetworks.datavia       - Geoplace DataVIA (OGC WFS, NSG data)
"""

from .exceptions import (
    AccountLockedError,
    APIError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    OrganisationSuspendedError,
    RateLimitError,
    RequestValidationError,
    ServerError,
    SignatureVerificationError,
    StreetworksError,
    TransportError,
)

__version__ = "0.2.0"  # keep in sync with pyproject.toml

__all__ = [
    "APIError",
    "AccountLockedError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "OrganisationSuspendedError",
    "RateLimitError",
    "RequestValidationError",
    "ServerError",
    "SignatureVerificationError",
    "StreetworksError",
    "TransportError",
    "__version__",
]
