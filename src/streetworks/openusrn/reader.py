"""Query the Open USRN GeoPackage with the standard library only.

A GeoPackage is a SQLite database following OGC conventions: the feature
table is registered in ``gpkg_contents``, its geometry column in
``gpkg_geometry_columns``, and each geometry is a small "GP" header followed
by standard WKB. That means :mod:`sqlite3` plus a compact WKB decoder is all
that's needed - no GDAL, GeoPandas, or other geospatial stack.

Geometries are in British National Grid (EPSG:27700) eastings/northings,
matching every other provider in this SDK.
"""

from __future__ import annotations

import sqlite3
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

__all__ = ["UsrnDatabase", "UsrnStreet", "gpkg_geometry_to_wkt"]


@dataclass(frozen=True)
class UsrnStreet:
    """One Open USRN feature: the USRN and its street geometry as WKT."""

    usrn: int
    geometry: str | None


# ---------------------------------------------------------------------------
# Minimal WKB -> WKT
# ---------------------------------------------------------------------------

_GEOM_NAMES = {1: "POINT", 2: "LINESTRING", 3: "POLYGON",
               4: "MULTIPOINT", 5: "MULTILINESTRING", 6: "MULTIPOLYGON",
               7: "GEOMETRYCOLLECTION"}


class _WkbReader:
    def __init__(self, data: bytes, offset: int = 0):
        self.data = data
        self.pos = offset

    def read(self, fmt: str) -> tuple:
        size = struct.calcsize(fmt)
        values = struct.unpack_from(fmt, self.data, self.pos)
        self.pos += size
        return values

    def geometry(self) -> str:
        (byte_order,) = self.read("B")
        endian = "<" if byte_order == 1 else ">"
        (raw_type,) = self.read(f"{endian}I")
        # Dimension flags come in two dialects: EWKB uses high bits
        # (0x80000000 = Z, 0x40000000 = M, 0x20000000 = embedded SRID),
        # ISO WKB adds 1000 (Z), 2000 (M) or 3000 (ZM) to the base type.
        has_z = bool(raw_type & 0x80000000)
        has_m = bool(raw_type & 0x40000000)
        if raw_type & 0x20000000:  # EWKB embedded SRID: skip it
            self.read(f"{endian}I")
        code = raw_type & 0x0FFFFFFF
        iso = code // 1000
        base = code % 1000
        if iso == 1:
            has_z = True
        elif iso == 2:
            has_m = True
        elif iso == 3:
            has_z = has_m = True
        dims = 2 + int(has_z) + int(has_m)
        name = _GEOM_NAMES.get(base)
        if name is None or iso > 3:
            raise ValueError(f"unsupported WKB geometry type {raw_type}")
        if base == 1:
            coords = self._point(endian, dims)
            return f"POINT ({coords})"
        if base == 2:
            return f"LINESTRING ({self._ring(endian, dims)})"
        if base == 3:
            return f"POLYGON ({self._rings(endian, dims)})"
        if base == 4:
            parts = self._collection(endian)
            inner = ", ".join(f"({p.split('(', 1)[1]}" for p in parts)
            return f"MULTIPOINT ({inner})"
        if base == 5:
            parts = self._collection(endian)
            inner = ", ".join(f"({p.split('(', 1)[1]}" for p in parts)
            return f"MULTILINESTRING ({inner})"
        if base == 6:
            parts = self._collection(endian)
            inner = ", ".join(f"({p.split('(', 1)[1]}" for p in parts)
            return f"MULTIPOLYGON ({inner})"
        parts = self._collection(endian)
        return f"GEOMETRYCOLLECTION ({', '.join(parts)})"

    def _point(self, endian: str, dims: int) -> str:
        values = self.read(f"{endian}{dims}d")
        return " ".join(_fmt(v) for v in values[:2])  # emit 2D WKT

    def _ring(self, endian: str, dims: int) -> str:
        (n,) = self.read(f"{endian}I")
        return ", ".join(self._point(endian, dims) for _ in range(n))

    def _rings(self, endian: str, dims: int) -> str:
        (n,) = self.read(f"{endian}I")
        return ", ".join(f"({self._ring(endian, dims)})" for _ in range(n))

    def _collection(self, endian: str) -> list[str]:
        (n,) = self.read(f"{endian}I")
        return [self.geometry() for _ in range(n)]


