"""Tests for the France BD TOPO (IGN) street-geometry adapter.

WFS fixtures are real, trimmed, live (2026-07): ``bdtopo_wfs_troncons.json``
(9 real `troncon_de_route` segments - 3 real "Rue Jean Monnet" segments
sharing one real BAN id; 4 real "Rue du Président Salvador Allende"
segments demonstrating the collaborative-name-vs-BAN-name nuance found
during this brief's investigation; a real rural gravel-road segment with
no BAN join at all; and the real "Impasse de Mollon" segment used to
cross-check the `voie_nommee` link) and ``bdtopo_wfs_voie_nommee.json`` (2
real named streets, including "Impasse de Mollon", whose
`liens_vers_supports` was confirmed live to resolve to the matching real
`troncon_de_route`).
"""

import json
import sqlite3
import struct
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.bdtopo import BDTopoClient, BDTopoDatabase
from streetworks.bdtopo.client import WFS_BASE_URL
from streetworks.bdtopo.models import troncon_from_feature, voie_nommee_from_feature
from streetworks.exceptions import RequestValidationError

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _troncons():
    doc = _load_json("bdtopo_wfs_troncons.json")
    return [troncon_from_feature(f) for f in doc["features"]]


# --------------------------------------------------------------------------- #
# models.py - real feature parsing, the two-level spine, the BAN join
# --------------------------------------------------------------------------- #


def test_troncon_from_feature_real_impasse_de_mollon():
    t = next(t for t in _troncons() if t.cleabs == "TRONROUT0000002005899987")
    assert t.nom_voie_ban_gauche == "Impasse de Mollon"
    assert t.identifiant_voie_ban_gauche == "01004_0668"
    assert t.toponyme_id_gauche() == "01004_0668"
    assert t.geometry is not None and t.geometry.startswith("LINESTRING")


def test_troncon_geometry_carries_real_3d_altitude():
    """Confirmed live: a real BD TOPO point carries a genuine third
    (altitude) coordinate, not just documented as 3D."""
    doc = _load_json("bdtopo_wfs_troncons.json")
    rural = next(
        f for f in doc["features"] if f["properties"]["cleabs"] == "TRONROUT0000000109622219"
    )
    first_point = rural["geometry"]["coordinates"][0]
    assert len(first_point) == 3
    lon, lat, altitude = first_point
    assert 100 < altitude < 300  # a real metres-above-sea-level value


def test_troncons_group_cleanly_by_identifiant_voie_ban():
    """The over-merge check, verified at full commune scale (Ambérieu-en-
    Bugey and Basse-Terre, zero over-merged by nom_voie_ban) during this
    brief's investigation; reproduced here on the real trimmed fixture."""
    troncons = _troncons()
    jean_monnet = [t for t in troncons if t.identifiant_voie_ban_gauche == "01004_0398"]
    assert len(jean_monnet) == 3
    assert {t.nom_voie_ban_gauche for t in jean_monnet} == {"Rue Jean Monnet"}


def test_real_naming_nuance_collaboratif_vs_ban_name():
    """The real, live-confirmed nuance: the same BAN id has two spellings
    in the crowd-sourced nom_collaboratif field (an abbreviation, not a
    genuine identity conflict) but exactly one in nom_voie_ban - grouping
    by identifiant_voie_ban and checking nom_voie_ban is clean; checking
    nom_collaboratif is not, which is why this SDK never groups by the
    collaborative name."""
    troncons = _troncons()
    allende = [t for t in troncons if t.identifiant_voie_ban_gauche == "97124_0283"]
    assert len(allende) == 4
    assert {t.nom_voie_ban_gauche for t in allende} == {"Rue du Président Salvador Allende"}
    collaboratif_variants = {t.nom_collaboratif_gauche for t in allende}
    assert collaboratif_variants == {"R SALVADOR ALLENDE", "Rue du Président Salvador Allende"}


def test_real_rural_road_has_no_ban_join():
    troncons = _troncons()
    rural = next(t for t in troncons if t.cleabs == "TRONROUT0000000109622219")
    assert rural.nature == "Route empierrée"
    assert rural.toponyme_id_gauche() is None
    assert rural.toponyme_id_droite() is None


def test_voie_nommee_from_feature_real_impasse_de_mollon():
    doc = _load_json("bdtopo_wfs_voie_nommee.json")
    voies = [voie_nommee_from_feature(f) for f in doc["features"]]
    mollon = next(v for v in voies if v.nom_voie_ban == "Impasse de Mollon")
    assert mollon.cleabs == "VOIE_NOM0000002336861171"
    assert mollon.identifiant_voie_ban == "01004_0668"
    assert mollon.toponyme_id() == "01004_0668"
    assert mollon.liens_vers_supports == "TRONROUT0000002005899987"
    assert mollon.geometry is not None and mollon.geometry.startswith("MULTILINESTRING")


