"""North American "511" REST platform - one commercial API shape reused,
byte-for-byte identically, by multiple independent government agencies
in both Canada and the US. Found while surveying the Canadian provinces
beyond British Columbia (see :mod:`streetworks.drivebc`) for roadworks
coverage: Ontario 511, 511 Alberta, Saskatchewan's Highway Hotline, New
Brunswick 511, Newfoundland and Labrador 511, Nova Scotia 511 and 511
Yukon **all** publish the exact same ``/api/v2/get/event`` endpoint
(confirmed live, 2026-08-21 - every one answers the identical URL path
with either real data or the identical structured "Invalid Key"
rejection), and the field shape itself is confirmed live by comparing
Ontario's real, unauthenticated response against Alberta's own published
field-by-field API documentation - every field name, type and the
``EventType`` roadworks discriminator match exactly (see below for the
full real ``EventType`` value set, corrected after Alberta's own real
authenticated pull). **Nevada 511, Georgia 511, Alaska 511 and Louisiana
511 turned out to be the identical platform too** - all four found
separately while surveying US roadworks coverage (none of Nevada,
Georgia or Louisiana is in the WZDx/CWZ US registry at all, confirmed
live), then confirmed live here the same way as every Canadian
jurisdiction: the identical ``/api/v2/get/event`` path, the identical
"Invalid Key" rejection, and a real, working ``/developers/doc`` page
whose own field-by-field documentation matches exactly. Georgia's own
real "TrafficImpacts" ArcGIS Hub pages, checked first, turned out to be
a real dead end - per-project public-information pages (e.g. "I-285 &
SR 400 Improvements"), not a live data feed; checking Georgia's own 511
site directly against this platform's shape was the real find. Alaska
is a real correction to the earlier USA gap-state survey, not a new
discovery from scratch: it had only been checked against its ArcGIS
Open Data catalogue (no live closures dataset there), never directly
against this platform's own endpoint shape the way Rhode Island/West
Virginia/South Dakota/Nebraska were - a direct re-check found it
immediately, ``/developers/doc`` explicitly naming "Temporary
Workzones" as a real event resource. Louisiana is a genuinely new find,
not a re-check of anything: found while searching for real Open511 (a
different, unrelated standard) adopters among the remaining USA gap
states - none were found, but a real ``511LA`` ``/help/endpoint/event``
page surfaced instead, the same URL shape Ontario/Nevada/Georgia
already publish on this platform. Manitoba, Prince Edward Island,
the Northwest Territories and Nunavut were checked and found to have no
matching site (no DNS record for the guessable ``511<jurisdiction>.ca``
pattern this platform's other real Canadian deployments use).

**Ontario is a genuine, confirmed exception: keyless.** A plain
``GET https://511on.ca/api/v2/get/event`` returns real data with **no**
``key`` parameter at all (confirmed live, 595 real events, 2026-08-21) -
despite the site's own "Sign up for an account" prompt, which turns out
to gate only the human-facing My511 personalisation features, not the
API itself. **Every other jurisdiction confirmed here requires one** -
confirmed live via each host's own real, structured rejection
(``{"Error":{"Message":"Invalid Key"}}``) on the identical endpoint with
no ``key`` supplied, and Alberta's own API docs explicitly state
``key: Developer Key, Required``. This SDK does not obtain that key on a
caller's behalf - see :mod:`streetworks.wzdx.client`'s own module
docstring for the identical Massachusetts CWZ situation and reasoning.
Saskatchewan's own public signup page has since been taken down
(confirmed live 2026-08-21, a few days after the endpoint itself was
first confirmed key-gated) - the real endpoint is otherwise unaffected;
see :mod:`streetworks.na511.jurisdictions`'s own ``SASKATCHEWAN`` entry.

**Because Ontario's real, keyless response already proves this exact
schema correct, the other key-gated jurisdictions aren't a guess the way
this SDK's DATEX "Credentials-wanted scaffold" adapters are** (e.g.
:mod:`streetworks.datex2.trafikverket`) - the field names, types and the
``EventType`` roadworks discriminator are drawn from a real, live,
unauthenticated pull against the identical platform, not documentation
alone. What's still genuinely unconfirmed for each remaining key-gated
jurisdiction is only whether its own authenticated response round-trips
through this exact parsing unchanged - everything else is as confirmed as
this SDK's fully shipped providers.

**Alberta's own real authenticated response confirmed exactly that,
2026-08-22** - a real developer key round-tripped 302 real events (161
real roadwork, 54 with a real decoded polyline) through this exact
parsing unchanged, no code changes needed. One genuine correction
surfaced by having a second jurisdiction's full real event population to
compare against Ontario's: **the real ``EventType`` enum has at least six
values, not three** - Ontario's own 595-event sample only ever showed
``"roadwork"``/``"accidentsAndIncidents"``/``"closures"``, but Alberta's
302-event pull also carries real ``"restrictionClass"`` (65),
``"generalInfo"`` (26) and ``"specialEvents"`` (13) records. This doesn't
change the roadworks filter itself - ``EventType == "roadwork"`` stays
exactly correct, cross-confirmed on a second jurisdiction - but the
enum's full membership was a real gap in the original claim, corrected
here rather than left stated too narrowly.

**Nevada's own real authenticated response confirmed the same thing
again, same day** - a real developer key round-tripped 92 real events
(74 real roadwork, 61 with a real decoded polyline) through the exact
same parsing, no code changes needed. A third-jurisdiction cross-check
of the ``EventType`` correction above: Nevada's pull also carried real
``"restrictionClass"``/``"specialEvents"`` records (not ``"generalInfo"``
this time - real per-jurisdiction variation, not a contradiction), the
roadworks filter itself staying exactly correct a third time. ``ab511``
and ``nv511`` are both verified in the registry accordingly;
``sk511``/``nb511``/``nl511``/``ns511``/``yt511``/``ga511``/``la511``
remain in the same "schema proven, own key untested" position Alberta
and Nevada themselves were in until now.

**Alaska's own real authenticated response confirmed the same thing a
third time, and surfaced two genuine converter bugs Ontario's/Alberta's/
Nevada's own real samples never triggered.** A real developer key
round-tripped 57 real events (50 real roadwork, 45 with a real decoded
polyline) through the exact same parsing - but two real fields needed a
fix, not just confirmation: ``StartDate``/``Reported`` carry .NET's
``DateTime.MinValue`` (serialised as Unix epoch seconds,
``-62135596800``) on 47/57 (82%) of all real Alaska events - the
majority shape there, not an edge case - which ``datetime.fromtimestamp``
parsed without error into a nonsensical "0001-01-01" date; and one real
record states ``Latitude``/``Longitude`` as exactly ``(0.0, 0.0)`` with
no polyline fallback, a real "Null Island" placeholder. Both are fixed
in :func:`streetworks.common.from_na511._epoch_seconds_to_dt`/
``_coordinate`` - see that module's own docstring. ``ab511``, ``nv511``
and ``ak511`` are all verified in the registry accordingly.

**Real fields** (confirmed live via Ontario's response, cross-checked
field-for-field against Alberta's own published docs): ``ID``,
``SourceId``, ``Organization``, ``RoadwayName``, ``DirectionOfTravel``,
``Description``, ``Reported``/``LastUpdated``/``StartDate``/
``PlannedEndDate`` (Unix epoch **seconds**, confirmed by magnitude - not
milliseconds, unlike this SDK's ArcGIS-sourced epoch fields elsewhere),
``LanesAffected``, ``Latitude``/``Longitude`` (plain WGS84 decimal
fields, not GeoJSON - already ``(lat, lon)`` order, no flip needed),
``EventType``, ``EventSubType`` (real but 0/590 populated in Ontario's
sample - Alberta's real pull shows it's a genuine, richer sub-category
when present, e.g. ``"constructionWork"``/``"bridgeConstruction"``),
``IsFullClosure``, ``Severity`` (real but uniformly ``"Unknown"``/
``"None"`` in every sample pulled so far, the same "real field, currently
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
doesn't already give and aren't promoted separately), ``Restrictions``
(real - null in Ontario's sample, but Alberta's real records populate
``Width``/``Height``/``Speed`` with genuine values, e.g. a real 5.7m
width / 5.4m height restriction), ``Recurrence``/``RecurrenceSchedules``
(real - empty strings in Ontario's sample, but genuinely populated on
Alberta with real HTML-ish day/time text and a structured
day-of-week/time-window schedule object respectively), ``LinkId``,
``Impact``. **Alberta's real pull also surfaced three fields never seen
on Ontario at all**: ``DetourPolyline``/``DetourInstructions`` (empty
strings on every real Alberta record sampled - real fields, not yet seen
populated) and ``Details`` (a real, often richer free-text field than
``Description``, e.g. naming the specific load restriction by class) -
noted here, not yet consumed by :func:`streetworks.common.from_na511`,
the same "related but distinct, flagged not consumed" treatment this SDK
gives comparable optional extensions elsewhere. **The field set genuinely
varies per jurisdiction, confirmed by a third real pull, not assumed
uniform**: Nevada's real records carry ``DetourPolyline``/
``DetourInstructions`` too (also always empty) but never ``Details`` at
all - present-but-empty and absent-entirely are both handled the same
way already (``.get()``, never a required key), so this needed no code
change, just an honest correction to "every jurisdiction returns the
same shape."

**Roadworks filter: ``EventType == "roadwork"``** - confirmed live on
four independent jurisdictions: 590/595 real Ontario events, 161/302
real Alberta events, 74/92 real Nevada events, and 50/57 real Alaska
events (the rest of each genuinely split across the other real
``EventType`` values - see above), the same clean filter holding on
materially less roadwork-skewed real populations each time.
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
    511 REST platform. ``api_key`` is required for every jurisdiction
    except Ontario, whose own real deployment needs none at all - see
    module docstring. This client stays generic, keyed by a jurisdiction
    from
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
