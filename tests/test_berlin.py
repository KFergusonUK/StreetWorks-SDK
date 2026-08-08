"""Tests for the Berlin VIZ adapter.

Credential-free, live-verified from day one - see the module docstring
in ``streetworks.berlin.client``. ``berlin_baustellen_live_pull.json``
holds 5 REAL records from a real, unauthenticated pull (2026-08-08): a
genuine matched pair (the same real worksite, Landesmeldestelle
``LMS-BR/r_LMS-BR/416895_LMS-BR/72`` and Verkehrsredaktion ``731/2026``,
linked via the real ``lms_id`` join key), a Landesmeldestelle-only
Baustelle (``330651``, with a blank ``validity.from`` - a real, common
case), a Verkehrsredaktion-only Sperrung with no ``lms_id`` at all
(``44/2025``), and a real ``Gefahr`` hazard-warning record (``380591``,
deliberately excluded from the roadworks filter) - not synthetic.
LineString vertex lists are trimmed for fixture size, coordinates are
real.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from streetworks.berlin import LANDESMELDESTELLE_URL, VERKEHRSREDAKTION_URL, BerlinClient
from streetworks.common import from_berlin
from streetworks.common.models import DateConfidence, SourceGrade

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "berlin_baustellen_live_pull.json"
RECORDS = json.loads(FIXTURE_PATH.read_text())

# Split the fixture the way the two real feeds actually shape it -
# Verkehrsredaktion records carry a "lms_id" key (even if null),
# Landesmeldestelle records never do.
LMS_RECORDS = [r for r in RECORDS if "lms_id" not in r["properties"]]
VIZ_RECORDS = [r for r in RECORDS if "lms_id" in r["properties"]]


def _by_id(records: list[dict], record_id: str) -> dict:
    return next(r for r in records if r["properties"]["id"] == record_id)


def _envelope(records: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": records}


def _mock_both_feeds() -> None:
    respx.get(LANDESMELDESTELLE_URL).mock(
        return_value=httpx.Response(200, json=_envelope(LMS_RECORDS))
    )
    respx.get(VERKEHRSREDAKTION_URL).mock(
        return_value=httpx.Response(200, json=_envelope(VIZ_RECORDS))
    )


# --------------------------------------------------------------------------- #
# Client wiring - credential-free
# --------------------------------------------------------------------------- #


@respx.mock
def test_iter_landesmeldestelle_needs_no_credentials_and_is_unfiltered():
    respx.get(LANDESMELDESTELLE_URL).mock(
        return_value=httpx.Response(200, json=_envelope(LMS_RECORDS))
    )
    with BerlinClient() as berlin:
        records = list(berlin.iter_landesmeldestelle())
    assert len(records) == len(LMS_RECORDS)  # includes the Gefahr record - unfiltered


@respx.mock
def test_iter_verkehrsredaktion_needs_no_credentials_and_is_unfiltered():
    respx.get(VERKEHRSREDAKTION_URL).mock(
        return_value=httpx.Response(200, json=_envelope(VIZ_RECORDS))
    )
    with BerlinClient() as berlin:
        records = list(berlin.iter_verkehrsredaktion())
    assert len(records) == len(VIZ_RECORDS)


@respx.mock
def test_iter_roadworks_merges_a_real_matched_pair_via_the_join_key():
    _mock_both_feeds()
    with BerlinClient() as berlin:
        records = list(berlin.iter_roadworks())

    matched = _by_id(records, "LMS-BR/r_LMS-BR/416895_LMS-BR/72")
    assert sorted(matched["properties"]["sources"]) == ["landesmeldestelle", "verkehrsredaktion"]
    assert matched["properties"]["viz_id"] == "731/2026"
    # Prefers Verkehrsredaktion's richer fields on a match.
    assert matched["properties"]["severity"] == "Vollsperrung"
    assert matched["properties"]["total_lanes"] == 2


@respx.mock
def test_iter_roadworks_keeps_unmatched_records_from_both_sides():
    _mock_both_feeds()
    with BerlinClient() as berlin:
        records = list(berlin.iter_roadworks())

    lms_only = _by_id(records, "LMS-BR/r_LMS-BR/330651_LMS-BR/72")
    assert lms_only["properties"]["sources"] == ["landesmeldestelle"]

    viz_only = _by_id(records, "44/2025")
    assert viz_only["properties"]["sources"] == ["verkehrsredaktion"]


@respx.mock
def test_iter_roadworks_excludes_gefahr():
    _mock_both_feeds()
    with BerlinClient() as berlin:
        records = list(berlin.iter_roadworks())
    ids = {r["properties"]["id"] for r in records}
    assert "LMS-BR/r_LMS-BR/380591_LMS-BR/72" not in ids
    # 2 raw roadworks records (416895 lms + 731/2026 viz) merge into 1 +
    # 1 lms-only + 1 viz-only = 3, Gefahr excluded.
    assert len(records) == 3


def test_client_requires_no_credentials():
    BerlinClient()


# --------------------------------------------------------------------------- #
# Converter - no grouping, 1:1
# --------------------------------------------------------------------------- #


def test_from_berlin_produces_one_works_per_record_no_grouping():
    works_list = from_berlin(RECORDS)
    assert len(works_list) == len(RECORDS)
    assert all(len(w.sites) == 1 for w in works_list)
    assert all(w.territory == "Germany" for w in works_list)
    assert all(w.source_grade == SourceGrade.TRAVELLER_INFO for w in works_list)


def test_from_berlin_point_geometry():
    works_list = from_berlin([_by_id(RECORDS, "LMS-BR/r_LMS-BR/330651_LMS-BR/72")])
    coord = works_list[0].sites[0].coordinate
    assert coord.crs == "EPSG:4326"
    assert coord.value == (52.55223, 13.3814)
    assert coord.points is None


def test_from_berlin_geometry_collection_captures_linestring_points():
    works_list = from_berlin([_by_id(RECORDS, "44/2025")])
    coord = works_list[0].sites[0].coordinate
    assert coord.value == (52.40220940824191, 13.554468154907228)
    assert coord.points is not None
    assert len(coord.points) > 1


def test_from_berlin_street_ref_is_never_populated():
    works_list = from_berlin(RECORDS)
    assert all(s.street_ref is None for w in works_list for s in w.sites)


def test_from_berlin_date_confidence_is_always_estimated():
    works_list = from_berlin(RECORDS)
    for w in works_list:
        for site in w.sites:
            assert site.date_confidence is DateConfidence.ESTIMATED
            assert site.actual_start is None
            assert site.actual_end is None


def test_from_berlin_parses_iso_dates_verkehrsredaktion_style():
    works_list = from_berlin([_by_id(RECORDS, "44/2025")])
    site = works_list[0].sites[0]
    assert site.proposed_start is not None
    assert site.proposed_start.year == 2025
    assert site.proposed_end is not None


def test_from_berlin_parses_german_dates_landesmeldestelle_style():
    works_list = from_berlin([_by_id(RECORDS, "LMS-BR/r_LMS-BR/330651_LMS-BR/72")])
    site = works_list[0].sites[0]
    assert site.proposed_start is None  # blank "from" - a real, common case
    assert site.proposed_end is not None
    assert site.proposed_end.year == 2026
    assert site.proposed_end.month == 12


def test_from_berlin_gefahr_still_converts_when_passed_directly():
    """from_berlin() itself never filters by subtype - only
    BerlinClient.iter_roadworks() does. A caller who fetches a Gefahr
    record explicitly still gets a real Works back, not a silent drop."""
    works_list = from_berlin([_by_id(RECORDS, "LMS-BR/r_LMS-BR/380591_LMS-BR/72")])
    assert len(works_list) == 1


def test_from_berlin_traffic_management_carries_severity():
    works_list = from_berlin([_by_id(RECORDS, "44/2025")])
    assert works_list[0].sites[0].traffic_management == "Fahrtrichtungssperrung"
