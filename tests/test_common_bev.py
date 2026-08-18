"""Tests for streetworks.common.from_bev.

Fixture rows are read directly from the same real, trimmed CSVs bundled
in tests/fixtures/bev_adressregister_real_sample.zip, joined the same
way streetworks.bev.BevStreetsClient.iter_streets does - see
tests/test_bev.py and streetworks.bev.client's own module docstring for
the live evidence behind each.
"""

import csv
import io
import zipfile
from pathlib import Path

from streetworks.common import GeometryGrade, from_bev_street

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bev_adressregister_real_sample.zip"

with zipfile.ZipFile(FIXTURE_PATH) as archive:
    with archive.open("GEMEINDE.csv") as raw_file:
        text = io.TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
        _GEMEINDE_BY_GKZ = {
            row["GKZ"]: row["GEMEINDENAME"] for row in csv.DictReader(text, delimiter=";")
        }
    with archive.open("STRASSE.csv") as raw_file:
        text = io.TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
        _ROWS = {}
        for row in csv.DictReader(text, delimiter=";"):
            row["GEMEINDENAME"] = _GEMEINDE_BY_GKZ.get(row["GKZ"], "")
            _ROWS[row["SKZ"]] = row


def test_real_name_and_identifier():
    street = from_bev_street(_ROWS["000001"])
    assert street.name == "Josef Stanislaus Albach-Gasse"
    identifier = street.identifiers[0]
    assert identifier.scheme == "skz"
    assert identifier.value == "000001"
    assert identifier.scope == "Austria"


def test_geometry_is_always_absent_never_fabricated():
    street = from_bev_street(_ROWS["000001"])
    assert street.geometry is None
    assert street.geometry_grade is GeometryGrade.ABSENT


def test_administrative_area_is_the_resolved_municipality_name():
    street = from_bev_street(_ROWS["126290"])
    assert street.administrative_area == "Donnerskirchen"
    assert street.territory == "Austria"


def test_strassennamenzusatz_preserved_raw_only():
    street = from_bev_street(_ROWS["126290"])
    assert street.name == "Reiterweg"
    assert street.raw["STRASSENNAMENZUSATZ"] == "Donnerskirchen"
