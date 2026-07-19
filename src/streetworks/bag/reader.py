"""Read the BAG GeoPackage with the standard library only - reusing
:mod:`streetworks.openusrn.reader`'s GeoPackage machinery (the "GP"-header
WKB decoder, ``gpkg_geometry_to_wkt``) rather than duplicating it, per the
design brief.

Unlike Open USRN's GeoPackage (one feature table), BAG's carries **several**
- one per object type that has a geometry (see :mod:`streetworks.bag.models`
for which ones, confirmed against the real national file), plus
``gpkg_contents``/``gpkg_geometry_columns`` metadata tables the GeoPackage
spec itself defines. :class:`BAGDatabase` is a thin, table-name-agnostic
browser over whatever tables the real file actually contains, discovered
from that metadata - not a hardcoded single-table reader like Open USRN's,
because BAG genuinely isn't single-table.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ..openusrn.reader import gpkg_geometry_to_wkt

__all__ = ["BAGDatabase", "BAGFeature", "TableInfo"]


@dataclass(frozen=True)
class TableInfo:
    """One GeoPackage table, as registered in ``gpkg_contents`` - a BAG
    object type (e.g. ``openbareruimte``, ``pand``) if it has features, or
    an attribute-only table if it has no geometry column."""

    table: str
    identifier: str | None  # gpkg_contents.identifier - BAG's own name for it
    data_type: str  # "features" or "attributes"
    geometry_column: str | None
    geometry_type: str | None
    srs_id: int | None


@dataclass(frozen=True)
class BAGFeature:
    """One row from a BAG GeoPackage table - every column preserved in
    ``.raw`` (BAG's own field names are Dutch and kept as-is - see the
    models module docstring), plus decoded WKT geometry if the table has
    a geometry column at all."""

    table: str
    geometry: str | None
    raw: dict


class BAGDatabase:
    """Open a downloaded ``bag-light.gpkg`` for table-by-table reading.

    >>> with BAGDatabase("bag-light.gpkg") as db:
    ...     for info in db.tables():
    ...         print(info.table, info.data_type, info.geometry_type)
    ...     for feature in db.iter_features("openbareruimte", limit=5):
    ...         print(feature.raw["naam"], feature.geometry)
    """

    def __init__(self, path: str | Path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        # Immutable read-only open: safe for concurrent readers, no journal -
        # same rationale as streetworks.openusrn.reader.UsrnDatabase.
        self._conn = sqlite3.connect(f"file:{path}?immutable=1", uri=True)

    def tables(self) -> list[TableInfo]:
        """Every table registered in ``gpkg_contents`` - the GeoPackage's
        own inventory, not a guess at BAG's object model."""
        rows = self._conn.execute(
            "SELECT c.table_name, c.identifier, c.data_type, "
            "g.column_name, g.geometry_type_name, g.srs_id "
            "FROM gpkg_contents c "
            "LEFT JOIN gpkg_geometry_columns g ON g.table_name = c.table_name "
            "ORDER BY c.table_name"
        ).fetchall()
        return [
            TableInfo(
                table=r[0],
                identifier=r[1],
                data_type=r[2],
                geometry_column=r[3],
                geometry_type=r[4],
                srs_id=r[5],
            )
            for r in rows
        ]

    def _columns(self, table: str) -> list[str]:
        return [r[1] for r in self._conn.execute(f'PRAGMA table_info("{table}")')]

    def count(self, table: str) -> int:
        """Row count for one table."""
        return self._conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

    def iter_features(self, table: str, *, limit: int | None = None) -> Iterator[BAGFeature]:
        """Stream every row of one table as a :class:`BAGFeature`."""
        info = next((t for t in self.tables() if t.table == table), None)
        if info is None:
            raise ValueError(f"no such table {table!r} in this GeoPackage")
        columns = self._columns(table)
        quoted_columns = ", ".join(f'"{c}"' for c in columns)
        sql = f'SELECT {quoted_columns} FROM "{table}"'
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        for row in self._conn.execute(sql):
            values = dict(zip(columns, row, strict=True))
            geometry = None
            if info.geometry_column and info.geometry_column in values:
                geometry = gpkg_geometry_to_wkt(values[info.geometry_column])
                values = {**values, info.geometry_column: geometry}
            yield BAGFeature(table=table, geometry=geometry, raw=values)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> BAGDatabase:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
