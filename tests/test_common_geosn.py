"""Tests for streetworks.common.from_geosn.

Fixture rows are read directly from the same real, trimmed export
bundled in tests/fixtures/geosn_hauskoordinaten_real_sample.zip - see
tests/test_geosn.py and streetworks.geosn.client's own module docstring
for the live evidence behind each.
"""

import csv
import io
import zipfile
from pathlib import Path

from streetworks.common import GeometryGrade, from_geosn_street

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "geosn_hauskoordinaten_real_sample.zip"

with zipfile.ZipFile(FIXTURE_PATH) as archive:
    with archive.open(archive.namelist()[0]) as raw_file:
        text = io.TextIOWrapper(raw_file, encoding="utf-8", newline="")
        _ROWS = {row["str"]: row for row in csv.DictReader(text, delimiter=";")}


def test_real_name_and_identifier():
    street = from_geosn_street(_ROWS["Dolsenhainer Straße"])
    assert street.name == "Dolsenhainer Straße"
    identifier = street.identifiers[0]
    assert identifier.scheme == "strschl"
    assert identifier.value == "59992"
    assert identifier.scope == "Germany"


def test_geometry_is_a_real_reprojected_utm33n_point():
    street = from_geosn_street(_ROWS["Dolsenhainer Straße"])
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    lat, lon = street.geometry.value
    # Real Saxony geography (Frohburg, near Leipzig) - (lat, lon)
    # convention, cross-checked against the same point in client.py's
    # own module docstring.
    assert 50.9 < lat < 51.1
    assert 12.4 < lon < 12.7


def test_administrative_area_is_the_real_municipality_name():
    street = from_geosn_street(_ROWS["Bergstraße"])
    assert street.administrative_area == "Stadt Zittau"
    assert street.territory == "Germany"
