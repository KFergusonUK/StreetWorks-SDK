"""Tests for the Madrid INFORMO adapter.

Credential-free, live-verified - see the module docstring in
``streetworks.madrid.client``. ``madrid_incidencias_live_pull.xml`` holds
7 REAL records from a real, unauthenticated pull (2026-08-08): four real
``es_obras='S'`` roadworks records (two ``RWL`` "long-duration", one
``RWK``, one ``RMK`` "maintenance" - covering both real
``incid_prevista``/``incid_planificada`` combinations seen live, and one
with a genuine multi-year start/end window), and three real
``es_obras='N'`` records that must be excluded: a ``LCS`` lane closure,
a ``TLO`` (traffic lights off, ``incid_estado='4'`` "en espera"), and the
real surprise finding - an ``RWR`` "operación asfalto" record, also
``es_obras='N'`` despite reading like roadworks. All IDs, coordinates,
dates and descriptions are real, not fabricated.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from streetworks.common import from_madrid
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.madrid import INCIDENCIAS_URL, MadridClient, parse_incidencias

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "madrid_incidencias_live_pull.xml"
FIXTURE_XML = FIXTURE_PATH.read_bytes()
RECORDS = parse_incidencias(FIXTURE_XML)


def _by_id(records: list[dict], incidencia_id: str) -> dict:
    return next(r for r in records if r["id_incidencia"] == incidencia_id)


def _mock_feed() -> None:
    respx.get(INCIDENCIAS_URL).mock(
        return_value=httpx.Response(200, content=FIXTURE_XML)
    )


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_incidencias_needs_no_credentials_and_is_unfiltered():
    _mock_feed()
    with MadridClient() as madrid:
        records = list(madrid.iter_incidencias())
    assert len(records) == len(RECORDS)  # includes the excluded es_obras='N' records


@respx.mock
def test_iter_roadworks_filters_to_es_obras_s():
    _mock_feed()
    with MadridClient() as madrid:
        records = list(madrid.iter_roadworks())
    assert len(records) == 4
    assert all(r["es_obras"] == "S" for r in records)
    ids = {r["id_incidencia"] for r in records}
    assert ids == {"39788", "39349", "39350", "44730"}


@respx.mock
def test_iter_roadworks_excludes_lane_closures_and_asphalt_ops():
    """The two real, evidenced findings the source's own es_obras flag
    settles - see module docstring: lane closures (LCS) and asphalt
    resurfacing (RWR) are both real but neither counts as "obras"."""
    _mock_feed()
    with MadridClient() as madrid:
        records = list(madrid.iter_roadworks())
    ids = {r["id_incidencia"] for r in records}
    assert "44793" not in ids  # LCS - carriles cortados
    assert "45463" not in ids  # TLO - semáforos apagados
    assert "45505" not in ids  # RWR - operación asfalto


def test_client_requires_no_credentials():
    MadridClient()


# --------------------------------------------------------------------------- #
# Converter - no grouping, 1:1
# --------------------------------------------------------------------------- #


def test_from_madrid_produces_one_works_per_record_no_grouping():
    works_list = from_madrid(RECORDS)
    assert len(works_list) == len(RECORDS)
    assert all(len(w.sites) == 1 for w in works_list)
    assert all(w.territory == "Spain" for w in works_list)
    assert all(w.administrative_area == "Ayuntamiento de Madrid" for w in works_list)
    assert all(w.source_grade == SourceGrade.OPERATOR for w in works_list)


def test_from_madrid_reference_is_id_incidencia_not_codigo():
    """codigo is a real, but not-always-unique, placeholder ('2025/0' on
    6/217 live records) - id_incidencia is the reliable reference."""
    works_list = from_madrid([_by_id(RECORDS, "39788")])
    assert works_list[0].reference == "39788"


def test_from_madrid_coordinate_uses_geographic_pair_labelled_etrs89():
    works_list = from_madrid([_by_id(RECORDS, "44730")])
    coord = works_list[0].sites[0].coordinate
    assert coord.crs == "EPSG:4258"
    assert coord.value == (40.4730681466582, -3.67690569016166)


def test_from_madrid_street_ref_is_never_populated():
    works_list = from_madrid(RECORDS)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_madrid_date_confidence_is_always_estimated():
    works_list = from_madrid(RECORDS)
    for w in works_list:
        for site in w.sites:
            assert site.date_confidence is DateConfidence.ESTIMATED
            assert site.actual_start is None
            assert site.actual_end is None


def test_from_madrid_parses_the_real_live_seven_fraction_digit_format():
    """Not the portal's documented +dd:00-offset format - the real wire
    format has no offset and seven fractional-second digits, one more
    than %f accepts. See module docstring."""
    works_list = from_madrid([_by_id(RECORDS, "39349")])
    site = works_list[0].sites[0]
    assert site.proposed_start is not None
    assert site.proposed_start.year == 2025
    assert site.proposed_start.month == 1
    assert site.proposed_start.day == 20
    assert site.proposed_end is not None
    assert site.proposed_end.year == 2026  # a genuine multi-year real window
    assert site.proposed_end.month == 10


def test_from_madrid_works_type_is_nom_tipo_incidencia():
    works_list = from_madrid([_by_id(RECORDS, "44730")])
    assert works_list[0].sites[0].works_type == "Obras de mantenimiento en la vía"


def test_from_madrid_location_description_is_descripcion():
    works_list = from_madrid([_by_id(RECORDS, "39350")])
    site = works_list[0].sites[0]
    assert site.location_description is not None
    assert "CANAL ISABEL II" in site.location_description


def test_from_madrid_excluded_records_still_convert_when_passed_directly():
    """from_madrid() itself never filters by es_obras - only
    MadridClient.iter_roadworks() does. A caller who fetches an excluded
    record explicitly still gets a real Works back, not a silent drop."""
    works_list = from_madrid([_by_id(RECORDS, "45505")])
    assert len(works_list) == 1
    assert works_list[0].sites[0].works_type == "Operación asfalto"
