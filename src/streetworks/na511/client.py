"""North American "511" REST platform - one commercial API shape reused,
byte-for-byte identically, by multiple independent government agencies.
Found while surveying the Canadian provinces beyond British Columbia
(see :mod:`streetworks.drivebc`) for roadworks coverage: Ontario 511,
511 Alberta and Saskatchewan's Highway Hotline all publish the exact
same ``/api/v2/get/event`` endpoint shape, confirmed live by comparing
Ontario's real, unauthenticated response against Alberta's own published
field-by-field API documentation - every field name, type and the
``EventType`` enum (``"roadwork"``/``"closures"``/``"accidentsAndIncidents"``)
match exactly. Nevada's own US 511 API (see the WZDx-adjacent US survey
in ``docs/providers/us.md``) shares the identical ``/developers/doc`` URL
convention too, though not independently confirmed to be the same
platform.

**Ontario is a genuine, confirmed exception: keyless.** A plain
``GET https://511on.ca/api/v2/get/event`` returns real data with **no**
``key`` parameter at all (confirmed live, 595 real events, 2026-08-21) -
despite the site's own "Sign up for an account" prompt, which turns out
to gate only the human-facing My511 personalisation features, not the
API itself. **Alberta and Saskatchewan both require one** - confirmed
live via each host's own real, structured rejection
(``{"Error":{"Message":"Invalid Key"}}``) on the identical endpoint with
no ``key`` supplied, and Alberta's own API docs explicitly state
``key: Developer Key, Required``. This SDK does not obtain that key on a
caller's behalf - see :mod:`streetworks.wzdx.client`'s own module
docstring for the identical Massachusetts CWZ situation and reasoning.

**Because Ontario's real, keyless response already proves this exact
schema correct, Alberta/Saskatchewan aren't a guess the way this SDK's
DATEX "Credentials-wanted scaffold" adapters are** (e.g.
:mod:`streetworks.datex2.trafikverket`) - the field names, types and the
``EventType`` roadworks discriminator are drawn from a real, live,
unauthenticated pull against the identical platform, not documentation
alone. What's still genuinely unconfirmed for Alberta/Saskatchewan
specifically is only whether their own authenticated response round-trips
through this exact parsing unchanged - everything else is as confirmed as
this SDK's fully shipped providers.

**Real fields** (confirmed live via Ontario's response, cross-checked
field-for-field against Alberta's own published docs): ``ID``,
``SourceId``, ``Organization``, ``RoadwayName``, ``DirectionOfTravel``,
``Description``, ``Reported``/``LastUpdated``/``StartDate``/
``PlannedEndDate`` (Unix epoch **seconds**, confirmed by magnitude - not
milliseconds, unlike this SDK's ArcGIS-sourced epoch fields elsewhere),
``LanesAffected``, ``Latitude``/``Longitude`` (plain WGS84 decimal
fields, not GeoJSON - already ``(lat, lon)`` order, no flip needed),
``EventType``, ``EventSubType`` (real but 0/590 populated in the sample
pulled), ``IsFullClosure``, ``Severity`` (real but uniformly
``"Unknown"`` in the sample, the same "real field, currently
uninformative" honesty this SDK already gives Lyon's own ``intervenant``),
``Comment`` (real but 0/590 populated), ``EncodedPolyline`` (Google's
Encoded Polyline Algorithm Format - real and populated on ~50% of real
roadwork events, confirmed live by decoding a real sample: its first and
last points match that same record's own stated ``Latitude``/
``Longitude`` and ``LatitudeSecondary``/``LongitudeSecondary``
respectively, within the real rounding gap between the polyline's 5
decimal digits and the plain fields' 6 - ``LatitudeSecondary``/
``LongitudeSecondary`` were never seen populated without
``EncodedPolyline`` also present, so they add nothing a decoded polyline
doesn't already give and aren't promoted separately), ``Restrictions`` (a real
but, in this sample, entirely-null object: ``Width``/``Height``/
``Length``/``Weight``/``Speed``), ``Recurrence``/``RecurrenceSchedules``,
``LinkId``, ``Impact``.

**Roadworks filter: ``EventType == "roadwork"``** - confirmed live,
590/595 real Ontario events (5 ``accidentsAndIncidents``, 0
``closures`` in the sample pulled, though real per the documented enum).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport
from .jurisdictions import JURISDICTIONS

__all__ = ["EVENT_PATH", "NA511Client"]

JSON = dict[str, Any]

#: Identical across every jurisdiction on this platform - confirmed live
#: for Ontario, and via Alberta's own published docs. See module
#: docstring.
EVENT_PATH = "api/v2/get/event"


class NA511Client:
    """Fetch real-time events from any jurisdiction on the North American
    511 REST platform. ``api_key`` is required for jurisdictions that
    gate the endpoint (Alberta, Saskatchewan - confirmed live); Ontario's
    own real deployment needs none at all - see module docstring. This
    client stays generic, keyed by a jurisdiction from
    :data:`streetworks.na511.jurisdictions.JURISDICTIONS` per call rather
    than one class per jurisdiction, since the real endpoint shape is
    identical - the same shape :class:`streetworks.ogc.germany.GermanRoadworksClient`
    already uses for its own ``.fetch(state)``.

    >>> from streetworks.na511 import NA511Client
    >>> from streetworks.na511.jurisdictions import ONTARIO
    >>> from streetworks.common import from_na511
    >>> with NA511Client() as client:  # doctest: +SKIP
    ...     works_list = from_na511(
    ...         client.fetch("ontario"),
    ...         territory=ONTARIO.territory,
    ...         administrative_area=ONTARIO.administrative_area,
    ...     )
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def iter_events(self, jurisdiction: str) -> Iterator[JSON]:
        """Every real event ``jurisdiction`` (a key of
        :data:`~streetworks.na511.jurisdictions.JURISDICTIONS`, e.g.
        ``"ontario"``) currently publishes - every real record checked so
        far comes back as a single JSON array in one response, no
        pagination parameters documented or needed on any jurisdiction
        checked."""
        base_url = JURISDICTIONS[jurisdiction].base_url
        params = {"format": "json"}
        if self.api_key:
            params["key"] = self.api_key
        response = self._transport.request("GET", f"{base_url}/{EVENT_PATH}", params=params)
        yield from response.json() or []

    def iter_roadworks(self, jurisdiction: str) -> Iterator[JSON]:
        """Like :meth:`iter_events`, filtered to the real
        ``EventType == "roadwork"`` discriminator - see module docstring."""
        for event in self.iter_events(jurisdiction):
            if event.get("EventType") == "roadwork":
                yield event

    def fetch(self, jurisdiction: str) -> list[JSON]:
        """:meth:`iter_roadworks` as a plain list - matches
        :meth:`streetworks.ogc.germany.GermanRoadworksClient.fetch`'s own
        shape, for the same generic per-jurisdiction dispatch use."""
        return list(self.iter_roadworks(jurisdiction))

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> NA511Client:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
