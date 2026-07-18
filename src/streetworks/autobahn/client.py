"""Client for Autobahn GmbH's national motorway roadworks API.

Open REST API, no credentials, no key - confirmed live. "All national
motorway roadworks" means fetching the road list, then one call per road
(113 real roads at time of writing, confirmed all 113/113 resolve without
error); there's no single all-roads endpoint. :meth:`AutobahnClient.roadworks`
takes each road id exactly as :meth:`AutobahnClient.list_roads` returned
it - **do not strip or reformat it**. One real entry, ``"A60 "``, carries a
trailing space, and it is not simply a formatting quirk on the one real
A60: the road list carries *two* separate entries, a plain ``"A60"`` and
this space-suffixed one, and they are genuinely different as far as the
API is concerned - confirmed live, ``GET .../A60/...`` returns 20 real
roadworks, ``GET .../A60%20/...`` (the listed id, correctly percent-encoded,
not stripped) returns zero. Stripping the space would silently refetch
the *other* entry's 20 records under the wrong road id, double-counting
them in an all-roads iteration - so despite looking like noise, the space
must survive untouched into the request.
"""

from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import quote

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Roadworks
from .parser import parse_roadworks

__all__ = ["BASE_URL", "AutobahnClient"]

BASE_URL = "https://verkehr.autobahn.de/o/autobahn"


class AutobahnClient:
    """Fetch German national motorway roadworks from Autobahn GmbH. No
    credentials required.

    >>> from streetworks.autobahn import AutobahnClient
    >>> with AutobahnClient() as autobahn:
    ...     roads = autobahn.list_roads()
    ...     a1_roadworks = autobahn.roadworks("A1")
    ...     for item in autobahn.iter_all_roadworks(roads):
    ...         print(item.road, item.title, item.start)
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def list_roads(self) -> list[str]:
        """``GET /`` - every road id currently published. Use these ids
        exactly as returned when calling :meth:`roadworks` - see module
        docstring."""
        response = self._transport.request("GET", f"{self.base_url}/")
        payload = response.json()
        return list(payload.get("roads") or ())

    def roadworks(self, road: str) -> list[Roadworks]:
        """``GET /{road}/services/roadworks`` for one road id, parsed. Pass
        ``road`` exactly as :meth:`list_roads` returned it - do not
        strip/upper-case it (see module docstring for why)."""
        response = self._transport.request(
            "GET", f"{self.base_url}/{quote(road)}/services/roadworks"
        )
        return parse_roadworks(response.json(), road)

    def iter_all_roadworks(self, roads: list[str] | None = None) -> Iterator[Roadworks]:
        """Fetch every road's roadworks in sequence (one request per road -
        ~113 as of this writing, no bulk endpoint exists) and yield every
        record flat, each carrying its own ``road``. Pass ``roads`` to fetch
        a subset instead of calling :meth:`list_roads` first."""
        for road in roads if roads is not None else self.list_roads():
            yield from self.roadworks(road)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> AutobahnClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
