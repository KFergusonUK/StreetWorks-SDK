"""Luxembourg - CACLR (Registre national des localités et des rues). See
:mod:`streetworks.caclr.client` for the full picture."""

from __future__ import annotations

from .client import DATASET_API_URL, CaclrStreetsClient

__all__ = ["DATASET_API_URL", "CaclrStreetsClient"]
