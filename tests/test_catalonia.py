"""Tests for the Servei Català de Trànsit (SCT, Catalonia) adapter.

The fixture (``sct_incidenciesGML.xml``) is real, trimmed from a live pull,
2026-07 - licensed under Catalonia's own "Llicència oberta d'ús
d'informació" (confirmed genuinely open, see ``docs/catalonia-sct-
investigation.md``), so real data is used directly, unlike the several
unconfirmed-licence sources elsewhere in this SDK. Four real records:
one ``Cons`` (excluded), one ``Retenció`` whose free-text ``causa`` says
"Obres" - the genuine edge case confirmed live and deliberately *not*
reclassified (see ``streetworks/sct/models.py``'s own docstring), and two
real ``Obres`` records, one of which (``causa="Insatal·lació i/o
desmuntatge de pòrtics"``) carries real Catalan diacritics including the
geminated "l·l".
"""

from pathlib import Path

import httpx
import respx

from streetworks.common import from_sct
from streetworks.sct import (
    BASE_URL,
    INCIDENTS_PATH,
    ROADWORKS_DESCRIPCIO_TIPUS,
    SCTClient,
    parse_incidents,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sct_incidenciesGML.xml"
FIXTURE_BYTES = FIXTURE_PATH.read_bytes()


def test_parses_all_real_incidents():
    incidents = parse_incidents(FIXTURE_BYTES)
    assert [i.identificador for i in incidents] == [
        "149994003",
        "149992801",
        "149674405",
        "147748402",
    ]


def test_roadworks_descripcio_tipus_is_obres_only():
    assert ROADWORKS_DESCRIPCIO_TIPUS == {"Obres"}


def test_is_roadworks_excludes_cons_and_retencio():
    incidents = {i.identificador: i for i in parse_incidents(FIXTURE_BYTES)}
    assert incidents["149994003"].is_roadworks is False  # Cons
    assert incidents["149674405"].is_roadworks is True  # Obres
    assert incidents["147748402"].is_roadworks is True  # Obres


def test_retencio_with_causa_obres_is_not_reclassified():
    """The genuine edge case: a real Retenció record whose free-text causa
    happens to say "Obres" - the dedicated descripcio_tipus field is
    trusted over the secondary free-text hint, see models.py's docstring."""
    incidents = {i.identificador: i for i in parse_incidents(FIXTURE_BYTES)}
    edge_case = incidents["149992801"]
    assert edge_case.descripcio_tipus == "Retenció"
    assert edge_case.causa == "Obres"
    assert edge_case.is_roadworks is False


def test_point_geometry_flipped_to_lat_lon():
    incidents = {i.identificador: i for i in parse_incidents(FIXTURE_BYTES)}
    incident = incidents["149674405"]
    # Real WKT states "1.72629587,41.29309171" (lon,lat) - flipped to this
    # SDK's (lat,lon) WGS84 convention.
    assert incident.point == (41.29309171, 1.72629587)


def test_catalan_diacritics_round_trip():
    incidents = {i.identificador: i for i in parse_incidents(FIXTURE_BYTES)}
    incident = incidents["147748402"]
    assert incident.causa == "Insatal·lació i/o desmuntatge de pòrtics"
    assert incident.carretera == "BV-1414"


def test_from_sct_no_dates_populated():
    """No start/end validity window exists in this feed - see models.py's
    own docstring for why proposed_start/actual_start are never inferred
    from the report timestamp."""
    incidents = [i for i in parse_incidents(FIXTURE_BYTES) if i.is_roadworks]
    works_list = from_sct(incidents)
    for works in works_list:
        site = works.sites[0]
        assert site.proposed_start is None
        assert site.proposed_end is None
        assert site.actual_start is None
        assert site.actual_end is None
        assert site.date_confidence.value == "unknown"


def test_from_sct_territory_and_authority():
    incidents = [i for i in parse_incidents(FIXTURE_BYTES) if i.is_roadworks]
    works_list = from_sct(incidents)
    for works in works_list:
        assert works.territory == "Spain"
        assert works.administrative_area == "Servei Català de Trànsit"


def test_from_sct_coordinate_crs_is_wgs84():
    incidents = [i for i in parse_incidents(FIXTURE_BYTES) if i.is_roadworks]
    works_list = from_sct(incidents)
    for works in works_list:
        assert works.sites[0].coordinate.crs == "EPSG:4326"


def test_from_sct_works_type_prefers_causa():
    incidents = {i.identificador: i for i in parse_incidents(FIXTURE_BYTES) if i.is_roadworks}
    works_list = from_sct(list(incidents.values()))
    by_ref = {w.reference: w for w in works_list}
    assert by_ref["149674405"].sites[0].works_type == "Senyalització vertical"


@respx.mock
def test_client_fetches_and_parses():
    respx.get(f"{BASE_URL}/{INCIDENTS_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with SCTClient() as sct:
        incidents = list(sct.iter_incidents())
    assert len(incidents) == 4


@respx.mock
def test_client_iter_roadworks_filters():
    respx.get(f"{BASE_URL}/{INCIDENTS_PATH}").mock(
        return_value=httpx.Response(200, content=FIXTURE_BYTES)
    )
    with SCTClient() as sct:
        roadworks = list(sct.iter_roadworks())
    assert len(roadworks) == 2
    assert all(i.descripcio_tipus == "Obres" for i in roadworks)
