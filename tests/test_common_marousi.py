"""Tests for streetworks.common.from_marousi.

Fixture is real Marousi street-name data
(tests/fixtures/marousi_streets_real.json), captured live 2026-08-17 -
licence genuinely unstated on the source catalogue (data.gov.gr shows
"License not specified" for this and every one of the 580 real
municipal datasets checked), built on the project owner's explicit
instruction, the same basis Jersey's own fixtures ship on. Polygon
rings are trimmed to 5 real vertices + the closing one (fixture size
only - the converter never reads ring geometry, so this doesn't affect
what's under test).
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_marousi_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "marousi_streets_real.json").read_text(
        encoding="utf-8"
    )
)

_FEATURES = {f["properties"]["id"]: f for f in FIXTURE["features"]}


def test_real_name_and_identifier():
    street = from_marousi_street(_FEATURES[5])  # ΑΓ. ΓΕΡΑΣΙΜΟΥ
    assert street.name == "ΑΓ. ΓΕΡΑΣΙΜΟΥ"
    identifier = street.identifiers[0]
    assert identifier.scheme == "id"
    assert identifier.value == "5"
    assert identifier.scope == "Marousi"


def test_geometry_is_always_absent_never_a_fabricated_centroid():
    street = from_marousi_street(_FEATURES[5])
    assert street.geometry is None
    assert street.geometry_grade is GeometryGrade.ABSENT
    # The real polygon is still preserved, unmodified, in raw.
    assert street.raw["geometry"]["type"] == "MultiPolygon"


def test_territory_and_fixed_administrative_area():
    street = from_marousi_street(_FEATURES[2])  # 25ΗΣ ΜΑΡΤΙΟΥ
    assert street.territory == "Greece"
    assert street.administrative_area == "Marousi"
