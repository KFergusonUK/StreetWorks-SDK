"""UK Police API (data.police.uk) - open crime and policing data.

No credentials required. Not itself a street-works dataset - included as a
safety signal (crime density near a worksite) alongside the street-works
providers elsewhere in this SDK.
"""

from .client import BASE_URL, SAFETY_RELEVANT_CATEGORIES, PoliceClient

__all__ = ["BASE_URL", "SAFETY_RELEVANT_CATEGORIES", "PoliceClient"]
