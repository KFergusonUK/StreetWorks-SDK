"""Kanton Zürich (Baustellen Kantonsstrassen) - this SDK's first Swiss
roadworks coverage. See :mod:`streetworks.canton_zurich.client` for the
full investigation, including the real no-unique-identifier finding and
why this is deliberately not deduped against Stadt Zürich
(:mod:`streetworks.zurich`).
"""

from .client import BASE_URL, CRS, TYPE_NAME, CantonZurichClient

__all__ = ["BASE_URL", "CRS", "TYPE_NAME", "CantonZurichClient"]
