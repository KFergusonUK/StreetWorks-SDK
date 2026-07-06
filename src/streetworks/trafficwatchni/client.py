"""Northern Ireland roadworks via TrafficWatchNI RSS.

The Department for Infrastructure's Traffic Information & Control Centre
(DfI TICC) publishes RSS feeds of roadworks, incidents and events - covering
trunk roads and motorways NI-wide, plus all roads in Greater Belfast -
refreshed every five minutes. No credentials are required.

**Attribution requirement**: the feed terms allow free use (including
commercial) provided *DfI Traffic Information and Control Centre is credited
as the information source* and item URLs are preserved. Keep the ``link`` on
each item intact and credit DfI TICC wherever the data is displayed.

This is a traveller-information feed, not a works register: items are
human-readable text, so the typed fields here are **best-effort extractions**
and the raw ``title``/``description`` are always preserved on every item.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from xml.etree.ElementTree import fromstring

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["TrafficWatchNIClient", "Feed", "Region", "RoadworksItem", "ATTRIBUTION"]

ATTRIBUTION = "Source: DfI Traffic Information and Control Centre (trafficwatchni.com)"

BASE_URL = "https://rss.trafficwatchni.com"


class Feed(str, Enum):
    ROADWORKS = "roadworks"
    INCIDENTS = "incidents"
    EVENTS = "events"


class Region(str, Enum):
    NORTHERN_IRELAND = ""          #: trunk roads and motorways, NI-wide
    BELFAST = "belfast"            #: all roads in the Greater Belfast area


@dataclass
class RoadworksItem:
    """One feed item. ``title``/``description`` are the authoritative raw
    text; everything else is best-effort extraction from it."""

    title: str
    description: str
    link: str | None = None
    published: datetime | None = None
    guid: str | None = None
    # --- best-effort extractions ----------------------------------------- #
    closure_type: str | None = None      # "Road closure", "Lane Closure", ...
    promoter: str | None = None          # "BT Openreach", "NI Water", ...
    start_date: date | None = None
    end_date: date | None = None
    operating_times: str | None = None   # "Daily 09:30 to 16:30", "Overnight"
    diversion: bool = False
    traffic_control: bool = False
    road: str | None = None
    town: str | None = None


_CLOSURE = re.compile(
    r"\b((?:Road|Lane(?:\s*\d+)?|Footway|Carriageway|Hard shoulder|Slip road)"
    r"\s+[Cc]losures?)",
)
_PROMOTER = re.compile(
    r"(?:work|works)\s+by\s+(.+?)(?=\s+(?:from|between|commencing)\b|\s*Closure|[.,;]|$)",
    re.I,
)
_DATE = re.compile(r"\b\w{3}\s+(\d{1,2}\s+\w{3}\s+\d{4})")
_DATE_RANGE = re.compile(
    r"from\s+\w{3}\s+(\d{1,2}\s+\w{3}\s+\d{4})\s*(?:to:?\s*\w{3}\s+(\d{1,2}\s+\w{3}\s+\d{4}))?",
    re.I,
)
_TIMES = re.compile(
    r"\b((?:Daily|Overnight(?:\s+only)?|Off-?peak|Continuously?)"
    r"(?:\s+(?:from\s+)?\d{1,2}[:.]\d{2}(?:hrs)?\s+(?:to|until)\s+\d{1,2}[:.]\d{2}(?:hrs)?)?)",
    re.I,
)


def _parse_date(text: str) -> date | None:
    try:
        return datetime.strptime(text, "%d %b %Y").date()
    except ValueError:
        return None


def _parse_pubdate(text: str | None) -> datetime | None:
    if not text:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def extract_fields(item: RoadworksItem) -> RoadworksItem:
    """Populate the best-effort fields from the raw title/description."""
    text = f"{item.title} {item.description}"

    closure = _CLOSURE.search(text)
    if closure:
        item.closure_type = " ".join(closure.group(1).split()).rstrip("s").title()

    promoter = _PROMOTER.search(text)
    if promoter:
        item.promoter = promoter.group(1).strip()

    date_range = _DATE_RANGE.search(text)
    if date_range:
        item.start_date = _parse_date(date_range.group(1))
        if date_range.group(2):
            item.end_date = _parse_date(date_range.group(2))

    times = _TIMES.search(text)
    if times:
        item.operating_times = " ".join(times.group(1).split())

    item.diversion = "diversion" in text.lower()
    item.traffic_control = "traffic control" in text.lower()

    # Titles commonly look like "Lane closure, , Malone Road, Belfast"
    parts = [p.strip() for p in item.title.split(",") if p.strip()]
    if len(parts) >= 3:
        item.road, item.town = parts[-2], parts[-1]
    elif len(parts) == 2:
        item.road = parts[-1]
    return item


def _child_text(element, tag: str) -> str | None:
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else None


def parse_feed(xml: str | bytes) -> list[RoadworksItem]:
    """Parse an RSS document into :class:`RoadworksItem` objects."""
    root = fromstring(xml)
    items: list[RoadworksItem] = []
    for element in root.iter("item"):
        item = RoadworksItem(
            title=_child_text(element, "title") or "",
            description=_child_text(element, "description") or "",
            link=_child_text(element, "link"),
            published=_parse_pubdate(_child_text(element, "pubDate")),
            guid=_child_text(element, "guid"),
        )
        items.append(extract_fields(item))
    return items


class TrafficWatchNIClient:
    """Fetch TrafficWatchNI RSS feeds. No credentials required.

    >>> from streetworks.trafficwatchni import TrafficWatchNIClient, Feed, Region
    >>> with TrafficWatchNIClient() as twni:
    ...     for item in twni.fetch(Feed.ROADWORKS):
    ...         print(item.closure_type, item.road, item.town, "-", item.promoter)
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def feed_url(self, feed: Feed, region: Region = Region.NORTHERN_IRELAND) -> str:
        suffix = f"_{region.value}" if region.value else ""
        return f"{self.base_url}/trafficwatchni_{feed.value}{suffix}_rss.xml"

    def fetch(
        self, feed: Feed = Feed.ROADWORKS, region: Region = Region.NORTHERN_IRELAND
    ) -> list[RoadworksItem]:
        """Fetch and parse a feed. The NI-wide feeds cover trunk roads and
        motorways; the Belfast feeds cover all roads in Greater Belfast."""
        response = self._transport.request("GET", self.feed_url(feed, region))
        return parse_feed(response.content)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> TrafficWatchNIClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
