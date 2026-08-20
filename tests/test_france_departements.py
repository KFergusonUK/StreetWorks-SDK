"""Tests for streetworks.opendatasoft (generic client + the French
département/métropole field-map registry) and
streetworks.common.from_departement_roadworks.

Fixtures are real trimmed OpenDataSoft Explore API v2.1 responses,
2026-08-20 (``limit=3`` each, ``geo_shape`` line coordinates trimmed to
5 points): Sarthe (real ``RD 0316``/``RD 0279`` closures, structured
ISO dates), Loire-Atlantique (real "Déviation"/"Travaux sur ouvrage
d'art" records, no structured dates - see module docstring for why),
Hauts-de-Seine (real tramway/cycle-lane infrastructure-project records,
also no structured dates), Toulouse Métropole (real ``T26...`` case
numbers) and Rennes Métropole (real ``id_evt`` values, the 30-day
window dataset).
"""

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import DateConfidence, from_departement_roadworks
from streetworks.opendatasoft import OpenDataSoftClient
from streetworks.opendatasoft.france_departements import (
    HAUTS_DE_SEINE,
    LOIRE_ATLANTIQUE,
    RENNES_METROPOLE,
    SARTHE,
    TOULOUSE_METROPOLE,
    DepartementRoadworksClient,
)

FIXTURES = Path(__file__).parent / "fixtures"
SARTHE_PAYLOAD = json.loads((FIXTURES / "france_sarthe_roadworks.json").read_text())
LA_PAYLOAD = json.loads((FIXTURES / "france_loire_atlantique_roadworks.json").read_text())
TOULOUSE_PAYLOAD = json.loads((FIXTURES / "france_toulouse_roadworks.json").read_text())
RENNES_PAYLOAD = json.loads((FIXTURES / "france_rennes_roadworks.json").read_text())
HDS_PAYLOAD = json.loads((FIXTURES / "france_hauts_de_seine_roadworks.json").read_text())


@respx.mock
def test_opendatasoft_client_pages_via_limit_offset():
    route = respx.get(SARTHE.records_url).mock(
        return_value=httpx.Response(200, json=SARTHE_PAYLOAD)
    )
    with OpenDataSoftClient() as ods:
        records = list(ods.iter_records(SARTHE.records_url))
    assert len(records) == 3
    params = dict(httpx.QueryParams(route.calls.last.request.url.query))
    assert params["limit"] == "100"
    assert params["offset"] == "0"


@respx.mock
def test_departement_client_fetch_sarthe():
    respx.get(SARTHE.records_url).mock(return_value=httpx.Response(200, json=SARTHE_PAYLOAD))
    with DepartementRoadworksClient() as france:
        records = france.fetch("Sarthe")
    assert len(records) == 3
    assert records[0]["loc_txt"] == "RD 0316 : Du 0+100 au 1+700"


@respx.mock
def test_departement_client_iter_all():
    respx.get(SARTHE.records_url).mock(return_value=httpx.Response(200, json=SARTHE_PAYLOAD))
    respx.get(LOIRE_ATLANTIQUE.records_url).mock(
        return_value=httpx.Response(200, json=LA_PAYLOAD)
    )
    with DepartementRoadworksClient() as france:
        results = list(france.iter_all(["Sarthe", "Loire-Atlantique"]))
    assert len(results) == 6
    assert {name for name, _ in results} == {"Sarthe", "Loire-Atlantique"}


def test_sarthe_structured_iso_dates_and_road_field():
    works = from_departement_roadworks(SARTHE_PAYLOAD["results"], SARTHE)
    w = next(w for w in works if w.reference == "275")
    site = w.sites[0]
    assert site.location_description == "RD 0316 : Du 0+100 au 1+700"
    assert w.promoter == "Télélec Réseaux"
    assert site.status == "Alternat"
    assert str(site.proposed_start) == "2026-07-01 02:00:00+00:00"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert w.administrative_area == "Sarthe"
    assert w.territory == "France"