def _fmt(value: float) -> str:
    return f"{value:.10g}"


def gpkg_geometry_to_wkt(blob: bytes | None) -> str | None:
    """Decode a GeoPackage geometry blob (GP header + WKB) to WKT.

    Returns ``None`` for NULL/empty geometries. Z coordinates are read but
    WKT is emitted 2D, since street works usage is planar (EPSG:27700).
    """
    if not blob or len(blob) < 8 or blob[:2] != b"GP":
        return None
    flags = blob[3]
    if flags & 0b00100000:  # empty-geometry flag
        return None
    envelope_code = (flags >> 1) & 0b111
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    envelope = envelope_sizes.get(envelope_code)
    if envelope is None:
        return None
    return _WkbReader(blob, 8 + envelope).geometry()


# ---------------------------------------------------------------------------
# The database
# ---------------------------------------------------------------------------


class UsrnDatabase:
    """Open a (downloaded, extracted) Open USRN GeoPackage for lookups.

    The feature table and its columns are discovered from the GeoPackage
    metadata tables rather than hard-coded, so supply refreshes that rename
    the layer keep working.

    >>> with UsrnDatabase("osopenusrn.gpkg") as db:
    ...     street = db.get(33909869)
    ...     print(street.geometry[:40])
    """

    def __init__(self, path: str | Path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        # Immutable read-only open: safe for concurrent readers, no journal.
        self._conn = sqlite3.connect(f"file:{path}?immutable=1", uri=True)
        self.table, self.usrn_column, self.geometry_column = self._discover()

    def _discover(self) -> tuple[str, str, str]:
        row = self._conn.execute(
            "SELECT table_name FROM gpkg_contents WHERE data_type='features' LIMIT 1"
        ).fetchone()
        if row is None:
            raise ValueError("no feature table registered in gpkg_contents")
        table = row[0]
        geom = self._conn.execute(
            "SELECT column_name FROM gpkg_geometry_columns WHERE table_name=?",
            (table,),
        ).fetchone()
        geometry_column = geom[0] if geom else "geometry"
        columns = [r[1] for r in self._conn.execute(f'PRAGMA table_info("{table}")')]
        usrn_column = next((c for c in columns if c.lower() == "usrn"), None)
        if usrn_column is None:
            raise ValueError(f"no USRN column found in {table!r} (columns: {columns})")
        return table, usrn_column, geometry_column

    def count(self) -> int:
        """Total number of USRNs in the file."""
        return self._conn.execute(f'SELECT COUNT(*) FROM "{self.table}"').fetchone()[0]

    def get(self, usrn: int | str) -> UsrnStreet | None:
        """Look up one USRN; ``None`` if not present."""
        row = self._conn.execute(
            f'SELECT "{self.usrn_column}", "{self.geometry_column}" '
            f'FROM "{self.table}" WHERE "{self.usrn_column}" = ?',
            (int(usrn),),
        ).fetchone()
        if row is None:
            return None
        return UsrnStreet(usrn=int(row[0]), geometry=gpkg_geometry_to_wkt(row[1]))

    def iter_streets(self, *, limit: int | None = None) -> Iterator[UsrnStreet]:
        """Iterate USRN features (optionally limited)."""
        sql = (
            f'SELECT "{self.usrn_column}", "{self.geometry_column}" '
            f'FROM "{self.table}"'
        )
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        for row in self._conn.execute(sql):
            yield UsrnStreet(usrn=int(row[0]), geometry=gpkg_geometry_to_wkt(row[1]))

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> UsrnDatabase:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
