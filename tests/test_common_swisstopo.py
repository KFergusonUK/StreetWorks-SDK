"""Tests for streetworks.common.from_swisstopo.

Fixture rows are read directly from the same real, trimmed CSV bundled
in tests/fixtures/swisstopo_strassenverzeichnis_real_sample.zip - see
tests/test_swisstopo.py and streetworks.swisstopo.client's own module
docstring for the live evidence behind each.
"""

import csv
import io
import zipfile
from pathlib import Path

from streetworks.common import GeometryGrade, from_swisstopo_street

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "swisstopo_strassenverzeichnis_real_sample.zip"

with zipfile.ZipFile(FIXTURE_PATH) as archive:
    with archive.open(archive.namelist()[0]) as raw_file:
        text = io.TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
        _ROWS = {row["STR_ESID"]: row for row in csv.DictReader(text, delimiter=";")}


def test_real_name_and_identifier():
    street = from_swisstopo_street(_ROWS["10211433"])
    assert street.name == "Obere Dalvazzastrasse"
    identifier = street.identifiers[0]
    assert identifier.scheme == "str_esid"
    assert identifier.value == "10211433"
    assert identifier.scope == "Switzerland"


def test_geometry_is_a_real_unswapped_projected_point():
    street = from_swisstopo_street(_ROWS["10211433"])
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry.crs == "EPSG:2056"
    # (x, y) = (easting, northing), never swapped - a projected CRS.
    assert street.geometry.value == (2777432.49, 1198628.884)
    assert street.geometry.points is None


def test_street_type_and_administrative_area():
    street = from_swisstopo_street(_ROWS["10211433"])
    assert street.street_type.label == "Street"
    assert street.administrative_area == "Luzein"
    assert street.territory == "Switzerland"


def test_real_area_and_place_types_never_coerced_to_street():
    area = from_swisstopo_street(_ROWS["10143894"])
    place = from_swisstopo_street(_ROWS["10078330"])
    assert area.street_type.label == "Area"
    assert place.street_type.label == "Place"


def test_planned_and_unofficial_rows_are_never_dropped():
    planned = from_swisstopo_street(_ROWS["10262740"])
    unofficial = from_swisstopo_street(_ROWS["10250779"])
    assert planned.name is not None
    assert planned.raw["STR_STATUS"] == "planned"
    assert unofficial.name is not None
    assert unofficial.raw["STR_OFFICIAL"] == "false"
