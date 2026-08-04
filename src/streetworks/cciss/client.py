"""Italy: CCISS (Centro di Coordinamento Informazioni sulla Sicurezza
Stradale) real-time traffic bulletin RSS - Italy's confirmed official
RTTI/SRTI National Access Point (per the European Commission's own
October 2025 National Access Points list, https://www.cciss.it/ is
listed for both delegated regulations), reached here via the real,
public, **keyless** RSS route rather than the registration-gated DATEX
II one.

.. attention::
   **Confirmed live (2026-08-03)** against a real, unauthenticated pull:
   100 real items, 70 explicitly ``lavori`` (roadworks), the rest a mix
   of weather, breakdowns, accidents, demonstrations and debris/spill
   incidents. No credentials required.

**This is a traveller-information feed, not a works register** - the
same shape as this SDK's existing TrafficWatchNI/Traffic Wales
adapters: items are human-readable Italian prose, so the typed fields
here are **best-effort extractions**, and the raw ``title``/
``description`` are always preserved on every item.
:class:`CcissClient` reuses that established pattern directly, not a new
one.

**No geometry** - unlike Traffic Wales's real ``georss:point``, this
feed's real XML carries only ``title``/``description``/``pubDate``/
``dc:date`` - no coordinates, no ``link``, no ``guid``. An earlier,
AI-generated summary of the CCISS homepage claimed items were
"georeferenced (latitude/longitude coordinates provided)" - checked
directly against the real RSS XML and found to be wrong; the homepage's
own interactive map likely has coordinates behind it, but the RSS feed
itself does not.

**The registration-gated DATEX II route (same ``cciss.it`` domain,
richer structured data under RTTI) remains a real, separate, later
option** - not pursued here; this module is the immediate, keyless
route.

**Real event-type vocabulary, confirmed live, not guessed.** The
authoritative event type is a free-Italian-text clause (``lavori``,
``personale su strada causa lavori``, ``tratto chiuso causa lavori``,
``manifestazione``, ``veicolo fermo o in avaria``, ``pioggia``,
``perdita di carico``, ``materiali dispersi``, ...) - kept as free text
via :attr:`BulletinItem.event_type`, the same "kept as a free-text
label, not an enum" discipline Traffic Wales's own ``severity`` field
already established, since no confident closed vocabulary could be
built from the real variety observed. :attr:`BulletinItem.is_roadworks`
is a real, evidenced classification: ``True`` when the event-type text
contains ``lavori`` (works - 70/100 real items), ``personale su strada``
(personnel on road - construction staging) or ``pulizia del manto
stradale`` (road-surface cleaning) - **not** for ``manifestazione``
(demonstration), weather, breakdowns, accidents, or debris/spill
incidents, all real and present in the same feed.

**A real, confirmed-live title/description quirk, checked and ruled
out**: initial regex-based extraction wrongly suggested the road name
embedded in each item's ``description`` was offset by one item from its
own ``title`` - re-checked via proper XML parsing (not regex) and found
to be a self-inflicted extraction bug, not a real feed defect; title and
description are correctly aligned. Flagged here so the same false lead
isn't rediscovered.

**Licence**: not confirmed - no licence statement was found on the
`cciss.it` site associated with this feed specifically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from xml.etree.ElementTree import Element, fromstring

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["RSS_URL", "CcissClient", "BulletinItem", "parse_feed"]

RSS_URL = "https://www.cciss.it/rss"

#: Real, evidenced roadworks terms (see module docstring for the real
#: counts) - a substring match against the free-text event_type clause,
#: not a closed enum.
_ROADWORKS_TERMS = re.compile(
    r"lavori|personale su strada|pulizia del manto stradale|cantiere", re.IGNORECASE
)

_ITALIAN_MONTHS = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}

_SOURCE_SUFFIX = re.compile(r"\s*<br/>\s*\(Fonte:[^)]*\)\s*$")
#: The whole temporal clause, e.g. "dalle 21:35 del 3 alle 05:00 del 4
#: agosto 2026" or "dalle 21:37 del 3 agosto 2026" - real shapes observed
#: live, see module docstring.
_TEMPORAL_CLAUSE = re.compile(r"\bdalle\s+\d{1,2}:\d{2}.*?\b\d{4}\b")
_TIME = re.compile(r"\b(\d{1,2}:\d{2})\b")
_DAY = re.compile(r"\bdel\s+(\d{1,2})\b")
_MONTH_YEAR = re.compile(r"\b([A-Za-zàèéìòù]+)\s+(\d{4})\b")
_BETWEEN = re.compile(r"\btra\s+(.+?)\s+e\s+(.+?)(?:\s+in direzione\s+(.+?))?\s*$")
_AT = re.compile(r"\ba\s+(.+?)(?:\s+in direzione\s+(.+?))?\s*$")


@dataclass
class BulletinItem:
    """One real CCISS bulletin item. ``title``/``description`` are the
    authoritative raw text; everything else is best-effort extraction
    from the description - see module docstring."""

    title: str
    description: str
    published: datetime | None = None
    # --- best-effort extractions ----------------------------------------- #
    road: str | None = None
    event_type: str | None = None
    is_roadworks: bool = False
    location_from: str | None = None
    location_to: str | None = None
    location_at: str | None = None
    direction: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    operating_window: str | None = None  # raw temporal clause, e.g. "dalle 21:37 del 3 agosto 2026"


def _parse_pubdate(text: str | None) -> datetime | None:
    if not text:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_italian_datetime(
    month_name: str, year: str, day: str | None, time_str: str | None
) -> datetime | None:
    if day is None or time_str is None:
        return None
    month = _ITALIAN_MONTHS.get(month_name.lower())
    if month is None:
        return None
    hour, _, minute = time_str.partition(":")
    try:
        return datetime(int(year), month, int(day), int(hour), int(minute))
    except ValueError:
        return None


def extract_fields(item: BulletinItem) -> BulletinItem:
    """Populate the best-effort fields from the raw description. The
    real shape is ``"{road}\\n {event_type}{temporal_clause}?
    {spatial_clause} <br/> (Fonte: www.cciss.it)"`` - see module
    docstring for the real temporal/spatial clause variety."""
    text = _SOURCE_SUFFIX.sub("", item.description)

    road, _, rest = text.partition("\n")
    if rest:
        item.road = road.strip() or None
    else:
        rest = text

    temporal_match = _TEMPORAL_CLAUSE.search(rest)
    if temporal_match:
        clause = temporal_match.group(0)
        item.operating_window = clause
        rest = rest[: temporal_match.start()] + rest[temporal_match.end() :]

        times = _TIME.findall(clause)
        days = _DAY.findall(clause)
        month_year = _MONTH_YEAR.search(clause)
        if month_year and days:
            month_name, year = month_year.groups()
            start_time = times[0] if times else None
            item.start = _parse_italian_datetime(month_name, year, days[0], start_time)
            end_day = days[1] if len(days) > 1 else days[0]
            end_time = times[1] if len(times) > 1 else None
            if end_time is not None:
                item.end = _parse_italian_datetime(month_name, year, end_day, end_time)

    between = _BETWEEN.search(rest)
    if between:
        item.location_from = between.group(1).strip()
        item.location_to = between.group(2).strip()
        if between.group(3):
            item.direction = between.group(3).strip()
        rest = rest[: between.start()]
    else:
        at = _AT.search(rest)
        if at:
            item.location_at = at.group(1).strip()
            if at.group(2):
                item.direction = at.group(2).strip()
            rest = rest[: at.start()]

    event_type = rest.strip()
    if event_type:
        item.event_type = event_type
        item.is_roadworks = bool(_ROADWORKS_TERMS.search(event_type))
    return item


def _child_text(element: Element, tag: str) -> str | None:
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else None


def parse_feed(xml: str | bytes) -> list[BulletinItem]:
    """Parse a real CCISS RSS document into :class:`BulletinItem`
    objects."""
    root = fromstring(xml)
    items: list[BulletinItem] = []
    for element in root.iter("item"):
        item = BulletinItem(
            title=_child_text(element, "title") or "",
            description=_child_text(element, "description") or "",
            published=_parse_pubdate(_child_text(element, "pubDate")),
        )
        items.append(extract_fields(item))
    return items


class CcissClient:
    """Fetch the real CCISS traffic bulletin RSS feed. No credentials
    required.

    >>> from streetworks.cciss import CcissClient
    >>> with CcissClient() as cciss:  # doctest: +SKIP
    ...     roadworks = [i for i in cciss.fetch() if i.is_roadworks]
    """

    def __init__(
        self,
        *,
        rss_url: str = RSS_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.rss_url = rss_url
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def fetch(self) -> list[BulletinItem]:
        """Fetch and parse the real, live bulletin feed - roadworks,
        weather, breakdowns, accidents and events, mixed, most recent
        first. Filter on ``item.is_roadworks`` for roadworks only."""
        response = self._transport.request("GET", self.rss_url)
        return parse_feed(response.content)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> CcissClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
