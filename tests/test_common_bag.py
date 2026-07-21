"""Tests for streetworks.common.from_bag.

Fixtures are real BAG Locatieserver responses (tests/fixtures/bag_*) built
earlier this session.
"""

import json
from pathlib import Path

import pytest

from streetworks.bag.models import location_from_doc
from streetworks.common import Identifier, from_bag

FIXTURES = Path(__file__).parent / "fixtures"


def _doc(fixture: str) -> dict:
    payload = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    return payload["response"]["docs"][0]


def test_real_adres_doc_becomes_an_address_with_no_suffix():
    address = location_from_doc(_doc("bag_lookup_response.json"))
    a = from_bag(address)

    assert a.housenumber == "1"
    assert a.suffix is None  # not modelled - see the module docstring
    assert a.street_name == "Dam"
    assert a.territory == "Netherlands"
    assert a.administrative_area == "Amsterdam"
    assert Identifier(scheme="openbare_ruimte_id", value="0363300000003186") in a.street_links


def test_weg_type_raises_rather_than_being_misrepresented_as_an_address():
    weg = location_from_doc(_doc("bag_free_response.json"))
    assert weg.type == "weg"
    with pytest.raises(ValueError, match="not an address"):
        from_bag(weg)
