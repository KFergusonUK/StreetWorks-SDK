"""Wales motorway and trunk road data via Traffic Wales RSS.

Traffic Wales (Welsh Government) publishes open RSS feeds - no registration
required - for roadworks, incidents/events, and headlines on the Welsh
motorway and trunk road network, in English and Welsh, updated every five
minutes.

**Attribution requirement**: Traffic Wales must be credited as the data
source wherever the data is used.

Coverage note: motorway and trunk roads only, and only Traffic Wales'
own records - this is a traveller-information feed, not a works register.
Traffic Wales also offers richer DATEX II feeds (roadworks, events, CCTV,
VMS) but access to those is restricted and granted on application via
https://traffic.wales/developers ; once granted, ``streetworks.datex2`` can
parse them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from xml.etree.ElementTree import fromstring

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["TrafficWalesClient", "Feed", "Language", "FeedItem", "ATTRIBUTION"]

ATTRIBUTION = "Data source: Traffic Wales (traffic.wales), Welsh Government"


class Feed(str, Enum):
    ROADWORKS = "roadworks"
    INCIDENTS_EVENTS = "incidents-events"
    HEADLINES = "headlines"


#: Welsh-language feeds live on traffig.cymru with Welsh path segments.
_WELSH_PATHS = {
    Feed.ROADWORKS: "gwaith-ffordd",
    Feed.INCIDENTS_EVENTS: "achlysuron-digwyddiadau",
    Feed.HEADLINES: "penawdau",
}


class Language(str, Enum):
    ENGLISH = "en"
    WELSH = "cy"


_ROAD = re.compile(r"\b([MAB]\d{1,4}(?:\([MA]\))?)\b")


@dataclass
class FeedItem:
    """One feed item. ``title``/``description`` are the authoritative raw
    text; ``roads`` is a best-effort extraction of road numbers from it."""

    title: str
    description: str
    link: str | None = None
    published: datetime | None = None
    guid: str | None = None
    categories: tuple[str, ...] = ()
    roads: tuple[str, ...] = ()


def _parse_pubdate(text: str | None) -> datetime | None:
    if not text:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def _child_text(element, tag: str) -> str | None:
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else None


def parse_feed(xml: str | bytes) -> list[FeedItem]:
    """Parse a Traffic Wales RSS document into :class:`FeedItem` objects."""
    root = fromstring(xml)
    items: list[FeedItem] = []
    for element in root.iter("item"):
        title = _child_text(element, "title") or ""
        description = _child_text(element, "description") or ""
        roads = tuple(dict.fromkeys(_ROAD.findall(f"{title} {description}")))
        items.append(
            FeedItem(
                title=title,
                description=description,
                link=_child_text(element, "link"),
                published=_parse_pubdate(_child_text(element, "pubDate")),
                guid=_child_text(element, "guid"),
                categories=tuple(
                    c.text.strip()
                    for c in element.findall("category")
                    if c.text and c.text.strip()
                ),
                roads=roads,
            )
        )
    return items


class TrafficWalesClient:
    """Fetch Traffic Wales open RSS feeds. No credentials required.

    >>> from streetworks.trafficwales import TrafficWalesClient, Feed
    >>> with TrafficWalesClient() as tw:
    ...     for item in tw.fetch(Feed.ROADWORKS):
    ...         print(item.roads, "-", item.title)
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ):
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    @staticmethod
    def feed_url(feed: Feed, language: Language = Language.ENGLISH) -> str:
        if language is Language.WELSH:
            return f"https://traffig.cymru/porthiad/{_WELSH_PATHS[feed]}/rss.xml"
        return f"https://traffic.wales/feeds/{feed.value}/rss.xml"

    def fetch(
        self, feed: Feed = Feed.ROADWORKS, language: Language = Language.ENGLISH
    ) -> list[FeedItem]:
        response = self._transport.request("GET", self.feed_url(feed, language))
        return parse_feed(response.content)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> TrafficWalesClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
