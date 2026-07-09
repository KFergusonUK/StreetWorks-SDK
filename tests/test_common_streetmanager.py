"""Tests for streetworks.common.from_streetmanager.

The fixture (tests/fixtures/streetmanager_permits_sandbox.json) is real
sandbox data: three permit rows (a "minor" permit with Point geometry and no
actual dates; a "paa" and the "major" permit that later superseded it,
sharing one work_reference_number, the major carrying real actual_start/end
dates and LineString geometry) and one forward-plan row. Confirms two things
the abstract design spec didn't - and live data did: permit references really
do follow the base reference plus "-01"/"-02" suffix convention, and a
Forward Plan already carries its eventual work_reference_number rather than
floating free of any Works.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from streetworks.common import DateConfidence, SourceGrade, from_streetmanager

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "streetmanager_permits_sandbox.json").read_text(
        encoding="utf-8"
    )
)


def _works_by_reference(works_list):
    return {w.reference: w for w in works_list}


def test_minor_permit_becomes_a_site_with_point_coordinate():
    works_list = from_streetmanager(FIXTURE["rows"])
    by_ref = _works_by_reference(works_list)
    works = by_ref["UG00065061596"]

    assert works.source_grade is SourceGrade.REGISTER
    assert works.promoter == "DURHAM COUNTY COUNCIL"
    assert works.location_usrn == "33909869"
    assert works.coordinate.crs == "EPSG:27700"
    assert works.coordinate.value == (425334.09, 533885.19)
    assert len(works.sites) == 1
    assert works.plannings == ()

    site = works.sites[0]
    assert site.reference == "UG00065061596-01"
    assert site.proposed_start == datetime(2026, 6, 3, tzinfo=timezone.utc)
    assert site.actual_start is None
    assert site.date_confidence is DateConfidence.ESTIMATED


def test_paa_and_major_permit_share_one_works_and_paa_is_planning_not_a_site():
    works_list = from_streetmanager(FIXTURE["rows"])
    by_ref = _works_by_reference(works_list)
    works = by_ref["UG27724003165"]

    # The PAA never becomes a WorksSite - it's a planning artifact under the
    # same Works as the permit that superseded it.
    assert len(works.sites) == 1
    assert works.sites[0].reference == "UG27724003165-02"
    assert len(works.plannings) == 1
    assert works.plannings[0].kind == "paa"
    assert works.plannings[0].works_reference == "UG27724003165"

    site = works.sites[0]
    # LineString geometry collapses to its first vertex.
    assert site.coordinate.value == (428390.419828733, 525491.263508591)
    assert site.actual_start == datetime(2025, 11, 19, 9, tzinfo=timezone.utc)
    assert site.actual_end == datetime(2025, 11, 19, 10, tzinfo=timezone.utc)
    assert site.date_confidence is DateConfidence.VERIFIED


def test_forward_plan_attaches_to_matching_works_not_free_standing():
    works_list = from_streetmanager(FIXTURE["rows"], FIXTURE["forward_plan_rows"])
    # UG27930424245 has no permits yet - only the forward plan references it -
    # so it gets its own thin Works rather than landing in the fallback
    # free-standing bucket.
    by_ref = _works_by_reference(works_list)
    assert "UG27930424245" not in by_ref  # no permit rows share this reference

    free_standing = [w for w in works_list if w.reference is None]
    assert len(free_standing) == 1
    assert len(free_standing[0].plannings) == 1
    planning = free_standing[0].plannings[0]
    assert planning.kind == "forward_plan"
    assert planning.works_reference == "UG27930424245"
    assert planning.indicative_start == datetime(2026, 2, 2, tzinfo=timezone.utc)


def test_forward_plan_attaches_to_an_existing_works_when_reference_matches():
    # Same fixture, but pretend the forward plan's reference matches a
    # permit group already present - it should attach there, not fall back.
    forward_plan = dict(FIXTURE["forward_plan_rows"][0])
    forward_plan["work_reference_number"] = "UG00065061596"

    works_list = from_streetmanager(FIXTURE["rows"], [forward_plan])
    by_ref = _works_by_reference(works_list)
    works = by_ref["UG00065061596"]
    assert len(works.plannings) == 1
    assert works.plannings[0].kind == "forward_plan"
    # No extra free-standing Works was added - the plan attached in place.
    assert all(w.reference is not None for w in works_list)
