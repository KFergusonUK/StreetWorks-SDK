"""Client for Servei Català de Trànsit's (SCT) real-time road incidents feed.

Open, credential-free, plain ``GET`` on a fixed URL - confirmed live,
2026-07. No WFS query parameters to construct: this is a continuously-
refreshed snapshot dump (the dataset's own metadata states
"Freqüència d'actualització: Contínua"), not a parameterised service - the
same access shape as NDW's or Luxembourg's fixed-URL DATEX downloads, not
a queryable WFS endpoint (the feed's own ``xsi:schemaLocation`` points at
a ``localhost:8080`` WFS reference that isn't externally reachable -
checked directly, confirmed a rendering artefact, not a real access
point).
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Incident
from .parser import parse_incidents

__all__ = ["BASE_URL", "INCIDENTS_PATH", "SCTClient"]

BASE_URL = "http://www.gencat.cat"
INCIDENTS_PATH = "transit/opendata/incidenciesGML.xml"


class SCTClient:
    """Fetch Catalonia's real-time road incidents (Servei Català de
    Trànsit). No credentials required.

    >>> from streetworks.sct import SCTClient
    >>> from streetworks.common import from_sct
    >>> with SCTClient() as sct:
    ...     incidents = list(sct.iter_roadworks())
    >>> works = from_sct(incidents)
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def get_incidents(self) -> bytes:
        """``GET incidenciesGML.xml`` - the raw WFS/GML response body (every
        current incident, not filtered)."""
        response = self._transport.request("GET", f"{self.base_url}/{INCIDENTS_PATH}")
        return response.content

    def iter_incidents(self) -> Iterator[Incident]:
        """Every current incident, unfiltered - includes ``Retenció``
        (congestion) and ``Cons`` (temporary lane measures) alongside
        ``Obres`` (roadworks). Use :meth:`iter_roadworks` for roadworks
        only."""
        yield from parse_incidents(self.get_incidents())

    def iter_roadworks(self) -> Iterator[Incident]:
        """Like :meth:`iter_incidents`, filtered to
        :attr:`~streetworks.sct.models.Incident.is_roadworks` (real
        ``descripcio_tipus == "Obres"`` records - see
        :mod:`streetworks.sct.models`)."""
        for incident in self.iter_incidents():
            if incident.is_roadworks:
                yield incident

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> SCTClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
