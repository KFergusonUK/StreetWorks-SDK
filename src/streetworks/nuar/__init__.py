"""NUAR (National Underground Asset Register) - TESTING ONLY, not a live
provider yet. See models.py's module docstring for full status and
provenance; see streetworks.nuar.models.NUAR_CONNECTOR_LIVE for the
current state, which is expected to change once a sandbox transport is
confirmed."""

from streetworks.nuar.models import (  # noqa: F401
    NUAR_CONNECTOR_LIVE,
    SCHEMA_LICENCE,
    SCHEMA_SOURCE,
    SCHEMA_STANDARD,
    SCHEMA_VERSION,
    FeatureKind,
    Measure,
    PositionalQuality,
    UndergroundAsset,
    UtilityType,
    underground_asset_from_nhdm_row,
)
from streetworks.nuar.models import _warn_testing_only as _w

_w()
del _w

__all__ = [
    "NUAR_CONNECTOR_LIVE",
    "SCHEMA_LICENCE",
    "SCHEMA_SOURCE",
    "SCHEMA_STANDARD",
    "SCHEMA_VERSION",
    "FeatureKind",
    "Measure",
    "PositionalQuality",
    "UndergroundAsset",
    "UtilityType",
    "underground_asset_from_nhdm_row",
]
