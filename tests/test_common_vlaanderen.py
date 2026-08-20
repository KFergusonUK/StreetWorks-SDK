"""Tests for streetworks.common.from_vlaanderen.

Fixture is real Straatnamenregister data
(tests/fixtures/vlaanderen_straatnamen_real.json), captured live
2026-08-20 from Basisregisters Vlaanderen's real, keyless REST API.
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_vlaanderen_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "vlaanderen_straatnamen_real.json").read_text(
        encoding="utf-8"
    )
)

_RECORDS = {r["identificator"]["objectId"]: r for r in FIXTURE}


def test_real_name_and_language_and_identifier():
    street = from_vlaanderen_street(_RECORDS["1"])
    assert street.name == "Acacialaan"
    assert street.names[0].language == "nl"
    identifier = street.identifiers[0]
    assert identifier.scheme == "straatnaam_objectid"
    assert identifier.value == "1"
    assert identifier.scope == "Belgium"


def test_geometry_is_always_absent_never_fabricated():
    street = from_vlaanderen_street(_RECORDS["1"])
    assert street.geometry is None
    assert street.geometry_grade is GeometryGrade.ABSENT


def test_administrative_area_never_populated():
    street = from_vlaanderen_street(_RECORDS["1"])
    assert street.administrative_area is None
    assert street.territory == "Belgium"


def test_historicised_status_never_dropped():
    street = from_vlaanderen_street(_RECORDS["141"])
    assert street.name == "Afzeliastraat"
    assert street.raw["straatnaamStatus"] == "gehistoreerd"
