"""Milan (Avvisi di manomissione excavation notices) - this SDK's second
Italy municipal provider, after Roma. See
:mod:`streetworks.milano.client` for the full investigation, including
how it resolves the "populous cities" pivot's own open question left by
Rome falling off-board as capital-projects-only.
"""

from .client import MANOMISSIONE_URL, MilanoClient

__all__ = ["MANOMISSIONE_URL", "MilanoClient"]
