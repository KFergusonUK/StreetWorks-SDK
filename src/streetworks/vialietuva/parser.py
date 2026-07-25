"""CSV parser for Via Lietuva's open roadworks data (data.gov.lt).

Each table is served as a complete CSV dump (no pagination on the
``:format/csv`` route - confirmed live, one request returns every row),
UTF-8, with a real ``charset=utf-8`` on ``Content-Type`` - Lithuanian
diacritics (``ą č ę ė į š ų ū ž``) round-trip cleanly, confirmed against
real ``aprasymas``/``pavadinimas`` text.
"""

from __future__ import annotations

import csv
import io

from .._dt import parse_iso8601 as _dt
from .models import RoadRepair, RoadSection

__all__ = ["parse_road_repairs", "parse_road_sections"]


def _bool(value: str) -> bool | None:
    if value == "True":
        return True
    if value == "False":
        return False
    return None


def _float(value: str) -> float | None:
    return float(value) if value else None


def parse_road_repairs(csv_text: str) -> list[RoadRepair]:
    """Parse a real ``Remontas`` CSV dump into :class:`~.models.RoadRepair`
    rows."""
    reader = csv.DictReader(io.StringIO(csv_text))
    repairs = []
    for row in reader:
        repairs.append(
            RoadRepair(
                work_id=row["darbo_id"],
                road_id=row["kelio_id"],
                direction=row["eismo_kryptis"] or None,
                km_from=_float(row["km_nuo"]),
                km_to=_float(row["km_iki"]),
                from_point_wkt=row["nuo_koord_lks"] or None,
                to_point_wkt=row["iki_koord_lks"] or None,
                geometry_wkt=row["geometrija"] or None,
                coordinates_validated=_bool(row["koord_validacija"]),
                start=_dt(row["data_nuo"] or None),
                end=_dt(row["data_iki"] or None),
                traffic_allowed=_bool(row["eismas_leidziamas"]),
                impact=row["poveikis_eismui"] or None,
                description=row["aprasymas"] or None,
                raw=dict(row),
            )
        )
    return repairs


def parse_road_sections(csv_text: str) -> dict[str, RoadSection]:
    """Parse a real ``KelioAtkarpa`` CSV dump into
    :class:`~.models.RoadSection`, keyed by ``road_id`` (confirmed live:
    unique per row - 10,284 rows, 10,284 distinct ``kelio_id`` values)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    sections: dict[str, RoadSection] = {}
    for row in reader:
        sections[row["kelio_id"]] = RoadSection(
            road_id=row["kelio_id"],
            number=row["numeris"] or None,
            name=row["pavadinimas"] or None,
            km_from=_float(row["km_nuo"]),
            km_to=_float(row["km_iki"]),
            raw=dict(row),
        )
    return sections
