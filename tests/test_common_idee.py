"""Tests for streetworks.common.from_idee - built directly against real
:class:`~streetworks.idee.models.Road` objects (parsed + resolved from
the same real fixtures test_idee.py uses), no HTTP mocking needed here."""

from __future__ import annotations

from pathlib import Path

from streetworks.common import from_idee
from streetworks.common.gazetteer import GeometryGrade
from streetworks.common.models import Coordinate, Identifier, SourceGrade
from streetworks.idee.models import Road
from streetworks.idee.parser import parse_road_links, parse_roads_page

FIXTURES = Path(__file__).parent / "fixtures"
ROADS_XML = (FIXTURES / "idee_roads_live_pull.xml").read_bytes()
ROADLINKS_XML = (FIXTURES / "idee_roadlinks_live_pull.xml").read_bytes()


def _real_road(name: str) -> Road:
    raw_roads, _ = parse_roads_page(ROADS_XML)
    geometries = parse_road_links(ROADLINKS_XML)
    raw_road = next(r for r in raw_roads if r.name == name)
    parts = tuple(tuple(geometries[lid]) for lid in raw_road.link_ids)
    geometry = Coordinate(value=parts[0][0], crs="EPSG:4258", parts=parts) if parts else None
    return Road(
        id=raw_road.id,
        name=raw_road.name,
        national_road_code=raw_road.national_road_code,
        local_road_code=raw_road.local_road_code,
        inspire_local_id=raw_road.inspire_local_id,
        inspire_namespace=raw_road.inspire_namespace,
        geometry=geometry,
        unresolved_links=0,
        raw=raw_road.raw,
    )


def test_from_idee_converts_a_real_single_link_road():
    road = _real_road("CONCORDIA")
    street = from_idee(road)

    assert street.name == "CONCORDIA"
    assert street.territory == "Spain"
    assert street.source_grade == SourceGrade.REGISTER
    assert street.geometry_grade == GeometryGrade.PUBLISHED
    assert street.geometry is road.geometry
    assert street.raw is road


def test_from_idee_carries_all_four_real_identifiers():
    road = _real_road("CONCORDIA")
    street = from_idee(road)

    by_scheme = {i.scheme: i for i in street.identifiers}
    assert set(by_scheme) == {"gmlId", "inspireId", "nationalRoadCode", "localRoadCode"}
    assert by_scheme["gmlId"] == Identifier(
        scheme="gmlId", value="TN-RO_ROAD_VIAL_LI80960000289"
    )
    assert by_scheme["inspireId"] == Identifier(
        scheme="inspireId", value="VIAL_LI80960000289", scope="ES.SCNE.IGR-RT"
    )
    assert by_scheme["nationalRoadCode"] == Identifier(
        scheme="nationalRoadCode", value="0809602044"
    )
    # local_road_code is genuinely municipality-scoped with no stated scope
    # on this feature - never fabricated.
    assert by_scheme["localRoadCode"] == Identifier(scheme="localRoadCode", value="48")
    assert by_scheme["localRoadCode"].scope is None


def test_from_idee_aggregates_two_roadlinks_into_one_streets_parts():
    road = _real_road("ARQUIMEDES")
    street = from_idee(road)

    assert street.geometry is not None
    assert street.geometry.parts is not None
    assert len(street.geometry.parts) == 2
    assert street.geometry_grade == GeometryGrade.PUBLISHED


def test_from_idee_never_emits_segment_refs():
    # This SDK deliberately doesn't build a Segment per RoadLink - see
    # from_idee's own module docstring.
    road = _real_road("CONCORDIA")
    street = from_idee(road)
    assert street.segment_refs == ()


def test_from_idee_sets_geometry_absent_when_every_link_is_unresolved():
    road = Road(
        id="TN-RO_ROAD_SYNTHETIC",
        name=None,
        national_road_code=None,
        local_road_code=None,
        inspire_local_id=None,
        inspire_namespace=None,
        geometry=None,
        unresolved_links=1,
        raw={},
    )
    street = from_idee(road)

    assert street.geometry is None
    assert street.geometry_grade == GeometryGrade.ABSENT
    assert street.names == ()
    # Even with no name/geometry, the gml:id identifier is always present.
    assert street.identifiers == (Identifier(scheme="gmlId", value="TN-RO_ROAD_SYNTHETIC"),)
