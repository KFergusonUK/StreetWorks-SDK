"""Tests for streetworks.common.from_dfi_roads - built directly against
:class:`~streetworks.dfi_roads.models.RoadSection` objects, no HTTP
mocking needed here."""

from __future__ import annotations

from streetworks.common import from_dfi_roads
from streetworks.common.models import Coordinate, Identifier
from streetworks.dfi_roads.models import RoadSection

_REAL_SECTION = RoadSection(
    section_code="7020A0002_02",
    section_name="BELFAST RD",
    division_name="NORTHERN",
    section_office_name="MID and EAST ANTRIM",
    class_name="A Class",
    section_type="DUAL 2-LANE",
    adoption_status="Adopted",
    shape_length=1167.05,
    geometry=Coordinate(
        value=(338735.9063, 385763.8438), crs="EPSG:29902", points=((338735.9063, 385763.8438),)
    ),
    raw={"Section_Code": "7020A0002_02"},
)


def test_from_dfi_roads_converts_to_a_segment_not_a_street():
    segment = from_dfi_roads(_REAL_SECTION)

    assert segment.names == (segment.names[0],)
    assert segment.names[0].value == "BELFAST RD"
    assert segment.geometry.crs == "EPSG:29902"
    assert segment.administrative_area == "MID and EAST ANTRIM"
    assert segment.street_type is not None
    assert segment.street_type.label == "A Class"
    assert segment.raw is _REAL_SECTION


def test_from_dfi_roads_identifier_is_the_real_section_code():
    segment = from_dfi_roads(_REAL_SECTION)
    assert segment.identifiers == (
        Identifier(scheme="section_code", value="7020A0002_02"),
    )


def test_from_dfi_roads_never_synthesises_a_street_ref():
    # DfI publishes sections, not a separate named-street entity - no
    # street_refs to point at.
    segment = from_dfi_roads(_REAL_SECTION)
    assert segment.street_refs == ()
