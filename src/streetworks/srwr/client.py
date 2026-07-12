"""Download client for SRWR Open Data archives.

The archives are published, credential-free, at ``https://downloads.srwr.scot``
under the Open Government Licence v3:

* ``/export/daily`` - the latest daily extract (automation endpoint)
* ``/export/{DD}.zip`` - one per day of the current month
* ``/export/{MMM}.zip`` - one per month of the current year (JAN, FEB, ...)
* ``/export/{YYYY}.zip`` - one per year
* ``/export/Historical{VV}.zip`` - pre-April-2018 history

The specification warns that archives are transiently unavailable while the
nightly roll-up runs, and asks consuming applications to include retry logic;
the shared transport's retry/backoff handles that here.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from .._transport import AsyncTransport, RetryConfig, SyncTransport
from .reader import Activity, Record, iter_activities, iter_records, latest_activities

__all__ = ["SRWRClient", "AsyncSRWRClient", "BASE_URL"]

BASE_URL = "https://downloads.srwr.scot/export"


def _check_is_archive(response: httpx.Response, path: str) -> None:
    """The export host serves an HTML file-list page at some URLs; catch the
    case where we fetched a page instead of an archive."""
    head = response.content[:64].lstrip()
    if head.startswith((b"<!", b"<html", b"<HTML")):
        raise ValueError(
            f"'{path}' returned an HTML page, not an archive - this URL is a "
            "file listing. Use download_archive() with an archive name such "
            "as '04.zip', or pass the direct file URL as base_url."
        )


class SRWRClient:
    """Fetch and read SRWR Open Data archives. No credentials required.

    >>> from streetworks.srwr import SRWRClient
    >>> with SRWRClient() as srwr:
    ...     path = srwr.download_daily("srwr-daily.zip")
    ...     for activity in srwr.iter_activities(path):
    ...         print(activity.activity_id, len(activity.records))
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 300.0,
        client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        # The export host redirects (e.g. /daily -> /daily/); browsers follow
        # silently, so the client must too.
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    # --- downloading ------------------------------------------------------ #

    def download_daily(self, dest: str | Path) -> Path:
        """Download the latest daily extract (the ``/daily`` automation
        endpoint) to ``dest`` and return its path."""
        return self._download("daily", dest)

    def download_archive(self, name: str, dest: str | Path) -> Path:
        """Download a named archive, e.g. ``"04.zip"``, ``"JUN.zip"``,
        ``"2025.zip"`` or ``"Historical01.zip"``."""
        return self._download(name, dest)

    def _download(self, path: str, dest: str | Path) -> Path:
        dest = Path(dest)
        response = self._transport.request("GET", f"{self.base_url}/{path}")
        _check_is_archive(response, path)
        dest.write_bytes(response.content)
        return dest

    # --- reading (thin wrappers over streetworks.srwr.reader) -------------- #

    @staticmethod
    def iter_records(source, **kwargs) -> iter[Record]:  # noqa: F821
        return iter_records(source, **kwargs)

    @staticmethod
    def iter_activities(source) -> iter[Activity]:  # noqa: F821
        return iter_activities(source)

    @staticmethod
    def latest_activities(source) -> iter[Activity]:  # noqa: F821
        return latest_activities(source)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> SRWRClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncSRWRClient:
    """Async twin of :class:`SRWRClient` for the download side; parsing is
    synchronous streaming either way."""

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 300.0,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        self._transport = AsyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    async def download_daily(self, dest: str | Path) -> Path:
        return await self._download("daily", dest)

    async def download_archive(self, name: str, dest: str | Path) -> Path:
        return await self._download(name, dest)

    async def _download(self, path: str, dest: str | Path) -> Path:
        dest = Path(dest)
        response = await self._transport.request("GET", f"{self.base_url}/{path}")
        _check_is_archive(response, path)
        dest.write_bytes(response.content)
        return dest

    iter_records = staticmethod(iter_records)
    iter_activities = staticmethod(iter_activities)
    latest_activities = staticmethod(latest_activities)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncSRWRClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
