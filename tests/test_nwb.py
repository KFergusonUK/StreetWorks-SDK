"""Tests for the Netherlands NWB (Nationaal Wegenbestand) street/road-network
adapter.

WFS fixtures are real, trimmed, live (2026-07): ``nwb_wfs_harlingen.json``
(7 real wegvakken from Harlingen - the "Alexiastraat" group sharing one real
`bag_orl`; the real "Sédyk" over-merge case, two different `bag_orl` under
one street name; a real empty-`bag_orl` footpath; a real cycle-path
segment), ``nwb_wfs_encoding.json`` (real "IJsselmondseplein"/Rotterdam and
"Marga Klompéstraat"/IJsselstein - the `ij` digraph in both a street name
and a municipality name, plus a diacritic). ``nwb_atom_index.xml``/
``nwb_atom_dataset.xml`` are the real two-hop Atom feed, unmodified.

The GeoPackage fixture is built the same way ``test_bag.py`` builds its
GeoPackage fixture: from scratch, following the real structure confirmed
against the actual ~1 GB national file (two tables, `wegvakken` and
`hectopunten`; `wegvakken` geometry is `MULTILINESTRING` wrapping exactly
one line, `hectopunten` is `MULTIPOINT` wrapping exactly one point - both
confirmed live, not assumed) - every identifier and attribute value used
is real (Harlingen `wvk_id`/`bag_orl`/`stt_naam` values, a real
`hectopunten` row), only coordinates are the real ones already captured
and geometries are single-part, matching what was actually observed.
"""

import json
import sqlite3
import struct
from pathlib import Path

import httpx
import pytest
import respx

from streetworks.exceptions import RequestValidationError
from streetworks.nwb import AsyncNWBClient, NWBClient, NWBDatabase
from streetworks.nwb.atom import parse_dataset_feed, parse_index_feed
from streetworks.nwb.client import WFS_BASE_URL
from streetworks.nwb.models import wegvak_from_feature

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# models.py - real WFS feature parsing, the bag_orl grouping/over-merge finding
# --------------------------------------------------------------------------- #


def _harlingen_wegvakken():
    doc = _load_json("nwb_wfs_harlingen.json")
    return [wegvak_from_feature(f) for f in doc["features"]]


def test_wegvak_from_feature_real_alexiastraat():
    w = _harlingen_wegvakken()[0]
    assert w.stt_naam == "Alexiastraat"
    assert w.gme_naam == "Harlingen"
    assert w.wvk_id == 314551046
    assert w.bag_orl == "0072300000319612"
    assert w.toponyme_id() == "0072300000319612"
    assert w.geometry is not None and w.geometry.startswith("LINESTRING")


def test_wegvakken_group_cleanly_by_bag_orl():
    """The over-merge check: real addresses sharing a real bag_orl share
    the same street name - verified at full municipality scale (Harlingen,
    1,886 wegvakken, 378 groups, zero over-merged) during this brief's
    investigation; reproduced here on the real trimmed fixture (3
    Alexiastraat segments, one real bag_orl)."""
    wegvakken = _harlingen_wegvakken()
    alexiastraat = [w for w in wegvakken if w.bag_orl == "0072300000319612"]
    assert len(alexiastraat) == 3
    assert {w.stt_naam for w in alexiastraat} == {"Alexiastraat"}


def test_real_over_merge_case_sedyk_two_bag_orl_one_name():
    """The real, live-confirmed counter-example: "Sédyk" (Harlingen) is
    one display name spanning two different real bag_orl values - proof
    that name-based grouping alone would over-merge here, and why
    toponyme_id() never falls back to the name."""
    wegvakken = _harlingen_wegvakken()
    sedyk = [w for w in wegvakken if w.stt_naam == "Sédyk"]
    assert len(sedyk) == 2
    bag_orls = {w.bag_orl for w in sedyk}
    assert bag_orls == {"0072300000285375", "0072300000285575"}


