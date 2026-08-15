"""NUAR (National Underground Asset Register) native model - TESTING ONLY.

.. warning::

   **This is not a live provider.** No NUAR consumption API connector exists
   in this SDK, and none can yet: as of 2026-08 the only access route to
   NUAR asset data is a use-case-gated sandbox running on *synthetic* data
   (OS/GDS announcement, 2026-08-07), whose API endpoints, auth and wire
   format are unpublished. This module exists so the standalone
   underground-asset entity is *modelled and ready* for that transport when
   it lands - it is a reference/testing shape, not a working data source.
   ``NUAR_CONNECTOR_LIVE`` is ``False`` and importing this package warns.

**Why this is its own native model, not ``Works``/``WorksSite``.** NUAR is a
different data class entirely - buried utility assets (pipes, cables, ducts,
chambers), not roadworks and not a street gazetteer. It is the first
non-roadworks, non-gazetteer entity in this SDK. Like :mod:`streetworks.
kartverket`, it is modelled natively and faithfully to its own published
schema; it is never coerced into the roadworks canonical types.

**Where the schema comes from (and its licence).** Unlike the *data*, the
NUAR *data model* is public. This module is derived from the **NUAR
Harmonised Data Model / MUDDI UK Excavation Profile V2.1.3**, published by
GDS at ``github.com/national-underground-asset-register/nuar-datamodel``
under the **Open Government Licence v3.0** - so it is freely reusable in
this MIT project with attribution, which the ``SCHEMA_*`` constants below
carry. The model is a UK profile of **OGC MUDDI** (Model for Underground
Data Definition and Integration), an approved OGC standard (July 2024).
Field shapes here match the profile's own published PostGIS DDL column
names verbatim, so the converter is built against the *confirmed* schema -
not a guess. The one piece the published schema does **not** settle is how
a future API will encode geometry on the wire (GeoJSON? WKT? OGC API
Features? tiles?); that seam is called out at :func:`underground_asset_from_nhdm_row`
and is the single thing that must be verified against the live sandbox
before this stops being "testing only".

**CRS and Z, per this SDK's discipline.** The published DDL stores geometry
as ``geometry(GEOMETRY, 27700)`` - British National Grid - *and* carries
explicit per-record ``horizontalcrs``/``verticalcrs`` text columns. Depth
is a real stated measure with its own method and units. So every
:class:`UndergroundAsset` carries an explicit-CRS :class:`~streetworks.
common.Coordinate` (defaulting to ``EPSG:27700`` only where the row itself
says so), and depth/Z is preserved from stated values - never defaulted to
zero, since for a buried asset a fabricated 0 depth is a safety lie, not a
harmless default.

**Minimal by design.** The full profile is 204 tables (nine utility sectors
x ~15 feature types plus registers). This models *one* entity discriminated
by :class:`UtilityType` and :class:`FeatureKind`, promoting only the fields
a safe-dig consumer needs as named attributes - identity, geometry, the
depth/accuracy/quality confidence cluster, status, provenance, and the few
type-specific tails (conveyance category, link topology, access covers,
container type). Everything else the profile defines rides losslessly in
``.raw``. No field is promoted here without that safe-dig consumer, per the
project's field-promotion rule.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from streetworks.common.models import Coordinate

__all__ = [
    "NUAR_CONNECTOR_LIVE",
    "SCHEMA_SOURCE",
    "SCHEMA_VERSION",
    "SCHEMA_LICENCE",
    "SCHEMA_STANDARD",
    "UtilityType",
    "FeatureKind",
    "Measure",
    "PositionalQuality",
    "UndergroundAsset",
    "underground_asset_from_nhdm_row",
]

#: Hard flag: there is no live NUAR consumption-API connector. Consumers and
#: any registry wiring must treat NUAR as testing-only until a real sandbox
#: transport is verified. NUAR must NOT be claimed as a live territory.
NUAR_CONNECTOR_LIVE = False

SCHEMA_STANDARD = "OGC MUDDI Conceptual Model (approved standard, July 2024)"
SCHEMA_SOURCE = (
    "NUAR Harmonised Data Model / MUDDI UK Excavation Profile, "
    "github.com/national-underground-asset-register/nuar-datamodel"
)
SCHEMA_VERSION = "V2.1.3"
SCHEMA_LICENCE = "Open Government Licence v3.0 (Crown Copyright)"


class UtilityType(str, Enum):
    """The utility sector an asset belongs to. In the published profile each
    sector is a separate set of physical tables (``water*``, ``gas*``, ...);
    here it is one discriminating attribute, mirroring the profile's own
    ``utilitytype`` column. ``OTHER`` is for a stated value outside this set
    (kept, never dropped) - the raw string is always in ``.raw``."""

    WATER = "water"
    GAS = "gas"
    ELECTRICITY = "electricity"
    SEWER = "sewer"
    DRAINAGE = "drainage"
    TELECOMMUNICATIONS = "telecommunications"
    THERMAL = "thermal"
    TRANSPORT_SIGNAL = "transport_signal"
    FUEL_AND_CHEMICALS = "fuel_and_chemicals"
    OTHER = "other"


class FeatureKind(str, Enum):
    """The MUDDI structural feature type, shared across every sector. The
    conveyance (:attr:`NETWORK_LINK`) is the primary safe-dig object - the
    buried line you might strike; the rest are its topology, access and
    protection. Only the kinds with a genuine safe-dig meaning are enumerated;
    a stated ``featuretype`` outside this set is preserved in ``.raw``."""

    NETWORK_LINK = "network_link"  #: conveyance - pipe/cable/duct run (the strike risk)
    NETWORK_NODE = "network_node"  #: junction/fitting point on a network
    ACCESS_OBJECT = "access_object"  #: chamber/manhole/access point
    CONTAINER_OBJECT = "container_object"  #: duct/casing containing conveyances
    SUPPORT_OBJECT = "support_object"  #: pole/support
    PHYSICAL_PROTECTION_OBJECT = "physical_protection_object"  #: slab/tile/tape


@dataclass(frozen=True)
class Measure:
    """A stated scalar with its unit, mirroring the profile's paired
    ``*_length``/``*_depth``/``*_width`` + ``*_unitofmeasure`` columns. Both
    parts come straight from the source; the unit is never assumed (a bare
    number with an implied metre is exactly the kind of silent assumption
    this SDK avoids), so ``unit`` is ``None`` only where the source states
    no unit alongside the value."""

    value: float
    unit: str | None = None


@dataclass(frozen=True)
class PositionalQuality:
    """The safe-dig confidence cluster - the fields that say *how much to
    trust where this asset is*, which for buried infrastructure matters as
    much as the geometry itself. All optional: populated only where the
    source states them, never inferred. ``quality_level`` is the profile's
    own ``qualitylevel`` codelist value (positional accuracy band);
    ``horizontal_measurement_method``/``depth_method`` record how the
    horizontal position and depth were captured (surveyed vs digitised vs
    estimated), which is the real signal behind a quality band."""

    quality_level: str | None = None
    horizontal_accuracy: Measure | None = None
    vertical_accuracy: Measure | None = None
    horizontal_measurement_method: str | None = None
    depth_method: str | None = None


@dataclass(frozen=True)
class UndergroundAsset:
    """One buried-utility feature, faithful to the NUAR/MUDDI profile.

    ``geometry`` is an explicit-CRS :class:`~streetworks.common.Coordinate`;
    for a :attr:`FeatureKind.NETWORK_LINK` it holds every vertex in
    ``points`` (the conveyance run), for a point feature just ``value``. Z is
    carried where the source states 3D geometry - and note ``depth`` is a
    *separate*, independently stated measure (depth below surface), not the
    same thing as a geometry Z ordinate; both are preserved when present.

    Only safe-dig-relevant fields are named. The full profile record -
    dimensions, operating pressures/temperatures, materials sub-types,
    lifecycle dates, every sector-specific column - is preserved verbatim in
    ``raw``; promote a field to a named attribute here only when a real
    consumer needs it, per the project rule.
    """

    system_id: str
    feature_kind: FeatureKind
    utility_type: UtilityType
    geometry: Coordinate | None = None

    depth: Measure | None = None
    quality: PositionalQuality | None = None

    object_name: str | None = None
    description: str | None = None
    material: str | None = None
    colour: str | None = None

    lifecycle_status: str | None = None
    operational_status: str | None = None
    underground_status: str | None = None

    data_owner: str | None = None
    operator: str | None = None
    data_provenance: str | None = None
    data_sensitivity_level: str | None = None
    date_last_updated: datetime | None = None
    date_data_collected: datetime | None = None

    # Type-specific tails - populated only for the relevant FeatureKind.
    conveyance_category: str | None = None  #: NETWORK_LINK
    start_node_id: str | None = None  #: NETWORK_LINK topology
    end_node_id: str | None = None  #: NETWORK_LINK topology
    access_type: str | None = None  #: ACCESS_OBJECT
    number_of_covers: int | None = None  #: ACCESS_OBJECT
    container_type: str | None = None  #: CONTAINER_OBJECT

    raw: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"<UndergroundAsset {self.utility_type.value}/"
            f"{self.feature_kind.value} {self.system_id!r}>"
        )


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _measure(row: dict[str, Any], value_key: str, unit_key: str) -> Measure | None:
    v = _float_or_none(row.get(value_key))
    if v is None:
        return None
    unit = row.get(unit_key)
    return Measure(value=v, unit=unit or None)


def _enum_or_other(enum_cls: type, value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return enum_cls(str(value).strip().lower().replace(" ", "_"))
    except ValueError:
        return fallback


def underground_asset_from_nhdm_row(
    row: dict[str, Any],
    *,
    feature_kind: FeatureKind,
    utility_type: UtilityType,
    geometry: Coordinate | None = None,
) -> UndergroundAsset:
    """Build an :class:`UndergroundAsset` from one NHDM-shaped record.

    Keys are the profile's published PostGIS DDL column names (``systemid``,
    ``depth_depth``, ``qualitylevel``, ...), so this maps the *confirmed*
    schema. It is written now, ahead of any live API, precisely so that when
    the sandbox transport is available the only work left is to point it at
    real rows.

    **The one unverified seam - geometry.** The published schema fixes the
    *attributes* but not how a future API will serialise geometry on the
    wire. This function therefore does **not** parse geometry itself: pass a
    ready-built :class:`~streetworks.common.Coordinate` as ``geometry`` once
    you know the wire format, sourcing its ``crs`` from the row's own
    ``horizontalcrs`` (falling back to ``EPSG:27700`` only if the row states
    nothing, matching the DDL's SRID default) and never silently reprojecting.
    Until the live sandbox confirms that format, leave it ``None``. This is
    the single thing standing between "testing only" and a verified provider.

    ``feature_kind`` and ``utility_type`` are passed in because in the
    published profile they are implied by *which table* a row came from, not
    by a single self-describing column; a real transport will make that
    mapping explicit and this signature already expects it.
    """
    return UndergroundAsset(
        system_id=str(row.get("systemid", "")),
        feature_kind=feature_kind,
        utility_type=utility_type,
        geometry=geometry,
        depth=_measure(row, "depth_depth", "depth_unitofmeasure"),
        quality=PositionalQuality(
            quality_level=row.get("qualitylevel"),
            horizontal_accuracy=_measure(
                row, "horizontalaccuracy_length", "horizontalaccuracy_unitofmeasure"
            ),
            vertical_accuracy=_measure(
                row, "verticalaccuracy_length", "verticalaccuracy_unitofmeasure"
            ),
            horizontal_measurement_method=row.get("horizontalmeasurementmethod"),
            depth_method=row.get("depthmethod"),
        ),
        object_name=row.get("objectname"),
        description=row.get("description"),
        material=row.get("material"),
        colour=row.get("colour"),
        lifecycle_status=row.get("lifecyclestatus"),
        operational_status=row.get("operationalstatus"),
        underground_status=row.get("undergroundstatus"),
        data_owner=row.get("dataowner"),
        operator=row.get("operator"),
        data_provenance=row.get("dataprovenance"),
        data_sensitivity_level=row.get("datasensitivitylevel"),
        date_last_updated=row.get("datelastupdated"),
        date_data_collected=row.get("datedatacollected"),
        conveyance_category=row.get("conveyancecategory"),
        start_node_id=row.get("startnodeid"),
        end_node_id=row.get("endnodeid"),
        access_type=row.get("accesstype"),
        number_of_covers=row.get("numberofcovers"),
        container_type=row.get("containertype"),
        raw=dict(row),
    )


def _warn_testing_only() -> None:
    warnings.warn(
        "streetworks.nuar is a TESTING-ONLY model, not a live provider: no "
        "NUAR consumption API connector exists (sandbox-gated, synthetic data, "
        "wire format unpublished as of 2026-08). The entity is modelled from "
        f"the public {SCHEMA_SOURCE} {SCHEMA_VERSION} ({SCHEMA_LICENCE}); do "
        "not treat NUAR as a live territory.",
        UserWarning,
        stacklevel=2,
    )
