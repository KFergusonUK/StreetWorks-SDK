"""Streaming readers for SRWR Open Data extract files.

The archives can be very large (a monthly file runs to millions of records),
so everything here streams: records are yielded one at a time and activities
are assembled from contiguous runs, without ever loading a whole file.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import IO

from .records import Record, parse_row

__all__ = ["iter_records", "iter_activities", "latest_activities", "Activity"]


class Activity:
    """All records for one Activity, grouped from a contiguous run.

    ``records`` preserves extract order. Convenience accessors expose the
    common record types; anything else is reachable via :meth:`of_type`.
    """

    __slots__ = ("activity_id", "records")

    def __init__(self, activity_id: int, records: list[Record]):
        self.activity_id = activity_id
        self.records = records

    def of_type(self, record_type: str) -> list[Record]:
        return [r for r in self.records if r.record_type == record_type]

    @property
    def activity(self) -> Record | None:
        """The 001 Activity record, if present."""
        found = self.of_type("001")
        return found[0] if found else None

    @property
    def streets(self) -> list[Record]:
        return self.of_type("004")

    @property
    def notices(self) -> list[Record]:
        return self.of_type("006")

    @property
    def phases(self) -> list[Record]:
        return self.of_type("007")

    @property
    def undertaker_phases(self) -> list[Record]:
        return self.of_type("008")

    @property
    def sites(self) -> list[Record]:
        return self.of_type("010")

    @property
    def inspections(self) -> list[Record]:
        return self.of_type("015")

    @property
    def fixed_penalty_notices(self) -> list[Record]:
        return self.of_type("019")

    def __repr__(self) -> str:
        return f"<Activity {self.activity_id} ({len(self.records)} records)>"


def _open_text(source: str | Path | IO[str]) -> tuple[IO[str], bool]:
    """Return a text stream for ``source`` and whether we own (must close) it.

    Accepts a path to a ``.csv``, a path to a ``.zip`` archive (the first
    ``.csv`` member is used), or an already-open text stream.
    """
    if hasattr(source, "read"):
        return source, False  # caller's stream, caller's responsibility
    path = Path(source)
    if path.suffix.lower() == ".zip":
        archive = zipfile.ZipFile(path)
        members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not members:
            archive.close()
            raise ValueError(f"no CSV member found in {path}")
        raw = archive.open(members[0])
        # utf-8-sig strips a BOM if present.
        return io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""), True
    return open(path, encoding="utf-8-sig", newline=""), True


def iter_records(
    source: str | Path | IO[str],
    *,
    record_types: Iterable[str] | None = None,
) -> Iterator[Record]:
    """Stream :class:`~streetworks.srwr.records.Record` objects from an
    extract file (a ``.csv``, a ``.zip`` archive, or an open text stream).

    ``record_types`` optionally filters to a set of type codes, e.g.
    ``("001", "007")``. Blank lines are skipped.
    """
    wanted = set(record_types) if record_types is not None else None
    stream, owned = _open_text(source)
    try:
        for row in csv.reader(stream):
            if not row:
                continue
            if wanted is not None and (len(row) < 2 or row[1] not in wanted):
                continue
            yield parse_row(row)
    finally:
        if owned:
            stream.close()


def iter_activities(source: str | Path | IO[str]) -> Iterator[Activity]:
    """Stream :class:`Activity` bundles.

    Although the specification describes an Activity's records as contiguous,
    real published extracts are sorted by Record Type, so grouping requires
    collecting a whole *daily section* before its Activities can be emitted.
    Each daily extract begins with a ``000`` Licensing record; in monthly and
    yearly archives (concatenations of dailies) those headers delimit the
    sections. Memory use is therefore bounded by the largest single day, not
    the whole file. Activities are yielded in first-seen order per section;
    records without an Activity ID (the header, 003 Project, 098/099
    reference data) are not attached to any Activity.
    """
    section: dict[int, list[Record]] = {}

    def flush() -> Iterator[Activity]:
        for aid, records in section.items():
            yield Activity(aid, records)
        section.clear()

    for record in iter_records(source):
        if record.record_type == "000":
            yield from flush()
            continue
        aid = record.activity_id
        if aid is None:
            continue
        section.setdefault(aid, []).append(record)
    yield from flush()


def latest_activities(source: str | Path | IO[str]) -> Iterator[Activity]:
    """Yield each Activity once, keeping only its **latest** occurrence.

    Monthly and yearly archives are concatenations of daily extracts, so an
    Activity updated several times appears once per day it changed; the
    specification's rule is that the most recent occurrence supersedes the
    rest. This holds the latest bundle for every Activity seen, so memory
    grows with the number of distinct Activities in the file - comfortable
    for daily archives, but for monthly/yearly archives on constrained
    machines prefer processing day by day via :func:`iter_activities`.
    """
    latest: dict[int, Activity] = {}
    for activity in iter_activities(source):
        latest[activity.activity_id] = activity
    yield from latest.values()
