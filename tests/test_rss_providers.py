"""Tests for the TrafficWatchNI and Traffic Wales RSS providers.

The NI fixture item text is taken from real observed TrafficWatchNI feed
content; the Wales fixture is synthetic RSS 2.0 (the live feed's exact item
phrasing is verified via the smoke test).
"""

from datetime import date

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
    respx.get("https://rss.trafficwatchni.com/trafficwatchni_roadworks_rss.xml").mock(
        return_value=httpx.Response(200, content=NI_RSS.encode())
    )
    with TrafficWatchNIClient() as twni:
        items = twni.fetch()
    assert len(items) == 2 and items[0].promoter == "BT Openreach"


WALES_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Traffic Wales Roadworks</title>
  <item>
    <title>M4 eastbound J24 to J23A - carriageway resurfacing</title>
    <description>Overnight closures on the M4 eastbound between junction 24
      and junction 23A for resurfacing. Diversion via A48.</description>
    <link>https://traffic.wales/current-projects/example</link>
    <pubDate>Sun, 05 Jul 2026 18:00:00 GMT</pubDate>
    <category>Roadworks</category>
    <category>South Wales</category>
  </item>
</channel></rss>"""


def test_wales_parses_roads_and_categories():
    items = parse_wales(WALES_RSS)
    assert len(items) == 1
    item = items[0]
    assert item.roads == ("M4", "A48")  # deduped, order of appearance
    assert item.categories == ("Roadworks", "South Wales")
    assert item.link and "traffic.wales" in item.link


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
    assert items[0].roads[0] == "M4"
