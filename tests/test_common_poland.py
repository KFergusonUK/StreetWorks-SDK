"""Tests for streetworks.common.from_poland.

Fixture is real GDDKiA data, parsed through the real client
(tests/fixtures/poland_utrudnienia.xml) - see test_poland.py's own
docstring for provenance.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree

from streetworks.common import DateConfidence, from_poland
from streetworks.poland.client import _parse_record


def _records_from_fixture():
    data = (Path(__file__).parent / "fixtures" / "poland_utrudnienia.xml").read_bytes()
    root = ElementTree.fromstring(data)
    return [_parse_record(e) for e in root.findall("utr")]


RECORDS = _records_from_fixture()
ROADWORKS = [r for r in RECORDS if r["typ"] == "U"]


def test_coordinate_is_true_lat_lon_not_swapped():
    works = from_poland(ROADWORKS)[0]
    coordinate = works.coordinate
    assert coordinate.crs == "EPSG:4326"
    assert coordinate.value == (53.598348, 18.617455)


def test_missing_coordinate_stays_none_not_guessed():
    works = from_poland(ROADWORKS)[1]
    assert works.coordinate is None


def test_location_description_combines_road_and_section():
    works = from_poland(ROADWORKS)[0]
    assert works.sites[0].location_description == "A1: W. Warlubie - W. Nowe Marzy"


def test_works_type_is_the_real_rodzaj_code():
    works = from_poland(ROADWORKS)[0]
    assert works.sites[0].works_type == "U33"


def test_traffic_management_is_the_real_objazd_text():
    works = from_poland(ROADWORKS)[0]
    assert "remont nawierzchni" in works.sites[0].traffic_management


def test_real_offset_without_colon_is_parsed():
    works = from_poland(ROADWORKS)[0]
    site = works.sites[0]
    tz = timezone(timedelta(hours=2))
    assert site.proposed_start == datetime(2026, 8, 22, 13, 0, 0, tzinfo=tz)
    assert site.proposed_end == datetime(2026, 8, 29, 13, 0, 0, tzinfo=tz)


def test_date_confidence_is_uniformly_estimated():
    for works in from_poland(ROADWORKS):
        assert works.sites[0].date_confidence is DateConfidence.ESTIMATED


def test_reference_is_none_no_native_id_exists():
    for works in from_poland(ROADWORKS):
        assert works.reference is None
        assert works.sites[0].reference is None


def test_territory_and_administrative_area():
    works_list = from_poland(ROADWORKS)
    assert all(w.territory == "Poland" for w in works_list)
    assert all(
        w.administrative_area == "Generalna Dyrekcja Dróg Krajowych i Autostrad (GDDKiA)"
        for w in works_list
    )
