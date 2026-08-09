"""Tests for the Lisboa (CML) Condicionamentos de Trânsito adapter.

Credential-free, live-verified - see the module docstring in
``streetworks.lisboa.client``. ``lisboa_condicionamentos_live_pull.json``
holds 7 REAL features from a real, unauthenticated pull (2026-08-09):
a real ``CARGAS E DESCARGAS`` (excluded - bare, no "OBRAS" suffix), a
real ``OBRA - FAIXA DE RODAGEM`` (roadworks), a real ``MANIFESTAÇÃO``
(excluded - a demonstration), a real ``CARGAS E DESCARGAS/OBRAS`` with
two real periods, a real ``CARGAS E DESCARGAS/OBRAS`` with a real
two-sub-line ``MultiLineString``, a real ``ACESSO DE VEÍCULOS À OBRA``
with real panfleto (PDF attachment) URLs, and a real
``OBRA - FAIXA DE RODAGEM`` from a "TODAS" (city-wide) freguesias
record. All ids, coordinates, dates and descriptions are real, not
fabricated. LineString vertex lists are trimmed for fixture size.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_lisboa
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.lisboa import CLOSURES_URL, LisboaClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "lisboa_condicionamentos_live_pull.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text())
RECORDS = FIXTURE["features"]


def _by_id(records: list[dict], feature_id: int) -> dict:
    return next(r for r in records if r["properties"]["id"] == feature_id)


def _mock_feed() -> None:
    respx.get(CLOSURES_URL).mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": RECORDS})
    )


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_condicionamentos_needs_no_credentials_and_is_unfiltered():
    _mock_feed()
    with LisboaClient() as lisboa:
        records = list(lisboa.iter_condicionamentos())
    assert len(records) == len(RECORDS)  # includes CARGAS E DESCARGAS / MANIFESTAÇÃO


@respx.mock
def test_iter_roadworks_excludes_deliveries_and_demonstrations():
    _mock_feed()
    with LisboaClient() as lisboa:
        records = list(lisboa.iter_roadworks())
    ids = {r["properties"]["id"] for r in records}
    assert 129153 not in ids  # CARGAS E DESCARGAS (bare)
    assert 131921 not in ids  # MANIFESTAÇÃO
    assert len(records) == 5


def test_client_requires_no_credentials():
    LisboaClient()


# --------------------------------------------------------------------------- #
# Converter - no grouping, 1:1
# --------------------------------------------------------------------------- #


def test_from_lisboa_produces_one_works_per_record_no_grouping():
    works_list = from_lisboa(RECORDS)
    assert len(works_list) == len(RECORDS)
    assert all(len(w.sites) == 1 for w in works_list)
    assert all(w.territory == "Portugal" for w in works_list)
    assert all(w.administrative_area == "Câmara Municipal de Lisboa" for w in works_list)
    assert all(w.source_grade == SourceGrade.OPERATOR for w in works_list)


def test_from_lisboa_reference_is_pedido():
    works_list = from_lisboa([_by_id(RECORDS, 131139)])
    assert works_list[0].reference == "COND-2025-6320-P11"


def test_from_lisboa_coordinate_uses_first_multilinestring_sublines():
    """130497 has a real 2-sub-line MultiLineString - only the first
    sub-line's vertices are used."""
    record = _by_id(RECORDS, 130497)
    assert len(record["geometry"]["coordinates"]) == 2
    works_list = from_lisboa([record])
    coord = works_list[0].sites[0].coordinate
    assert coord.crs == "EPSG:4326"
    assert coord.points is not None
    first_sub_line_len = len(record["geometry"]["coordinates"][0])
    assert len(coord.points) == first_sub_line_len
    assert coord.value == coord.points[0]


def test_from_lisboa_street_ref_is_never_populated():
    works_list = from_lisboa(RECORDS)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_lisboa_date_confidence_is_always_estimated():
    works_list = from_lisboa(RECORDS)
    for w in works_list:
        for site in w.sites:
            assert site.date_confidence is DateConfidence.ESTIMATED
            assert site.actual_start is None
            assert site.actual_end is None


def test_from_lisboa_single_period_window():
    works_list = from_lisboa([_by_id(RECORDS, 131139)])
    site = works_list[0].sites[0]
    assert site.proposed_start is not None
    assert site.proposed_start.year == 2026
    assert site.proposed_start.month == 7
    assert site.proposed_end is not None
    assert site.proposed_end.month == 8


def test_from_lisboa_multi_period_window_uses_first_start_last_end():
    """132192 has 2 real periods - first period's start, last period's
    end become the WorksSite window."""
    record = _by_id(RECORDS, 132192)
    periods = record["properties"]["periodos_condicionamentos"]
    assert len(periods) == 2
    works_list = from_lisboa([record])
    site = works_list[0].sites[0]
    assert site.proposed_start is not None
    assert site.proposed_end is not None
    assert site.proposed_start < site.proposed_end


def test_from_lisboa_works_type_is_motivo():
    works_list = from_lisboa([_by_id(RECORDS, 131914)])
    assert works_list[0].sites[0].works_type == "ACESSO DE VEÍCULOS À OBRA"


def test_from_lisboa_location_description_combines_morada_and_freguesias():
    works_list = from_lisboa([_by_id(RECORDS, 131139)])
    site = works_list[0].sites[0]
    assert site.location_description is not None
    assert "Misericórdia" in site.location_description


def test_from_lisboa_excluded_records_still_convert_when_passed_directly():
    """from_lisboa() itself never filters by motivo - only
    LisboaClient.iter_roadworks() does."""
    works_list = from_lisboa([_by_id(RECORDS, 131921)])
    assert len(works_list) == 1
    assert works_list[0].sites[0].works_type == "MANIFESTAÇÃO"


def test_from_lisboa_traffic_management_carries_restricao_circulacao():
    works_list = from_lisboa([_by_id(RECORDS, 131139)])
    assert works_list[0].sites[0].traffic_management == "Corte total"
