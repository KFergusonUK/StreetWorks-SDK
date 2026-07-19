"""Parse the BAG Atom download feed to discover the current GeoPackage/zip
URLs - never hardcode a dated filename (the NDW lesson: PDOK republishes
monthly and the file name changes with it, e.g. real filenames seen include
a build date). The feed itself is the documented discovery mechanism.

Confirmed live 2026-07 at ``https://service.pdok.nl/lv/bag/atom/bag.xml``
(the feed's own self-referential ``<link rel="self">``/``<id>`` elements use
a ``.../kadaster/bag/...`` path instead of ``.../lv/bag/...`` - both resolve,
neither redirects to the other; this module accepts either as the feed URL
and doesn't assume one is canonical).
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree

__all__ = ["AtomEntry", "FEED_URL", "parse_feed"]

FEED_URL = "https://service.pdok.nl/lv/bag/atom/bag.xml"

_ATOM_NS = "http://www.w3.org/2005/Atom"


@dataclass(frozen=True)
class AtomEntry:
    """One download offered by the feed - real ones seen live: the
    history-free GeoPackage, and the full-history XML zip extract."""

    title: str
    url: str
    media_type: str | None
    length: int | None  # bytes, per the feed's own `length` attribute
    rights: str | None
    crs_label: str | None  # e.g. "Amersfoort / RD New" (EPSG:28992)
    updated: str | None


def parse_feed(xml_bytes: bytes) -> list[AtomEntry]:
    """Parse a BAG Atom feed document into its download entries."""
    root = ElementTree.fromstring(xml_bytes)
    entries = []
    for entry_el in root.findall(f"{{{_ATOM_NS}}}entry"):
        title_el = entry_el.find(f"{{{_ATOM_NS}}}title")
        link_el = entry_el.find(f"{{{_ATOM_NS}}}link[@rel='alternate']")
        rights_el = entry_el.find(f"{{{_ATOM_NS}}}rights")
        updated_el = entry_el.find(f"{{{_ATOM_NS}}}updated")
        category_el = entry_el.find(f"{{{_ATOM_NS}}}category")
        if link_el is None or link_el.get("href") is None:
            continue  # not a real downloadable entry - skip rather than guess
        length = link_el.get("length")
        entries.append(
            AtomEntry(
                title=(title_el.text or "") if title_el is not None else "",
                url=link_el.get("href", ""),
                media_type=link_el.get("type"),
                length=int(length) if length else None,
                rights=rights_el.text if rights_el is not None else None,
                crs_label=category_el.get("label") if category_el is not None else None,
                updated=updated_el.text if updated_el is not None else None,
            )
        )
    return entries
