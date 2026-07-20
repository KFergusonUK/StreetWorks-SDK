"""Read the NWB GeoPackage with the standard library only - reusing
:mod:`streetworks.openusrn.reader`'s GeoPackage machinery (the "GP"-header
WKB decoder, ``gpkg_geometry_to_wkt``), the same way
:mod:`streetworks.bag.reader` does.

Confirmed live against the real national file: it holds **two** tables,
``wegvakken`` (1,638,814 rows - road segments, this module's primary
target) and ``hectopunten`` (161,893 rows - hectometre points, each
referencing a wegvak by ``wvk_id``; noted in
:mod:`streetworks.nwb.models`'s module docstring, not modelled as its own
type here, but reachable through :class:`NWBDatabase`'s generic,
table-name-agnostic interface like any other table). Both counts match
the live WFS `resultType=hits` figures exactly.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ..openusrn.reader import gpkg_geometry_to_wkt
from .models import Wegvak, wegvak_from_row

__all__ = ["NWBDatabase", "NWBFeature", "TableInfo"]


@dataclass(frozen=True)
class TableInfo:
    """One GeoPackage table, as registered in ``gpkg_contents``."""

    table: str
    identifier: str | None
    data_type: str
    geometry_column: str | None
    geometry_type: str | None
    srs_id: int | None


@dataclass(frozen=True)
class NWBFeature:
    """One row from any NWB GeoPackage table - every column preserved in
    ``.raw``, plus decoded WKT geometry if the table has one."""

    table: str
    geometry: str | None
    raw: dict


class NWBDatabase:
    """Open a downloaded ``nwb_wegen.gpkg`` for table-by-table reading.

    >>> with NWBDatabase("nwb_wegen.gpkg") as db:
    ...     for info in db.tables():
    ...         print(info.table, info.geometry_type)
    ...     for wegvak in db.iter_wegvakken(limit=5):
    ...         print(wegvak.stt_naam, wegvak.toponyme_id())
    """

    def __init__(self, path: str | Path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        self._conn = sqlite3.connect(f"file:{path}?immutable=1", uri=True)

    def tables(self) -> list[TableInfo]:
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
        return self._conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

    def iter_features(self, table: str, *, limit: int | None = None) -> Iterator[NWBFeature]:
        """Stream every row of one table (any real table - ``wegvakken``,
        ``hectopunten``, or one this SDK hasn't named) as an
        :class:`NWBFeature`."""
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
            yield NWBFeature(table=table, geometry=geometry, raw=values)

    def iter_wegvakken(self, *, limit: int | None = None) -> Iterator[Wegvak]:
        """Stream ``wegvakken`` as typed :class:`~streetworks.nwb.models.Wegvak`
        records - a thin, typed wrapper over :meth:`iter_features`."""
        for feature in self.iter_features("wegvakken", limit=limit):
            yield wegvak_from_row(feature.raw, geometry=feature.geometry)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> NWBDatabase:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
