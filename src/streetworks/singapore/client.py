"""LTA DataMall (Singapore) - the Land Transport Authority's national
roadworks/traffic-incidents feed.

.. attention::
   **PENDING LIVE VERIFICATION.** This module is built entirely from LTA's
   own official, current API documentation - the "LTA DataMall API User
   Guide & Documentation", Version 6.9 (3 Aug 2026), fetched live
   (``datamall.lta.gov.sg/content/dam/datamall/datasets/LTA_DataMall_API_User_Guide.pdf``)
   - and from a real, live, unauthenticated request confirming the auth
   mechanism and endpoint shape (a ``GET`` with a placeholder ``AccountKey``
   header returns a genuine ``401`` on both real endpoints, not a ``404`` -
   confirming the paths and the header name, not the response schema). No
   real authenticated response has been seen. No API key was obtained on
   the caller's behalf - registration is self-service ("Request for API
   Access" on datamall.lta.gov.sg), not a formal contract, so this is a
   **Credentials-wanted** scaffold, not a dead end.

**Three real, complementary datasets, genuinely different shapes - found by
reading the spec, not guessed:**

- ``RoadWorks`` ("Approved Road Works") - road works currently
  approved/being carried out. Real fields: ``EventID``, ``StartDate``,
  ``EndDate`` (both ``YYYY-MM-DD``), ``SvcDept`` (the department or
  company performing the work - a real applicant-style field, the same
  role Vienna's/NYC DOT's own applicant fields already play in this SDK),
  ``RoadName``, ``Other`` (free-text messages). **No coordinates at all**
  - a genuine, documented gap, not a parsing omission. Updated every 24
  hours.
- ``RoadOpenings`` ("Planned Road Openings") - the same real field shape
  as ``RoadWorks``, a genuinely separate dataset (new-road-opening events,
  not works-in-progress) rather than a duplicate. Also no coordinates,
  also 24-hour updates.
- ``TrafficIncidents`` - live current-road-incident feed, 2-minute update
  frequency, genuinely different shape again: real fields ``Type`` (an
  explicit 13-value enum - ``Accident``, **``Roadwork``**, ``Vehicle
  breakdown``, ``Weather``, ``Obstacle``, ``Road Block``, ``Heavy
  Traffic``, ``Miscellaneous``, ``Diversion``, ``Unattended Vehicle``,
  ``Fire``, ``Plant Failure``, ``Reverse Flow``), ``Latitude``/
  ``Longitude`` (a real point, unlike the other two datasets), and
  ``Message`` (free text). **No id field and no dates at all** - a real,
  documented gap in the opposite direction from ``RoadWorks``/
  ``RoadOpenings``. ``Type == "Roadwork"`` is the real, spec-stated
  roadworks filter for this dataset - confirmed by the enum's own
  documented label, not inferred.

**Auth**: a single ``AccountKey`` header, confirmed live (a placeholder
value returns a real ``401``, not a ``404``, on both ``RoadWorks`` and
``TrafficIncidents``). Response envelope is real OData shape -
``{"odata.metadata": "...", "value": [...]}`` - **paginated at 500 records
per call**, documented explicitly: append ``?$skip=500``/``$skip=1000``/...
to fetch subsequent pages; a response's own record count, not a stated
total, is the only way to know when to stop (an empty ``value`` array
signals the end - not yet confirmed against a real response, since no
authenticated pull has been made).

**Licence**: Singapore Open Data Licence v1.0 - confirmed via LTA's own
published licence page (worldwide, perpetual, royalty-free, non-exclusive,
commercial use explicitly permitted). Rate limit: 10,000,000 calls/day
(LTA's own stated API Terms of Service figure) - generous, no throttling
logic needed here.

**Credentials**: free self-service registration ("Request for API Access"
on `datamall.lta.gov.sg <https://datamall.lta.gov.sg/content/datamall/en.html>`_)
issues an ``AccountKey``. Env var: ``SINGAPORE_LTA_ACCOUNT_KEY`` (see
``.env.example``, ``scripts/smoke_test.py``).

**What's still open until a real key is used**:

1. Whether the empty-``value``-array pagination end condition is correct,
   or whether LTA signals "no more pages" a different way (e.g. a record
   count under 500 on the final page, which this client also treats as a
   stop signal defensively).
2. Whether ``SvcDept``/``Other``/``Message`` ever contain structured data
   beyond free text (unconfirmed either way from the spec alone).
3. Real record volumes and whether ``RoadWorks``/``RoadOpenings`` ever
   exceed one page (500 records) in practice.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "ROADWORK_INCIDENT_TYPE", "SingaporeClient"]

warnings.warn(
    "streetworks.singapore is a Credentials-wanted scaffold: built to LTA "
    "DataMall's own current, official API User Guide (see module "
    "docstring), not yet verified against a real authenticated response. "
    "Have an LTA DataMall AccountKey (free self-service registration)? "
    "Running the smoke test and reporting back one real trimmed record "
    "from each of RoadWorks/RoadOpenings/TrafficIncidents would confirm "
    "this adapter - see the 'help wanted' issues at "
    "https://github.com/KFergusonUK/StreetWorks-SDK/issues for exactly "
    "what's needed.",
    UserWarning,
    stacklevel=2,
)

JSON = dict[str, Any]

BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"

#: The real, spec-documented roadworks value within TrafficIncidents'
#: own Type enum - see module docstring.
ROADWORK_INCIDENT_TYPE = "Roadwork"

_PAGE_SIZE = 500


class SingaporeClient:
    """Fetch LTA DataMall's roadworks-relevant datasets. Requires a real
    ``AccountKey`` (free self-service registration - see module
    docstring). **Pending live verification.**

    >>> from streetworks.singapore import SingaporeClient
    >>> from streetworks.common import from_singapore
    >>> with SingaporeClient(account_key=account_key) as client:  # doctest: +SKIP
    ...     works_list = from_singapore(list(client.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        account_key: str,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not account_key:
            raise ValueError("account_key is required - see module docstring")
        self.base_url = base_url.rstrip("/")
        owned_client = client or httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"AccountKey": account_key, "accept": "application/json"},
        )
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def _iter_paginated(self, path: str) -> Iterator[JSON]:
        skip = 0
        while True:
            response = self._transport.request(
                "GET", f"{self.base_url}/{path}", params={"$skip": skip} if skip else None
            )
            page = response.json().get("value") or []
            yield from page
            if len(page) < _PAGE_SIZE:
                return
            skip += _PAGE_SIZE

    def iter_road_works(self) -> Iterator[JSON]:
        """Real "Approved Road Works" records - see module docstring."""
        for record in self._iter_paginated("RoadWorks"):
            yield {**record, "kind": "road_works"}

    def iter_road_openings(self) -> Iterator[JSON]:
        """Real "Planned Road Openings" records - a genuinely separate
        dataset from :meth:`iter_road_works`, see module docstring."""
        for record in self._iter_paginated("RoadOpenings"):
            yield {**record, "kind": "road_openings"}

    def iter_traffic_incidents(self) -> Iterator[JSON]:
        """Every real current traffic incident, unfiltered - includes
        non-roadworks types (accidents, breakdowns, weather, ...). See
        module docstring."""
        for record in self._iter_paginated("TrafficIncidents"):
            yield {**record, "kind": "incident"}

    def iter_roadworks(self) -> Iterator[JSON]:
        """Combines all three real roadworks-relevant sources -
        ``RoadWorks``, ``RoadOpenings``, and ``TrafficIncidents`` filtered
        to ``Type == "Roadwork"``. See module docstring."""
        yield from self.iter_road_works()
        yield from self.iter_road_openings()
        for record in self.iter_traffic_incidents():
            if record.get("Type") == ROADWORK_INCIDENT_TYPE:
                yield record

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> SingaporeClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
