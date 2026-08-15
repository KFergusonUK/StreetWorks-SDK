"""Spain: national road-transport network (IGN, over IDEE's INSPIRE WFS).
See :mod:`streetworks.idee.client` for the full investigation and
provenance."""

from .client import BASE_URL, IdeeTransportesClient
from .models import Road

__all__ = ["BASE_URL", "IdeeTransportesClient", "Road"]
