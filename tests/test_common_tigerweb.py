"""Tests for streetworks.common.from_tigerweb.

Fixtures are real TIGERweb responses (tests/fixtures/tigerweb_*), a real
Washington DC bbox query and a real I-95 query, captured live this
session. TIGER/TIGERweb is US federal government work - public domain
(17 U.S.C. Sec. 105) - so real data is committed here, unlike Jersey.
"""

import json
from pathlib import Path

from streetworks.common import from_tigerweb

FIXTURES = Path(__file__).parent / "fixtures"


def _features(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["features"]


def test_real_local_road_becomes_a_segment_with_mtfcc_and_name():
    feature = _features("tigerweb_local_roads_dc.json")[0]
    segment = from_tigerweb(feature)

    assert segment.names[0].value == "D St NW"
    assert segment.street_type.code == "S1400"
    assert segment.street_type.label is None  # carried undecoded, no lookup table
    assert segment.geometry.crs == "EPSG:4326"
    assert segment.identifiers[0].scheme == "tiger_oid"


def test_tiger_oid_is_dataset_scoped_not_a_street_register_identifier():
    feature = _features("tigerweb_local_roads_dc.json")[0]
    segment = from_tigerweb(feature)
    identifier = segment.identifiers[0]
    assert identifier.value == feature["properties"]["OID"]
    # No scope set - this isn't a municipality-scoped id, it's a
    # dataset-scoped one; the scheme name itself carries that meaning.
    assert identifier.scope is None


def test_real_interstate_carries_s1100_mtfcc_and_rttyp_in_raw():
    feature = _features("tigerweb_primary_roads_i95.json")[0]
    segment = from_tigerweb(feature)

    assert segment.names[0].value == "I- 95"
    assert segment.street_type.code == "S1100"
    assert segment.raw["properties"]["RTTYP"] == "I"


def test_no_street_ever_produced_only_segment():
    # from_tigerweb has no Street-producing path at all - checked, not
    # assumed, see the module docstring: TIGERweb has no named-street
    # entity anywhere in the service.
    feature = _features("tigerweb_local_roads_dc.json")[0]
    segment = from_tigerweb(feature)
    assert type(segment).__name__ == "Segment"


def test_as_at_is_always_none_no_per_feature_date_field_exists():
    feature = _features("tigerweb_local_roads_dc.json")[0]
    segment = from_tigerweb(feature)
    assert segment.as_at is None


def test_unnamed_segment_has_no_names_but_still_converts():
    features = _features("tigerweb_local_roads_dc.json")
    unnamed = [f for f in features if not f["properties"].get("NAME")]
    if unnamed:
        segment = from_tigerweb(unnamed[0])
        assert segment.names == ()
