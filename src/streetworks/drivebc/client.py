"""DriveBC (British Columbia, Canada) - the province's own Open511
implementation, this SDK's first Canadian roadworks provider and second
country in the Americas alongside the US cluster (WZDx, NYC DOT, Chicago
CDOT).

.. attention::
   **Confirmed live (2026-08-08)** against a real, unauthenticated pull
   (246 real events at time of writing).

**Built bespoke, not as a general ``streetworks.open511`` parser -
deliberately, against the source brief's own recommendation.** The brief
proposed building a reusable Open511 parser on the reasoning that Open511
is a multi-jurisdiction standard (the WZDx precedent). Checked live before
committing to that: DriveBC/BC is the only real, confirmed
roadworks-events Open511 implementation found - the standard's own
adoption is real but thin (San Francisco Bay Area 511's Open511 use is
*transit* data, a different resource entirely; no second real
roadworks-events jurisdiction was found live). Per this SDK's own
"extract shared code only on the second real consumer" pattern (the same
reasoning that kept Paris Chantiers bespoke rather than forcing a
premature ``streetworks.opendatasoft``), this ships as
``streetworks.drivebc`` - genuinely Open511-shaped internally, so a real
second jurisdiction could still prompt an extraction later, but not
pre-abstracted from one data point.

**Endpoint and pagination**: keyless ``GET`` on
``https://api.open511.gov.bc.ca/events``, `limit`/`offset` pagination
(max ``limit=500``, confirmed live via the API's own structured error on
an over-large request - ``{"error": "Limit out of acceptable range: ...",
"error_code": 1005}``), no ``next_url`` - the API's own ``/help`` page
documents looping ``offset`` in ``limit``-sized steps until a short page,
which is what :meth:`DriveBCClient.iter_events` does. All 246 real events
fit in one page at the max limit today.

**Roadworks filter: ``event_type == "CONSTRUCTION"``** - confirmed live,
194/246 real events. The other three real values seen live -
``INCIDENT`` (38), ``ROAD_CONDITION`` (12), ``WEATHER_CONDITION`` (2) -
are excluded, matching the brief's own filter plan exactly.

**Two real, mutually-exclusive schedule shapes, not one** - a genuine
finding beyond what the brief anticipated. 222/246 real events state
``schedule.intervals`` (ISO-8601 time-interval strings, e.g.
``"2026-05-07T04:00/2026-11-25T21:00"``, or open-ended
``"2022-12-07T20:19/"``); the other 24 state
``schedule.recurring_schedules`` instead (day-of-week list + daily
start/end time + an overall date range - a weekday work-window shape
``intervals`` can't express) - no event carries both or neither. See
:func:`streetworks.common.from_drivebc` for how each becomes a
``WorksSite`` window.

**Interval date-times carry no UTC offset**, unlike the top-level
``created``/``updated`` fields, which do (e.g. ``-07:00``). The
jurisdiction resource states ``"timezone": "America/Vancouver"``, so
these are almost certainly local BC time - but that's an inference, not
something the interval strings themselves state, so they're parsed
naive rather than a timezone being silently attached.

**Geometry: real GeoJSON, `Point` or `LineString`, WGS84** - 160
`LineString` / 86 `Point` in this pull, confirmed live, no reprojection
question.

**``roads[]`` is free-text - no join key**, confirmed: ``name``/``from``/
``to``/``direction``, never a road-network identifier. ``street_ref``
stays unpopulated in the converter, same discipline as every other
name-only provider in this SDK.

**Network scope: ``strategic``** (BC MoTI's own network only, never
municipal streets) - real evidence, not the brief's stated assumption
taken on faith: every event's ``areas[]`` names one of BC MoTI's own
internal administrative Districts (Lower Mainland, Vancouver Island,
Cariboo, ...), never a municipality, and the jurisdiction resource
itself self-describes as "highways managed by the Government of British
Columbia." One real nuance worth flagging: `roads[].name` is `"Other
Roads"` on 67/246 real events (not just numbered highways) - real
values include unnumbered local-sounding names (`"Main Street"`,
`"Horse Lake Road"`) - still organised entirely under BC MoTI's own
Districts in every case checked, not confirmed to ever cross into
municipal territory, but the road *names* alone don't rule it out
either; flagged rather than silently assumed comprehensive.

**Licence: Open Government Licence - British Columbia (OGL-BC),
confirmed live from the API's own `/help` page** - *"Use of the
Information provided by this API is governed by the [OGL-BC]"*, a
worldwide, royalty-free, perpetual, non-exclusive licence, commercial use
permitted, attribution required. The jurisdiction resource's own
``license_url`` field (a PDF path under ``data.gov.bc.ca``) is dead -
confirmed 404-redirects to a generic catalogue landing page - so this
client's docs cite the real, live OGL-BC text
(``www2.gov.bc.ca/gov/content?id=A519A56BC2BF44E4A008B33FCF527F61``)
instead, not the jurisdiction resource's own stale pointer. Default
attribution: *"Contains information licensed under the Open Government
Licence - British Columbia."*

**No app key required** - every claim above came from a fully
unauthenticated pull; the distribution-list email the API's own docs
mention is an opt-in courtesy, not a registration wall.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["EVENTS_URL", "DriveBCClient"]

JSON = dict[str, Any]

#: Confirmed live 2026-08-08.
EVENTS_URL = "https://api.open511.gov.bc.ca/events"

#: The API's own documented maximum - confirmed live via its structured
#: "Limit out of acceptable range" error on a larger request.
_MAX_LIMIT = 500


class DriveBCClient:
    """Fetch DriveBC's (British Columbia) Open511 road events. No
    credentials required.

    >>> from streetworks.drivebc import DriveBCClient
    >>> from streetworks.common import from_drivebc
    >>> with DriveBCClient() as drivebc:  # doctest: +SKIP
    ...     works = from_drivebc(list(drivebc.iter_roadworks()))
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_events(self) -> Iterator[JSON]:
        """Every real event, unfiltered - includes incidents, road/weather
        conditions, everything the ``CONSTRUCTION`` filter excludes.
        Pages via ``limit``/``offset`` (the API's own documented shape -
        no ``next_url``) until a short page ends the loop."""
        offset = 0
        while True:
            response = self._transport.request(
                "GET", EVENTS_URL, params={"limit": _MAX_LIMIT, "offset": offset}
            )
            body = response.json()
            events = body.get("events") or []
            yield from events
            if len(events) < _MAX_LIMIT:
                return
            offset += len(events)

    def iter_roadworks(self) -> Iterator[JSON]:
        """Real roadworks events only (``event_type == 'CONSTRUCTION'``) -
        see module docstring."""
        for event in self.iter_events():
            if event.get("event_type") == "CONSTRUCTION":
                yield event

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> DriveBCClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
