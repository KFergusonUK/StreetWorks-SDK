"""Derived helpers layered on top of the raw Street Manager endpoints.

Public functions are re-exported here, so callers can do e.g.
``from streetworks.streetmanager.utils import summarise_active`` without
reaching into the per-endpoint module.
"""

from .section_58_utils import summarise_active

__all__ = [
    "summarise_active",
]
