"""Switzerland - swisstopo's Amtliches Verzeichnis der Strassen. See
:mod:`streetworks.swisstopo.client` for the full picture."""

from __future__ import annotations

from .client import BASE_URL, SwisstopoStreetsClient

__all__ = ["BASE_URL", "SwisstopoStreetsClient"]
