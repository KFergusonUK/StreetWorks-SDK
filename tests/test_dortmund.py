"""Tests for streetworks.dortmund and streetworks.common.from_dortmund.

Fixtures are real trimmed API responses captured live 2026-08-20 from
`open-data.dortmund.de`'s real ``fb66-baustellen-tagesaktuell``/
``fb66-baustellen-geplant`` datasets (3 real records each, first page,
``limit=3``) - see streetworks.dortmund.client's module docstring for
the full investigation, including why this SDK's first German
municipal roadworks provider exists alongside the state-level cluster.
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import DateConfidence, from_dortmund
from streetworks.dortmund import GEPLANT_URL, TAGESAKTUELL_URL, DortmundClient

FIXTURES = Path(__file__).parent / "fixtures"
TAGESAKTUELL_PAYLOAD = json.loads((FIXTURES / "dortmund_tagesaktuell.json").read_text())
GEPLANT_PAYLOAD = json.loads((FIXTURES / "dortmund_geplant.json").read_text())
_TAGESAKTUELL_RECORDS = [item["record"] for item in TAGESAKTUELL_PAYLOAD["records"]]
_GEPLANT_RECORDS = [item["record"] for item in GEPLANT_PAYLOAD["records"]]


@respx.mock
def test_iter_tagesaktuell_unwraps_the_real_nested_record_shape():
    respx.get(TAGESAKTUELL_URL).mock(
        return_value=httpx.Response(200, json=TAGESAKTUELL_PAYLOAD)
    )
    with DortmundClient() as dortmund:
        records = list(dortmund.iter_tagesaktuell())
    assert len(records) == 3
    # Real payload lives under item["record"], not the item itself.
    assert records[0]["id"] == "e67a4fdab485cfafad87af19e1ad20645de48926"
    assert "fields" in records[0]


@respx.mock
def test_iter_roadworks_combines_both_real_datasets():
    respx.get(TAGESAKTUELL_URL).mock(
        return_value=httpx.Response(200, json=TAGESAKTUELL_PAYLOAD)
    )
    respx.get(GEPLANT_URL).mock(return_value=httpx.Response(200, json=GEPLANT_PAYLOAD))
    with DortmundClient() as dortmund:
        records = list(dortmund.iter_roadworks())
    assert len(records) == 6


def test_real_reference_promoter_and_location():
    works = from_dortmund([_TAGESAKTUELL_RECORDS[0]])
    w = works[0]
    assert w.reference == "e67a4fdab485cfafad87af19e1ad20645de48926"
    assert w.promoter == "EB70 - Stadtentwässerung"
    assert w.territory == "Germany"
    assert w.administrative_area == "Dortmund"  # endpoint provenance, not stadtbezirk
    assert w.sites[0].location_description == "Hörde"  # the real stadtbezirk value
    assert "Virchowstraße" in w.sites[0].works_type


def test_genuine_wgs84_coordinate_no_reprojection():
    works = from_dortmund([_TAGESAKTUELL_RECORDS[0]])
    coordinate = works[0].coordinate
    assert coordinate.crs == "EPSG:4326"
    lat, lon = coordinate.value
    assert 51.0 < lat < 51.7  # real Dortmund bounds
    assert 7.2 < lon < 7.7


def test_date_only_dates_localised_to_europe_berlin():
    works = from_dortmund([_TAGESAKTUELL_RECORDS[0]])
    site = works[0].sites[0]
    assert str(site.proposed_start) == "2026-05-04 00:00:00+02:00"
    assert str(site.proposed_end) == "2026-10-02 00:00:00+02:00"
    assert site.date_confidence is DateConfidence.VERIFIED


def test_status_carries_real_literal_tagesaktuell_or_geplant():
    tages_works = from_dortmund([_TAGESAKTUELL_RECORDS[0]])
    geplant_works = from_dortmund([_GEPLANT_RECORDS[0]])
    assert tages_works[0].sites[0].status == "tagesaktuell"
    assert geplant_works[0].sites[0].status == "geplant"
    # actual_start only populated for genuinely current (not planned) works.
    assert tages_works[0].sites[0].actual_start is not None
    assert geplant_works[0].sites[0].actual_start is None
