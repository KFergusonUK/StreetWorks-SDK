"""Client for Via Lietuva's open roadworks data on data.gov.lt.

Open CSV/JSON dump, no credentials, no key - confirmed live. This is the
**open data.gov.lt route, not the RTTI NAP NAPCORE lists** - the listed NAP
is agreement-gated and returns 403 without one; this dataset
("Eismo ribojimai valstybinės reikšmės keliuose" - traffic restrictions on
state roads, provider Via Lietuva) is published separately, openly, under
**CC BY 4.0** (confirmed via the dataset's own licence field on
data.gov.lt), no agreement needed.

A "Saugykla" storage/query API also exists for this dataset; the plain
``:format/csv`` full-dump route was used instead since it's simpler, needs
no query construction, and was confirmed live to return every row in one
request (no pagination to handle) - `.get_table()` is generic enough to
call any of the dataset's four tables, not just the two modelled here.
"""

from __future__ import annotations

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import RoadRepair, RoadSection
from .parser import parse_road_repairs, parse_road_sections

__all__ = ["BASE_URL", "TABLE_ROAD_REPAIRS", "TABLE_ROAD_SECTIONS", "ViaLietuvaClient"]

BASE_URL = "https://get.data.gov.lt"

#: The roadworks core - see the module docstring in ``models.py`` for why
#: the other two restriction tables (``Kliutis``, ``Renginys``) aren't
#: fetched here.
TABLE_ROAD_REPAIRS = "Remontas"

#: State road reference data - gazetteer-shaped, not roadworks. See the
#: module docstring in ``models.py``.
TABLE_ROAD_SECTIONS = "KelioAtkarpa"

_TABLE_PATH = "datasets/gov/via_lietuva/eismo_ribojimai/{table}/:format/csv"


class ViaLietuvaClient:
    """Fetch Lithuania's national roadworks (Via Lietuva, via data.gov.lt).
    No credentials required.

    >>> from streetworks.vialietuva import ViaLietuvaClient
    >>> from streetworks.common import from_vialietuva
    >>> with ViaLietuvaClient() as lt:
    ...     repairs = lt.road_repairs()
    ...     sections = lt.road_sections()  # gazetteer-shaped lookup, not Works
    >>> works = from_vialietuva(repairs)
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

    def get_table(self, table: str) -> str:
        """``GET`` one of the dataset's tables (e.g. ``TABLE_ROAD_REPAIRS``)
        as raw CSV text."""
        response = self._transport.request(
            "GET", f"{self.base_url}/{_TABLE_PATH.format(table=table)}"
        )
        return response.text

    def road_repairs(self) -> list[RoadRepair]:
        """The ``Remontas`` table, parsed - Lithuania's roadworks core."""
        return parse_road_repairs(self.get_table(TABLE_ROAD_REPAIRS))

    def road_sections(self) -> dict[str, RoadSection]:
        """The ``KelioAtkarpa`` table, parsed and keyed by ``road_id`` -
        gazetteer-shaped reference data, not roadworks. Confirmed live:
        every :attr:`~.models.RoadRepair.road_id` from :meth:`road_repairs`
        has a matching entry here."""
        return parse_road_sections(self.get_table(TABLE_ROAD_SECTIONS))

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> ViaLietuvaClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
