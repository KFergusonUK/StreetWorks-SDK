"""Tests for streetworks.common.from_dc.

Fixture is real DDOT Construction Permit data
(tests/fixtures/dc_construction_permits.json), captured live 2026-08-21 -
DC's open data is licensed CC BY 4.0, so real records are committed here,
the same way Jersey's/TIGERweb's are. Covers real ``Issued``, ``Pending
Assignment``, ``Denied`` and ``Approved (Pending Payment)`` statuses, a
record with every work-type flag false, a record with five of six true,
and real records with no ``PERMITNUMBER`` yet assigned.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from streetworks.common import DateConfidence, SourceGrade, from_dc

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "dc_construction_permits.json").read_text(
        encoding="utf-8"
    )
)


def _by_permit(works_list):
    return {w.reference: w for w in works_list if w.reference}


def test_issued_status_produces_verified_actual_dates():
    works_list = from_dc(FIXTURE["features"])
    works = _by_permit(works_list)["PA490385"]
    site = works.sites[0]

    assert site.status == "Issued"
    assert site.works_type == "Excavation"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert site.actual_start == datetime(2026, 8, 3, 4, 0, tzinfo=timezone.utc)
    assert site.actual_end == datetime(2027, 1, 29, 5, 0, tzinfo=timezone.utc)
    assert site.proposed_start is None
    assert works.promoter == "DCWater/CIP"
    assert works.territory == "USA"
    assert works.administrative_area == "District Department of Transportation"
    assert works.source_grade is SourceGrade.REGISTER


def test_pending_assignment_status_produces_estimated_proposed_dates():
    works_list = from_dc(FIXTURE["features"])
    pending = [w for w in works_list if w.sites[0].status == "Pending Assignment"]
    assert pending  # real records exist in this fixture

    site = pending[0].sites[0]
    assert site.date_confidence is DateConfidence.ESTIMATED
    assert site.actual_start is None


def test_denied_status_is_not_verified():
    works_list = from_dc(FIXTURE["features"])
    denied = [w for w in works_list if w.sites[0].status == "Denied"]
    assert denied  # a real record exists in this fixture
    assert denied[0].sites[0].date_confidence is not DateConfidence.VERIFIED


def test_no_permit_number_yet_still_produces_a_free_standing_works():
    # Real "Pending Assignment" records have no PERMITNUMBER at all yet -
    # an honest gap, not dropped.
    works_list = from_dc(FIXTURE["features"])
    unassigned = [w for w in works_list if w.reference is None]
    assert unassigned


def test_work_type_joins_every_true_flag_not_just_the_first():
    works_list = from_dc(FIXTURE["features"])
    multi = next(
        w for w in works_list if w.sites[0].works_type and w.sites[0].works_type.count("/") >= 3
    )
    assert multi.sites[0].works_type == (
        "Excavation / Paving / Landscaping / Projections / Fixture"
    )


def test_no_flags_true_gives_none_not_empty_string():
    works_list = from_dc(FIXTURE["features"])
    works = _by_permit(works_list)["PA480897"]
    assert works.sites[0].works_type is None


def test_coordinate_is_flipped_to_lat_lon_wgs84():
    works_list = from_dc(FIXTURE["features"])
    works = _by_permit(works_list)["PA490385"]
    coordinate = works.sites[0].coordinate
    assert coordinate.crs == "EPSG:4326"
    lat, lon = coordinate.value
    assert 38 < lat < 39  # DC's real latitude band
    assert -78 < lon < -76  # DC's real longitude band


def test_work_detail_lands_on_traffic_management():
    works_list = from_dc(FIXTURE["features"])
    works = _by_permit(works_list)["PA490385"]
    assert "Lead Free DC Program" in works.sites[0].traffic_management
