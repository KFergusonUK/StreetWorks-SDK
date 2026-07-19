"""Tests for the Netherlands BAG gazetteer adapter.

Locatieserver/Atom fixtures are real, trimmed live responses (2026-07):
``bag_free_response.json`` (a housenumber query), ``bag_suggest_response.json``,
``bag_reverse_response.json`` (``fl=*``), ``bag_lookup_response.json``,
``bag_search_diacritics.json`` (real "Ruïnelaan, Lochem" - exercises the
diaeresis and the NWB-sourced line-geometry finding), and
``bag_atom_feed.xml`` (the real feed, unmodified).

The GeoPackage fixture is built the same way ``test_openusrn.py`` builds
its GeoPackage fixture: from scratch, following the real OGC GeoPackage
structure, so the multi-table reader is exercised against the real file
shape without shipping a 7.8 GB binary. Every identifier and attribute
value used is real, taken from the actual national ``bag-light.gpkg``
during this brief's investigation (Appingedam/Hoogerheide,
Groningen/Utrecht real municipalities); only the large real polygon/
multipolygon geometries are replaced with small synthetic ones (real
geometry decoding is already covered by ``test_openusrn.py``'s WKB tests,
reused unchanged here - see ``streetworks.bag.reader``).
"""

import json
import sqlite3
import struct
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.bag import BAGClient, BAGDatabase
from streetworks.bag.atom import parse_feed
from streetworks.bag.client import LOCATIESERVER_BASE_URL
from streetworks.bag.models import location_from_doc
from streetworks.exceptions import RequestValidationError

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# atom.py - real feed parsing
# --------------------------------------------------------------------------- #


def test_parse_feed_finds_geopackage_and_extract():
    xml_bytes = (FIXTURES / "bag_atom_feed.xml").read_bytes()
    entries = parse_feed(xml_bytes)
    assert len(entries) == 2

    gpkg = next(e for e in entries if e.media_type == "application/geopackage+sqlite3")
    assert gpkg.url == "https://service.pdok.nl/kadaster/bag/atom/downloads/bag-light.gpkg"
    assert gpkg.length == 7801561088
    assert gpkg.crs_label == "Amersfoort / RD New"

    extract = next(e for e in entries if e.media_type == "application/zip")
    assert extract.url.endswith("lvbag-extract-nl.zip")
    assert extract.length == 3610187048


def test_parse_feed_rights_is_cc0_not_pdm():
    """Real live element - the design brief named PDM, the feed says CC0."""
    xml_bytes = (FIXTURES / "bag_atom_feed.xml").read_bytes()
    entries = parse_feed(xml_bytes)
    cc0 = "https://creativecommons.org/publicdomain/zero/1.0/deed.nl"
    assert all(e.rights == cc0 for e in entries)


