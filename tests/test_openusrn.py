"""Tests for the OS Open USRN provider.

The GeoPackage fixture is built from scratch following the OGC GeoPackage
spec (gpkg_contents / gpkg_geometry_columns metadata, "GP"-header geometry
blobs wrapping standard WKB), so the reader is exercised against the real
file structure without shipping a 300 MB binary.
"""

import sqlite3
import struct

import httpx
import pytest
import respx

from streetworks.openusrn import (
    OpenUSRNClient,
    UsrnDatabase,
    extract_gpkg,
    gpkg_geometry_to_wkt,
)


def wkb_linestring(points: list[tuple[float, float]]) -> bytes:
    out = struct.pack("<BI", 1, 2) + struct.pack("<I", len(points))
    for x, y in points:
        out += struct.pack("<2d", x, y)
    return out


def gpkg_blob(wkb: bytes, *, srs_id: int = 27700) -> bytes:
    # "GP", version 0, flags: little-endian byte order, no envelope
    return b"GP" + bytes([0, 0b00000001]) + struct.pack("<i", srs_id) + wkb


@pytest.fixture()
def gpkg_path(tmp_path):
    path = tmp_path / "osopenusrn.gpkg"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE gpkg_contents (
            table_name TEXT PRIMARY KEY, data_type TEXT, identifier TEXT,
            srs_id INTEGER
        );
        CREATE TABLE gpkg_geometry_columns (
            table_name TEXT, column_name TEXT, geometry_type_name TEXT,
            srs_id INTEGER, z TINYINT, m TINYINT
        );
        CREATE TABLE "openUSRN" (
            fid INTEGER PRIMARY KEY, usrn INTEGER, geometry BLOB
        );
        INSERT INTO gpkg_contents VALUES ('openUSRN', 'features', 'Open USRN', 27700);
        INSERT INTO gpkg_geometry_columns
            VALUES ('openUSRN', 'geometry', 'MULTILINESTRING', 27700, 0, 0);
        """
    )
    # A Durham street (real USRN verified live against DataVIA) and one more
    conn.execute(
        'INSERT INTO "openUSRN" VALUES (1, 33909869, ?)',
        (gpkg_blob(wkb_linestring([(424000.5, 542000.25), (424100.0, 542050.0)])),),
    )
    conn.execute('INSERT INTO "openUSRN" VALUES (2, 84202034, NULL)')
    conn.commit()
    conn.close()
    return path


def test_discovers_layer_and_looks_up_usrn(gpkg_path):
    with UsrnDatabase(gpkg_path) as db:
        assert db.table == "openUSRN"
        assert db.count() == 2
        street = db.get(33909869)
        assert street.usrn == 33909869
        assert street.geometry == ("LINESTRING (424000.5 542000.25, 424100 542050)")
        assert db.get("33909869").usrn == 33909869  # string USRNs accepted
        assert db.get(999) is None


def test_null_geometry_yields_none(gpkg_path):
    with UsrnDatabase(gpkg_path) as db:
        assert db.get(84202034).geometry is None


def test_iter_streets(gpkg_path):
    with UsrnDatabase(gpkg_path) as db:
        usrns = [s.usrn for s in db.iter_streets()]
    assert usrns == [33909869, 84202034]


def test_wkb_decoder_handles_multilinestring_and_point():
    inner = wkb_linestring([(1.0, 2.0), (3.0, 4.0)])
    multi = struct.pack("<BII", 1, 5, 1) + inner
    assert gpkg_geometry_to_wkt(gpkg_blob(multi)) == ("MULTILINESTRING ((1 2, 3 4))")
    point = struct.pack("<BI2d", 1, 1, 5.5, 6.5)
    assert gpkg_geometry_to_wkt(gpkg_blob(point)) == "POINT (5.5 6.5)"
    assert gpkg_geometry_to_wkt(None) is None
    assert gpkg_geometry_to_wkt(b"not a gpkg blob") is None


def test_extract_gpkg_passthrough_and_zip(tmp_path, gpkg_path):
    assert extract_gpkg(gpkg_path) == gpkg_path
    import zipfile

    z = tmp_path / "bundle.zip"
    with zipfile.ZipFile(z, "w") as archive:
        archive.write(gpkg_path, "osopenusrn.gpkg")
    extracted = extract_gpkg(z, tmp_path / "out")
    with UsrnDatabase(extracted) as db:
        assert db.count() == 2


@respx.mock
def test_client_lists_downloads_and_streams_file(tmp_path):
    respx.get("https://api.os.uk/downloads/v1/products/OpenUSRN/downloads").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "fileName": "osopenusrn.zip",
                    "format": "GeoPackage",
                    "size": 310000000,
                    "url": "https://files.os.example/osopenusrn.zip",
                }
            ],
        )
    )
    respx.get("https://files.os.example/osopenusrn.zip").mock(
        return_value=httpx.Response(200, content=b"PK\x03\x04usrn-bytes")
    )
    with OpenUSRNClient() as client:
        entries = client.downloads()
        assert entries[0]["format"] == "GeoPackage"
        path = client.download(tmp_path / "usrn.zip")
    assert path.read_bytes().endswith(b"usrn-bytes")


def wkb_linestring_z(points: list[tuple[float, float, float]]) -> bytes:
    """ISO WKB LineString Z (type 1002) - what Open USRN really contains."""
    out = struct.pack("<BI", 1, 1002) + struct.pack("<I", len(points))
    for x, y, z in points:
        out += struct.pack("<3d", x, y, z)
    return out


def test_wkb_decoder_handles_iso_z_multilinestring():
    """Regression: real Open USRN geometries are MultiLineString Z (ISO 1005);
    misreading Z coordinates as 2D desyncs the stream and produced garbage
    type errors mid-collection."""
    child_a = wkb_linestring_z([(424000.5, 542000.25, 60.0), (424100.0, 542050.0, 61.5)])
    child_b = wkb_linestring_z([(424100.0, 542050.0, 61.5), (424200.0, 542100.0, 63.0)])
    multi_z = struct.pack("<BII", 1, 1005, 2) + child_a + child_b
    wkt = gpkg_geometry_to_wkt(gpkg_blob(multi_z))
    # Z is read correctly (keeping the stream aligned) and WKT emitted 2D
    assert wkt == (
        "MULTILINESTRING ((424000.5 542000.25, 424100 542050), (424100 542050, 424200 542100))"
    )


def test_wkb_decoder_handles_ewkb_z_and_zm():
    point_ewkb_z = struct.pack("<BI3d", 1, 0x80000001, 1.0, 2.0, 3.0)
    assert gpkg_geometry_to_wkt(gpkg_blob(point_ewkb_z)) == "POINT (1 2)"
    point_iso_zm = struct.pack("<BI4d", 1, 3001, 1.0, 2.0, 3.0, 4.0)
    assert gpkg_geometry_to_wkt(gpkg_blob(point_iso_zm)) == "POINT (1 2)"
