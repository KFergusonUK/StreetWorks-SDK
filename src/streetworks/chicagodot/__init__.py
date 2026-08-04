"""Chicago: CDOT Street Closures - this SDK's second US city permit
register, after NYC. See :mod:`streetworks.chicagodot.client` for the
full investigation.
"""

from .client import STREET_CLOSURES_URL, ChicagoDotClient

__all__ = ["STREET_CLOSURES_URL", "ChicagoDotClient"]
