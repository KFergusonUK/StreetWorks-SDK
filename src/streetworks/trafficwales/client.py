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

Verified against the live feed (July 2026): titles are colon-delimited
``road : direction : from-to : [work type :] restriction[ : restriction] :
date-time :``, but the date-time segment isn't reliably last (some items put
it right after the from-to segment, before the restriction text) and the
work-type segment is frequently missing - so it's located by pattern
wherever it falls, not by position. One real item even has an empty leading
(road) segment. The description repeats the title, then adds labelled
fields (``Start time:``, ``End Date:``, ``Severity:``, ``Source:``,
``Last updated:``) in ``DD/MM/YYYY H:MM`` - these are 4-digit-year and more
reliable than the title's 2-digit dates, so they're preferred. ``Severity``
mixes closure-type text ("Road closure") with genuine severity words
("Slight"/"Moderate"/"Severe") - kept as a free-text label, not an enum.
Geometry is a WGS84 ``georss:point`` (namespaced - the plain ``_child_text``
helper below can't reach it). The feed serves httpx's default UA fine; it
just refuses bare curl - nothing here needs to imitate a browser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from xml.etree.ElementTree import Element, fromstring

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

_GEORSS_NS = "{http://www.georss.org/georss}"

#: The trailing/embedded date-time segment, e.g. "15/07/26-16/07/26 2000-0600"
#: or a single day "13/07/26 0930-1530" - located by pattern, not position,
#: since it isn't reliably the last title segment (see module docstring).
_OPERATING_WINDOW = re.compile(
    r"\d{2}/\d{2}/\d{2}(?:-\d{2}/\d{2}/\d{2})?\s+\d{4}(?:-\d{4})?"
)

#: Segments that describe the closure/restriction itself rather than the
#: type of work - used to tell a lone remaining title segment apart from a
#: work-type one when only one is present (see _split_title_segments).
_RESTRICTION_WORDS = re.compile(
    r"closed|closure|lanes?|contraflow|narrow|diversion", re.I
)


@dataclass
class FeedItem:
    """One feed item. ``title``/``description`` are the authoritative raw
    text; everything else is best-effort extraction from them."""

    title: str
    description: str
    link: str | None = None
    published: datetime | None = None
    guid: str | None = None
    categories: tuple[str, ...] = ()
    roads: tuple[str, ...] = ()
    # --- best-effort extractions ----------------------------------------- #
    coordinate: tuple[float, float] | None = None  # (lat, lon), WGS84
    road: str | None = None
    direction: str | None = None
    location_from_to: str | None = None
    work_type: str | None = None
    restriction: str | None = None
    severity: str | None = None  # free text - mixes closure-type & severity
    start: datetime | None = None
    end: datetime | None = None
    operating_window: str | None = None  # raw "DD/MM/YY[-DD/MM/YY] HHMM[-HHMM]"
    source: str | None = None
    last_updated: datetime | None = None


def _parse_pubdate(text: str | None) -> datetime | None:
    if not text:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_uk_datetime(text: str | None) -> datetime | None:
    """``DD/MM/YYYY H:MM`` or ``DD/MM/YYYY HH:MM`` (4-digit year, UK order -
    the description's labelled fields, preferred over the title's 2-digit
    dates)."""
    if not text:
        return None
    try:
        return datetime.strptime(text.strip(), "%d/%m/%Y %H:%M")
    except ValueError:
        return None


def _child_text(element: Element, tag: str) -> str | None:
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else None


def _georss_point(element: Element) -> tuple[float, float] | None:
    child = element.find(f"{_GEORSS_NS}point")
    if child is None or not child.text:
        return None
    parts = child.text.split()
    if len(parts) != 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def _labelled_field(description: str, label: str) -> str | None:
    """Pull ``"Label: value"`` out of the comma-separated description prose
    - labels are matched independently (not by fixed position), since a feed
    that can drop a title segment shouldn't be trusted to keep every label in
    the same order either."""
    match = re.search(rf"{re.escape(label)}:\s*([^,]+)", description)
    return match.group(1).strip() if match else None


def _split_title_segments(title: str) -> tuple[
    str | None, str | None, str | None, str | None, str | None, str | None
]:
    """Split a colon-delimited title into
    ``(road, direction, location_from_to, work_type, restriction, operating_window)``.

    Segment count and the date-time segment's position both vary (see module
    docstring), so the date-time segment is located by pattern and pulled out
    first; whatever's left after road/direction/from-to is one work-type/
    restriction segment (kept as restriction - it's usually the closure
    description) or several (first is work-type, the rest joined into
    restriction).
    """
    parts = [p.strip() for p in title.split(":")]
    while parts and not parts[-1]:
        parts.pop()  # drop the trailing empty segment from a trailing " :"

    operating_window: str | None = None
    remaining: list[str] = []
    for part in parts:
        match = _OPERATING_WINDOW.search(part)
        if match and operating_window is None:
            operating_window = match.group(0)
            continue
        remaining.append(part)

    road = remaining[0] if len(remaining) > 0 and remaining[0] else None
    direction = remaining[1] if len(remaining) > 1 and remaining[1] else None
    location_from_to = remaining[2] if len(remaining) > 2 and remaining[2] else None
    tail = [p for p in remaining[3:] if p]

    work_type: str | None = None
    restriction: str | None = None
    if len(tail) == 1:
        restriction = tail[0]
    elif len(tail) >= 2:
        # Work type and restriction(s) appear in either order across real
        # items - "Resurfacing work : Road closed" and "Lanes closed :
        # Environmental work" both occur. Trust whichever end reads as a
        # restriction and take the work type from the other end; if both
        # (or neither) end read as a restriction, there's no confident split
        # so everything stays joined as restriction rather than guessing.
        first_is_restriction = bool(_RESTRICTION_WORDS.search(tail[0]))
        last_is_restriction = bool(_RESTRICTION_WORDS.search(tail[-1]))
        if last_is_restriction and not first_is_restriction:
            work_type, restriction = tail[0], " : ".join(tail[1:])
        elif first_is_restriction and not last_is_restriction:
            work_type, restriction = tail[-1], " : ".join(tail[:-1])
        else:
            restriction = " : ".join(tail)

    return road, direction, location_from_to, work_type, restriction, operating_window


def parse_feed(xml: str | bytes) -> list[FeedItem]:
    """Parse a Traffic Wales RSS document into :class:`FeedItem` objects."""
    root = fromstring(xml)
    items: list[FeedItem] = []
    for element in root.iter("item"):
        title = _child_text(element, "title") or ""
        description = _child_text(element, "description") or ""
        roads = tuple(dict.fromkeys(_ROAD.findall(f"{title} {description}")))
        road, direction, location_from_to, work_type, restriction, operating_window = (
            _split_title_segments(title)
        )
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
                coordinate=_georss_point(element),
                road=road,
                direction=direction,
                location_from_to=location_from_to,
                work_type=work_type,
                restriction=restriction,
                severity=_labelled_field(description, "Severity"),
                start=_parse_uk_datetime(_labelled_field(description, "Start time")),
                end=_parse_uk_datetime(_labelled_field(description, "End Date")),
                operating_window=operating_window,
                source=_labelled_field(description, "Source"),
                last_updated=_parse_uk_datetime(_labelled_field(description, "Last updated")),
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
