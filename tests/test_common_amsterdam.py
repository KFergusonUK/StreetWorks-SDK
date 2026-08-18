"""Tests for streetworks.common.from_amsterdam.

Fixture is real Amsterdam WIOR (Werken in de Openbare Ruimte) data
(tests/fixtures/amsterdam_roadworks_real.json), captured live
2026-08-18 from api.data.amsterdam.nl's real, keyless REST endpoint.
The MultiPolygon record's rings are trimmed to 4 real vertices + the
closing one (fixture size only - the converter only ever reads the
first ring's first vertex, so this doesn't affect what's under test).
"""

import json
from pathlib import Path

from streetworks.common import DateConfidence, from_amsterdam

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "amsterdam_roadworks_real.json").read_text(
        encoding="utf-8"
    )
)

_RECORDS = {r["wiorNummer"]: r for r in FIXTURE}


def test_real_reference_and_project_name_as_location_description():
    works = from_amsterdam([_RECORDS["W22013761"]])[0]
    assert works.reference == "W22013761"
    site = works.sites[0]
    assert site.location_description == (
        "Noordzeeweg (tussen Luvernes en Hornweg) T-stukken vervangen 550037139"
    )
    assert site.works_type == "Vervanging"


def test_polygon_geometry_uses_first_ring_first_vertex():
    works = from_amsterdam([_RECORDS["W22013761"]])[0]
    lat, lon = works.coordinate.value
    # Real Amsterdam geography - (lat, lon) convention, swapped from
    # the real [lon, lat] GeoJSON order.
    assert 52.3 < lat < 52.5
    assert 4.7 < lon < 5.0


def test_multipolygon_uses_first_polygon_first_ring_first_vertex():
    works = from_amsterdam([_RECORDS["W23009721"]])[0]
    lat, lon = works.coordinate.value
    assert 52.3 < lat < 52.5
    assert 4.7 < lon < 5.0


def test_in_progress_status_is_verified_with_actual_dates():
    works = from_amsterdam([_RECORDS["W22013761"]])[0]
    site = works.sites[0]
    assert site.status == "Uitvoering"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert site.actual_start is not None
    assert site.actual_end is not None


def test_planning_status_is_estimated_with_no_actual_dates():
    works = from_amsterdam([_RECORDS["W23007308"]])[0]
    site = works.sites[0]
    assert site.status == "Projectaanpak"
    assert site.date_confidence is DateConfidence.ESTIMATED
    assert site.actual_start is None
    assert site.actual_end is None
    assert site.proposed_start is not None


def test_no_grouping_flat_one_to_one():
    works_list = from_amsterdam(list(_RECORDS.values()))
    assert len(works_list) == 3
    assert all(len(w.sites) == 1 for w in works_list)


def test_promoter_and_street_ref_never_populated():
    works = from_amsterdam([_RECORDS["W22013761"]])[0]
    assert works.promoter is None
    assert works.sites[0].street_ref is None
