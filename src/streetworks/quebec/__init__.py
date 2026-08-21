"""Québec (province): the Ministère des Transports et de la Mobilité
durable's own roadworks feed. See :mod:`streetworks.quebec.client` for
the full investigation.
"""

from .client import BASE_URL, TYPE_NAME, QuebecClient

__all__ = ["BASE_URL", "TYPE_NAME", "QuebecClient"]
