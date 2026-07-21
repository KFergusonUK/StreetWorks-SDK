"""Tests for streetworks.common.from_nwb.

``from_nwb`` never emits a Street - see the module's own docstring for the
"no synthetic streets" reasoning. Fixture is real Rijkswaterstaat WFS data
(tests/fixtures/nwb_wfs_harlingen.json) built earlier this session.
"""

import json
from pathlib import Path

from streetworks.common import Identifier, from_nwb
from streetworks.nwb.models import wegvak_from_feature

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "nwb_wfs_harlingen.json").read_text(encoding="utf-8")
)


def test_wegvak_becomes_a_segment_with_name_and_bag_orl_street_ref():
    # Contradicts the design brief's own assumption that Segment.names was
    # "BD TOPO only, so far" - NWB's stt_naam is real and populated here too.
    wegvak = wegvak_from_feature(FIXTURE["features"][0])
    segment = from_nwb(wegvak)

    assert segment.identifiers == (Identifier(scheme="wvk_id", value="314551046"),)
    assert segment.names[0].value == "Alexiastraat"
    assert segment.street_refs == (Identifier(scheme="bag_orl", value="0072300000319612"),)
    assert segment.street_type.code == "VP"
    assert segment.administrative_area == "Harlingen"
    assert segment.as_at is not None  # from real wvk_begdat


def test_wegvak_house_number_ranges_promote_to_address_ranges():
    wegvak = wegvak_from_feature(FIXTURE["features"][0])
    segment = from_nwb(wegvak)

    # Real fixture: hnrstrlnks="", hnrstrrhts="E", e_hnr_rhts=2, l_hnr_rhts=10
    # - so only the "rechts" (right) side produces a range.
    assert len(segment.address_ranges) == 1
    right = segment.address_ranges[0]
    assert right.side == "rechts"
    assert right.structure == "E"
    assert right.first == 2
    assert right.last == 10


def test_wegvak_without_bag_orl_has_no_street_refs():
    wegvak = wegvak_from_feature(FIXTURE["features"][0])
    from dataclasses import replace

    orphan = replace(wegvak, bag_orl=None)
    segment = from_nwb(orphan)
    assert segment.street_refs == ()  # never falls back to name matching
