"""Smoke tests for the streetworks.common gazetteer canonical types
themselves (Street/Segment/Address and their shared value types) - not
converters, those are tested per provider (test_common_datavia.py etc.)."""

from streetworks.common import (
    Address,
    AddressRange,
    Coordinate,
    GeometryGrade,
    Identifier,
    Name,
    Segment,
    Street,
    StreetType,
)


def test_coordinate_still_accepts_plain_2d_points_unchanged():
    # Backwards compatibility: every existing works converter still
    # produces bare 2-tuples - this must keep working exactly as before.
    c = Coordinate(value=(412345.0, 112345.0), crs="EPSG:27700")
    assert c.value == (412345.0, 112345.0)
    assert c.points is None
    assert c.parts is None


def test_coordinate_z_survives_never_defaulted_to_zero():
    # NVDB's real LINESTRING Z under EPSG:5973.
    c = Coordinate(
        value=(123995.67, 6483373.56, 28.483),
        crs="EPSG:5973",
        points=((123995.67, 6483373.56, 28.483), (123992.01, 6483370.58, 28.703)),
    )
    assert c.value[2] == 28.483
    assert c.points[1][2] == 28.703


def test_coordinate_parts_holds_a_multilinestring_and_leaves_value_points_alone():
    # DataVIA's real MultiLineString (one Street aggregating several ESUs).
    parts = (((1.0, 2.0), (3.0, 4.0)), ((5.0, 6.0), (7.0, 8.0)))
    c = Coordinate(value=parts[0][0], crs="EPSG:4326", parts=parts)
    assert c.value == (1.0, 2.0)  # first part, first vertex
    assert c.points is None  # single-line consumers see no line here
    assert len(c.parts) == 2


def test_identifier_carries_scope_for_municipality_scoped_schemes():
    # Kartverket's adressekode: the same real code (1300) means different
    # streets in different kommuner - scope is what makes it safe to compare.
    a = Identifier(scheme="adressekode", value="1300", scope="5610")
    b = Identifier(scheme="adressekode", value="1300", scope="0301")
    assert a != b  # same value, different scope -> not the same street


def test_identifier_scope_is_none_for_nationally_unique_schemes():
    usrn = Identifier(scheme="usrn", value="33909869")
    assert usrn.scope is None


def test_street_name_property_returns_first_name_in_source_order():
    street = Street(
        names=(Name(value="HIGH STREET", language="eng"), Name(value="STRYD FAWR", language="cym"))
    )
    assert street.name == "HIGH STREET"


def test_street_name_property_is_none_with_no_names():
    assert Street().name is None


def test_street_geometry_grade_has_no_derived_value():
    # There is deliberately no GeometryGrade.DERIVED - a canonical Street
    # never synthesises geometry the source didn't publish.
    assert {g.value for g in GeometryGrade} == {"published", "absent"}


def test_street_with_absent_geometry_is_a_real_case_not_an_error():
    # OS Open USRN's real NULL-geometry rows.
    street = Street(
        identifiers=(Identifier(scheme="usrn", value="84202034"),),
        geometry=None,
        geometry_grade=GeometryGrade.ABSENT,
    )
    assert street.geometry is None
    assert street.geometry_grade is GeometryGrade.ABSENT


def test_segment_street_refs_is_plural_many_to_many():
    # A real ESU (4276210541888, Durham) belongs to two distinct USRNs -
    # Church Street and Church Street Villas - proving Segment is
    # independent of Street, not a child of it.
    segment = Segment(
        geometry=Coordinate(value=(-1.57, 54.77), crs="EPSG:4326"),
        identifiers=(Identifier(scheme="esu", value="4276210541888"),),
        street_refs=(
            Identifier(scheme="usrn", value="11713561"),
            Identifier(scheme="usrn", value="11713562"),
        ),
    )
    assert len(segment.street_refs) == 2


def test_address_range_carries_undecoded_structure_code():
    # NWB's real hnrstrlnks/hnrstrrhts values - "N"/"E"/empty observed live,
    # never decoded into a label.
    even_side = AddressRange(side="rechts", first=2, last=10, structure="E")
    assert even_side.structure == "E"


def test_address_requires_geometry_but_suffix_and_links_are_optional():
    address = Address(geometry=Coordinate(value=(2.35, 48.86), crs="EPSG:4326"))
    assert address.suffix is None
    assert address.street_links == ()


def test_street_type_code_and_label_are_independently_optional():
    # NWB: code only (bst_code, no plain label carried). BD TOPO: label
    # only (nature, no code). NVDB: both (typeVeg + typeVeg_sosi).
    code_only = StreetType(code="VP")
    label_only = StreetType(label="Route à 1 chaussée")
    both = StreetType(code="enkelBilveg", label="Enkel bilveg")
    assert code_only.label is None
    assert label_only.code is None
    assert both.code and both.label