def test_voie_nommee_link_resolves_to_the_real_matching_troncon():
    """The two-level-spine finding, cross-checked across both real
    fixtures: voie_nommee.liens_vers_supports resolves to a real
    troncon_de_route with the *same* BAN identifier - confirmed live, not
    assumed from field naming alone."""
    voie_doc = _load_json("bdtopo_wfs_voie_nommee.json")
    voies = [voie_nommee_from_feature(f) for f in voie_doc["features"]]
    mollon = next(v for v in voies if v.nom_voie_ban == "Impasse de Mollon")

    troncons = _troncons()
    linked = next(t for t in troncons if t.cleabs == mollon.liens_vers_supports)
    assert linked.identifiant_voie_ban_gauche == mollon.identifiant_voie_ban


# --------------------------------------------------------------------------- #
# client.py - WFS query/count (respx-mocked)
# --------------------------------------------------------------------------- #


@respx.mock
def test_client_query_troncons_parses_real_response():
    respx.get(WFS_BASE_URL).mock(
        return_value=httpx.Response(200, json=_load_json("bdtopo_wfs_troncons.json"))
    )
    with BDTopoClient() as bdtopo:
        results = bdtopo.query_troncons(cql_filter="identifiant_voie_ban_gauche='01004_0398'")
    assert len(results) == 9


@respx.mock
def test_client_query_troncons_passes_cql_filter_param():
    route = respx.get(WFS_BASE_URL).mock(
        return_value=httpx.Response(200, json=_load_json("bdtopo_wfs_troncons.json"))
    )
    with BDTopoClient() as bdtopo:
        bdtopo.query_troncons(cql_filter="insee_commune_gauche='01004'", count=10)
    params = route.calls.last.request.url.params
    assert params["CQL_FILTER"] == "insee_commune_gauche='01004'"
    assert params["COUNT"] == "10"
    assert params["TYPENAME"] == "BDTOPO_V3:troncon_de_route"


@respx.mock
def test_client_query_voies_nommees_parses_real_response():
    route = respx.get(WFS_BASE_URL).mock(
        return_value=httpx.Response(200, json=_load_json("bdtopo_wfs_voie_nommee.json"))
    )
    with BDTopoClient() as bdtopo:
        results = bdtopo.query_voies_nommees(cql_filter="insee_commune='01004'")
    assert len(results) == 2
    assert route.calls.last.request.url.params["TYPENAME"] == "BDTOPO_V3:voie_nommee"


@respx.mock
def test_client_count_troncons_parses_number_matched():
    xml = (
        '<?xml version="1.0"?><wfs:FeatureCollection '
        'xmlns:wfs="http://www.opengis.net/wfs/2.0" numberMatched="2478" '
        'numberReturned="0"/>'
    )
    respx.get(WFS_BASE_URL).mock(return_value=httpx.Response(200, text=xml))
    with BDTopoClient() as bdtopo:
        assert bdtopo.count_troncons(cql_filter="insee_commune_gauche='01004'") == 2478


@respx.mock
def test_client_query_error_maps_to_request_validation_error():
    """Real live shape (unknown TYPENAME): an OWS ExceptionReport, XML,
    HTTP 400 - confirmed live."""
    xml = (
        '<?xml version="1.0"?><ows:ExceptionReport '
        'xmlns:ows="http://www.opengis.net/ows/1.1" version="2.0.0">'
        '<ows:Exception exceptionCode="InvalidParameterValue" locator="typeName">'
        "<ows:ExceptionText>Feature type unknown</ows:ExceptionText>"
        "</ows:Exception></ows:ExceptionReport>"
    )
    respx.get(WFS_BASE_URL).mock(return_value=httpx.Response(400, text=xml))
    with BDTopoClient() as bdtopo, pytest.raises(RequestValidationError):
        bdtopo.query_troncons()


@respx.mock
async def test_async_client_query_troncons_parses_real_response():
    from streetworks.bdtopo import AsyncBDTopoClient

    respx.get(WFS_BASE_URL).mock(
        return_value=httpx.Response(200, json=_load_json("bdtopo_wfs_troncons.json"))
    )
    async with AsyncBDTopoClient() as bdtopo:
        results = await bdtopo.query_troncons(cql_filter="insee_commune_gauche='01004'")
    assert len(results) == 9


# --------------------------------------------------------------------------- #
# reader.py - the GeoPackage reader, built from real values (unverified
# against a real downloaded file - see the package docstring)
# --------------------------------------------------------------------------- #


def _wkb_linestring_3d(points: list[tuple[float, float, float]]) -> bytes:
    body = b"".join(struct.pack("<3d", x, y, z) for x, y, z in points)
    ring = struct.pack("<I", len(points)) + body
    return struct.pack("<BI", 1, 1002) + ring  # ISO WKB LineString Z


def _wkb_multilinestring(lines: list[list[tuple[float, float]]]) -> bytes:
    out = struct.pack("<BII", 1, 5, len(lines))
    for points in lines:
        body = b"".join(struct.pack("<2d", x, y) for x, y in points)
        ring = struct.pack("<I", len(points)) + body
        out += struct.pack("<BI", 1, 2) + ring
    return out


