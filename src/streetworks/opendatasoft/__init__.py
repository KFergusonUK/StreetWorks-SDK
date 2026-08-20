"""OpenDataSoft Explore API v2.1 - a generic fetch client, extracted
after a second and third real consumer (Sarthe, Loire-Atlantique,
Hauts-de-Seine) turned up the identical shape :mod:`streetworks.paris`
already established. See :mod:`streetworks.opendatasoft.client` for the
full reasoning.
"""

from .client import OpenDataSoftClient

__all__ = ["OpenDataSoftClient"]
