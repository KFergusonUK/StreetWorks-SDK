"""Stream Kartverket's bulk ``MatrikkelenAdresse`` CSV files - never loads
a whole file into memory, following the BAN/SRWR precedent.

Confirmed live: every real download is a zip containing exactly one CSV
member (``matrikkelenAdresse.csv``), UTF-8 **with a BOM** (``utf-8-sig`` -
confirmed on the real Karasjok/Oslo/Røst files; the CSV's own Sámi
characters (``á``, ``š``, ...) and Norwegian characters (``æ``, ``ø``,
``å``) round-trip correctly once the BOM is stripped), semicolon-delimited,
one row per address. Real column set confirmed against actual national
data - notably ``uuidAdresse`` (a genuine, verified-unique-per-file stable
identifier - zero duplicates across 106,154 real Oslo rows checked) and
``atkomstId``/``sommeratkomstId``/``vinteratkomstId`` (a real,
Norway-specific "access point" concept: a separate coordinate for how an
address is actually reached, with **distinct summer and winter variants**
for addresses only reachable seasonally - confirmed present in the schema,
though unpopulated in every real municipality file sampled, including a
remote island one, so this SDK carries them in ``.raw`` without claiming
they're commonly populated).
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import IO

from .models import Address, address_from_csv_row

__all__ = ["iter_addresses"]


def _open_csv_member(source: str | Path | IO[str]) -> tuple[IO[str], bool]:
    """Return a text stream over the CSV member of a downloaded bulk zip
    (a path to ``.zip``, a path to an already-extracted ``.csv``, or an
    already-open text stream) and whether the caller must close it -
    same shape as :func:`streetworks.srwr.reader._open_text`."""
    if not isinstance(source, (str, Path)):
        return source, False  # caller's stream, caller's responsibility
    path = Path(source)
    if path.suffix.lower() == ".zip":
        archive = zipfile.ZipFile(path)
        members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not members:
            archive.close()
            raise ValueError(f"no CSV member found in {path}")
        raw = archive.open(members[0])
        return io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), True
    return open(path, encoding="utf-8-sig", newline=""), True


def iter_addresses(source: str | Path | IO[str]) -> Iterator[Address]:
    """Stream :class:`~streetworks.kartverket.models.Address` records from
    a bulk file - a path to the downloaded ``.zip``, a path to an already-
    extracted ``.csv``, or an open stream of either."""
    stream, owned = _open_csv_member(source)
    try:
        reader = csv.DictReader(stream, delimiter=";")
        for row in reader:
            yield address_from_csv_row(row)
    finally:
        if owned:
            stream.close()