def test_parse_feed_ignores_entries_without_a_download_link():
    xml_bytes = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>No link here</title></entry>
    </feed>"""
    assert parse_feed(xml_bytes) == []


# --------------------------------------------------------------------------- #
# models.py - real Locatieserver doc parsing
# --------------------------------------------------------------------------- #


def test_location_from_doc_weg_result():
    doc = _load_json("bag_free_response.json")["response"]["docs"][0]
    loc = location_from_doc(doc)
    assert loc.type == "weg"
    assert loc.straatnaam == "Dam"
    assert loc.openbareruimte_id == "0363300000003186"
    assert loc.identificatie == "0363300000003186"
    assert loc.lon == pytest.approx(4.89304433)
    assert loc.lat == pytest.approx(52.37297089)
    assert loc.rd_x == pytest.approx(121347.914)
    assert loc.rd_y == pytest.approx(487347.519)


def test_location_from_doc_adres_result():
    doc = _load_json("bag_free_response.json")["response"]["docs"][1]
    loc = location_from_doc(doc)
    assert loc.type == "adres"
    assert loc.huisnummer == 1
    assert loc.postcode == "1012JS"
    assert loc.woonplaatsnaam == "Amsterdam"
    # Same street, same openbareruimte_id as the "weg" result above.
    assert loc.openbareruimte_id == "0363300000003186"


def test_location_from_doc_diacritics_preserved():
    doc = _load_json("bag_search_diacritics.json")["response"]["docs"][0]
    loc = location_from_doc(doc)
    assert loc.straatnaam == "Ruïnelaan"
    assert loc.weergavenaam == "Ruïnelaan, Lochem"
    assert loc.raw["straatnaam_verkort"] == "Ruïneln"


def test_location_from_doc_weg_line_geometry_not_promoted_to_a_field():
    """A real "weg" result with fl=* carries a MULTILINESTRING in
    geometrie_ll/geometrie_rd - sourced from NWB, not BAG itself (see
    models.py's module docstring). BAGLocation only models the point;
    the line stays reachable via .raw."""
    doc = _load_json("bag_search_diacritics.json")["response"]["docs"][0]
    assert doc["bron"] == "BAG/NWB"
    assert doc["geometrie_ll"].startswith("MULTILINESTRING")
    loc = location_from_doc(doc)
    assert loc.lon is not None and loc.lat is not None  # point still parsed, from centroide
    assert loc.raw["geometrie_ll"] == doc["geometrie_ll"]


def test_location_from_doc_reverse_result_has_afstand():
    doc = _load_json("bag_reverse_response.json")["response"]["docs"][0]
    loc = location_from_doc(doc)
    assert loc.afstand is not None
    assert loc.type == "adres"


# --------------------------------------------------------------------------- #
# client.py - Locatieserver (respx-mocked) and Atom-driven downloads
# --------------------------------------------------------------------------- #


@respx.mock
def test_client_search_parses_real_response():
    respx.get(f"{LOCATIESERVER_BASE_URL}/free").mock(
        return_value=httpx.Response(200, json=_load_json("bag_free_response.json"))
    )
    with BAGClient() as bag:
        results = bag.search("Dam 1 Amsterdam")
    assert len(results) == 3
    assert results[0].type == "weg"


@respx.mock
def test_client_suggest_parses_real_response():
    respx.get(f"{LOCATIESERVER_BASE_URL}/suggest").mock(
        return_value=httpx.Response(200, json=_load_json("bag_suggest_response.json"))
    )
    with BAGClient() as bag:
        results = bag.suggest("Damrak Amsterdam")
    assert len(results) == 3
    assert {r.type for r in results} == {"weg", "adres"}


@respx.mock
def test_client_reverse_defaults_to_fl_star():
    route = respx.get(f"{LOCATIESERVER_BASE_URL}/reverse").mock(
        return_value=httpx.Response(200, json=_load_json("bag_reverse_response.json"))
    )
    with BAGClient() as bag:
        results = bag.reverse(4.89304, 52.37297)
    assert route.calls.last.request.url.params["fl"] == "*"
    assert len(results) == 2


@respx.mock
def test_client_reverse_rd_uses_x_y_params():
    route = respx.get(f"{LOCATIESERVER_BASE_URL}/reverse").mock(
        return_value=httpx.Response(200, json=_load_json("bag_reverse_response.json"))
    )
    with BAGClient() as bag:
        bag.reverse_rd(121347.914, 487347.519)
    params = route.calls.last.request.url.params
    assert params["X"] == "121347.914"
    assert params["Y"] == "487347.519"


@respx.mock
def test_client_lookup_returns_single_result():
    respx.get(f"{LOCATIESERVER_BASE_URL}/lookup").mock(
        return_value=httpx.Response(200, json=_load_json("bag_lookup_response.json"))
    )
    with BAGClient() as bag:
        result = bag.lookup("adr-2a8dc1af055da20b8bcdc8e4dbda1eaa")
    assert result is not None
    assert result.postcode == "1012JS"


@respx.mock
def test_client_lookup_none_when_no_docs():
    respx.get(f"{LOCATIESERVER_BASE_URL}/lookup").mock(
        return_value=httpx.Response(200, json={"response": {"docs": []}})
    )
    with BAGClient() as bag:
        assert bag.lookup("nonexistent") is None


@respx.mock
def test_client_search_error_maps_to_request_validation_error():
    respx.get(f"{LOCATIESERVER_BASE_URL}/free").mock(
        return_value=httpx.Response(400, json={"error": "bad request"})
    )
    with BAGClient() as bag, pytest.raises(RequestValidationError):
        bag.search("x")


@respx.mock
def test_client_discover_downloads_parses_real_feed():
    respx.get("https://service.pdok.nl/lv/bag/atom/bag.xml").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "bag_atom_feed.xml").read_bytes())
    )
    with BAGClient() as bag:
        entries = bag.discover_downloads()
    assert len(entries) == 2


@respx.mock
def test_client_download_geopackage_resolves_url_from_feed(tmp_path):
    respx.get("https://service.pdok.nl/lv/bag/atom/bag.xml").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "bag_atom_feed.xml").read_bytes())
    )
    respx.get("https://service.pdok.nl/kadaster/bag/atom/downloads/bag-light.gpkg").mock(
        return_value=httpx.Response(200, content=b"gpkg-bytes-stand-in")
    )
    with BAGClient() as bag:
        path = bag.download_geopackage(tmp_path / "bag-light.gpkg")
    assert path.read_bytes() == b"gpkg-bytes-stand-in"


@respx.mock
def test_client_download_extract_resolves_url_from_feed(tmp_path):
    respx.get("https://service.pdok.nl/lv/bag/atom/bag.xml").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "bag_atom_feed.xml").read_bytes())
    )
    respx.get("https://service.pdok.nl/kadaster/bag/atom/downloads/lvbag-extract-nl.zip").mock(
        return_value=httpx.Response(200, content=b"zip-bytes-stand-in")
    )
    with BAGClient() as bag:
        path = bag.download_extract(tmp_path / "extract.zip")
    assert path.read_bytes() == b"zip-bytes-stand-in"


@respx.mock
def test_client_download_geopackage_missing_from_feed_raises():
    respx.get("https://service.pdok.nl/lv/bag/atom/bag.xml").mock(
        return_value=httpx.Response(200, content=b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>')
    )
    with BAGClient() as bag, pytest.raises(ValueError, match="geopackage"):
        bag.download_geopackage("dest.gpkg")


# --------------------------------------------------------------------------- #
# reader.py - the multi-table GeoPackage, built from real values, small geometry
# --------------------------------------------------------------------------- #


def _wkb_point(x: float, y: float) -> bytes:
    return struct.pack("<BI2d", 1, 1, x, y)


def _wkb_polygon(points: list[tuple[float, float]]) -> bytes:
    ring = struct.pack("<I", len(points)) + b"".join(struct.pack("<2d", x, y) for x, y in points)
    return struct.pack("<BII", 1, 3, 1) + ring


def _wkb_multipolygon(polygons: list[list[tuple[float, float]]]) -> bytes:
    # Each sub-polygon is a complete standalone WKB Polygon (own byte-order
    # + type header) - that's what MultiPolygon's own spec requires.
    out = struct.pack("<BII", 1, 6, len(polygons))
    for points in polygons:
        out += _wkb_polygon(points)
    return out


def _gpkg_blob(wkb: bytes, *, srs_id: int = 28992) -> bytes:
    return b"GP" + bytes([0, 0b00000001]) + struct.pack("<i", srs_id) + wkb


@pytest.fixture()
def bag_gpkg_path(tmp_path):
    path = tmp_path / "bag-light-sample.gpkg"
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
        CREATE TABLE verblijfsobject (
            feature_id INTEGER PRIMARY KEY, geom BLOB, identificatie TEXT,
            openbare_ruimte_naam TEXT, openbare_ruimte_identificatie TEXT,
            huisnummer INTEGER, postcode TEXT, woonplaats_naam TEXT,
            status TEXT, gebruiksdoel TEXT
        );
        CREATE TABLE ligplaats (
            feature_id INTEGER PRIMARY KEY, geom BLOB, identificatie TEXT,
            openbare_ruimte_naam TEXT, openbare_ruimte_identificatie TEXT,
            huisnummer INTEGER, postcode TEXT, woonplaats_naam TEXT, status TEXT
        );
        CREATE TABLE woonplaats (
            feature_id INTEGER PRIMARY KEY, geom BLOB, identificatie TEXT,
            woonplaats TEXT, status TEXT
        );
        INSERT INTO gpkg_contents VALUES
            ('verblijfsobject', 'features', 'verblijfsobject', 28992),
            ('ligplaats', 'features', 'ligplaats', 28992),
            ('woonplaats', 'features', 'woonplaats', 28992);
        INSERT INTO gpkg_geometry_columns VALUES
            ('verblijfsobject', 'geom', 'POINT', 28992, 0, 0),
            ('ligplaats', 'geom', 'POLYGON', 28992, 0, 0),
            ('woonplaats', 'geom', 'MULTIPOLYGON', 28992, 0, 0);
        """
    )
    # Real identifiers/attributes from the actual national bag-light.gpkg
    # (Appingedam, Molenstraat) - two dwellings on the same real street id,
    # small synthetic points in place of the real RD coordinates' full precision.
    conn.execute(
        "INSERT INTO verblijfsobject VALUES (1, ?, '0003010000125985', 'Molenstraat', "
        "'0003300000117142', 16, '9901KB', 'Appingedam', "
        "'Verblijfsobject in gebruik', 'woonfunctie')",
        (_gpkg_blob(_wkb_point(252767.348, 593745.504)),),
    )
    conn.execute(
        "INSERT INTO verblijfsobject VALUES (2, ?, '0003010000125986', 'Molenstraat', "
        "'0003300000117142', 20, '9901KB', 'Appingedam', "
        "'Verblijfsobject in gebruik', 'woonfunctie')",
        (_gpkg_blob(_wkb_point(252769.565, 593744.87)),),
    )
    conn.execute(
        "INSERT INTO ligplaats VALUES (1, ?, '0003020000000001', 'Fivelkade W', "
        "'0003300000117059', 4, '9901GE', 'Appingedam', 'Plaats aangewezen')",
        (
            _gpkg_blob(
                _wkb_polygon(
                    [
                        (252475.401, 593758.074),
                        (252474.344, 593760.335),
                        (252455.436, 593751.494),
                        (252475.401, 593758.074),
                    ]
                )
            ),
        ),
    )
    hoogerheide_ring = [
        (78988.952, 384548.144),
        (78992.462, 384549.74),
        (78998.712, 384555.12),
        (78988.952, 384548.144),
    ]
    conn.execute(
        "INSERT INTO woonplaats VALUES (1, ?, '1000', 'Hoogerheide', 'Woonplaats aangewezen')",
        (_gpkg_blob(_wkb_multipolygon([hoogerheide_ring])),),
    )
    conn.commit()
    conn.close()
    return path