def test_sarthe_linestring_geometry_kept_as_points():
    # value (the real geo_point_2d) and points (the real geo_shape
    # LineString vertices) are two independently real, stated facts on
    # this source, not one derived from the other - the same
    # Point+LineString-as-separate-facts shape from_berlin's own
    # GeometryCollection handling already establishes, not the single-
    # geometry from_datavia/from_nrn case where value is defined as the
    # line's own first vertex.
    works = from_departement_roadworks(SARTHE_PAYLOAD["results"], SARTHE)
    w = next(w for w in works if w.reference == "275")
    assert w.coordinate.crs == "EPSG:4326"
    assert len(w.coordinate.points) == 5


def test_loire_atlantique_uses_localisation_point_field_not_geo_point_2d():
    assert LOIRE_ATLANTIQUE.point_field == "localisation"
    works = from_departement_roadworks(LA_PAYLOAD["results"], LOIRE_ATLANTIQUE)
    w = works[0]
    assert w.coordinate is not None
    lat, lon = w.coordinate.value
    assert 46.0 < lat < 48.0  # real Loire-Atlantique bounds
    assert -2.5 < lon < -0.5


def test_loire_atlantique_has_no_structured_dates_or_id():
    # Real free-text date range only ("Du 18/08/2026 au 20/08/2026") -
    # never parsed, and no real per-record id exists at all.
    works = from_departement_roadworks(LA_PAYLOAD["results"], LOIRE_ATLANTIQUE)
    w = works[0]
    assert w.reference == ""
    assert w.sites[0].proposed_start is None
    assert w.sites[0].date_confidence is DateConfidence.UNKNOWN
    assert w.sites[0].works_type == "Déviation"


def test_hauts_de_seine_avancement_status_and_multi_road_field():
    works = from_departement_roadworks(HDS_PAYLOAD["results"], HAUTS_DE_SEINE)
    w = next(w for w in works if w.reference == "1290")
    site = w.sites[0]
    assert site.status == "Travaux en cours"
    assert site.location_description == "RD 13, RD 97, RD 98, RD 106, RD 909, RD986, RD 992"
    assert w.promoter == "CD92 / Direction des Mobilités"
    # No structured date field exists for this département either.
    assert site.date_confidence is DateConfidence.UNKNOWN


def test_hauts_de_seine_multilinestring_first_part_only():
    works = from_departement_roadworks(HDS_PAYLOAD["results"], HAUTS_DE_SEINE)
    w = next(w for w in works if w.reference == "1290")
    assert w.coordinate.points is not None
    # The real first MultiLineString part for this record has 4 vertices
    # (untrimmed - shorter than the fixture's own 5-point trim cap).
    assert len(w.coordinate.points) == 4


def test_toulouse_metropole_real_case_number_and_promoter():
    works = from_departement_roadworks(TOULOUSE_PAYLOAD["results"], TOULOUSE_METROPOLE)
    w = next(w for w in works if w.reference == "T26VLT04616")
    site = w.sites[0]
    assert site.location_description == "RUE DE MAGUELONNES"
    assert w.promoter == "ORANGE"
    assert site.status == "Alternat - Occupation de 1 file - Occupation du trottoir"
    assert str(site.proposed_start) == "2026-08-03 00:00:00+00:00"
    assert site.date_confidence is DateConfidence.VERIFIED
    assert w.administrative_area == "Toulouse Métropole"


def test_rennes_metropole_uses_the_30_day_superset_dataset():
    assert "travaux_30_jours" in RENNES_METROPOLE.records_url


def test_rennes_metropole_real_id_evt_and_disruption_level_status():
    works = from_departement_roadworks(RENNES_PAYLOAD["results"], RENNES_METROPOLE)
    w = next(w for w in works if w.reference == "78332")
    site = w.sites[0]
    assert site.location_description == "171 Rue de Vern"
    assert site.status == "Impact nul"
    assert site.works_type == "Interdiction de stationnement"
    assert str(site.proposed_start) == "2025-12-04 00:00:00+00:00"
    assert w.administrative_area == "Rennes Métropole"
