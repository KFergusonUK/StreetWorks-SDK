"""Parse the Matrikkelen-Adresse Atom feed to discover current bulk CSV
download URLs - never hardcode a URL built from a municipality name,
because Norway's municipalities are renamed/merged from time to time and
the real file names embed the human-readable name (e.g.
``Basisdata_5610_Karasjok_4258_MatrikkelenAdresse_CSV.zip``), the same
"discover, don't hardcode" lesson BAG's Atom feed already established.

Confirmed live 2026-07 at
``http://nedlasting.geonorge.no/geonorge/ATOM-feeds/MatrikkelenAdresse_AtomFeedCSV.xml``
(redirects to https - followed automatically). One feed lists **every**
area (national, county/fylke, and municipality/kommune) in **every** CRS
variant Kartverket publishes for that area side by side (confirmed:
``4258`` and ``25833`` everywhere, plus a UTM zone matching the area for
zone-straddling regions, e.g. ``25835`` for Finnmark) - so discovery
always parses the one feed and filters client-side, there's no
narrower per-area feed URL.

**Two real quirks in the feed itself, worth knowing before trusting it
blindly:**

1. Every entry's ``<link type="...">`` claims
   ``application/gml+xml;version=3.2.1`` **even for CSV entries** -
   confirmed on every real entry checked. The real format is only
   reliable from the URL's own filename (``..._CSV.zip``) or the
   human-readable ``<title>``, never from ``type`` - this parser reads
   the URL, not the (wrong) MIME type.
2. ``<rights>`` is usually ``"Kartverket"`` but not always - some
   municipalities' entries instead name the real local data steward
   (confirmed live: Karasjok's entries say
   ``"DSB - Sivilforsvaret og brannvesenet"``, Norway's civil defence and
   fire directorate). Not a bug - a genuine per-area attribution
   difference - kept as each entry's own ``rights``, not overwritten with
   the feed-level default.

Unlike BAG's feed, entries here carry no ``length`` attribute - file size
isn't knowable without actually requesting the file.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree

__all__ = ["BulkEntry", "FEED_URL", "parse_feed"]

FEED_URL = (
    "http://nedlasting.geonorge.no/geonorge/ATOM-feeds/MatrikkelenAdresse_AtomFeedCSV.xml"
)

_ATOM_NS = "http://www.w3.org/2005/Atom"
_CRS_SCHEME = "http://www.opengis.net/def/crs/"


@dataclass(frozen=True)
class BulkEntry:
    """One bulk CSV download the feed currently offers."""

    title: str
    url: str
    epsg: str | None  # e.g. "EPSG:4258" - from the entry's own <category>
    kommune: str | None  # None for county/national-level entries
    rights: str | None
    updated: str | None


def parse_feed(xml_bytes: bytes) -> list[BulkEntry]:
    """Parse a Matrikkelen-Adresse Atom feed document into its CSV
    download entries. Non-CSV entries (this feed is CSV-only per its own
    ``<subtitle>``, but never assume) are skipped, identified by the
    URL's filename, not the (unreliable) ``type`` attribute."""
    root = ElementTree.fromstring(xml_bytes)
    entries = []
    for entry_el in root.findall(f"{{{_ATOM_NS}}}entry"):
        title_el = entry_el.find(f"{{{_ATOM_NS}}}title")
        link_el = entry_el.find(f"{{{_ATOM_NS}}}link[@rel='alternate']")
        rights_el = entry_el.find(f"{{{_ATOM_NS}}}rights")
        updated_el = entry_el.find(f"{{{_ATOM_NS}}}updated")
        if link_el is None or link_el.get("href") is None:
            continue
        url = link_el.get("href", "")
        if not url.endswith("_CSV.zip"):
            continue

        epsg = None
        kommune = None
        for category_el in entry_el.findall(f"{{{_ATOM_NS}}}category"):
            if category_el.get("scheme") == _CRS_SCHEME:
                epsg = category_el.get("term")
            elif category_el.get("term") == "Kommune":
                kommune = category_el.get("label")

        entries.append(
            BulkEntry(
                title=(title_el.text or "").strip() if title_el is not None else "",
                url=url,
                epsg=epsg,
                kommune=kommune,
                rights=rights_el.text if rights_el is not None else None,
                updated=updated_el.text if updated_el is not None else None,
            )
        )
    return entries
