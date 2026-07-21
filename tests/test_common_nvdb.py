"""Tests for streetworks.common.from_nvdb.

Fixtures are real NVDB API responses (tests/fixtures/nvdb_*) built earlier
this session.
"""

import json
from pathlib import Path

from streetworks.common import Identifier, from_nvdb
from streetworks.nvdb.models import vegadresse_from_response, veglenkesekvens_from_response

FIXTURES = Path(__file__).parent / "fixtures"


def _json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_veglenkesekvens_becomes_a_segment_with_z_geometry():
    sekvens = veglenkesekvens_from_response(_json("nvdb_veglenkesekvenser.json")["objekter"][0])
    segment = from_nvdb(sekvens)

    assert segment.identifiers == (Identifier(scheme="veglenkesekvensid", value="1"),)
    assert segment.geometry.crs == "EPSG:5973"
    # Z survives - a real altitude, never defaulted to 0.
    assert len(segment.geometry.value) == 3
    assert segment.geometry.value[2] != 0
    assert segment.street_type.label == "Enkel bilveg"
    assert segment.street_type.code == "enkelBilveg"


def test_vegadresse_becomes_a_street_spanning_two_veglenkesekvenser():
    # "Dalveien" (adressekode 1140) is real, live-confirmed to span two
    # topologically-unrelated veglenkesekvenser - the exact structural
    # disagreement with BD TOPO's nesting this design brief needed.
    adresse = vegadresse_from_response(_json("nvdb_adresse_dalveien.json"))
    street = from_nvdb(adresse)

    assert street.identifiers == (Identifier(scheme="adressekode", value="1140", scope="4202"),)
    assert street.name == "Dalveien"
    assert street.territory == "Norway"
    assert set(street.segment_refs) == {
        Identifier(scheme="veglenkesekvensid", value="384"),
        Identifier(scheme="veglenkesekvensid", value="2399262"),
    }
    assert len(street.segment_refs) == 2  # many-to-many, not collapsed to one
