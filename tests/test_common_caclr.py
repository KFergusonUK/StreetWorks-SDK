"""Tests for streetworks.common.from_caclr.

Fixture rows are read directly from the same real, trimmed tables
bundled in tests/fixtures/caclr_real_sample.zip, joined the same way
streetworks.caclr.CaclrStreetsClient.iter_streets does - see
tests/test_caclr.py and streetworks.caclr.client's own module docstring
for the live evidence behind each.
"""

import zipfile
from pathlib import Path

from streetworks.caclr.client import _COMMUNE_FIELDS, _LOCALITE_FIELDS, _RUE_FIELDS, _read_table
from streetworks.common import GeometryGrade, from_caclr_street

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "caclr_real_sample.zip"

with zipfile.ZipFile(FIXTURE_PATH) as archive:
    _localites = {
        row["NUMERO"]: row for row in _read_table(archive, "LOCALITE", _LOCALITE_FIELDS)
    }
    _communes = {
        (row["FK_CANTO_CODE"], row["CODE"]): row
        for row in _read_table(archive, "COMMUALL", _COMMUNE_FIELDS)
    }
    _ROWS = {}
    for row in _read_table(archive, "RUE", _RUE_FIELDS):
        locality = _localites.get(row["FK_LOCAL_NUMERO"])
        commune_nom = ""
        if locality is not None:
            commune = _communes.get((locality["FK_CANTO_CODE"], locality["FK_COMMU_CODE"]))
            if commune is not None:
                commune_nom = commune["NOM"]
        row["COMMUNE_NOM"] = commune_nom
        _ROWS[row["NUMERO"]] = row


def test_real_name_and_identifier():
    street = from_caclr_street(_ROWS["00001"])
    assert street.name == "Ale Wee"
    identifier = street.identifiers[0]
    assert identifier.scheme == "numero"
    assert identifier.value == "00001"
    assert identifier.scope == "Luxembourg"


def test_geometry_is_always_absent_never_fabricated():
    street = from_caclr_street(_ROWS["00001"])
    assert street.geometry is None
    assert street.geometry_grade is GeometryGrade.ABSENT


def test_administrative_area_is_the_correctly_resolved_commune():
    street = from_caclr_street(_ROWS["00001"])
    # Confirms the composite-key join, not the naive single-key one that
    # would land on "Burmerange" - see streetworks.caclr.client's docstring.
    assert street.administrative_area == "Luxembourg"
    assert street.territory == "Luxembourg"


def test_end_dated_and_provisional_streets_never_dropped():
    end_dated = from_caclr_street(_ROWS["06780"])
    provisional = from_caclr_street(_ROWS["00056"])
    assert end_dated.name == "Rue du Fort Berlaimont"
    assert end_dated.raw["DATE_FIN_VALID"] == "12.12.2014"
    assert provisional.name == "Château de Beggen"
    assert provisional.raw["INDIC_PROVISOIRE"] == "O"