def test_tables_lists_real_gpkg_contents(bag_gpkg_path):
    with BAGDatabase(bag_gpkg_path) as db:
        infos = {t.table: t for t in db.tables()}
    assert infos["verblijfsobject"].geometry_type == "POINT"
    assert infos["ligplaats"].geometry_type == "POLYGON"
    assert infos["woonplaats"].geometry_type == "MULTIPOLYGON"
    assert all(t.srs_id == 28992 for t in infos.values())


def test_iter_features_verblijfsobject_decodes_point_geometry(bag_gpkg_path):
    with BAGDatabase(bag_gpkg_path) as db:
        features = list(db.iter_features("verblijfsobject"))
    assert len(features) == 2
    assert features[0].raw["identificatie"] == "0003010000125985"
    assert features[0].geometry == "POINT (252767.348 593745.504)"


def test_iter_features_two_addresses_share_real_street_id(bag_gpkg_path):
    with BAGDatabase(bag_gpkg_path) as db:
        features = list(db.iter_features("verblijfsobject"))
    street_ids = {f.raw["openbare_ruimte_identificatie"] for f in features}
    names = {f.raw["openbare_ruimte_naam"] for f in features}
    assert street_ids == {"0003300000117142"}
    assert names == {"Molenstraat"}


def test_iter_features_ligplaats_decodes_polygon(bag_gpkg_path):
    with BAGDatabase(bag_gpkg_path) as db:
        features = list(db.iter_features("ligplaats"))
    assert features[0].geometry.startswith("POLYGON ((252475.401 593758.074")


def test_iter_features_woonplaats_decodes_multipolygon(bag_gpkg_path):
    with BAGDatabase(bag_gpkg_path) as db:
        features = list(db.iter_features("woonplaats"))
    assert features[0].raw["woonplaats"] == "Hoogerheide"
    assert features[0].geometry.startswith("MULTIPOLYGON (((78988.952 384548.144")


def test_iter_features_limit(bag_gpkg_path):
    with BAGDatabase(bag_gpkg_path) as db:
        features = list(db.iter_features("verblijfsobject", limit=1))
    assert len(features) == 1


def test_count(bag_gpkg_path):
    with BAGDatabase(bag_gpkg_path) as db:
        assert db.count("verblijfsobject") == 2
        assert db.count("ligplaats") == 1
        assert db.count("woonplaats") == 1


def test_iter_features_unknown_table_raises(bag_gpkg_path):
    with BAGDatabase(bag_gpkg_path) as db, pytest.raises(ValueError, match="pand"):
        list(db.iter_features("pand"))


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        BAGDatabase(tmp_path / "does-not-exist.gpkg")
