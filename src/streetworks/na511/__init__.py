"""North American 511 platform: one commercial REST API shape shared by
Ontario 511, 511 Alberta and Saskatchewan's Highway Hotline. See
:mod:`streetworks.na511.client` for the full investigation and
:mod:`streetworks.na511.jurisdictions` for the confirmed per-jurisdiction
registry.
"""

from . import jurisdictions
from .client import EVENT_PATH, NA511Client

__all__ = ["EVENT_PATH", "NA511Client", "jurisdictions"]
