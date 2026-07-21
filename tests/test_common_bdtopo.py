"""Tests for streetworks.common.from_bdtopo.

Fixtures are real Géoplateforme WFS responses (tests/fixtures/bdtopo_wfs_*)
built earlier this session.
"""

import json
from dataclasses import replace
from pathlib import Path

from streetworks.bdtopo.models import troncon_from_feature, voie_nommee_from_feature
from streetworks.common import Identifier, from_bdtopo

FIXTURES = Path(__file__).parent / "fixtures"


def _feature(name: str):
    doc = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return doc["features"][0]


def test_troncon_becomes_a_segment_with_left_right_names_and_street_refs():
    troncon = troncon_from_feature(_feature("bdtopo_wfs_troncons.json"))
    segment = from_bdtopo(troncon)

    assert segment.identifiers == (Identifier(scheme="cleabs", value=troncon.cleabs),)
    assert segment.geometry.crs == "EPSG:4326"
    assert segment.street_type.label == "Route à 1 chaussée"
    # Both sides state the same real name/id here - one Name, one street_ref,
    # not duplicated.
    assert len(segment.names) == 1
    assert segment.names[0].side == "gauche"
    assert segment.street_refs == (
        Identifier(scheme="identifiant_voie_ban", value="01004_0398", scope="01004"),
    )


def test_voie_nommee_becomes_a_street_with_segment_refs_and_address_links():
    voie = voie_nommee_from_feature(_feature("bdtopo_wfs_voie_nommee.json"))
    street = from_bdtopo(voie)

    assert street.identifiers == (Identifier(scheme="cleabs", value=voie.cleabs),)
    assert street.name == "Impasse de Mollon"
    assert street.street_type.label == "impasse"
    assert street.territory == "France"
    assert street.segment_refs == (
        Identifier(scheme="cleabs", value="TRONROUT0000002005899987"),
    )
    assert street.address_links == (
        Identifier(scheme="identifiant_voie_ban", value="01004_0668", scope="01004"),
    )


def test_troncon_administrative_area_none_when_left_right_communes_differ():
    troncon = troncon_from_feature(_feature("bdtopo_wfs_troncons.json"))
    # Real fixture has matching left/right INSEE codes - flip one to
    # exercise the straddling case without asserting a wrong single value.
    straddling = replace(troncon, insee_commune_droite="99999")
    segment = from_bdtopo(straddling)
    assert segment.administrative_area is None
