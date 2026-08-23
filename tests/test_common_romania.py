"""Tests for streetworks.common.from_romania.

Fixture is real CNAIR data, parsed through the real client
(tests/fixtures/romania_dispecerat.html) - see test_romania.py's own
docstring for provenance.
"""

from datetime import datetime
from pathlib import Path

from streetworks.common import DateConfidence, from_romania
from streetworks.romania.client import ROADWORKS_SECTIONS, _DispatchBoardParser

HTML = (Path(__file__).parent / "fixtures" / "romania_dispecerat.html").read_text(
    encoding="utf-8"
)


def _roadworks_records():
    parser = _DispatchBoardParser()
    parser.feed(HTML)
    records = []
    for title in ROADWORKS_SECTIONS:
        for row in parser.sections.get(title, []):
            records.append({**row, "section": title})
    return records


RECORDS = _roadworks_records()


def _by_road(works_list):
    return {w.sites[0].location_description.split(":")[0]: w for w in works_list}


def test_coordinate_is_always_none_no_field_exists():
    for works in from_romania(RECORDS):
        assert works.coordinate is None


def test_reference_is_always_none_positional_number_not_stable():
    for works in from_romania(RECORDS):
        assert works.reference is None
        assert works.sites[0].reference is None


def test_works_type_from_short_duration_section():
    works = _by_road(from_romania(RECORDS))["A1"]
    assert works.sites[0].works_type == "Lucrări de scurtă durată"


def test_works_type_from_rehabilitation_section():
    works = _by_road(from_romania(RECORDS))["A2"]
    assert works.sites[0].works_type == "Reabilitare, modernizare, întreținere și reparații"


def test_location_description_combines_road_and_localities():
    works = _by_road(from_romania(RECORDS))["A1"]
    assert works.sites[0].location_description == "A1: ACILIU (SB) - SIBIU (SB)"


def test_traffic_management_prefers_cauza_falls_back_to_lucrari():
    works_a1 = _by_road(from_romania(RECORDS))["A1"]
    assert "dispozitive de acoperire" in works_a1.sites[0].traffic_management
    works_a2 = _by_road(from_romania(RECORDS))["A2"]
    assert "reparatii pod" in works_a2.sites[0].traffic_management


def test_real_dates_parsed_naive_no_timezone():
    works = _by_road(from_romania(RECORDS))["A1"]
    site = works.sites[0]
    assert site.proposed_start == datetime(2026, 8, 20, 14, 0, 0)
    assert site.proposed_end == datetime(2026, 8, 24, 12, 0, 0)


def test_date_confidence_is_uniformly_estimated():
    for works in from_romania(RECORDS):
        assert works.sites[0].date_confidence is DateConfidence.ESTIMATED


def test_territory_and_administrative_area():
    works_list = from_romania(RECORDS)
    assert all(w.territory == "Romania" for w in works_list)
    assert all(
        "CNAIR" in w.administrative_area for w in works_list
    )
