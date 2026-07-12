"""Smoke tests for the streetworks.common canonical types themselves (not
converters - those are tested per provider, e.g. test_common_srwr.py)."""

from datetime import datetime

from streetworks.common import (
    Coordinate,
    DateConfidence,
    Notice,
    SourceGrade,
    Works,
    WorksPlanning,
    WorksSite,
)


def test_coordinate_carries_explicit_crs():
    bng = Coordinate(value=(412345.0, 112345.0), crs="EPSG:27700")
    wgs84 = Coordinate(value=(51.5, -0.12), crs="EPSG:4326")
    assert bng.crs == "EPSG:27700"
    assert wgs84.crs == "EPSG:4326"
    assert bng != wgs84


def test_works_site_defaults_are_honest_emptiness():
    site = WorksSite()
    assert site.reference is None
    assert site.date_confidence is DateConfidence.UNKNOWN
    assert site.notices == ()
    assert site.raw is None


def test_works_wraps_sites_and_keeps_raw():
    site = WorksSite(
        reference="UG1071000002-01",
        works_type="highway_repair_and_maintenance_works",
        date_confidence=DateConfidence.VERIFIED,
        proposed_start=datetime(2026, 7, 1),
        notices=(Notice(notice_type="works_start", date=datetime(2026, 7, 1)),),
        source_grade=SourceGrade.REGISTER,
    )
    works = Works(
        reference="UG1071000002",
        location_usrn="12345",
        promoter="Example Utility Ltd",
        source_grade=SourceGrade.REGISTER,
        sites=(site,),
        raw={"work_reference_number": "UG1071000002"},
    )
    assert works.sites[0].reference == "UG1071000002-01"
    assert works.sites[0].notices[0].notice_type == "works_start"
    assert works.raw == {"work_reference_number": "UG1071000002"}
    assert works.plannings == ()


def test_works_planning_is_a_distinct_type_with_optional_link():
    paa = WorksPlanning(
        kind="paa",
        works_reference="UG1071000002",
        indicative_start=datetime(2026, 8, 1),
        source_grade=SourceGrade.REGISTER,
    )
    forward_plan = WorksPlanning(kind="forward_plan", source_grade=SourceGrade.REGISTER)
    assert paa.works_reference == "UG1071000002"
    assert forward_plan.works_reference is None
