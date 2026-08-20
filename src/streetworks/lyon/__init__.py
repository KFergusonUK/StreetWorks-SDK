"""Lyon: Métropole de Lyon's own roadworks feed. See
:mod:`streetworks.lyon.client` for the full investigation.
"""

from .client import BASE_URL, TYPE_NAME, LyonClient

__all__ = ["BASE_URL", "TYPE_NAME", "LyonClient"]
