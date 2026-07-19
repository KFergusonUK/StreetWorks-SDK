"""BAG access: the credential-free PDOK Locatieserver (live search/suggest/
reverse/lookup) and Atom-feed-driven bulk downloads of the GeoPackage/XML
extract - see :mod:`streetworks.bag.atom` for why the download URL is
discovered, never hardcoded.

**The Locatieserver is a geocoding service, not the reference dataset** -
PDOK's own documentation says so plainly, and points elsewhere (the
GeoPackage/extract) for bulk retrieval; confirmed live that
``.../locatieserver/search/v3_1/openapi.json`` lists exactly four
endpoints (``/free``, ``/suggest``, ``/reverse``, ``/lookup``), matching
what's wrapped here. ``/reverse`` returns a **sparse** field set by
default (confirmed live: only ``id``/``weergavenaam``/``type``/``score``/
``afstand``) unlike ``/free``/``/suggest``/``/lookup``, which return the
full record without asking - so :meth:`BAGClient.reverse` passes ``fl="*"``
by default (overridable) to match the other three methods' richness rather
than surprise a caller with a thinner shape on this one endpoint alone.

Confirmed live: a missing/empty ``q`` on ``/free`` does **not** error (no
400) - it silently returns an arbitrary top-ranked match instead. Unlike
BAN's geocoding API, there is no request-validation error path to map here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport, _raise_for_response
from .atom import FEED_URL, AtomEntry, parse_feed
from .models import BAGLocation, location_from_doc

__all__ = ["BAGClient", "LOCATIESERVER_BASE_URL"]

LOCATIESERVER_BASE_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1"


def _locations_from_response(data: dict) -> list[BAGLocation]:
    docs = data.get("response", {}).get("docs", [])
    return [location_from_doc(doc) for doc in docs]


class BAGClient:
    """Dutch national address and buildings register (BAG) - live lookup via
    the PDOK Locatieserver, plus discovery + streamed download of the bulk
    GeoPackage/XML extract via the Atom feed. No credentials required.

    >>> from streetworks.bag import BAGClient
    >>> with BAGClient() as bag:
    ...     hits = bag.search("Dam 1 Amsterdam")
    ...     downloads = bag.discover_downloads()          # from the Atom feed
    ...     path = bag.download_geopackage("bag-light.gpkg")  # ~7.8 GB, streamed
    """

    def __init__(
        self,
        *,
        locatieserver_base_url: str = LOCATIESERVER_BASE_URL,
        feed_url: str = FEED_URL,
        retry: RetryConfig | None = None,
        timeout: float = 600.0,
        client: httpx.Client | None = None,
    ):
        self.locatieserver_base_url = locatieserver_base_url.rstrip("/")
        self.feed_url = feed_url
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=self._client
        )

    # --- Locatieserver (live) ---------------------------------------------- #

    def search(
        self, q: str, *, rows: int = 10, fq: str | None = None, **params: Any
    ) -> list[BAGLocation]:
        """Free-text search (``/free``) - addresses, streets, places,
        municipalities, hectometre posts and more, per PDOK's own type
        vocabulary. ``fq`` filters by source, e.g. ``fq="bron:BAG"``."""
        query: dict[str, Any] = {"q": q, "rows": rows, **params}
        if fq:
            query["fq"] = fq
        response = self._transport.request(
            "GET", f"{self.locatieserver_base_url}/free", params=query
        )
        return _locations_from_response(response.json())

    def suggest(
        self, q: str, *, rows: int = 10, fq: str | None = None, **params: Any
    ) -> list[BAGLocation]:
        """Type-ahead suggestions (``/suggest``) - lighter-weight than
        :meth:`search`, meant for interactive autocomplete."""
        query: dict[str, Any] = {"q": q, "rows": rows, **params}
        if fq:
            query["fq"] = fq
        response = self._transport.request(
            "GET", f"{self.locatieserver_base_url}/suggest", params=query
        )
        return _locations_from_response(response.json())

    def reverse(
        self,
        lon: float,
        lat: float,
        *,
        rows: int = 1,
        distance: float | None = None,
        fl: str = "*",
        **params: Any,
    ) -> list[BAGLocation]:
        """Reverse-geocode a WGS84 point (``/reverse``). ``fl="*"`` by
        default - see the module docstring for why. ``distance`` is a
        search radius in metres."""
        query: dict[str, Any] = {"lat": lat, "lon": lon, "rows": rows, "fl": fl, **params}
        if distance is not None:
            query["distance"] = distance
        response = self._transport.request(
            "GET", f"{self.locatieserver_base_url}/reverse", params=query
        )
        return _locations_from_response(response.json())

    def reverse_rd(
        self, x: float, y: float, *, rows: int = 1, distance: float | None = None, fl: str = "*"
    ) -> list[BAGLocation]:
        """Reverse-geocode an RD (EPSG:28992) point - confirmed live as an
        equally valid ``/reverse`` input alongside WGS84 lat/lon."""
        query: dict[str, Any] = {"X": x, "Y": y, "rows": rows, "fl": fl}
        if distance is not None:
            query["distance"] = distance
        response = self._transport.request(
            "GET", f"{self.locatieserver_base_url}/reverse", params=query
        )
        return _locations_from_response(response.json())

    def lookup(self, id: str) -> BAGLocation | None:
        """Fetch one result by its Locatieserver ``id`` (e.g. as returned
        by :meth:`search`/:meth:`suggest`)."""
        response = self._transport.request(
            "GET", f"{self.locatieserver_base_url}/lookup", params={"id": id}
        )
        locations = _locations_from_response(response.json())
        return locations[0] if locations else None

    # --- bulk files (Atom feed discovery + streamed download) ------------- #

    def discover_downloads(self) -> list[AtomEntry]:
        """Parse the Atom feed and return every real download it currently
        offers - never a hardcoded URL, see :mod:`streetworks.bag.atom`."""
        response = self._transport.request("GET", self.feed_url)
        return parse_feed(response.content)

    def download_geopackage(self, dest: str | Path) -> Path:
        """Stream the current history-free GeoPackage (~7.8 GB, confirmed
        live 2026-07) to ``dest`` - its real URL is resolved from the Atom
        feed on every call, not cached across releases."""
        entry = self._find_download("application/geopackage+sqlite3")
        return self._download(entry.url, dest)

    def download_extract(self, dest: str | Path) -> Path:
        """Stream the current full-history XML extract zip (~3.6 GB,
        confirmed live 2026-07) to ``dest``. This SDK does not parse it -
        see :mod:`streetworks.bag.models` for what it contains and why."""
        entry = self._find_download("application/zip")
        return self._download(entry.url, dest)

    def _find_download(self, media_type: str) -> AtomEntry:
        entries = self.discover_downloads()
        for entry in entries:
            if entry.media_type == media_type:
                return entry
        raise ValueError(
            f"no {media_type!r} entry in the current Atom feed - PDOK may "
            f"have changed the feed's shape, see {self.feed_url}"
        )

    def _download(self, url: str, dest: str | Path) -> Path:
        dest = Path(dest)
        with self._client.stream("GET", url) as response:
            if response.status_code >= 400:
                response.read()
                _raise_for_response(response)
            with open(dest, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        return dest

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> BAGClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