def _gpkg_blob(wkb: bytes, *, srs_id: int = 4326) -> bytes:
    return b"GP" + bytes([0, 0b00000001]) + struct.pack("<i", srs_id) + wkb


@pytest.fixture()
def bdtopo_gpkg_path(tmp_path):
    path = tmp_path / "bdtopo-sample.gpkg"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE gpkg_contents (
            table_name TEXT PRIMARY KEY, data_type TEXT, identifier TEXT, srs_id INTEGER
        );
        CREATE TABLE gpkg_geometry_columns (
            table_name TEXT, column_name TEXT, geometry_type_name TEXT,
            srs_id INTEGER, z TINYINT, m TINYINT
        );
        CREATE TABLE troncon_de_route (
            fid INTEGER PRIMARY KEY, geom BLOB, cleabs TEXT, nature TEXT,
            nom_collaboratif_gauche TEXT, nom_voie_ban_gauche TEXT,
            identifiant_voie_ban_gauche TEXT
        );
        CREATE TABLE voie_nommee (
            fid INTEGER PRIMARY KEY, geom BLOB, cleabs TEXT, nom_voie_ban TEXT,
            identifiant_voie_ban TEXT, liens_vers_supports TEXT
        );
        INSERT INTO gpkg_contents VALUES
            ('troncon_de_route', 'features', 'troncon_de_route', 4326),
            ('voie_nommee', 'features', 'voie_nommee', 4326);
        INSERT INTO gpkg_geometry_columns VALUES
            ('troncon_de_route', 'geom', 'LINESTRING', 4326, 1, 0),
            ('voie_nommee', 'geom', 'MULTILINESTRING', 4326, 0, 0);
        """
    )
    # Real identifiers/attributes from the real live WFS (Ambérieu-en-Bugey,
    # Impasse de Mollon) - small real 3D coordinates for the segment.
    mollon_line_3d = [(5.36688679, 45.96617356, 341.3), (5.3666079, 45.96587669, 342.0)]
    mollon_line_2d = [(5.36688679, 45.96617356), (5.3666079, 45.96587669)]
    conn.execute(
        "INSERT INTO troncon_de_route VALUES "
        "(1, ?, 'TRONROUT0000002005899987', 'Chemin', 'IMP DE MOLLON', "
        "'Impasse de Mollon', '01004_0668')",
        (_gpkg_blob(_wkb_linestring_3d(mollon_line_3d)),),
    )
    conn.execute(
        "INSERT INTO voie_nommee VALUES "
        "(1, ?, 'VOIE_NOM0000002336861171', 'Impasse de Mollon', "
        "'01004_0668', 'TRONROUT0000002005899987')",
        (_gpkg_blob(_wkb_multilinestring([mollon_line_2d])),),
    )
    conn.commit()
    conn.close()
    return path


def test_tables_lists_real_gpkg_contents(bdtopo_gpkg_path):
    with BDTopoDatabase(bdtopo_gpkg_path) as db:
        infos = {t.table: t for t in db.tables()}
    assert infos["troncon_de_route"].geometry_type == "LINESTRING"
    assert infos["voie_nommee"].geometry_type == "MULTILINESTRING"
    assert all(t.srs_id == 4326 for t in infos.values())


def test_iter_troncons_decodes_geometry_and_typed_fields(bdtopo_gpkg_path):
    with BDTopoDatabase(bdtopo_gpkg_path) as db:
        troncons = list(db.iter_troncons())
    assert len(troncons) == 1
    t = troncons[0]
    assert t.cleabs == "TRONROUT0000002005899987"
    assert t.identifiant_voie_ban_gauche == "01004_0668"
    assert t.toponyme_id_gauche() == "01004_0668"
    assert t.geometry.startswith("LINESTRING")


def test_iter_voies_nommees_decodes_geometry_and_links_to_troncon(bdtopo_gpkg_path):
    with BDTopoDatabase(bdtopo_gpkg_path) as db:
        voies = list(db.iter_voies_nommees())
        troncons = list(db.iter_troncons())
    assert len(voies) == 1
    voie = voies[0]
    assert voie.geometry.startswith("MULTILINESTRING")
    linked = next(t for t in troncons if t.cleabs == voie.liens_vers_supports)
    assert linked.identifiant_voie_ban_gauche == voie.identifiant_voie_ban


def test_count(bdtopo_gpkg_path):
    with BDTopoDatabase(bdtopo_gpkg_path) as db:
        assert db.count("troncon_de_route") == 1
        assert db.count("voie_nommee") == 1


def test_iter_features_unknown_table_raises(bdtopo_gpkg_path):
    with BDTopoDatabase(bdtopo_gpkg_path) as db, pytest.raises(ValueError, match="batiment"):
        list(db.iter_features("batiment"))


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        BDTopoDatabase(tmp_path / "does-not-exist.gpkg")
