"""Tests for streetworks.common.from_wzdx.

Covers the four real-feed fixtures shared with test_wzdx.py (thin Works,
both date-confidence encodings, the VERIFIED/ESTIMATED split, non-work-zone
events skipped) plus an explicit cross-converter check: from_wzdx and
from_datex2 must produce EPSG:4326 Coordinate.value in the *same* axis
order for the same real-world point, since from_wzdx's native GeoJSON
(longitude, latitude) has to be flipped to match from_datex2's
(latitude, longitude) - getting that flip wrong would silently corrupt
every WZDx coordinate without either converter's own tests noticing.
"""

import json
from pathlib import Path

from streetworks.common import DateConfidence, SourceGrade, from_datex2, from_wzdx
from streetworks.datex2.models import Location, Situation, SituationRecord, Validity
from streetworks.wzdx.models import Geometry, RoadEvent
from streetworks.wzdx.parser import parse_road_events


def _fixture(name: str) -> dict:
    return json.loads(
        (Path(__file__).parent / "fixtures" / f"wzdx_{name}.json").read_text(encoding="utf-8")
    )


def test_coordinate_axis_order_matches_from_datex2_for_the_same_point():
    # A real Boston-area point: latitude ~42.5 (north), longitude ~-71.5
    # (west) - the two values are far enough apart that a missed/extra flip
    # is unmistakable in the assertion, not just a sign-coincidence.
    lat, lon = 42.5, -71.5

    wzdx_event = RoadEvent(
        id="wz-1",
        event_type="work-zone",
        geometry=Geometry(kind="Point", points=((lon, lat),)),  # native GeoJSON (lon, lat)
    )
    wzdx_coordinate = from_wzdx([wzdx_event])[0].coordinate

    datex_situation = Situation(
        id="sit-1",
        records=[
            SituationRecord(
                id="rec-1",
                record_type="MaintenanceWorks",
                validity=Validity(),
                location=Location(points=((lat, lon),)),  # native DATEX (lat, lon)
            )
        ],
    )
    datex_coordinate = from_datex2(datex_situation).coordinate

    assert wzdx_coordinate is not None and datex_coordinate is not None
    assert wzdx_coordinate.crs == datex_coordinate.crs == "EPSG:4326"
    assert wzdx_coordinate.value == datex_coordinate.value == (lat, lon)


def test_from_wzdx_skips_non_work_zone_events():
    events = parse_road_events(_fixture("quebec"))
    assert any(e.event_type == "detour" for e in events)  # fixture has one
    works_list = from_wzdx(events)
    all_sites = [s for w in works_list for s in w.sites]
    assert all(s.works_type != "detour" for s in all_sites)
    assert len(works_list) == 2  # only the two work-zone events convert


def test_from_wzdx_thin_works_since_no_works_ref_observed():
    events = parse_road_events(_fixture("hidot"))
    works_list = from_wzdx(events)
    assert len(works_list) == 2
    assert all(w.reference is None for w in works_list)  # no works_ref in this feed
    assert all(len(w.sites) == 1 for w in works_list)
    assert all(s.source_grade is SourceGrade.OPERATOR for w in works_list for s in w.sites)


def test_from_wzdx_date_confidence_prefers_accuracy_enum_over_boolean():
    events = parse_road_events(_fixture("wsdot"))
    works_list = from_wzdx(events)
    site = works_list[0].sites[0]
    # start_date_accuracy="verified" AND is_start_date_verified=True agree
    # here, but the mapping should be driven by the accuracy enum per the
    # stated preference order.
    assert site.date_confidence is DateConfidence.VERIFIED
    assert site.actual_start == site.proposed_start


def test_from_wzdx_boolean_only_feed_maps_false_to_estimated():
    events = parse_road_events(_fixture("hidot"))
    works_list = from_wzdx(events)
    site = works_list[0].sites[0]
    assert site.date_confidence is DateConfidence.ESTIMATED  # is_start_date_verified=False
    assert site.actual_start is None
