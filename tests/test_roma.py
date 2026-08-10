"""Tests for the Roma ("Roma si trasforma") adapter.

Credential-free, live-verified - see the module docstring in
``streetworks.roma.client``. ``roma_interventi_live_pull.json`` holds 6
REAL records from a real, unauthenticated pull (2026-08-09): three real
"Strade e infrastrutture" + "Cantiere" records with coordinates (real
street-maintenance projects), one real "Strade e infrastrutture" +
"Cantiere" record with no coordinate (a district-wide maintenance
project with no point geometry), a real "Strade e infrastrutture"
record already at "Fine lavori" (finished, excluded), and a real
"Cantiere" record tagged "Rigenerazione urbana" instead (excluded - not
street/infrastructure). All nids, titles and coordinates are real, not
fabricated.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_roma
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.roma import INTERVENTI_URL, RomaClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "roma_interventi_live_pull.json"
RECORDS = json.loads(FIXTURE_PATH.read_text())


def _by_nid(records: list[dict], nid: str) -> dict:
    return next(r for r in records if r["nid"] == nid)


def _mock_feed() -> None:
    respx.get(INTERVENTI_URL).mock(return_value=httpx.Response(200, json=RECORDS))


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_interventi_needs_no_credentials_and_is_unfiltered():
    _mock_feed()
    with RomaClient() as roma:
        records = list(roma.iter_interventi())
    assert len(records) == len(RECORDS)  # includes finished + non-street records


@respx.mock
def test_iter_roadworks_filters_to_strade_and_cantiere():
    _mock_feed()
    with RomaClient() as roma:
        records = list(roma.iter_roadworks())
    assert len(records) == 4
    for r in records:
        assert "Strade e infrastrutture" in r["field_tag_temi"]
        assert r["field_stato_lavori"] == "Cantiere"


@respx.mock
def test_iter_roadworks_excludes_finished_and_other_theme():
    _mock_feed()
    with RomaClient() as roma:
        records = list(roma.iter_roadworks())
    nids = {r["nid"] for r in records}
    assert "1433" not in nids  # Fine lavori
    assert "1237" not in nids  # Rigenerazione urbana, not street


def test_client_requires_no_credentials():
    RomaClient()


# --------------------------------------------------------------------------- #
# Converter - no grouping, 1:1
# --------------------------------------------------------------------------- #


def test_from_roma_produces_one_works_per_record_no_grouping():
    works_list = from_roma(RECORDS)
    assert len(works_list) == len(RECORDS)
    assert all(len(w.sites) == 1 for w in works_list)
    assert all(w.territory == "Italy" for w in works_list)
    assert all(w.administrative_area == "Roma Capitale" for w in works_list)
    assert all(w.source_grade == SourceGrade.OPERATOR for w in works_list)


def test_from_roma_reference_is_nid():
    works_list = from_roma([_by_nid(RECORDS, "1703")])
    assert works_list[0].reference == "1703"


def test_from_roma_corrects_the_source_lon_lat_swap():
    """The source's own field_posizione has "lon"/"lat" swapped
    relative to true geography - Rome's real latitude is ~41.9, real
    longitude ~12.5. This must NOT be reproduced."""
    record = _by_nid(RECORDS, "1703")
    raw_position = record["field_posizione"]
    assert 41 < raw_position["lon"] < 42  # source's "lon" is really latitude
    assert 12 < raw_position["lat"] < 13  # source's "lat" is really longitude

    works_list = from_roma([record])
    coord = works_list[0].sites[0].coordinate
    assert coord.crs == "EPSG:4326"
    true_lat, true_lon = coord.value
    assert 41 < true_lat < 42  # corrected: real latitude
    assert 12 < true_lon < 13  # corrected: real longitude


def test_from_roma_missing_coordinate_stays_none():
    works_list = from_roma([_by_nid(RECORDS, "1374")])
    assert works_list[0].sites[0].coordinate is None


def test_from_roma_street_ref_is_never_populated():
    works_list = from_roma(RECORDS)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_roma_no_dates_ever_populated():
    """No date field exists anywhere in this schema - date_confidence
    is always UNKNOWN, never inferred from field_stato_lavori."""
    works_list = from_roma(RECORDS)
    for w in works_list:
        for site in w.sites:
            assert site.date_confidence is DateConfidence.UNKNOWN
            assert site.proposed_start is None
            assert site.proposed_end is None
            assert site.actual_start is None
            assert site.actual_end is None


def test_from_roma_works_type_is_tag_temi():
    works_list = from_roma([_by_nid(RECORDS, "1703")])
    assert works_list[0].sites[0].works_type == "Strade e infrastrutture"


def test_from_roma_location_description_includes_title():
    works_list = from_roma([_by_nid(RECORDS, "1703")])
    site = works_list[0].sites[0]
    assert site.location_description is not None
    assert "Via Portuense" in site.location_description


def test_from_roma_excluded_records_still_convert_when_passed_directly():
    """from_roma() itself never filters by tag/status - only
    RomaClient.iter_roadworks() does."""
    works_list = from_roma([_by_nid(RECORDS, "1433")])
    assert len(works_list) == 1
