"""Oslo: SøkSys activities - this SDK's second Nordic roadworks
coverage. See :mod:`streetworks.oslo.client` for the full investigation,
including why the source brief's guessed Origo/NVDB backends don't match
the real SøkSys source.
"""

from .client import ACTIVITIES_URL, DEFAULT_EXTENT, OsloClient

__all__ = ["ACTIVITIES_URL", "DEFAULT_EXTENT", "OsloClient"]
