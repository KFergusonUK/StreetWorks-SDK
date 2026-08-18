"""Denmark - Danmarks Adresseregister (DAR), the national named-road
register. See :mod:`streetworks.dar.client` for the full picture."""

from __future__ import annotations

from .client import BASE_URL, STREETS_ENTITY, DarClient

__all__ = ["BASE_URL", "STREETS_ENTITY", "DarClient"]
