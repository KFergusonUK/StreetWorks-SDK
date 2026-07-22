"""streetworks - an open SDK for street works and roadworks data.

Don't know where to start? ``streetworks.providers()``/``get_provider()``
answer "what covers X" and "give me Y's client" without needing to already
know which technology a country/nation publishes over - see
:mod:`streetworks.registry`.

Providers:
    streetworks.streetmanager - DfT Street Manager (V6/V7, sandbox + production)
    streetworks.opendata      - Street Manager Open Data (AWS SNS push notifications)
    streetworks.datavia       - Geoplace DataVIA (OGC WFS, NSG data)
"""

from .exceptions import (
    AccountLockedError,
    AmbiguousProviderError,
    APIError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    OrganisationSuspendedError,
    ProviderNotFoundError,
    RateLimitError,
    RequestValidationError,
    ServerError,
    SignatureVerificationError,
    StreetworksError,
    TransportError,
    TruncatedResultError,
)
from .registry import Kind, ProviderEntry, get_provider, providers

__version__ = "0.8.0"  # keep in sync with pyproject.toml

__all__ = [
    "APIError",
    "AccountLockedError",
    "AmbiguousProviderError",
    "AuthenticationError",
    "ForbiddenError",
    "Kind",
    "NotFoundError",
    "OrganisationSuspendedError",
    "ProviderEntry",
    "ProviderNotFoundError",
    "RateLimitError",
    "RequestValidationError",
    "ServerError",
    "SignatureVerificationError",
    "StreetworksError",
    "TransportError",
    "TruncatedResultError",
    "__version__",
    "get_provider",
    "providers",
]
