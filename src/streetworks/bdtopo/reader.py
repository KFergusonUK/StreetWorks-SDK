"""Read a BD TOPO GeoPackage with the standard library only - reusing
:mod:`streetworks.openusrn.reader`'s GeoPackage machinery (the "GP"-header
WKB decoder, ``gpkg_geometry_to_wkt``), the same way
:mod:`streetworks.bag.reader`/:mod:`streetworks.nwb.reader` do.

**This reader was not verified against a real downloaded file** - a real
gap, not an oversight, see the package docstring for the live investigation
into IGN's bulk-download route (`geoservices.ign.fr/telechargement`,
`cartes.gouv.fr`, `wxs.ign.fr`, and the WFS's own output-format list were
all checked; none yielded an automatable, unauthenticated download path).
Table/column names here follow IGN's own naming convention exactly as
confirmed live via the WFS (`troncon_de_route`, `voie_nommee`, and every
field name in :mod:`streetworks.bdtopo.models`) - IGN's WFS and GeoPackage
exports are documented as generated from the same underlying data model,
so this is a reasonable inference, not a guess, but it is explicitly an
inference: if you have a real BD TOPO GeoPackage and its table/column
names differ from what's here, that's a real finding worth reporting back,
not this reader silently failing.

Like :mod:`streetworks.bag.reader`, this is a thin, table-name-agnostic
browser over whatever tables a real GeoPackage actually contains (BD TOPO
is IGN's *entire* topographic database - buildings, hydrography,
vegetation, transport, and more, all in one file - so a real download
holds many more tables than just the transport theme; this SDK only reads
the two named in the design brief, `troncon_de_route` and `voie_nommee`
via :meth:`BDTopoDatabase.iter_troncons`/:meth:`iter_voies_nommees`, but
:meth:`BDTopoDatabase.iter_features` will read any table by name).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ..openusrn.reader import gpkg_geometry_to_wkt
from .models import Troncon, VoieNommee, troncon_from_properties, voie_nommee_from_properties

__all__ = ["BDTopoDatabase", "BDTopoFeature", "TableInfo"]


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
class BDTopoFeature:
    """One row from any BD TOPO GeoPackage table - every column preserved
    in ``.raw``, plus decoded WKT geometry if the table has one."""

    table: str
    geometry: str | None
    raw: dict


class BDTopoDatabase:
    """Open a BD TOPO GeoPackage (obtained manually - see the module
    docstring) for table-by-table reading. Reads the transport theme only
    via the typed methods; the file itself holds BD TOPO's other themes
    too (buildings, hydrography, ...), reachable generically via
    :meth:`iter_features` but not modelled by this SDK.

    >>> with BDTopoDatabase("BDTOPO.gpkg") as db:
    ...     for info in db.tables():
    ...         print(info.table, info.geometry_type)
    ...     for troncon in db.iter_troncons(limit=5):
    ...         print(troncon.nom_voie_ban_gauche, troncon.toponyme_id_gauche())
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

    def iter_features(self, table: str, *, limit: int | None = None) -> Iterator[BDTopoFeature]:
        """Stream every row of one table (any real table BD TOPO's
        GeoPackage holds) as a :class:`BDTopoFeature`."""
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
            yield BDTopoFeature(table=table, geometry=geometry, raw=values)

    def iter_troncons(self, *, limit: int | None = None) -> Iterator[Troncon]:
        """Stream ``troncon_de_route`` as typed
        :class:`~streetworks.bdtopo.models.Troncon` records."""
        for feature in self.iter_features("troncon_de_route", limit=limit):
            props = {k: v for k, v in feature.raw.items() if k != "geom"}
            yield troncon_from_properties(props, geometry=feature.geometry)

    def iter_voies_nommees(self, *, limit: int | None = None) -> Iterator[VoieNommee]:
        """Stream ``voie_nommee`` as typed
        :class:`~streetworks.bdtopo.models.VoieNommee` records."""
        for feature in self.iter_features("voie_nommee", limit=limit):
            props = {k: v for k, v in feature.raw.items() if k != "geom"}
            yield voie_nommee_from_properties(props, geometry=feature.geometry)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> BDTopoDatabase:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
