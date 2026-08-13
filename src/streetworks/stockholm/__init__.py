"""Stockholm (Trafikkontoret) - a Phase 0 Credentials-wanted scaffold, one
phase earlier than :mod:`streetworks.datex2.trafikverket`. See
:mod:`streetworks.stockholm.client` for the full investigation, including
why this resolves - by confirming, not disproving - the Nordic-capitals
investigation brief's own "Rome-risk" flag.
"""

from .client import BASE_URL, StockholmClient

__all__ = ["BASE_URL", "StockholmClient"]
