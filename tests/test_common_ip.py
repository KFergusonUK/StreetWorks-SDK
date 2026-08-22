"""Tests for streetworks.common.from_ip.

Fixture is real IP Condicionamentos data (tests/fixtures/ip_condicionamentos.json),
captured live 2026-08-22 - see streetworks.arcgis.ip's own module docstring.
Covers a real MaintenanceWorks record with a genuine future ``datafim``, one
with a null ``datafim``, one with the real "no defined end" sentinel
(2050-12-31 23:59:59 UTC), a ConstructionWorks record, and the two real
non-roadworks types (PoorRoadInfrastructure, GenericIncident) - excluded
upstream by IPRoadworksClient.iter_roadworks(), not by this converter -
from_ip assumes its caller already filtered.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from streetworks.common import DateConfidence, from_ip

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "ip_condicionamentos.json").read_text(encoding="utf-8")
)
_ROADWORKS_TYPES = ("MaintenanceWorks", "ConstructionWorks")
ROADWORK = [r for r in FIXTURE if r["properties"]["tipo"] in _ROADWORKS_TYPES]


def _by_id(works_list):
    return {w.reference: w for w in works_list}


def test_real_future_end_date_is_preserved():
    # datainicio_str/datafim_str are local Portugal time (the epoch fields
    # datainicio/datafim are authoritative UTC, one hour behind in April/
    # September WEST) - asserting against the real epoch values here.
    works = _by_id(from_ip(ROADWORK))["22959042"]
    site = works.sites[0]
    assert site.proposed_start == datetime(2025, 4, 6, 21, 0, tzinfo=timezone.utc)
    assert site.proposed_end == datetime(2026, 9, 29, 15, 30, tzinfo=timezone.utc)


def test_null_end_date_stays_none():
    works = _by_id(from_ip(ROADWORK))["22959037"]
    assert works.sites[0].proposed_end is None


def test_no_end_sentinel_is_not_surfaced_as_a_real_date():
    """The real 2050-12-31 23:59:59 UTC sentinel means 'no end stated' -
    see module docstring. Must never appear as proposed_end."""
    works = _by_id(from_ip(ROADWORK))["22959036"]
    assert works.sites[0].proposed_end is None
    assert works.sites[0].proposed_start == datetime(2024, 4, 1, 21, 0, tzinfo=timezone.utc)


def test_coordinate_flips_geojson_lon_lat_to_lat_lon():
    works = _by_id(from_ip(ROADWORK))["22959036"]
    coordinate = works.coordinate
    assert coordinate.crs == "EPSG:4326"
    lat, lon = coordinate.value
    assert abs(lat - 41.20782825711039) < 0.0001
    assert abs(lon - (-8.17564018137777)) < 0.0001


def test_location_description_combines_route_pk_direction_and_place():
    works = _by_id(from_ip(ROADWORK))["22959036"]
    assert (
        works.sites[0].location_description
        == "EN211 PK 0 (Crescente) — Marco de Canaveses, Porto"
    )


def test_traffic_management_is_the_real_free_text_summary():
    works = _by_id(from_ip(ROADWORK))["22959037"]
    assert works.sites[0].traffic_management == "Semaforos inop"


def test_works_type_and_status():
    works = _by_id(from_ip(ROADWORK))["22959159"]
    assert works.sites[0].works_type == "ConstructionWorks"
    assert works.sites[0].status == "ativo"


def test_date_confidence_is_uniformly_estimated():
    for works in from_ip(ROADWORK):
        assert works.sites[0].date_confidence is DateConfidence.ESTIMATED


def test_territory_and_administrative_area():
    works_list = from_ip(ROADWORK)
    assert all(w.territory == "Portugal" for w in works_list)
    assert all(w.administrative_area == "Infraestruturas de Portugal (IP)" for w in works_list)


def test_non_roadworks_records_convert_too_since_filtering_is_the_callers_job():
    non_roadwork = [r for r in FIXTURE if r["properties"]["tipo"] not in _ROADWORKS_TYPES]
    works_list = from_ip(non_roadwork)
    assert len(works_list) == 2
    assert {w.sites[0].works_type for w in works_list} == {
        "PoorRoadInfrastructure",
        "GenericIncident",
    }
