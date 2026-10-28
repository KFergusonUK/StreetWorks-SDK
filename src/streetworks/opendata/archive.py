"""Street Manager Open Data archive - every Open Data event, as monthly zips.

DfT publishes the events behind the Street Manager Open Data feed (the same
messages the SNS feed pushes - see :mod:`streetworks.opendata`) as a public
archive: one zip per topic per month, at
``https://opendata.manage-roadworks.service.gov.uk/{topic}/{yyyy}/{mm}.zip``,
linked from DfT's "Archived notifications" page. No credentials or
registration. Licence: Open Government Licence v3.0, per the footer of the
DfT docs page that hosts the archive browser (the archive host itself states
none).

Confirmed live 2026-10-28, from the bucket listing, HEAD/GET requests and real
files:

* **Three topics**, no gaps: ``permit`` from 2020/07, ``activity`` from
  2020/09, ``section_58`` from 2022/03.
* **Published monthly**, normally on the 1st of the following month (June
  2026 came on 21 July). Months are cut at UK local midnight, not UTC: an
  event at ``2026-07-31T23:19Z`` (00:19 BST) is in the August file.
* **Sizes.** ``permit`` is about 0.85-1.2 GB a month (about 1.1 million
  events) and about 71 GB for the whole archive; ``activity`` is 10-25 MB a
  month; ``section_58`` 2-4 MB.
* **One event per zip member**, named
  ``{object_reference}_{event_type}_event_{date}_{time}-{n}.json``; each is
  the envelope :class:`~streetworks.opendata.EventNotification` models, and
  every ``object_data`` field seen matches DfT's Event Notifier Message
  schema. Names aren't parsed here: permit references can contain
  underscores, so the JSON is the only reliable source.
* **No duplicates seen** - none within a month, and none across Aug/Sep 2026
  for ``activity`` and ``section_58`` (by ``event_reference``, or by
  reference, event type and time). So nothing is de-duplicated.
* **The host is S3 behind CloudFront**: a public bucket listing (so
  :meth:`ArchiveClient.files` lists what's published rather than guessing),
  404 for a month not yet published, ``Accept-Ranges: bytes`` (so
  :meth:`ArchiveClient.download` resumes), and an ``ETag`` that is the file's
  MD5 (so downloads are verified).

Nothing here downloads anything unless asked: :meth:`ArchiveClient.download`
streams one file to disk, and :func:`iter_events` reads zips already on disk.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
import zlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from xml.etree import ElementTree

import httpx
from pydantic import ValidationError

from .._transport import RetryConfig, SyncTransport, _raise_for_response
from ..exceptions import NotFoundError, TransportError
from .models import EventNotification

__all__ = [
    "BASE_URL",
    "ArchiveClient",
    "ArchiveFile",
    "ReadStats",
    "Topic",
    "iter_events",
]

BASE_URL = "https://opendata.manage-roadworks.service.gov.uk"

_S3 = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
_KEY = re.compile(r"^(?P<topic>[a-z0-9_]+)/(?P<year>\d{4})/(?P<month>\d{2})\.zip$")
_MD5_ETAG = re.compile(r'^"?(?P<md5>[0-9a-f]{32})"?$')


class Topic(str, Enum):
    PERMIT = "permit"
    ACTIVITY = "activity"
    SECTION_58 = "section_58"


_TOPICS = frozenset(t.value for t in Topic)


@dataclass(frozen=True)
class ArchiveFile:
    """One published month, as the bucket listing describes it."""

    topic: Topic
    year: int
    month: int
    url: str
    size: int
    last_modified: str
    etag: str


class ArchiveClient:
    """List and download the Street Manager Open Data archive. No
    credentials required.

    >>> from streetworks.opendata.archive import ArchiveClient, Topic
    >>> with ArchiveClient() as arc:
    ...     arc.available(Topic.PERMIT, 2026, 9)
    ...     arc.download(Topic.PERMIT, 2026, 9, "sm/permit-2026-09.zip")  # ~1 GB
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 600.0,
        client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    def url(self, topic: Topic | str, year: int, month: int) -> str:
        """The URL a month's zip is (or will be) published at. No I/O."""
        if not 1 <= month <= 12:
            raise ValueError(f"month must be 1-12, got {month}")
        return f"{self.base_url}/{Topic(topic).value}/{year:04d}/{month:02d}.zip"

    def available(self, topic: Topic | str, year: int, month: int) -> bool:
        """Whether a month has been published yet (one ``HEAD``; a month not
        yet published is a 404)."""
        try:
            self._transport.request("HEAD", self.url(topic, year, month))
        except NotFoundError:
            return False
        return True

    def files(self, topic: Topic | str | None = None) -> list[ArchiveFile]:
        """Every published month, from the public bucket listing, by topic
        and oldest first - optionally for one topic. Keys that aren't a
        ``{topic}/{yyyy}/{mm}.zip`` for a known topic are left out."""
        params = {"list-type": "2"}
        if topic is not None:
            params["prefix"] = f"{Topic(topic).value}/"
        found: list[ArchiveFile] = []
        while True:
            root = ElementTree.fromstring(
                self._transport.request("GET", f"{self.base_url}/", params=params).content
            )
            for entry in root.findall("s3:Contents", _S3):
                key = entry.findtext("s3:Key", "", _S3)
                match = _KEY.match(key)
                if not match or match["topic"] not in _TOPICS:
                    continue
                found.append(
                    ArchiveFile(
                        topic=Topic(match["topic"]),
                        year=int(match["year"]),
                        month=int(match["month"]),
                        url=f"{self.base_url}/{key}",
                        size=int(entry.findtext("s3:Size", "0", _S3)),
                        last_modified=entry.findtext("s3:LastModified", "", _S3),
                        etag=entry.findtext("s3:ETag", "", _S3),
                    )
                )
            token = root.findtext("s3:NextContinuationToken", None, _S3)
            if root.findtext("s3:IsTruncated", "false", _S3) != "true" or not token:
                break
            params["continuation-token"] = token
        return sorted(found, key=lambda f: (f.topic.value, f.year, f.month))

    def download(
        self,
        topic: Topic | str,
        year: int,
        month: int,
        dest: str | Path,
        *,
        resume: bool = True,
        verify: bool = True,
    ) -> Path:
        """Stream one month's zip to ``dest`` and return its path.

        A permit month is about 1 GB; it is streamed in 1 MB chunks, never
        held in memory. Bytes go to ``dest`` + ``.part`` and are renamed into
        place only once complete, so an interrupted run never leaves a
        truncated file that looks like a good zip. With ``resume``, a
        leftover ``.part`` is continued with an HTTP ``Range`` request. With
        ``verify``, the finished file's MD5 is checked against the ``ETag``;
        if a resumed ``.part`` turns out to belong to an older copy of the
        file, it is discarded and the download restarted once from scratch.
        Raises :class:`~streetworks.exceptions.NotFoundError` for a month not
        yet published, and :class:`~streetworks.exceptions.TransportError` if
        the file doesn't match its ``ETag``.
        """
        url = self.url(topic, year, month)
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        head = self._transport.request("HEAD", url)
        size = int(head.headers["content-length"])
        etag = head.headers.get("etag", "")
        md5 = _MD5_ETAG.match(etag)

        for attempt in (1, 2):
            offset = part.stat().st_size if resume and part.exists() else 0
            if offset > size or (offset and not etag):
                offset = 0
            if offset < size:
                headers = {"Range": f"bytes={offset}-", "If-Range": etag} if offset else {}
                with self._client.stream("GET", url, headers=headers) as response:
                    if response.status_code >= 400:
                        response.read()
                        _raise_for_response(response)
                    if response.status_code != 206:
                        offset = 0  # whole file sent: it changed, or the range was ignored
                    with open(part, "ab" if offset else "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
            if part.stat().st_size != size:
                raise TransportError(
                    f"{url} downloaded {part.stat().st_size} of {size} bytes; "
                    f"run again to resume from {part}"
                )
            if not verify or md5 is None or _md5(part) == md5["md5"]:
                part.replace(dest)
                return dest
            part.unlink()
            if not offset or attempt == 2:
                raise TransportError(f"{url} does not match its ETag {etag} after download")
        raise AssertionError("unreachable")  # pragma: no cover

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> ArchiveClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class ReadStats:
    """Counts from one :func:`iter_events` pass - pass one in to see what was
    read and what was skipped."""

    zips: int = 0
    bad_zips: int = 0
    members: int = 0
    bad_members: int = 0
    events: int = 0


# iter_events filter -> the object_data field it matches. The names are the
# SNS MessageAttributes the live feed can be filtered on; ha_org and
# promoter_org carry SWA codes, not organisation names.
_FILTER_FIELDS = {
    "usrn": "usrn",
    "area": "area_name",
    "ha_org": "highway_authority_swa_code",
    "promoter_org": "promoter_swa_code",
    "activity_type": "activity_type",
}

FilterValue = str | int | Iterable[str | int] | None


def _as_set(value: FilterValue) -> frozenset[str] | None:
    if value is None:
        return None
    if isinstance(value, (str, int)):
        return frozenset({str(value)})
    return frozenset(str(v) for v in value)


def iter_events(
    source: str | Path,
    *,
    event_types: str | Iterable[str] | None = None,
    usrn: FilterValue = None,
    area: FilterValue = None,
    ha_org: FilterValue = None,
    promoter_org: FilterValue = None,
    activity_type: FilterValue = None,
    stats: ReadStats | None = None,
) -> Iterator[EventNotification]:
    """Yield the events in an archive zip, or in every zip under a folder
    (searched recursively, in name order), one member at a time.

    Every filter takes one value or a collection, and keeps an event whose
    value matches any of them; filters combine with AND. ``event_types``
    matches ``event_type`` (e.g. ``"PERMIT_SUBMITTED"``); the others match
    ``object_data`` and are named after the live feed's SNS
    MessageAttributes: ``usrn``, ``area`` (``area_name``), ``ha_org``
    (``highway_authority_swa_code``), ``promoter_org``
    (``promoter_swa_code``) and ``activity_type``. An event without the
    field doesn't match - activity and section 58 events carry no promoter,
    and section 58 events no ``activity_type``.

    A zip that won't open, or a member that won't decompress or isn't an
    event, is skipped and counted on ``stats`` - never raised.

    Memory: Python's ``zipfile`` reads a zip's whole member list on open.
    For a permit month (about 1.1 million members) that list holds about
    0.7 GB, peaking near 0.9 GB while it is read, until that zip is
    finished. Activity and section 58 months are small.
    """
    stats = stats if stats is not None else ReadStats()
    wanted_types = _as_set(event_types)
    filters = {
        "usrn": usrn,
        "area": area,
        "ha_org": ha_org,
        "promoter_org": promoter_org,
        "activity_type": activity_type,
    }
    wanted = {
        _FILTER_FIELDS[name]: values
        for name, value in filters.items()
        if (values := _as_set(value)) is not None
    }
    source = Path(source)
    zips = sorted(source.rglob("*.zip")) if source.is_dir() else [source]
    for path in zips:
        try:
            archive = zipfile.ZipFile(path)
        except (zipfile.BadZipFile, OSError):
            stats.bad_zips += 1
            continue
        stats.zips += 1
        with archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                stats.members += 1
                try:
                    raw = json.loads(archive.read(info))
                except (zipfile.BadZipFile, zlib.error, NotImplementedError, ValueError, OSError):
                    stats.bad_members += 1
                    continue
                if not isinstance(raw, dict):
                    stats.bad_members += 1
                    continue
                if wanted_types is not None and raw.get("event_type") not in wanted_types:
                    continue
                data = raw.get("object_data") or {}
                if any(
                    field not in data or str(data[field]) not in values
                    for field, values in wanted.items()
                ):
                    continue
                try:
                    event = EventNotification.model_validate(raw)
                except ValidationError:
                    stats.bad_members += 1
                    continue
                stats.events += 1
                yield event