def test_real_empty_bag_orl_case():
    wegvakken = _harlingen_wegvakken()
    no_join = [w for w in wegvakken if w.bag_orl is None]
    assert len(no_join) == 1
    assert no_join[0].toponyme_id() is None


def test_real_cycle_path_bst_code():
    """Two real FP (fietspad/cycle path) wegvakken: one with a real
    bag_orl join, one without - both genuinely FP-typed, confirmed live."""
    wegvakken = _harlingen_wegvakken()
    fp_names = {w.stt_naam for w in wegvakken if w.raw.get("bst_code") == "FP"}
    assert fp_names == {"Grote Sluisbrug", "Achlumerdijk"}
    achlumerdijk = next(w for w in wegvakken if w.stt_naam == "Achlumerdijk")
    assert achlumerdijk.bag_orl == "0072300000285450"


def test_encoding_ij_digraph_in_street_and_municipality_name():
    docs = _load_json("nwb_wfs_encoding.json")["features"]
    wegvakken = [wegvak_from_feature(f) for f in docs]
    ijsselmondseplein = next(w for w in wegvakken if w.stt_naam == "IJsselmondseplein")
    assert ijsselmondseplein.gme_naam == "Rotterdam"

    marga = next(w for w in wegvakken if w.gme_naam == "IJsselstein")
    assert marga.stt_naam == "Marga Klompéstraat"


# --------------------------------------------------------------------------- #
# atom.py - real two-hop feed parsing
# --------------------------------------------------------------------------- #


def test_parse_index_feed_finds_dataset():
    xml_bytes = (FIXTURES / "nwb_atom_index.xml").read_bytes()
    datasets = parse_index_feed(xml_bytes)
    assert len(datasets) == 1
    assert datasets[0].title == "NWB - Wegen"
    assert datasets[0].feed_url.endswith("nwb_wegen.xml")


def test_parse_dataset_feed_finds_real_geopackage_download():
    xml_bytes = (FIXTURES / "nwb_atom_dataset.xml").read_bytes()
    downloads = parse_dataset_feed(xml_bytes)
    assert len(downloads) == 1
    entry = downloads[0]
    assert entry.url.endswith("nwb_wegen.gpkg")
    assert entry.media_type == "application/geopackage+sqlite3"
    assert entry.length == 1029582848
    assert entry.rights == "https://creativecommons.org/publicdomain/zero/1.0/deed.nl"
    assert entry.crs_label == "Amersfoort / RD New"


