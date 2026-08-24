"""South Korea (Korea Expressway Corporation) roadworks - Credentials wanted.

See :mod:`streetworks.korea.client` for the full picture, including what's
confirmed (real fields, licence, registration process) and what's still
open (the real pull URL, the real field key names).
"""

from __future__ import annotations

from .client import KoreaClient

__all__ = ["KoreaClient"]
