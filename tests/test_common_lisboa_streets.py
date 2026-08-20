"""Tests for streetworks.common.from_lisboa_streets.

Fixture is real Toponímia de Lisboa data
(tests/fixtures/lisboa_streets_real.json), captured live 2026-08-20 from
CML's own Cultura_Toponimia ArcGIS Feature Service - see
streetworks.arcgis.lisboa's own module docstring for the full
investigation. Three real records: "Avenida da Liberdade" (a genuine
MultiLineString, trimmed to 3 real parts), "Rua do Possolo" (a real
former name in DENOMINACOES_ANTERIORES: "Rua da Boa-Morte"), "Rua Pinto
Ferreira" (a real LEGENDA honoree bio). HISTORIAL text is trimmed to a
real verbatim prefix on all three (fixture size only - some real
HISTORIAL values run to several paragraphs).
"""

import json
from pathlib import Path

from streetworks.common import GeometryGrade, from_lisboa_street

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "lisboa_streets_real.json").read_text(encoding="utf-8")
)

_FEATURES = {f["properties"]["DESIGNACAO"]: f for f in FIXTURE["features"]}


def test_real_name_and_cod_local_identifier():
    street = from_lisboa_street(_FEATURES["Avenida da Liberdade"])
    assert street.name == "Avenida da Liberdade"
    identifier = street.identifiers[0]
    assert identifier.scheme == "cod_local"
    assert identifier.value == "34187"
    assert identifier.scope == "Lisboa"


def test_geometry_is_a_real_multilinestring_via_parts_not_flipped_axis_order():
    street = from_lisboa_street(_FEATURES["Avenida da Liberdade"])
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry.parts is not None
    assert len(street.geometry.parts) == 3
    # GeoJSON's own (lon, lat) order, preserved - not flipped - real
    # Lisbon geography (lon around -9.x, lat around 38.7).
    lon, lat = street.geometry.value
    assert -9.2 < lon < -9.1
    assert 38.6 < lat < 38.8
    assert street.geometry.points is None  # points describes the first part only for LineString


def test_geometry_is_a_real_linestring_via_points():
    street = from_lisboa_street(_FEATURES["Rua do Possolo"])
    assert street.geometry_grade is GeometryGrade.PUBLISHED
    assert street.geometry.parts is None
    assert street.geometry.points is not None
    assert len(street.geometry.points) == 4


def test_administrative_area_carries_the_real_verbatim_multi_parish_string():
    street = from_lisboa_street(_FEATURES["Rua do Possolo"])
    assert street.administrative_area == (
        "Campo de Ourique (Nova Freguesia), Estrela (Nova Freguesia)"
    )
    assert street.territory == "Portugal"


def test_former_name_and_legenda_stay_on_raw_only():
    possolo = from_lisboa_street(_FEATURES["Rua do Possolo"])
    assert possolo.raw["properties"]["DENOMINACOES_ANTERIORES"] == "Rua da Boa-Morte"

    pinto = from_lisboa_street(_FEATURES["Rua Pinto Ferreira"])
    assert "Engenheiro e Professor" in pinto.raw["properties"]["LEGENDA"]
