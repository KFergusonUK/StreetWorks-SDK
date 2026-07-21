"""Tests for streetworks.common.from_srwr.

Reuses the same real-derived Activity/Phase (007)/Notice (006) fixture
lines as test_srwr.py and adds an Undertaker-Phase (008) row (following the
real field layout in srwr/records.py's FIELDS["008"]) to exercise the
phase_number join that from_srwr adds - the base SRWR reader has no such
join.
"""

import io

from streetworks.common import DateConfidence, SourceGrade, from_srwr
from streetworks.srwr import iter_activities

HEADER = (
    '02,000,"#SRWR data for 2026-07-04, Produced 2026-07-05 02:00, '
    'For licensing visit https://roadworks.scot/opendata"'
)
ACTIVITY_A = (
    '02,001,03268777,2022-12-09 09:13:35.08,2026-07-04 04:20:09.72,'
    '010360002,"TL002-S1711",009066001,02,"False",,2,84202034,"False"'
)
PHASE_A = (
    '02,007,03268777,2022-12-09 09:13:35.08,2026-07-04 04:20:09.72,,'
    '"Outside Crossgates Cottages",2,,05,07,"False",'
    '"LINESTRING (333226.5 709261.7, 333285.0 709270.1)",03,07,"False","False",'
    '"False","False","False","False","False","False",'
    '"True","False","False","False","False","False"'
)
NOTICE_A = (
    '02,006,03268777,010360002,2,38,2022-12-09 09:13:35.08,'
    '"Revised duration",,1,"False",3,,,2022-12-12 08:00:00.00,2022-12-16 17:00:00.00'
)

UNDERTAKER_PHASE_A = ",".join(
    [
        "02",
        "008",
        "03268777",  # activity_id
        "2",  # phase_number - matches PHASE_A/NOTICE_A
        "2022-12-09 09:00:00.00",  # proposed_start
        '"True"',  # has_proposed_start_time
        "2022-12-12 08:00:00.00",  # actual_start
        '"True"',  # has_actual_start_time
        "2022-12-16 17:00:00.00",  # estimated_end_proposed
        "2022-12-16 17:05:00.00",  # actual_end
        "",  # earliest_start_advance_planning
        "",  # latest_start_advance_planning
        "",  # earliest_start_proposed
        "",  # latest_start_proposed
        "",  # latest_possible_end
        "",  # reasonable_duration
        "",  # reasonable_end
        "",  # duration_challenge_estimate
        "",  # phase_type
        "",  # works_technique
        "",  # street_category
        "05",  # traffic_management_type
    ]
)

SECTION = "\r\n".join([HEADER, ACTIVITY_A, NOTICE_A, PHASE_A, UNDERTAKER_PHASE_A])


def test_from_srwr_joins_phase_to_undertaker_phase_and_attaches_notices():
    activity = next(iter_activities(io.StringIO(SECTION)))
    works = from_srwr(activity)

    assert works.reference == "TL002-S1711"
    assert works.location_usrn == "84202034"
    assert works.territory == "Scotland"
    assert works.administrative_area == "9066001"  # bare notifiable_district_id, no districts map
    assert works.source_grade is SourceGrade.REGISTER
    assert len(works.sites) == 1

    site = works.sites[0]
    assert site.reference == "3268777-2"
    # WorksSite delegates territory/administrative_area to its parent Works.
    assert site.territory == "Scotland"
    assert site.administrative_area == "9066001"
    assert site.works_type  # decoded via describe(), not the bare "05" code
    assert site.status  # decoded activity_status
    assert site.location_description == "Outside Crossgates Cottages"
    # Dates come from the joined 008 record, not the 007.
    assert site.proposed_start.isoformat(sep=" ") == "2022-12-09 09:00:00"
    assert site.actual_start.isoformat(sep=" ") == "2022-12-12 08:00:00"
    assert site.actual_end.isoformat(sep=" ") == "2022-12-16 17:05:00"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert site.traffic_management  # decoded traffic_management_type

    assert len(site.notices) == 1
    assert site.notices[0].text == "Revised duration"
    assert site.notices[0].notice_type  # decoded notice_type
    assert site.raw[0].record_type == "007"
    assert site.raw[1].record_type == "008"


def test_from_srwr_without_undertaker_phase_falls_back_to_unknown_confidence():
    section = "\r\n".join([HEADER, ACTIVITY_A, PHASE_A])
    activity = next(iter_activities(io.StringIO(section)))
    works = from_srwr(activity)

    site = works.sites[0]
    assert site.proposed_start is None
    assert site.actual_start is None
    assert site.date_confidence is DateConfidence.UNKNOWN
    assert site.notices == ()
    assert site.raw == (site.raw[0],)  # just the phase, no undertaker-phase to join


def test_from_srwr_decodes_administrative_area_when_districts_map_given():
    activity = next(iter_activities(io.StringIO(SECTION)))
    works = from_srwr(activity, districts={9066001: "Fife Council"})
    assert works.administrative_area == "Fife Council"


def test_from_srwr_leaves_site_street_ref_none_despite_a_stated_header_usrn():
    # streetworks 0.8.0: SRWR states street identity (001.usrn, used for
    # Works.location_usrn above, and separately real 004 "streets" records)
    # but never ties it to a specific phase/site - so WorksSite.street_ref
    # stays None rather than copying the activity-level usrn onto every
    # site, which could misattribute street identity where an activity
    # spans more than one real street. See from_srwr's module docstring.
    activity = next(iter_activities(io.StringIO(SECTION)))
    works = from_srwr(activity)
    assert works.location_usrn == "84202034"  # stated at the Works level
    assert works.sites[0].street_ref is None  # not attributed per-site
