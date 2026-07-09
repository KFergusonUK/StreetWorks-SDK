"""Tests for streetworks.common.from_trafficwatchni / from_trafficwales.

Both providers are traveller-information RSS feeds, not works registers, so
their converters are thin: one Works wrapping exactly one WorksSite, and
date_confidence is always UNKNOWN - reuses the same real fixture content as
test_rss_providers.py.
"""

from datetime import date
from pathlib import Path

from streetworks.common import DateConfidence, SourceGrade, from_trafficwales, from_trafficwatchni
from streetworks.trafficwales import parse_feed as parse_wales
from streetworks.trafficwatchni import parse_feed as parse_ni

NI_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Trafficwatch NI Current Roadworks</title>
  <item>
    <title>Lane closure, , Malone Road, Belfast</title>
    <description>Road closure required to facilitate work by BT Openreach
      Closure to operate: Daily 09:30 to 16:30 from Thu 19 Mar 2026 to: Thu
      19 Mar 2026 Diversion to operate, delays expected. Alternative Route
      Via: Lisburn Road.</description>
    <link>https://www.trafficwatchni.com/twni/roadworks/12345</link>
    <pubDate>Wed, 18 Mar 2026 09:00:00 GMT</pubDate>
    <guid>twni-12345</guid>
  </item>
</channel></rss>"""

WALES_RSS = (Path(__file__).parent / "fixtures" / "trafficwales_roadworks.xml").read_text(
    encoding="utf-8"
)


def test_from_trafficwatchni_wraps_one_site_with_unknown_confidence():
    item = parse_ni(NI_RSS)[0]
    works = from_trafficwatchni(item)

    assert works.source_grade is SourceGrade.TRAVELLER_INFO
    assert works.promoter == "BT Openreach"
    assert works.coordinate is None  # NI's feed carries no geometry
    assert len(works.sites) == 1

    site = works.sites[0]
    assert site.works_type == "Lane Closure"
    assert site.location_description == "Malone Road, Belfast"
    assert site.proposed_start.date() == date(2026, 3, 19)
    assert site.proposed_end.date() == date(2026, 3, 19)
    assert site.date_confidence is DateConfidence.UNKNOWN
    assert site.traffic_management == "Diversion in place"
    assert site.raw is item
    assert works.raw is item


def test_from_trafficwales_wraps_one_site_with_coordinate():
    item = parse_wales(WALES_RSS)[0]
    works = from_trafficwales(item)

    assert works.source_grade is SourceGrade.TRAVELLER_INFO
    assert works.promoter == "Welsh Government"
    assert works.coordinate is not None
    assert works.coordinate.crs == "EPSG:4326"
    assert works.coordinate.value == (51.78344, -2.939548)

    site = works.sites[0]
    assert site.works_type == "Resurfacing work"
    assert site.location_description == "A40, Eastbound, Raglan to Abergavenny Hardwick R/bout"
    assert site.proposed_start.isoformat() == "2026-07-15T20:00:00"
    assert site.proposed_end.isoformat() == "2026-07-16T06:00:00"
    assert site.date_confidence is DateConfidence.UNKNOWN
    assert site.operating_window == "15/07/26-16/07/26 2000-0600"
    assert site.traffic_management == "Road closed : Diversions in place - Road closure"


def test_from_trafficwales_item_missing_work_type_still_converts():
    item = parse_wales(WALES_RSS)[1]  # the "missing work-type segment" item
    works = from_trafficwales(item)
    site = works.sites[0]
    assert site.works_type is None
    assert site.traffic_management == "Lanes closed - Moderate"
