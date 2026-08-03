"""New York City: NYC DOT Street Construction Permits - the local
follow-on to New York State's WZDx coverage (see :mod:`streetworks.wzdx`).
See :mod:`streetworks.nycdot.client` for the full investigation.
"""

from .client import PERMITS_URL, NycDotClient

__all__ = ["PERMITS_URL", "NycDotClient"]
