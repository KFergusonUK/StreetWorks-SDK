"""Tests for the Via Lietuva (Lithuania) open-data roadworks adapter.

Fixtures are real trimmed CSV dumps from a live pull, 2026-07, licensed
CC BY 4.0: ``vialietuva_remontas.csv`` (5 real rows from the ``Remontas``
table - one with a real ``MULTILINESTRING`` path, one point-only, one with
no stated traffic-impact/description text, one open-ended (empty
``data_iki``), and the real, genuinely test-looking ``darbo_id=1`` row -
see ``models.py``'s own docstring for why that's left in, not filtered),
and ``vialietuva_kelio_atkarpa.csv`` (the 3 real ``KelioAtkarpa`` rows the
``Remontas`` fixture's ``kelio_id`` values join to).
"""

from pathlib import Path

import httpx
import respx

from streetworks.common import from_vialietuva
from streetworks.vialietuva import (
    TABLE_ROAD_REPAIRS,
    TABLE_ROAD_SECTIONS,
    ViaLietuvaClient,
    parse_road_repairs,
    parse_road_sections,
)
from streetworks.vialietuva.client import BASE_URL

FIXTURES = Path(__file__).parent / "fixtures"
REMONTAS_CSV = (FIXTURES / "vialietuva_remontas.csv").read_text(encoding="utf-8")
KELIO_ATKARPA_CSV = (FIXTURES / "vialietuva_kelio_atkarpa.csv").read_text(encoding="utf-8")


def test_parses_road_repairs():
    repairs = parse_road_repairs(REMONTAS_CSV)
    assert [r.work_id for r in repairs] == ["1", "10", "1314", "1457", "8191"]


def test_repair_with_real_multilinestring_geometry():
    repairs = parse_road_repairs(REMONTAS_CSV)
    repair = next(r for r in repairs if r.work_id == "1")
    assert repair.road_id == "1236"
    assert repair.direction == "PR"
    assert repair.geometry_wkt is not None
    assert repair.geometry_wkt.startswith("MULTILINESTRING")
    assert repair.from_point_wkt == "POINT (6061836 567621)"
    assert repair.coordinates_validated is True
    assert repair.traffic_allowed is False
    assert repair.impact == "Mažai svarbus"  # real diacritics round-trip


def test_repair_without_geometry_line_falls_back_to_point():
    repairs = parse_road_repairs(REMONTAS_CSV)
    repair = next(r for r in repairs if r.work_id == "10")
    assert repair.geometry_wkt is None
    assert repair.from_point_wkt == "POINT (6054291 570648)"
    assert "Viaduko remontas" in repair.description


def test_repair_with_missing_impact_and_description():
    repairs = parse_road_repairs(REMONTAS_CSV)
    repair = next(r for r in repairs if r.work_id == "1457")
    assert repair.impact is None
    assert repair.description is None or repair.description == ""


def test_repair_open_ended_end_date():
    repairs = parse_road_repairs(REMONTAS_CSV)
    repair = next(r for r in repairs if r.work_id == "8191")
    assert repair.start is not None
    assert repair.end is None


def test_parses_road_sections_and_joins_to_repairs():
    sections = parse_road_sections(KELIO_ATKARPA_CSV)
    repairs = parse_road_repairs(REMONTAS_CSV)
    for repair in repairs:
        assert repair.road_id in sections
    section = sections["1236"]
    assert section.number == "A1"
    assert section.name == "Vilnius–Kaunas–Klaipėda"  # real diacritics


def test_from_vialietuva_axis_order_is_northing_easting():
    repairs = parse_road_repairs(REMONTAS_CSV)
    repair = next(r for r in repairs if r.work_id == "1")
    works = from_vialietuva([repair])
    site = works[0].sites[0]
    # WKT states "POINT (6061836 567621)" - Lithuania's real northing range
    # is ~5,990,000-6,265,000, easting ~300,000-720,000, so the first
    # number is northing, the second easting - reversed from the usual
    # (easting, northing) WKT convention. See from_vialietuva's docstring.
    assert site.coordinate.value == (6061836.0, 567621.0)
    assert site.coordinate.crs == "EPSG:3346"
    assert site.coordinate.parts is not None  # real MULTILINESTRING kept whole


def test_from_vialietuva_point_only_repair_has_no_parts():
    repairs = parse_road_repairs(REMONTAS_CSV)
    repair = next(r for r in repairs if r.work_id == "10")
    works = from_vialietuva([repair])
    site = works[0].sites[0]
    assert site.coordinate.value == (6054291.0, 570648.0)
    assert site.coordinate.parts is None


def test_from_vialietuva_territory_and_authority():
    repairs = parse_road_repairs(REMONTAS_CSV)
    works = from_vialietuva(repairs)
    for w in works:
        assert w.territory == "Lithuania"
        assert w.administrative_area == "Via Lietuva"
        assert w.sites[0].works_type == "Remontas"


def test_from_vialietuva_date_confidence():
    repairs = parse_road_repairs(REMONTAS_CSV)
    works = from_vialietuva(repairs)
    for w in works:
        site = w.sites[0]
        if site.proposed_start is not None:
            assert site.date_confidence.value == "estimated"
        else:
            assert site.date_confidence.value == "unknown"


@respx.mock
def test_client_fetches_both_tables():
    respx.get(f"{BASE_URL}/datasets/gov/via_lietuva/eismo_ribojimai/{TABLE_ROAD_REPAIRS}/:format/csv").mock(
        return_value=httpx.Response(200, text=REMONTAS_CSV)
    )
    respx.get(f"{BASE_URL}/datasets/gov/via_lietuva/eismo_ribojimai/{TABLE_ROAD_SECTIONS}/:format/csv").mock(
        return_value=httpx.Response(200, text=KELIO_ATKARPA_CSV)
    )
    with ViaLietuvaClient() as lt:
        repairs = lt.road_repairs()
        sections = lt.road_sections()
    assert len(repairs) == 5
    assert len(sections) == 3
