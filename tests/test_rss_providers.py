"""Tests for the TrafficWatchNI and Traffic Wales RSS providers.

Both fixtures' item text is taken from real observed feed content: NI from
prior smoke-testing, Wales from a live fetch of
https://traffic.wales/feeds/roadworks/rss.xml (2026-07-08) - chosen to cover
the parser's real edge cases: a normal work-type-then-restriction title, one
missing the work-type segment entirely, one where restriction and work type
appear in the *reverse* of the usual order ("Lanes closed : Environmental
work"), and one with an empty leading (road) segment.
"""

from datetime import date, datetime
from pathlib import Path

import httpx
import respx

from streetworks.trafficwales import Feed as WalesFeed
from streetworks.trafficwales import Language, TrafficWalesClient
from streetworks.trafficwales import parse_feed as parse_wales
from streetworks.trafficwatchni import Feed, Region, TrafficWatchNIClient
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
  <item>
    <title>Footway closure, , Antrim Road, Glengormley</title>
    <description>Footway closure to facilitate works by NI Water from Mon 23
      Mar 2026 to: Fri 27 Mar 2026. Traffic control in operation.</description>
    <link>https://www.trafficwatchni.com/twni/roadworks/12346</link>
    <pubDate>Wed, 18 Mar 2026 09:00:00 GMT</pubDate>
    <guid>twni-12346</guid>
  </item>
</channel></rss>"""


def test_ni_parses_and_extracts_real_item_shape():
    items = parse_ni(NI_RSS)
    assert len(items) == 2
    first = items[0]
    # Raw text always preserved
    assert first.title.startswith("Lane closure")
    assert "BT Openreach" in first.description
    # Best-effort extractions. The real data is contradictory here (title
    # says lane closure, description prose says "Road closure required...");
    # the title segment is TWNI's deliberate classification, so it wins.
    assert first.closure_type == "Lane Closure"
    assert first.promoter == "BT Openreach"
    assert first.start_date == date(2026, 3, 19)
    assert first.end_date == date(2026, 3, 19)
    assert first.operating_times == "Daily 09:30 to 16:30"
    assert first.diversion is True
    assert first.road == "Malone Road"
    assert first.town == "Belfast"
    assert first.link and "trafficwatchni.com" in first.link  # URL preserved

    second = items[1]
    assert second.closure_type == "Footway Closure"
    assert second.promoter == "NI Water"
    assert second.start_date == date(2026, 3, 23)
    assert second.end_date == date(2026, 3, 27)
    assert second.traffic_control is True
    assert second.road == "Antrim Road" and second.town == "Glengormley"


def test_ni_feed_urls():
    with TrafficWatchNIClient() as twni:
        assert twni.feed_url(Feed.ROADWORKS) == (
            "https://rss.trafficwatchni.com/trafficwatchni_roadworks_rss.xml"
        )
        assert twni.feed_url(Feed.INCIDENTS, Region.BELFAST) == (
            "https://rss.trafficwatchni.com/trafficwatchni_incidents_belfast_rss.xml"
        )


@respx.mock
def test_ni_client_fetches_and_parses():
    respx.get(
        "https://rss.trafficwatchni.com/trafficwatchni_roadworks_rss.xml"
    ).mock(return_value=httpx.Response(200, content=NI_RSS.encode()))
    with TrafficWatchNIClient() as twni:
        items = twni.fetch()
    assert len(items) == 2 and items[0].promoter == "BT Openreach"


WALES_RSS = (Path(__file__).parent / "fixtures" / "trafficwales_roadworks.xml").read_text(
    encoding="utf-8"
)


def test_wales_parses_full_item_with_work_type_and_restriction():
    items = parse_wales(WALES_RSS)
    assert len(items) == 4
    item = items[0]
    assert item.roads == ("A40",)
    assert item.link and "traffic.wales" in item.link
    assert item.guid == "RNMDA_2026130475"
    assert item.coordinate == (51.78344, -2.939548)
    assert item.road == "A40"
    assert item.direction == "Eastbound"
    assert item.location_from_to == "Raglan to Abergavenny Hardwick R/bout"
    assert item.work_type == "Resurfacing work"
    assert item.restriction == "Road closed : Diversions in place"
    assert item.severity == "Road closure"
    assert item.source == "Welsh Government"
    assert item.start == datetime(2026, 7, 15, 20, 0)
    assert item.end == datetime(2026, 7, 16, 6, 0)
    assert item.operating_window == "15/07/26-16/07/26 2000-0600"
    assert item.last_updated == datetime(2026, 7, 6, 8, 28)


def test_wales_item_missing_work_type_segment():
    items = parse_wales(WALES_RSS)
    item = items[1]
    assert item.road == "A40"
    assert item.location_from_to == "Nantgaredig to Abergwili"
    assert item.work_type is None
    assert item.restriction == "Lanes closed"
    assert item.severity == "Moderate"
    assert item.start == datetime(2026, 7, 13, 9, 30)
    assert item.end == datetime(2026, 7, 13, 15, 30)


def test_wales_item_restriction_before_work_type():
    # Real items aren't consistent about segment order - this one puts the
    # restriction ("Lanes closed") before the work type ("Environmental
    # work"), the reverse of the usual order.
    items = parse_wales(WALES_RSS)
    item = items[2]
    assert item.work_type == "Environmental work"
    assert item.restriction == "Lanes closed"


def test_wales_item_with_empty_road_segment():
    items = parse_wales(WALES_RSS)
    item = items[3]
    assert item.road is None
    assert item.direction == "Both directions"
    assert item.location_from_to == "Abergavenny Hardwick R/bout to Raglan"
    assert item.restriction == "Bridge closed Local lanes closed"
    # A single time value, not a "HHMM-HHMM" range - still captured whole.
    assert item.operating_window == "06/07/26-14/09/26 0600"


def test_wales_feed_urls_english_and_welsh():
    assert TrafficWalesClient.feed_url(WalesFeed.ROADWORKS) == (
        "https://traffic.wales/feeds/roadworks/rss.xml"
    )
    assert TrafficWalesClient.feed_url(WalesFeed.ROADWORKS, Language.WELSH) == (
        "https://traffig.cymru/porthiad/gwaith-ffordd/rss.xml"
    )
    assert TrafficWalesClient.feed_url(WalesFeed.HEADLINES, Language.WELSH) == (
        "https://traffig.cymru/porthiad/penawdau/rss.xml"
    )


@respx.mock
def test_wales_client_fetches_and_parses():
    respx.get("https://traffic.wales/feeds/roadworks/rss.xml").mock(
        return_value=httpx.Response(200, content=WALES_RSS.encode())
    )
    with TrafficWalesClient() as tw:
        items = tw.fetch(WalesFeed.ROADWORKS)
    assert items[0].roads[0] == "A40"
