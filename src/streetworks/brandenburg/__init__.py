"""Germany (Brandenburg) - the WFS BB-BE Gazetteer street layer. See
:mod:`streetworks.brandenburg.client` for the full picture."""

from __future__ import annotations

from .client import BASE_URL, TYPE_NAME, BrandenburgStreetsClient

__all__ = ["BASE_URL", "TYPE_NAME", "BrandenburgStreetsClient"]