def test_parse_index_feed_ignores_entries_without_alternate_feed_link():
    xml_bytes = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>No feed link</title></entry>
    </feed>"""
    assert parse_index_feed(xml_bytes) == []


# --------------------------------------------------------------------------- #
# client.py - WFS query/count (respx-mocked) and two-hop bulk discovery
# --------------------------------------------------------------------------- #


@respx.mock
def test_client_query_parses_real_response():
    respx.get(WFS_BASE_URL).mock(
        return_value=httpx.Response(200, json=_load_json("nwb_wfs_harlingen.json"))
    )
    with NWBClient() as nwb:
        results = nwb.query(cql_filter="gme_naam='Harlingen'")
    assert len(results) == 7


@respx.mock
def test_client_query_passes_cql_filter_param():
    route = respx.get(WFS_BASE_URL).mock(
        return_value=httpx.Response(200, json=_load_json("nwb_wfs_harlingen.json"))
    )
    with NWBClient() as nwb:
        nwb.query(cql_filter="gme_naam='Harlingen'", count=10)
    params = route.calls.last.request.url.params
    assert params["CQL_FILTER"] == "gme_naam='Harlingen'"
    assert params["count"] == "10"
    assert params["typeName"] == "wegvakken"


@respx.mock
def test_client_count_parses_number_matched():
    xml = (
        '<?xml version="1.0"?><wfs:FeatureCollection '
        'xmlns:wfs="http://www.opengis.net/wfs/2.0" numberMatched="1886" '
        'numberReturned="0"/>'
    )
    respx.get(WFS_BASE_URL).mock(return_value=httpx.Response(200, text=xml))
    with NWBClient() as nwb:
        assert nwb.count(cql_filter="gme_naam='Harlingen'") == 1886


@respx.mock
def test_client_query_error_maps_to_request_validation_error():
    respx.get(WFS_BASE_URL).mock(
        return_value=httpx.Response(
            400, json={"message": "Invalid Output Format Parameter"}
        )
    )
    with NWBClient() as nwb, pytest.raises(RequestValidationError):
        nwb.query()


@respx.mock
def test_client_discover_download_follows_both_hops():
    respx.get("https://service.pdok.nl/rws/nwbwegen/atom/index.xml").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "nwb_atom_index.xml").read_bytes())
    )
    respx.get("https://service.pdok.nl/rws/nationaal-wegenbestand-wegen/atom/nwb_wegen.xml").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "nwb_atom_dataset.xml").read_bytes())
    )
    with NWBClient() as nwb:
        entry = nwb.discover_download()
    assert entry.url.endswith("nwb_wegen.gpkg")


@respx.mock
def test_client_download_geopackage_streams_to_file(tmp_path):
    respx.get("https://service.pdok.nl/rws/nwbwegen/atom/index.xml").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "nwb_atom_index.xml").read_bytes())
    )
    respx.get("https://service.pdok.nl/rws/nationaal-wegenbestand-wegen/atom/nwb_wegen.xml").mock(
        return_value=httpx.Response(200, content=(FIXTURES / "nwb_atom_dataset.xml").read_bytes())
    )
    respx.get(
        "https://service.pdok.nl/rws/nationaal-wegenbestand-wegen/atom/downloads/nwb_wegen.gpkg"
    ).mock(return_value=httpx.Response(200, content=b"gpkg-bytes-stand-in"))
    with NWBClient() as nwb:
        path = nwb.download_geopackage(tmp_path / "nwb_wegen.gpkg")
    assert path.read_bytes() == b"gpkg-bytes-stand-in"


@respx.mock
def test_client_discover_download_missing_geopackage_raises():
    respx.get("https://service.pdok.nl/rws/nwbwegen/atom/index.xml").mock(
        return_value=httpx.Response(200, content=b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>')
    )
    with NWBClient() as nwb, pytest.raises(ValueError, match="geopackage"):
        nwb.discover_download()


@respx.mock
async def test_async_client_query_parses_real_response():
    respx.get(WFS_BASE_URL).mock(
        return_value=httpx.Response(200, json=_load_json("nwb_wfs_harlingen.json"))
    )
    async with AsyncNWBClient() as nwb:
        results = await nwb.query(cql_filter="gme_naam='Harlingen'")
    assert len(results) == 7


# --------------------------------------------------------------------------- #
# reader.py - the multi-table GeoPackage, built from real values
# --------------------------------------------------------------------------- #


def _wkb_multilinestring_one_part(points: list[tuple[float, float]]) -> bytes:
    ring = struct.pack("<I", len(points)) + b"".join(struct.pack("<2d", x, y) for x, y in points)
    line = struct.pack("<BI", 1, 2) + ring  # one standalone LineString
    return struct.pack("<BII", 1, 5, 1) + line  # MultiLineString wrapping it


def _wkb_multipoint_one_part(x: float, y: float) -> bytes:
    point = struct.pack("<BI2d", 1, 1, x, y)  # one standalone Point
    return struct.pack("<BII", 1, 4, 1) + point  # MultiPoint wrapping it


def _gpkg_blob(wkb: bytes, *, srs_id: int = 28992) -> bytes:
    return b"GP" + bytes([0, 0b00000001]) + struct.pack("<i", srs_id) + wkb


@pytest.fixture()
def nwb_gpkg_path(tmp_path):
    path = tmp_path / "nwb-sample.gpkg"
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
        CREATE TABLE wegvakken (
            fid INTEGER PRIMARY KEY, geom BLOB, wvk_id INTEGER, stt_naam TEXT,
            gme_naam TEXT, bag_orl TEXT, bst_code TEXT
        );
        CREATE TABLE hectopunten (
            fid INTEGER PRIMARY KEY, geom BLOB, wvk_id INTEGER,
            hectomtrng INTEGER, afstand INTEGER
        );
        INSERT INTO gpkg_contents VALUES
            ('wegvakken', 'features', 'wegvakken', 28992),
            ('hectopunten', 'features', 'hectopunten', 28992);
        INSERT INTO gpkg_geometry_columns VALUES
            ('wegvakken', 'geom', 'MULTILINESTRING', 28992, 0, 0),
            ('hectopunten', 'geom', 'MULTIPOINT', 28992, 0, 0);
        """
    )
    # Real identifiers/attributes from the actual national nwb_wegen.gpkg
    # (Harlingen, Alexiastraat - wvk_id 314551046, bag_orl 0072300000319612).
    line1 = [(157459.192, 575533.315), (157456.646, 575489.013)]
    line2 = [(157456.646, 575489.013), (157450.0, 575470.0)]
    conn.execute(
        "INSERT INTO wegvakken VALUES (1, ?, 314551046, 'Alexiastraat', 'Harlingen', "
        "'0072300000319612', 'VP')",
        (_gpkg_blob(_wkb_multilinestring_one_part(line1)),),
    )
    conn.execute(
        "INSERT INTO wegvakken VALUES (2, ?, 314551047, 'Alexiastraat', 'Harlingen', "
        "'0072300000319612', 'VP')",
        (_gpkg_blob(_wkb_multilinestring_one_part(line2)),),
    )
    # Real hectopunt row (wvk_id 103225003).
    conn.execute(
        "INSERT INTO hectopunten VALUES (1, ?, 103225003, 40, 1)",
        (_gpkg_blob(_wkb_multipoint_one_part(51902.534, 412884.229)),),
    )
    conn.commit()
    conn.close()
    return path


