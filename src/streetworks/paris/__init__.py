"""Paris: "Chantiers à Paris" occupation-permit register - the French
analogue of this SDK's NYC DOT/Chicago CDOT municipal permit registers,
on OpenDataSoft rather than Socrata. See :mod:`streetworks.paris.client`
for the full investigation.
"""

from .client import CHANTIERS_URL, ParisClient

__all__ = ["CHANTIERS_URL", "ParisClient"]
