"""streetworks.nuar - a testing-only reference model, not a live provider
(yet - see the package's own docstring). No network access anywhere in
this file: there is no endpoint to hit."""

import importlib
import sys

import pytest

from streetworks.common.models import Coordinate
from streetworks.nuar.models import (
    NUAR_CONNECTOR_LIVE,
    FeatureKind,
    Measure,
    UtilityType,
    _enum_or_other,
    underground_asset_from_nhdm_row,
)

_WATER_LINK_ROW = {
    "systemid": "NUAR-WML-0001",
    "utilitytype": "water",
    "depth_depth": "1.2",
    "depth_unitofmeasure": "m",
    "qualitylevel": "A",
    "horizontalaccuracy_length": "0.1",
    "horizontalaccuracy_unitofmeasure": "m",
    "verticalaccuracy_length": "0.05",
    "verticalaccuracy_unitofmeasure": "m",
    "horizontalmeasurementmethod": "surveyed",
    "depthmethod": "surveyed",
    "objectname": "Trunk main",
    "description": "Cast iron trunk water main",
    "material": "cast_iron",
    "colour": None,
    "lifecyclestatus": "in_service",
    "operationalstatus": "active",
    "undergroundstatus": "underground",
    "dataowner": "Anglian Water",
    "operator": "Anglian Water",
    "dataprovenance": "surveyed",
    "datasensitivitylevel": "standard",
    "datelastupdated": None,
    "datedatacollected": None,
    "conveyancecategory": "trunk_main",
    "startnodeid": "NODE-1",
    "endnodeid": "NODE-2",
}


def test_importing_the_package_warns_and_is_not_live():
    sys.modules.pop("streetworks.nuar", None)
    with pytest.warns(UserWarning, match="TESTING-ONLY"):
        nuar = importlib.import_module("streetworks.nuar")
    assert nuar.NUAR_CONNECTOR_LIVE is False
    assert NUAR_CONNECTOR_LIVE is False


def test_underground_asset_from_nhdm_row_maps_a_network_link():
    coordinate = Coordinate(value=(451000.0, 205000.0), crs="EPSG:27700")

    asset = underground_asset_from_nhdm_row(
        _WATER_LINK_ROW,
        feature_kind=FeatureKind.NETWORK_LINK,
        utility_type=UtilityType.WATER,
        geometry=coordinate,
    )

    assert asset.feature_kind is FeatureKind.NETWORK_LINK
    assert asset.utility_type is UtilityType.WATER
    assert asset.system_id == "NUAR-WML-0001"

    assert asset.depth == Measure(value=1.2, unit="m")
    assert asset.quality is not None
    assert asset.quality.quality_level == "A"
    assert asset.quality.horizontal_accuracy == Measure(value=0.1, unit="m")
    assert asset.quality.vertical_accuracy == Measure(value=0.05, unit="m")

    # geometry is carried through exactly as given - no reprojection, no
    # CRS substitution.
    assert asset.geometry is coordinate
    assert asset.geometry.crs == "EPSG:27700"

    # .raw is the full source row, verbatim - including keys the named
    # attributes above don't otherwise surface.
    assert asset.raw == _WATER_LINK_ROW
    assert asset.raw is not _WATER_LINK_ROW  # a copy, not a shared reference


def test_geometry_defaults_to_none_when_wire_format_is_unverified():
    asset = underground_asset_from_nhdm_row(
        _WATER_LINK_ROW,
        feature_kind=FeatureKind.NETWORK_LINK,
        utility_type=UtilityType.WATER,
    )
    assert asset.geometry is None


def test_enum_or_other_falls_back_on_an_unrecognised_value():
    # A stated utilitytype outside the enumerated set falls back to OTHER
    # rather than raising - the row's own original string is never lost,
    # since .raw always carries the full source row regardless.
    row = dict(_WATER_LINK_ROW, utilitytype="steam")
    assert _enum_or_other(UtilityType, row["utilitytype"], UtilityType.OTHER) is UtilityType.OTHER

    asset = underground_asset_from_nhdm_row(
        row,
        feature_kind=FeatureKind.NETWORK_LINK,
        utility_type=_enum_or_other(UtilityType, row["utilitytype"], UtilityType.OTHER),
    )
    assert asset.utility_type is UtilityType.OTHER
    assert asset.raw["utilitytype"] == "steam"


def test_enum_or_other_recognises_a_real_value():
    assert _enum_or_other(UtilityType, "water", UtilityType.OTHER) is UtilityType.WATER


def test_enum_or_other_falls_back_on_none():
    assert _enum_or_other(UtilityType, None, UtilityType.OTHER) is UtilityType.OTHER