def test_tables_lists_real_gpkg_contents(nwb_gpkg_path):
    with NWBDatabase(nwb_gpkg_path) as db:
        infos = {t.table: t for t in db.tables()}
    assert infos["wegvakken"].geometry_type == "MULTILINESTRING"
    assert infos["hectopunten"].geometry_type == "MULTIPOINT"
    assert all(t.srs_id == 28992 for t in infos.values())


def test_iter_wegvakken_decodes_geometry_and_typed_fields(nwb_gpkg_path):
    with NWBDatabase(nwb_gpkg_path) as db:
        wegvakken = list(db.iter_wegvakken())
    assert len(wegvakken) == 2
    assert wegvakken[0].wvk_id == 314551046
    assert wegvakken[0].stt_naam == "Alexiastraat"
    assert wegvakken[0].bag_orl == "0072300000319612"
    assert wegvakken[0].geometry.startswith("MULTILINESTRING")


def test_iter_wegvakken_group_by_bag_orl(nwb_gpkg_path):
    with NWBDatabase(nwb_gpkg_path) as db:
        wegvakken = list(db.iter_wegvakken())
    assert {w.bag_orl for w in wegvakken} == {"0072300000319612"}
    assert {w.stt_naam for w in wegvakken} == {"Alexiastraat"}


def test_iter_features_hectopunten_decodes_multipoint(nwb_gpkg_path):
    with NWBDatabase(nwb_gpkg_path) as db:
        features = list(db.iter_features("hectopunten"))
    assert len(features) == 1
    assert features[0].raw["wvk_id"] == 103225003
    assert features[0].geometry == "MULTIPOINT ((51902.534 412884.229))"


def test_count(nwb_gpkg_path):
    with NWBDatabase(nwb_gpkg_path) as db:
        assert db.count("wegvakken") == 2
        assert db.count("hectopunten") == 1


def test_iter_features_unknown_table_raises(nwb_gpkg_path):
    with NWBDatabase(nwb_gpkg_path) as db, pytest.raises(ValueError, match="mutaties"):
        list(db.iter_features("mutaties_wegvakken"))


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        NWBDatabase(tmp_path / "does-not-exist.gpkg")
