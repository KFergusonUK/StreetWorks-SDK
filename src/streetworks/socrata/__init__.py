"""Generic Socrata (SODA) client - shared transport for this SDK's
Socrata-backed providers (:mod:`streetworks.wzdx.registry`,
:mod:`streetworks.nycdot`). See :mod:`streetworks.socrata.client` for
the full investigation.
"""

from .client import SodaClient

__all__ = ["SodaClient"]
