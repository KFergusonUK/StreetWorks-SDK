"""Lisboa: CML's Condicionamentos de Trânsito feed - this SDK's first
Portugal provider at any level. See :mod:`streetworks.lisboa.client` for
the full investigation, including how the real endpoint was found (not
documented anywhere public) and the freshness check that ruled out the
catalogue's stale metadata.
"""

from .client import CLOSURES_URL, LisboaClient

__all__ = ["CLOSURES_URL", "LisboaClient"]
