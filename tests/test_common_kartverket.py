"""Tests for streetworks.common.from_kartverket.

Fixtures are real Kartverket responses (tests/fixtures/kartverket_*) built
earlier this session. SSR (place names) has no converter here - it's
neither a street nor an address, per the design brief.
"""

import csv
import json
from pathlib import Path

from streetworks.common import from_kartverket
from streetworks.kartverket.models import address_from_csv_row, address_from_json

FIXTURES = Path(__file__).parent / "fixtures"


def test_rest_route_has_no_identifiers_a_real_gap_not_a_bug():
    doc = json.loads((FIXTURES / "kartverket_search.json").read_text(encoding="utf-8"))
    address = address_from_json(doc["adresser"][0])
    a = from_kartverket(address)

    assert a.identifiers == ()  # REST API states neither lokalid nor uuid_adresse
    assert a.housenumber == "1"
    assert a.street_name == "Karl Johans gate"
    assert a.street_links[0].scheme == "adressekode"
    assert a.street_links[0].scope == "3105"  # municipality-scoped


def test_bulk_route_carries_a_real_uuid_adresse_identifier():
    with (FIXTURES / "kartverket_bulk_sample.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    address = address_from_csv_row(rows[0])
    a = from_kartverket(address)

    assert len(a.identifiers) == 1
    assert a.identifiers[0].scheme == "uuid_adresse"
    assert a.as_at is not None  # real oppdateringsdato parsed


def test_same_adressekode_in_different_kommuner_is_not_the_same_street():
    # Real, live-confirmed: code 15100 means a different street in
    # Sarpsborg than the same code would in another municipality - scope
    # is what keeps the two from comparing equal.
    doc = json.loads((FIXTURES / "kartverket_search.json").read_text(encoding="utf-8"))
    address = address_from_json(doc["adresser"][0])
    a = from_kartverket(address)
    assert a.street_links[0].value == "15100"
    assert a.street_links[0].scope == "3105"
