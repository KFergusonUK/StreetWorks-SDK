"""Tests for the Paris "Chantiers à Paris" adapter.

Credential-free, live-verified from day one - see the module docstring
in ``streetworks.paris.client``. ``paris_chantiers_live_pull.json`` holds
5 REAL rows from a real, unauthenticated pull (2026-08-06): a real
``chantier_cite_id`` group of 3 (``329467``, a green-space maintenance
job spanning 3 genuinely different real polygons in the 16th
arrondissement), one real ``"Opérateurs de réseau"`` (CPCU district
heating) row, and one real ``"Tiers (travaux sur bâtiment)"`` row (the
category deliberately excluded from the default roadworks filter) -
not synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.common import from_paris
from streetworks.common.models import DateConfidence, SourceGrade
from streetworks.paris import CHANTIERS_URL, ParisClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "paris_chantiers_live_pull.json"
RECORDS = json.loads(FIXTURE_PATH.read_text())
_ADMINISTRATIVE_AREA = "Ville de Paris - Direction de la Voirie et des Déplacements"


def _by_emprise(num_emprise: str):
    return next(r for r in RECORDS if r["num_emprise"] == num_emprise)


def _envelope(records: list[dict]) -> dict:
    return {"total_count": len(records), "results": records}


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_permits_needs_no_credentials_and_defaults_unfiltered():
    route = respx.get(CHANTIERS_URL).mock(return_value=httpx.Response(200, json=_envelope(RECORDS)))
    with ParisClient() as paris:
        records = list(paris.iter_permits())
    assert len(records) == 5
    assert "where" not in route.calls[0].request.url.params


@respx.mock
def test_iter_roadworks_excludes_the_confirmed_private_category():
    route = respx.get(CHANTIERS_URL).mock(return_value=httpx.Response(200, json=_envelope([])))
    with ParisClient() as paris:
        list(paris.iter_roadworks())
    where = route.calls[0].request.url.params.get("where")
    assert "Tiers (travaux sur bâtiment)" in where
    assert "!=" in where


@respx.mock
def test_iter_permits_stops_on_a_short_final_page():
    """A page shorter than page_size is the standard "no more rows"
    signal - a single request, not a follow-up empty-page check."""
    route = respx.get(CHANTIERS_URL).mock(
        return_value=httpx.Response(200, json=_envelope(RECORDS))
    )
    with ParisClient() as paris:
        records = list(paris.iter_permits(page_size=100))
    assert len(records) == 5
    assert route.call_count == 1
    assert route.calls[0].request.url.params.get("limit") == "100"
    assert route.calls[0].request.url.params.get("offset") == "0"


@respx.mock
def test_iter_permits_pages_via_limit_offset():
    page_one = {"total_count": 5, "results": [{"id": i} for i in range(3)]}
    page_two = {"total_count": 5, "results": [{"id": i} for i in range(3, 5)]}
    route = respx.get(CHANTIERS_URL).mock(
        side_effect=[httpx.Response(200, json=page_one), httpx.Response(200, json=page_two)]
    )
    with ParisClient() as paris:
        records = list(paris.iter_permits(page_size=3))
    assert len(records) == 5
    assert route.calls[0].request.url.params.get("offset") == "0"
    assert route.calls[1].request.url.params.get("offset") == "3"


def test_client_requires_no_credentials():
    ParisClient()


# --------------------------------------------------------------------------- #
# Converter - the real chantier_cite_id grouping
# --------------------------------------------------------------------------- #


def test_from_paris_groups_a_real_multi_emprise_chantier():
    """A real chantier (329467) with 3 real emprise rows across 3 real,
    genuinely different polygons - a green-space maintenance job."""
    works_list = from_paris(RECORDS)
    chantier = next(w for w in works_list if w.reference == "329467")
    assert len(chantier.sites) == 3
    assert {s.reference for s in chantier.sites} == {"EC506528", "EC506524", "EC506527"}
    assert chantier.promoter == "Direction des Espaces Verts et de l'Environnement"
    assert chantier.territory == "France"
    assert chantier.administrative_area == _ADMINISTRATIVE_AREA
    assert chantier.source_grade == SourceGrade.REGISTER


def test_from_paris_site_geometry_is_the_representative_point():
    works_list = from_paris(RECORDS)
    chantier = next(w for w in works_list if w.reference == "329467")
    site = next(s for s in chantier.sites if s.reference == "EC506528")
    assert site.coordinate.crs == "EPSG:4326"
    assert site.coordinate.value == (48.8446293654848, 2.2707740692298866)


def test_from_paris_street_ref_is_never_populated():
    """No segment/street identifier is stated anywhere in the real
    schema - see the module docstring for the full finding."""
    works_list = from_paris(RECORDS)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_paris_date_confidence_is_always_estimated():
    """No status field exists on this dataset at all - only
    date_debut/date_fin. See module docstring."""
    works_list = from_paris(RECORDS)
    for w in works_list:
        for site in w.sites:
            assert site.date_confidence is DateConfidence.ESTIMATED
            assert site.actual_start is None
            assert site.actual_end is None


def test_from_paris_dates_are_parsed():
    works_list = from_paris(RECORDS)
    chantier = next(w for w in works_list if w.reference == "329467")
    site = chantier.sites[0]
    assert site.proposed_start is not None
    assert site.proposed_end is not None


def test_from_paris_tiers_category_still_converts_when_passed_directly():
    """from_paris() itself never filters by category - only
    ParisClient.iter_roadworks()'s where clause does. A caller who
    fetches a Tiers row explicitly still gets a real Works back, not a
    silent drop."""
    tiers_record = _by_emprise("EC500567")
    works_list = from_paris([tiers_record])
    assert len(works_list) == 1
    assert works_list[0].sites[0].works_type == "Construction ou réhabilitation d'immeuble"


def test_from_paris_thin_group_falls_back_when_chantier_cite_id_missing():
    record = dict(_by_emprise("EC459894"))
    del record["chantier_cite_id"]
    works_list = from_paris([record])
    assert len(works_list) == 1
    assert works_list[0].reference == record["num_emprise"]


def test_from_paris_no_geometry_is_handled():
    record = dict(_by_emprise("EC500567"))
    del record["geo_point_2d"]
    works_list = from_paris([record])
    assert works_list[0].sites[0].coordinate is None
