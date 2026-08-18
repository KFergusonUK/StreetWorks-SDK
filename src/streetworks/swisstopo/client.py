"""swisstopo (Bundesamt für Landestopografie) - the Amtliches
Verzeichnis der Strassen ("Official directory of streets"), Switzerland's
federal street-name register. This SDK's first Swiss streets/gazetteer
coverage, a sibling to the existing Swiss roadworks providers (Kanton
Zürich, Stadt Zürich) at national scale.

**A genuine federal register, not a swisstopo-original survey.** Street
names are declared in the Eidgenössisches Gebäude- und Wohnungsregister
(GWR, the Federal Register of Buildings and Dwellings, run by the
Federal Statistical Office/BFS) by each municipality (occasionally the
canton); BFS transmits the data to swisstopo daily, which enriches it
with geometry and republishes it (confirmed live from swisstopo's own
product page, ``swisstopo.admin.ch/de/amtliches-verzeichnis-der-strassen``)
- the same "geometry added downstream of a name authority" shape
Ireland's Monaghan and Finland's Digiroad both have with their own
respective road authorities.

**Bulk CSV, not the live point-query API - a deliberate choice, matching
the same call ANNCSU (Italy) already made for its own bulk-vs-live-query
trade-off.** A real, live, keyless REST API also exists
(``api3.geo.admin.ch/rest/services/api/MapServer/find``, confirmed live
with real ``LineString`` geometry per street), but it only supports
search-by-name/bbox, not "give me everything" - enumerating all real
Swiss streets through it would mean many thousands of individual
queries. This client uses the real national bulk CSV instead, found via
swisstopo's own STAC catalogue
(``data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.amtliches-strassenverzeichnis``),
confirmed live: one ZIP, updated daily (confirmed: fetched same-day as
this module's own investigation).

**A real, deliberate trade-off: point geometry only, not the live API's
richer LineString.** This bulk CSV's own real schema states a single
``STR_EASTING``/``STR_NORTHING`` pair per street - genuinely different
(sparser) from the live `find` API's per-feature `LineString`, and from
the bulk File Geodatabase/INTERLIS XTF resources also published
alongside this CSV (confirmed live: the XTF alone is a real 842 MB
uncompressed file - too large for this SDK's stdlib-plus-httpx,
no-heavy-GIS-dependency convention to parse, the same reasoning that
kept this SDK off `pyproj`). The point is real, stated data - not a
computed centroid - just a narrower resource than the richest one
swisstopo publishes.

**224,985 real national street records, confirmed live 2026-08-18 -
100% carrying a real name and a real coordinate, zero duplicate IDs.**
The cleanest coverage figures of any streets provider this SDK has
built. Real fields: ``STR_ESID`` (a real, unique identifier),
``STN_LABEL`` (the real name), ``ZIP_LABEL`` (postal code + town),
``COM_NAME``/``COM_FOSNR`` (the real municipality name and its federal
number), ``COM_CANTON`` (a real 2-letter canton code - all 26 real
Swiss cantons are present), ``STR_TYPE`` (a real, English-language
enum despite the German column names - ``Street``/``Area``/``Place``,
169,971/52,658/2,356 respectively), ``STR_STATUS`` (``real`` on
224,873 rows, ``planned`` on 112 - kept as-is, never filtered by this
client), ``STR_OFFICIAL`` (``true``/``false`` - 3,654 real rows are
declared but not yet official), and a real, largely-unused parent/child
hierarchy (``STR_PARENT``/``STR_CHILDREN``, populated on only 339/338
rows respectively).

**CRS: real Swiss LV95 (``EPSG:2056``), stated explicitly by this
resource's own filename convention and confirmed against real coordinate
magnitude** (eastings ~2.48-2.84M, northings ~1.07-1.30M, the genuine
LV95 7-digit range) - a different, newer CRS from the live `find` API's
own real ``EPSG:21781`` (the older LV03 grid), a real inconsistency
between swisstopo's own resources for the same dataset, noted rather
than silently normalised.

**A real bonus, found but not built here**: this collection also
publishes a Liechtenstein-scoped sibling resource
(``amtliches-strassenverzeichnis_li``), confirmed live to exist with the
identical schema - not fetched by this client, since only Switzerland
was asked for; a real, ready next step if Liechtenstein coverage is ever
wanted.

**No credentials.** Licence: swisstopo's own OGD (open government data)
terms, confirmed live (`swisstopo.admin.ch/ogd-conditions`) - free use,
distribution, enrichment and commercial use, with mandatory source
attribution (e.g. "©swisstopo") - functionally CC BY-equivalent, stated
under swisstopo's own named terms rather than a generic CC label.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "SwisstopoStreetsClient"]

JSON = dict[str, str]

#: The real, live, keyless national bulk-download route for
#: Switzerland's own street register (LV95/EPSG:2056). See module
#: docstring - a Liechtenstein-scoped sibling exists at the same path
#: with "_li_" in place of "_ch_", not fetched here.
BASE_URL = (
    "https://data.geo.admin.ch/ch.swisstopo.amtliches-strassenverzeichnis/"
    "amtliches-strassenverzeichnis_ch/amtliches-strassenverzeichnis_ch_2056.csv.zip"
)


class SwisstopoStreetsClient:
    """Fetch Switzerland's real federal street-name register (Amtliches
    Verzeichnis der Strassen). No credentials required.

    >>> from streetworks.swisstopo import SwisstopoStreetsClient
    >>> from streetworks.common import from_swisstopo_street
    >>> with SwisstopoStreetsClient() as swisstopo:  # doctest: +SKIP
    ...     streets = [from_swisstopo_street(r) for r in swisstopo.iter_streets()]
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 120.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_streets(self) -> Iterator[JSON]:
        """Every real Swiss street - the full national bulk download,
        unfiltered (including real ``STR_STATUS="planned"`` and
        ``STR_OFFICIAL="false"`` rows - see module docstring)."""
        response = self._transport.request("GET", BASE_URL)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            inner_name = archive.namelist()[0]
            with archive.open(inner_name) as raw_file:
                text = io.TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
                reader: Any = csv.DictReader(text, delimiter=";")
                yield from reader

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> SwisstopoStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
