"""Tests for streetworks.common.from_digiroad.

Fixture is real Digiroad data (tests/fixtures/digiroad_streets_real.json),
captured live 2026-08-17 - Creative Commons Attribution 4.0
International, confirmed live from the dataset's own avoindata.fi
catalogue entry. LineStrings are trimmed to at most 4 real vertices
(fixture size only). Covers: a real bilingual street (Temppelikatu/
Tempelgatan), a real Finnish-only street (Hietalahdenlaituri), a real
state-numbered road that's also named (Mannerheimintie, route 1), and
a real genuinely unnamed segment.
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_digiroad_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "digiroad_streets_real.json").read_text(
        encoding="utf-8"
    )
)

_FEATURES = {f["properties"]["link_id"]: f for f in FIXTURE["features"]}


def test_bilingual_names_kept_separate_via_language():
    street = from_digiroad_street(_FEATURES["b32bdcc9-79a3-483e-bf52-7c87579240b6:2"])
    by_lang = {n.language: n.value for n in street.names}
    assert by_lang == {"fi": "Temppelikatu", "sv": "Tempelgatan"}
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry.crs == "EPSG:4326"


def test_finnish_only_street_has_one_name():
    street = from_digiroad_street(_FEATURES["fced41b1-dbda-4f1b-8ea8-92a8bb3cb78c:2"])
    assert len(street.names) == 1
    assert street.names[0].language == "fi"
    assert street.names[0].value == "Hietalahdenlaituri"


def test_state_numbered_road_keeps_both_number_and_name():
    # Mannerheimintie is both a real named street AND route 1 - the
    # name is never dropped just because a route number also exists.
    street = from_digiroad_street(_FEATURES["c21d878d-abdf-42b1-beba-b356063a53f5:2"])
    assert street.name == "Mannerheimintie"


def test_unnamed_segment_has_no_fabricated_name():
    street = from_digiroad_street(_FEATURES["bccecaf5-89cf-4a98-b975-0c41bdacef71:2"])
    assert street.names == ()
    assert street.name is None


def test_real_identifiers_link_id_mml_id_kuntakoodi():
    street = from_digiroad_street(_FEATURES["b32bdcc9-79a3-483e-bf52-7c87579240b6:2"])
    by_scheme = {i.scheme: i.value for i in street.identifiers}
    assert by_scheme["link_id"] == "b32bdcc9-79a3-483e-bf52-7c87579240b6:2"
    assert "mml_id" in by_scheme
    assert "kuntakoodi" in by_scheme


def test_geometry_preserves_real_z_elevation():
    street = from_digiroad_street(_FEATURES["b32bdcc9-79a3-483e-bf52-7c87579240b6:2"])
    assert len(street.geometry.value) == 3  # (x, y, z) - real elevation, never dropped
