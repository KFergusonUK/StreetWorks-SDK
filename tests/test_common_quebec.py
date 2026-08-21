"""Tests for streetworks.common.from_quebec.

Fixture is real MTQ "Travaux routiers" data
(tests/fixtures/quebec_travaux_routiers.json), captured live 2026-08-21 -
MTQ's open data is licensed CC BY 4.0, so real records are committed
here, the same way Jersey's/Lyon's/DC's are. Covers a real multi-entrave
chantier (identifiantChantier 250648, 3 real entraves) and four other
real single-entrave chantiers spanning distinct entraveType values.
"""

import json
from pathlib import Path

from streetworks.common import DateConfidence, SourceGrade, from_quebec

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "quebec_travaux_routiers.json").read_text(
        encoding="utf-8"
    )
)


def _by_chantier(works_list):
    return {w.reference: w for w in works_list}


def test_groups_records_by_identifiant_chantier_into_one_works_with_multiple_sites():
    works_list = from_quebec(FIXTURE["features"])
    works = _by_chantier(works_list)["250648"]

    assert len(works.sites) == 3
    assert {s.reference for s in works.sites} == {"135768", "165258", "165685"}
    assert works.territory == "Canada"
    assert works.administrative_area == "Ministère des Transports et de la Mobilité durable (MTQ)"
    assert works.source_grade is SourceGrade.OPERATOR


def test_single_entrave_chantiers_get_their_own_works():
    works_list = from_quebec(FIXTURE["features"])
    works = _by_chantier(works_list)["311996"]
    assert len(works.sites) == 1
    assert works.sites[0].reference == "164507"


def test_date_confidence_is_uniformly_estimated():
    # No independent verified/status flag exists on this feed - see
    # from_quebec's own module docstring.
    works_list = from_quebec(FIXTURE["features"])
    for works in works_list:
        for site in works.sites:
            assert site.date_confidence is DateConfidence.ESTIMATED
            assert site.actual_start is None


def test_dates_parse_the_real_slash_separated_format_in_montreal_zone():
    works_list = from_quebec(FIXTURE["features"])
    site = next(s for w in works_list for s in w.sites if s.reference == "135768")
    assert site.proposed_start is not None
    assert site.proposed_start.year == 2022
    assert site.proposed_start.month == 10
    assert site.proposed_start.day == 8
    assert site.proposed_start.tzinfo is not None


def test_works_type_is_the_real_work_title_status_is_the_severity_enum():
    works_list = from_quebec(FIXTURE["features"])
    site = next(s for w in works_list for s in w.sites if s.reference == "164507")
    assert site.works_type == "Construction pont temporaire"
    assert site.status == "Mineure (semaine et fin de semaine)"


def test_traffic_management_carries_the_real_entrave_prose():
    works_list = from_quebec(FIXTURE["features"])
    site = next(s for w in works_list for s in w.sites if s.reference == "164507")
    assert "alternance" in site.traffic_management


def test_empty_route_autoroute_does_not_crash_and_geometry_still_present():
    # A real record in the multi-entrave group has routeAutoroute="" -
    # not promoted anywhere, but the record still converts cleanly.
    works_list = from_quebec(FIXTURE["features"])
    site = next(s for w in works_list for s in w.sites if s.reference == "165685")
    assert site.coordinate is not None
    assert site.coordinate.crs == "EPSG:4326"


def test_linestring_geometry_keeps_every_vertex():
    works_list = from_quebec(FIXTURE["features"])
    site = next(s for w in works_list for s in w.sites if s.reference == "135768")
    assert site.coordinate.points is not None
    assert len(site.coordinate.points) > 1
