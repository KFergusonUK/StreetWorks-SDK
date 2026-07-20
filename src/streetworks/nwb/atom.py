"""Discover the current NWB GeoPackage download URL - never hardcode a
dated filename, the same lesson BAG's/Kartverket's Atom feeds already
established (monthly republication means filenames/paths can change).

**NWB's feed is two hops, unlike every other Atom feed in this SDK** -
confirmed live 2026-07: the top-level index
(``https://service.pdok.nl/rws/nwbwegen/atom/index.xml``) lists one entry
per dataset (here, just "NWB - Wegen") whose own ``<link rel="alternate">``
points to a *second* feed (``.../atom/nwb_wegen.xml``), and only that
second feed's entry carries the real downloadable file. BAG's and
Kartverket's feeds are both one hop (the index entry links the file
directly) - :func:`discover_download` follows both hops so callers don't
need to know this.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree

__all__ = [
    "INDEX_FEED_URL",
    "DatasetEntry",
    "DownloadEntry",
    "parse_dataset_feed",
    "parse_index_feed",
]

INDEX_FEED_URL = "https://service.pdok.nl/rws/nwbwegen/atom/index.xml"

_ATOM_NS = "http://www.w3.org/2005/Atom"


@dataclass(frozen=True)
class DatasetEntry:
    """One dataset listed in the top-level index feed - its ``feed_url``
    is the second-hop feed that actually lists downloads."""

    title: str
    feed_url: str
    rights: str | None


@dataclass(frozen=True)
class DownloadEntry:
    """One real download, from a second-hop dataset feed."""

    title: str
    url: str
    media_type: str | None
    length: int | None
    rights: str | None
    crs_label: str | None
    updated: str | None


def _alternate_feed_link(entry_el: ElementTree.Element) -> str | None:
    for link_el in entry_el.findall(f"{{{_ATOM_NS}}}link"):
        if link_el.get("rel") == "alternate" and link_el.get("type") == "application/atom+xml":
            return link_el.get("href")
    return None


def parse_index_feed(xml_bytes: bytes) -> list[DatasetEntry]:
    """Parse the top-level index feed into its dataset entries (each
    pointing to a second-hop feed, not a downloadable file directly)."""
    root = ElementTree.fromstring(xml_bytes)
    entries = []
    for entry_el in root.findall(f"{{{_ATOM_NS}}}entry"):
        title_el = entry_el.find(f"{{{_ATOM_NS}}}title")
        rights_el = entry_el.find(f"{{{_ATOM_NS}}}rights")
        feed_url = _alternate_feed_link(entry_el)
        if feed_url is None:
            continue
        entries.append(
            DatasetEntry(
                title=(title_el.text or "").strip() if title_el is not None else "",
                feed_url=feed_url,
                rights=rights_el.text if rights_el is not None else None,
            )
        )
    return entries


def parse_dataset_feed(xml_bytes: bytes) -> list[DownloadEntry]:
    """Parse a second-hop dataset feed into its real downloads."""
    root = ElementTree.fromstring(xml_bytes)
    entries = []
    for entry_el in root.findall(f"{{{_ATOM_NS}}}entry"):
        title_el = entry_el.find(f"{{{_ATOM_NS}}}title")
        rights_el = entry_el.find(f"{{{_ATOM_NS}}}rights")
        updated_el = entry_el.find(f"{{{_ATOM_NS}}}updated")
        category_el = entry_el.find(f"{{{_ATOM_NS}}}category")
        link_el = entry_el.find(f"{{{_ATOM_NS}}}link[@rel='alternate']")
        if link_el is None or link_el.get("href") is None:
            continue
        length = link_el.get("length")
        entries.append(
            DownloadEntry(
                title=(title_el.text or "").strip() if title_el is not None else "",
                url=link_el.get("href", ""),
                media_type=link_el.get("type"),
                length=int(length) if length else None,
                rights=rights_el.text if rights_el is not None else None,
                crs_label=category_el.get("label") if category_el is not None else None,
                updated=updated_el.text if updated_el is not None else None,
            )
        )
    return entries
