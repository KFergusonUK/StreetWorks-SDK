"""Tests for streetworks.common.from_autobahn.

Uses the same real trimmed A1/A61 fixtures as test_autobahn.py - notably
the five real records sharing works "2023-000045", split 3/2 across the
A1 and A61 API responses (a genuine junction project), which is exactly
what exercises the cross-road grouping this converter has to get right.
"""

import json
from pathlib import Path

from streetworks.autobahn.parser import parse_roadworks
from streetworks.common import from_autobahn

FIXTURES = Path(__file__).parent / "fixtures"
A1_PAYLOAD = json.loads((FIXTURES / "autobahn_a1_roadworks.json").read_text())
A61_PAYLOAD = json.loads((FIXTURES / "autobahn_a61_roadworks.json").read_text())


def test_from_autobahn_groups_across_roads_into_one_works():
    a1_items = parse_roadworks(A1_PAYLOAD, "A1")
    a61_items = parse_roadworks(A61_PAYLOAD, "A61")
    works_list = from_autobahn(a1_items + a61_items)

    junction_works = next(w for w in works_list if w.reference == "2023-000045")
    assert len(junction_works.sites) == 5  # 3 from A1 + 2 from A61
    assert junction_works.territory == "Germany"
    assert junction_works.administrative_area == "Autobahn GmbH"
    assert all(site.date_confidence.value == "verified" for site in junction_works.sites)

    # The unrelated singleton ROADWORKS record is its own Works.
    singleton = next(w for w in works_list if w.reference.startswith("2026-021338"))
    assert len(singleton.sites) == 1
    # Real LineString geometry survives all the way to Coordinate.points.
    assert singleton.coordinate.points is not None and len(singleton.coordinate.points) > 2


def test_from_autobahn_estimated_vs_unknown_confidence():
    items = parse_roadworks(A1_PAYLOAD, "A1")
    works_list = from_autobahn(items)
    by_ref = {s.reference: s for w in works_list for s in w.sites}

    # Short-term item whose date came from parsed text, not a real field.
    estimated = by_ref[next(i.identifier for i in items if "06-00-00-000.de3" in i.identifier)]
    assert estimated.date_confidence.value == "estimated"
    assert estimated.actual_start is None  # only a VERIFIED start ever populates actual_start

    # The genuinely-unparseable short-term item.
    unknown = by_ref[next(i.identifier for i in items if i.identifier.endswith("_001.de3"))]
    assert unknown.date_confidence.value == "unknown"
    assert unknown.proposed_start is None


def test_from_autobahn_verified_start_sets_actual_start():
    items = parse_roadworks(A1_PAYLOAD, "A1")
    works_list = from_autobahn(items)
    site = next(s for w in works_list for s in w.sites if s.reference.endswith("_003.de1"))
    assert site.date_confidence.value == "verified"
    assert site.actual_start == site.proposed_start
