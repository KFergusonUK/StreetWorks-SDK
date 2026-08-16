"""Northern Ireland: OSNI (Ordnance Survey Northern Ireland) Open Data -
Gazetteer - Streetnames. See :mod:`streetworks.osni.client` for the full
investigation and provenance."""

from .client import BASE_URL, OsniStreetnamesClient
from .models import Streetname

__all__ = ["BASE_URL", "OsniStreetnamesClient", "Streetname"]
