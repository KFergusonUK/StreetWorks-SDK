"""Tests for streetworks.common.from_ban.

Exercises the exact route-dependency the design brief called out: the
geocoding API folds any suffix into ``housenumber``; only the bulk CSV
routes decompose it. Fixtures are real BAN data built earlier this session.
"""

import csv
import json
from pathlib import Path

from streetworks.ban.models import (
    address_from_api_feature,
    address_from_bal_row,
    address_from_csv_row,
)
from streetworks.common import Identifier, from_ban

FIXTURES = Path(__file__).parent / "fixtures"


def test_api_route_leaves_suffix_none_whole_value_in_housenumber():
    doc = json.loads((FIXTURES / "ban_reverse.json").read_text(encoding="utf-8"))
    address = address_from_api_feature(doc["features"][0])
    a = from_ban(address)

    assert a.housenumber == "8"
    assert a.suffix is None  # the API never decomposes it
    assert a.street_name == "Rue des Halles"


def test_bal_route_decomposes_a_real_bis_suffix():
    with (FIXTURES / "ban_bulk_csv_bal_sample.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    bis_row = next(r for r in rows if r.get("suffixe"))
    address = address_from_bal_row(bis_row)
    a = from_ban(address)

    assert a.housenumber == "4"
    assert a.suffix == "bis"  # real, decomposed value


def test_street_links_marks_toponyme_id_as_derived_not_a_ban_field():
    doc = json.loads((FIXTURES / "ban_reverse.json").read_text(encoding="utf-8"))
    address = address_from_api_feature(doc["features"][0])
    a = from_ban(address)

    assert len(a.street_links) == 1
    link = a.street_links[0]
    assert link.scheme == "ban_toponyme_id_derived"
    assert link.value == "75101_4461"
    assert link.scope == "75101"  # municipality-scoped, per BAN's own identifier shape


def test_plain_csv_route_keeps_stated_id_fantoir_as_a_second_identifier():
    with (FIXTURES / "ban_bulk_csv_sample.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    row_with_fantoir = next(r for r in rows if r.get("id_fantoir"))
    address = address_from_csv_row(row_with_fantoir)
    a = from_ban(address)

    schemes = {link.scheme for link in a.street_links}
    assert "ban_toponyme_id_derived" in schemes
    assert "id_fantoir" in schemes  # genuinely stated, kept alongside the derived one


def test_ban_id_is_none_on_plain_csv_route_and_present_on_bulk_bal():
    with (FIXTURES / "ban_bulk_csv_sample.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    address = address_from_csv_row(rows[0])
    a = from_ban(address)
    assert Identifier(scheme="ban_id", value=address.ban_id) not in a.identifiers
    assert not any(i.scheme == "ban_id" for i in a.identifiers)
