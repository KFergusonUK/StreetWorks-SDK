"""Guernsey Street Gazetteer -> streetworks.common converter. This SDK's
second Channel Islands streets coverage, alongside Jersey's own (see
:mod:`.from_jersey_streets`) - found by checking whether Jersey's real
setup has a Guernsey sibling; it genuinely does, on the same real
platform (:mod:`streetworks.arcgis.guernsey`).

**Geometry is always absent on the canonical model - not a gap, a real
schema fact.** Unlike Jersey's own real ``USRN_XY1``/``USRN_XY2`` pair,
Guernsey's ``Roads`` layer states no per-feature point/line field at
all - only the real polygon itself. Per the same discipline
:mod:`.from_paris` established (``Coordinate.points`` is documented for
line vertices, not polygon rings - forcing one in would misuse that
contract), this converter never does so: every real
:class:`~streetworks.common.gazetteer.Street` here carries
``geometry=None``, ``GeometryGrade.ABSENT``. The real WGS84 polygon
(confirmed live - see :mod:`streetworks.arcgis.guernsey`'s module
docstring for the full CRS story) is preserved unmodified in
``Street.raw`` for any caller that needs the full footprint.

``identifiers`` carries the real ``USRN`` (scheme ``"usrn"``, scoped
``"Guernsey"`` - a distinct numbering block from both Jersey's and Great
Britain's own) formatted to two decimal places where fractional (real,
live-confirmed genuine subdivisions, e.g. a parent ``20194`` with real
child polygons ``20194.02``/``20194.04``/... - not a data-quality issue;
see the module docstring in :mod:`streetworks.arcgis.guernsey`), and,
where stated and non-zero, the real ``UPRN`` (scheme ``"uprn"``).

``street_type`` carries the real ``CLASS`` value undecoded (e.g.
``"PCP"``, ``"XDA"``) - no lookup table bundled, the same treatment
NWB's own ``bst_code`` gets. This is the *only* real classification
field this layer states; there is no clean way to separate genuine
street names from other real ``ROAD`` values (e.g. ``"CAR PARK"``) using
it or any other field - see module docstring in
:mod:`streetworks.arcgis.guernsey` for why every non-blank ``ROAD`` is
converted regardless.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import GeometryGrade, Name, Street, StreetType
from .models import Identifier, SourceGrade

__all__ = ["from_guernsey_street"]

JSON = dict[str, Any]


def _usrn_str(value: float | None) -> str | None:
    """Guernsey's real USRN includes genuine fractional subdivisions
    (confirmed live) - rounded to 2dp to mask real IEEE-754 float-encoding
    noise (a stated 20194.05 can arrive over the wire as
    20194.049999999999), formatted without a trailing .00 for whole
    values."""
    if value is None:
        return None
    rounded = round(value, 2)
    return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.2f}"


def from_guernsey_street(feature: JSON) -> Street:
    """Convert one real Guernsey street GeoJSON ``Feature`` (from
    :meth:`streetworks.arcgis.guernsey.GuernseyStreetsClient.iter_streets`)
    into a :class:`~streetworks.common.gazetteer.Street`."""
    properties = feature.get("properties", {})

    road = properties.get("ROAD")
    names = (Name(value=road),) if road and road.strip() else ()

    usrn = _usrn_str(properties.get("USRN"))
    uprn = properties.get("UPRN")
    identifiers = []
    if usrn:
        identifiers.append(Identifier(scheme="usrn", value=usrn, scope="Guernsey"))
    if uprn:
        identifiers.append(Identifier(scheme="uprn", value=str(uprn)))

    cls = properties.get("CLASS")
    street_type = StreetType(code=cls) if cls and cls.strip() else None

    parish = properties.get("PARISH")

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        street_type=street_type,
        geometry=None,
        geometry_grade=GeometryGrade.ABSENT,
        territory="Guernsey",
        administrative_area=parish if parish and parish.strip() else None,
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )
