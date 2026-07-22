"""Tests for streetworks.common.from_jersey.

Fixture is real Jersey RoadWorkx data (tests/fixtures/jersey_roadworks_real.json),
captured live this session - Jersey's data is open for public consumption
(per instruction), so real records are committed here, the same way
TIGERweb's are. Covers all three real STATUS values (In Progress, Pending,
Finished) and a real multi-site project (P108864-JSC, three real JOBIDs).
"""

import json
from pathlib import Path

from streetworks.common import DateConfidence, SourceGrade, from_jersey

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "jersey_roadworks_real.json").read_text(
        encoding="utf-8"
    )
)


def _works_by_reference(works_list):
    return {w.reference: w for w in works_list}


def test_groups_records_by_projid_into_one_works_with_multiple_sites():
    # Real project P108864-JSC: three real RoadWorks records (JOBID
    # 107263/107264/107265) sharing one PROJID - confirmed live.
    works_list = from_jersey(FIXTURE["features"])
    by_ref = _works_by_reference(works_list)
    works = by_ref["P108864-JSC"]

    assert len(works.sites) == 3
    assert {s.reference for s in works.sites} == {"107263", "107264", "107265"}
    assert works.territory == "Jersey"
    assert works.administrative_area == "GHA"
    assert works.promoter == "Jubilee Scaffolding"
    assert works.source_grade is SourceGrade.REGISTER


def test_in_progress_status_produces_verified_actual_dates():
    works_list = from_jersey(FIXTURE["features"])
    site = _works_by_reference(works_list)["P108864-JSC"].sites[0]

    assert site.status == "In Progress"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert (site.actual_start.year, site.actual_start.month, site.actual_start.day) == (
        2021,
        11,
        7,
    )
    assert (site.actual_start.hour, site.actual_start.minute) == (10, 0)
    assert site.actual_end is not None
    assert site.proposed_start is None


def test_pending_status_produces_estimated_proposed_dates():
    # The design brief's "planned/future dimension" - a real STATUS value,
    # not a separate layer or type. See from_jersey's module docstring.
    works_list = from_jersey(FIXTURE["features"])
    pending = [w for w in works_list if w.sites[0].status == "Pending"]
    assert pending  # real Pending records exist in this fixture

    site = pending[0].sites[0]
    assert site.date_confidence is DateConfidence.ESTIMATED
    assert site.proposed_start is not None
    assert site.actual_start is None


def test_dates_are_timezone_aware_in_jerseys_own_zone():
    works_list = from_jersey(FIXTURE["features"])
    site = _works_by_reference(works_list)["P108864-JSC"].sites[0]
    assert site.actual_start.tzinfo is not None
    # Jersey observes the same UTC offset as the UK - November is GMT (UTC+0).
    assert site.actual_start.utcoffset().total_seconds() == 0


def test_geometry_carries_real_jersey_crs_never_reprojected():
    works_list = from_jersey(FIXTURE["features"])
    site = _works_by_reference(works_list)["P108864-JSC"].sites[0]
    assert site.coordinate.crs == "EPSG:3109"
    assert site.coordinate.points is not None  # a real multi-vertex LineString


def test_finished_status_is_also_verified_not_estimated():
    works_list = from_jersey(FIXTURE["features"])
    finished = [w for w in works_list if w.sites[0].status == "Finished"]
    assert finished  # real Finished records exist in this fixture

    site = finished[0].sites[0]
    assert site.date_confidence is DateConfidence.VERIFIED
    assert site.actual_end is not None
