"""CNAIR (Compania Națională de Administrare a Infrastructurii Rutiere)
- Romania's national roads/motorways authority's real-time "Dispecerat
Online" dispatch board, credential-free.

Found while surveying Europe for missing national feeds, the same
technique that found Poland's GDDKiA and Brussels Road Events.

.. attention::
   **This is a real, live, keyless source - but a genuinely different
   technical shape from every other provider in this SDK.** There is no
   separate JSON/XML/GeoJSON API: the page's own bundled JS
   (``js/custom.js``) was checked and confirmed to do nothing but a
   full ``location.reload()`` every ~8 hours - real current data is
   server-rendered directly into the page's own HTML ``<table>``
   elements, not fetched separately. This client parses that HTML with
   the standard library's own :mod:`html.parser` (no third-party HTML
   parsing dependency added - see below), the only way to consume this
   real source at all. **Expect a materially higher failure rate than
   this SDK's JSON/XML adapters** - a markup change on CNAIR's own site
   (a class name, a section title's wording) can silently break parsing
   in a way a schema change to a real API typically can't. Both
   ``iter_events()``/``iter_roadworks()`` degrade to an empty result on
   a structural mismatch rather than raising, the same "never crash on
   a source shape it doesn't recognise" discipline this SDK's own
   defensive XML/JSON parsing already follows - but that same
   discipline means a real breakage can look identical to "no events
   today" from the caller's side. Treat a persistent zero-length result
   as a signal to check the source by hand, not as proof nothing is
   happening.

**Confirmed live 2026-08-23**: `dispecerat.andnet.ro` returns a real,
current dispatch board - `Situația drumurilor naționale... - Platformă
Dispecerat Online CNAIR`. The page itself declares nine numbered
sections (road events, weather closures/restrictions, short-duration
works, ongoing closures, ongoing restrictions, rehabilitation works,
carriageway condition, weather, temperatures) - **two are unambiguous
roadworks by their own real section titles, not guessed from content**:
``"1.1. Lucrări de scurtă durată:"`` ("Short-duration works", 5 real
rows) and ``"6. ... lucrări de reabilitare, modernizări, întretinere și
reparații:"`` ("... rehabilitation, modernization, maintenance and
repair works", 45 real rows). Two other sections (``"4. ... circulația
întreruptă:"``/``"5. ... circulația îngreunată:"`` - ongoing
closures/restrictions) do carry some real works-caused records (a real
section-4 sample reads "lucrari de racordare cu noul sector al
autostrazii A7" - connection works for a new motorway sector) but
aren't roadworks-exclusive by their own title (closures/restrictions
can have other causes too) - deliberately **not** included in
``iter_roadworks()``, available raw via ``iter_events()``.

**No coordinates anywhere in this schema - a genuine, confirmed gap,
not a parsing failure.** Real fields are road indicator
(``"A1"``/``"DN23"``), a from/to kilometre-point pair, real dates,
a real "between localities" free-text range (e.g. ``"ACILIU (SB) -
SIBIU (SB)"``), and cause/work-type + remediation-measures free text -
no lat/lon field exists at all.

**``"NR. CRT."`` (e.g. ``"6.15"``) is a real but positional row number,
not a stable id** - it renumbers on every re-render as records are
added/removed, confirmed by its own sequential, section-scoped pattern
- not used as a reference.

**No third-party HTML-parsing dependency added.** Every other real
option (BeautifulSoup, lxml) would add a permanent dependency for every
user of this SDK just to support this one HTML-shaped source - instead
this client uses only the standard library's own :class:`html.parser.HTMLParser`,
keeping any extra cost confined to callers who actually fetch this
specific real source.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from html.parser import HTMLParser
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "ROADWORKS_SECTIONS", "RomaniaClient"]

JSON = dict[str, Any]

#: Confirmed live 2026-08-23. See module docstring.
BASE_URL = "https://dispecerat.andnet.ro/"

#: The two real section titles confirmed roadworks-exclusive by their
#: own wording - see module docstring for why sections 4/5 aren't
#: included.
ROADWORKS_SECTIONS = frozenset(
    {
        "1.1. Lucrări de scurtă durată:",
        "6. Drumuri naționale, drumuri expres și autostrăzi pe care se "
        "efectueaza lucrări de reabilitare, modernizări, întretinere și "
        "reparații:",
    }
)


class _DispatchBoardParser(HTMLParser):
    """Real, defensive parser for the CNAIR dispatch board's own HTML
    shape - see module docstring. Never raises on unexpected markup;
    a section this doesn't recognise is simply not collected."""

    def __init__(self) -> None:
        super().__init__()
        self.sections: dict[str, list[JSON]] = defaultdict(list)
        self._current_section: str | None = None
        self._awaiting_section_title = False
        self._in_row = False
        self._current_row: JSON = {}
        self._current_field: str | None = None
        self._text_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        if tag == "p" and attr_dict.get("class") == "h5 font-weight-bold":
            self._awaiting_section_title = True
        elif tag == "tr" and attr_dict.get("class") == "tablerow":
            self._in_row = True
            self._current_row = {}
        elif tag == "td" and self._in_row:
            self._current_field = attr_dict.get("placeholder")
            self._text_buffer = []

    def handle_data(self, data: str) -> None:
        if self._awaiting_section_title:
            self._current_section = data.strip()
        elif self._current_field is not None:
            self._text_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self._awaiting_section_title:
            self._awaiting_section_title = False
        elif tag == "td" and self._current_field is not None:
            self._current_row[self._current_field] = "".join(self._text_buffer).strip()
            self._current_field = None
        elif tag == "tr" and self._in_row:
            if self._current_section:
                self.sections[self._current_section].append(self._current_row)
            self._in_row = False


class RomaniaClient:
    """Fetch CNAIR's real-time Dispecerat Online dispatch board. No
    credentials required. See module docstring for the real
    higher-failure-rate caveat this HTML-shaped source carries.

    >>> from streetworks.romania import RomaniaClient
    >>> from streetworks.common import from_romania
    >>> with RomaniaClient() as client:  # doctest: +SKIP
    ...     works_list = from_romania(list(client.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def _sections(self) -> dict[str, list[JSON]]:
        response = self._transport.request("GET", self.base_url)
        parser = _DispatchBoardParser()
        parser.feed(response.text)
        return parser.sections

    def iter_events(self) -> Iterator[JSON]:
        """Every real record from every real section, unfiltered - each
        tagged with its own real ``section`` title. See module
        docstring for what the nine real sections are."""
        for section, rows in self._sections().items():
            for row in rows:
                yield {**row, "section": section}

    def iter_roadworks(self) -> Iterator[JSON]:
        """Real records from the two sections confirmed roadworks-
        exclusive by their own titles - see module docstring for why
        sections 4/5 aren't included despite carrying some real
        works-caused records too."""
        sections = self._sections()
        for title in ROADWORKS_SECTIONS:
            for row in sections.get(title, []):
                yield {**row, "section": title}

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> RomaniaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
