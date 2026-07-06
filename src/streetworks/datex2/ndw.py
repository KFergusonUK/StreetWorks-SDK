"""NDW (Netherlands) open-data source for DATEX II roadworks.

NDW publishes the Dutch national roadworks and events data, credential-free,
on its open data portal. The planned-works feed is a gzipped DATEX II v3
SituationPublication.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["NDWClient", "BASE_URL", "PLANNED_WORKS_FEED", "CURRENT_STATUS_FEED"]

BASE_URL = "https://opendata.ndw.nu"

#: The complete roadworks & events feed - planned *and* current (DATEX II v3,
#: gzipped XML, ~14 MB). Verified against the live NDW Open Data Portal
#: directory listing. (A browser may save it with the final dot turned into an
#: underscore; the portal path keeps the dot before ``xml``.)
PLANNED_WORKS_FEED = "planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz"

#: Current/active status messages only (a smaller feed on the same portal).
CURRENT_STATUS_FEED = "actueel_beeld.xml.gz"


class NDWClient:
    """Download NDW open-data feeds. No credentials required.

    >>> from streetworks.datex2 import NDWClient, iter_roadworks
    >>> with NDWClient() as ndw:
    ...     feed = ndw.download_planned_works("ndw-works.xml.gz")
    >>> for situation in iter_roadworks(feed):
    ...     print(situation.id, situation.roadworks[0].source_name)
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
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def download(self, name: str, dest: str | Path) -> Path:
        """Download a named feed file from the portal to ``dest``."""
        dest = Path(dest)
        response = self._transport.request("GET", f"{self.base_url}/{name}")
        dest.write_bytes(response.content)
        return dest

    def download_planned_works(self, dest: str | Path) -> Path:
        """Download the planned roadworks & events feed (~15 MB gzipped)."""
        return self.download(PLANNED_WORKS_FEED, dest)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> NDWClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
