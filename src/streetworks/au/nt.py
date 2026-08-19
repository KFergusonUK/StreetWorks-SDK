"""Northern Territory: Road Report NT (Department of Infrastructure,
Planning and Logistics - DIPL, since renamed Department of Logistics and
Infrastructure - DLI; the agency name is itself in flux).

.. attention::
   **Confirmed live (2026-08-19)** against a real, unauthenticated pull of
   ``GET https://roadreport.nt.gov.au/api/Obstruction/GetAll`` (140
   CURRENT records, 26 of them ``obstructionType == "Roadworks"``).
   Credential-free. **Licence genuinely unconfirmed** - no reuse statement
   was found on the site or any catalogue listing, the same unconfirmed
   basis :mod:`streetworks.au.tas` / :mod:`streetworks.arcgis.jersey`
   already ship on. This is a working adapter, not the
   ``ProviderUnavailableError`` scaffold it used to be.

**Coverage** (from ``roadreport.nt.gov.au``'s own public description):
all NT-Government-managed roads statewide, including remote/unsealed and
Aboriginal-land access roads - **council roads excluded** (the site
directs those inquiries to the relevant local council instead).

**Nature - still a road-*condition* system.** The live GetAll mix is
dominated by weight/vehicle-type restrictions, changing surface
conditions, road damage and flooding. Roadworks is a real, official
subset - 26/140 on the 2026-08-19 pull - not the whole feed.
``roadreport.nt.gov.au/terminology`` defines Roadwork as construction,
repair or maintenance in the road reserve. :meth:`RoadReportNtClient.iter_roadworks`
therefore returns only records that are actually works
(``obstructionType == "Roadworks"``, type-code ``28``). Every other
obstruction type stays reachable via :meth:`iter_obstructions` for a
conditions/routing consumer, and is **not** mapped onto
:class:`~streetworks.common.Works`.

**The public JSON endpoint, not the SignalR hub.** Earlier investigation
of the minified Angular frontend found an undocumented SignalR hub
(``roadsReportingHub`` / ``GetAllMajorRoadObstructions``). That hub is
still not consumed here - encoding reverse-engineered hub internals as
a stable contract is out of scope, the same distinction this SDK draws
everywhere else. The adapter talks only to the ordinary HTTP JSON
endpoint the site itself exposes at ``/api/Obstruction/GetAll``.

**Envelope, confirmed live:** ``{ success, message, response: [...] }``
(plus a JSON.NET ``$id``). HTTP 200 on the confirmation pull;
``success`` was ``true``; ``message`` was ``null``. No pagination - one
response held every current record (140 items, ~106 KB), matching the
endpoint's own "GetAll" name. ``status`` was ``"CURRENT"`` on 140/140.

**Real field list** (every key present on 140/140 unless noted):
``recordId`` / ``obstructionId`` (both unique across the pull;
``Works.reference`` uses ``obstructionId`` as the obstruction's own id,
not the JSON.NET ``$id`` and not ``recordId``), ``status``, ``road`` /
``roadName``, ``lane``, ``prpFrom`` / ``distanceFrom`` / ``prpTo`` /
``distanceTo``, ``obstructionType`` / ``obstructionTypeCode``,
``restrictionType`` / ``restrictionTypeCode``, ``dateFrom`` (always
populated) / ``dateTo`` (**0/140 populated** on this pull - mapped when
present, usually ``None``), ``dateActive`` (139/140),
``dateLastUpdated``, ``startPoint`` / ``endPoint`` (``[lat, lon]``
arrays, not GeoJSON), ``comment``, ``locationComment``,
``isDefaultLocationComment``, ``reversed``. ``geometry`` and
``geometries`` were empty on every record - line/point geometry is
taken from the start/end points only.

**Dates are naive local-looking ``YYYY-MM-DD HH:MM:SS`` strings** - no
offset, no ``Z``, no stated timezone. Parsed as naive datetimes, never
assigned ACST/ACDT, because the source does not state one.

**Licence**: not specified on any catalogue listing found.

**Credentials**: none. Confirmed live - the GetAll pull succeeded with
no authentication.
"""

from __future__ import annotations

from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport
from ..exceptions import StreetworksError

__all__ = [
    "BASE_URL",
    "GETALL_PATH",
    "ROADWORKS_TYPE",
    "ROADWORKS_TYPE_CODE",
    "RoadReportNtClient",
    "is_roadworks",
]

JSON = dict[str, Any]

BASE_URL = "https://roadreport.nt.gov.au"
GETALL_PATH = "/api/Obstruction/GetAll"

#: Official Road Report NT terminology for construction / repair /
#: maintenance in the road reserve. Confirmed live as the only works
#: type in the GetAll mix (26/140 records, 2026-08-19).
ROADWORKS_TYPE = "Roadworks"
ROADWORKS_TYPE_CODE = "28"


def is_roadworks(record: JSON) -> bool:
    """True when a GetAll record is actually works - the official
    ``Roadworks`` type (code ``28``). Other obstruction types are
    conditions (weight limits, flooding, surface damage) and stay out
    of :meth:`RoadReportNtClient.iter_roadworks`."""
    if record.get("obstructionType") == ROADWORKS_TYPE:
        return True
    code = record.get("obstructionTypeCode")
    return code == ROADWORKS_TYPE_CODE or code == 28


class RoadReportNtClient:
    """Fetch current NT-Government road obstructions from Road Report
    NT's public ``GET /api/Obstruction/GetAll`` JSON endpoint. No
    credentials required - see module docstring.

    >>> from streetworks.au.nt import RoadReportNtClient
    >>> from streetworks.common import from_au_nt_roadreport
    >>> with RoadReportNtClient() as nt:  # doctest: +SKIP
    ...     works_list = from_au_nt_roadreport(nt.iter_roadworks())
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

    def get_obstructions(self) -> JSON:
        """``GET /api/Obstruction/GetAll`` - every current obstruction,
        all types mixed, as the live envelope
        ``{success, message, response: [...]}``. No pagination (confirmed
        live: one response held the full current set). Returns the parsed
        JSON envelope."""
        response = self._transport.request("GET", f"{self.base_url}{GETALL_PATH}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise StreetworksError(
                "Road Report NT GetAll returned a non-object JSON payload"
            )
        if payload.get("success") is False:
            raise StreetworksError(
                f"Road Report NT GetAll reported success=false: {payload.get('message')!r}"
            )
        return payload

    def iter_obstructions(self) -> list[JSON]:
        """Every current obstruction in ``response``, every type -
        roadworks, weight/vehicle restrictions, flooding, surface
        conditions, and the rest. See :meth:`iter_roadworks` for the
        works-only convenience."""
        payload = self.get_obstructions()
        items = payload.get("response") or []
        return [item for item in items if isinstance(item, dict)]

    def iter_roadworks(self) -> list[JSON]:
        """``obstructionType == "Roadworks"`` (code ``28``) only - the
        official works slice of a conditions-dominated feed (26/140 on
        the 2026-08-19 pull). Other types stay out of this iterator."""
        return [item for item in self.iter_obstructions() if is_roadworks(item)]

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> RoadReportNtClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
