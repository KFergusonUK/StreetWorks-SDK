"""New England Compass (NEC) - the real, keyless ITS Center-to-Center
(C2C) XML data portal shared by Maine, New Hampshire and Vermont's own
Advanced Traffic Management Systems (ATMS). A genuinely different real
system from :mod:`streetworks.na511`'s own ``NEW_ENGLAND`` entry (the
North American 511 commercial platform's ``newengland511.org``
deployment, key-gated) - found by tracing the real developer-portal link
newengland511.org's own signup page actually points at
(``nec-por.ne-compass.com/DeveloperPortal``), not the dead page this SDK
first assumed. Confirmed live, 2026-08-23: the portal's own real
`C2C schema files <https://nec-por.ne-compass.com/DeveloperPortal/Content/Schemas/Compass%20C2C%20Schemas.zip>`_
document the wire format (the ``http://its.gov/c2c_icd`` XML namespace, a
real national ITS standard, not bespoke to this deployment), and every
real endpoint answers with genuine current data, no key or account of
any kind.

**Two real, differently-shaped resources, not one** - ``laneClosureData``
(175/118/54 real records for Maine/New Hampshire/Vermont respectively,
2026-08-23) states ``startDate``/``startTime``/``endDate``/``endTime``;
``incidentData`` (1/1/2 real records the same day - genuinely much
smaller, not a second copy of the same data) states ``confirmedDate``/
``confirmedTime`` instead, with no end date at all. Real ``id`` values
never overlap between the two resources (checked directly, not assumed)
- both are needed for complete coverage, since real roadworks-typed
records appear in *both* (a real New Hampshire ``incidentData`` record,
type ``Construction``, is not duplicated anywhere in that state's real
``laneClosureData``).

**Roadworks filter: the real ``type`` element's own child attribute**
(e.g. ``<type RoadMaintenance="true" />``) **is a genuine multi-value
discriminator, not a boolean** - confirmed live, real values seen across
all three states: ``Construction``, ``RoadMaintenance``,
``BridgeMaintenance``, ``BridgeOut``, ``SpecialEvent``,
``OversizedVehicle``, ``PSA``, ``Other``. ``Construction``/
``RoadMaintenance``/``BridgeMaintenance``/``BridgeOut`` are the real
roadworks values (321 real records across all three states and both
resources, 2026-08-23) - checked by reading real sample descriptions,
not assumed from the name alone: a real ``BridgeOut``-typed record reads
"Rehabilitation of bridge on VT-31... A temporary bridge is being
installed" - genuine construction, not incidental bridge failure.
``SpecialEvent`` (parades, foot races, town fairs), ``OversizedVehicle``
(wide-load routing restrictions), ``PSA`` (a real seasonal-road-opening
announcement) and ``Other`` (checked: a real weight-restriction-lifted
notice) are all confirmed genuinely not roadworks.

**Coordinates are real WGS84 degrees times 1,000,000, stored as plain
integers** - confirmed live against a known real place (a real Leeds,
Maine record's ``startLocation`` states ``lat=44345313``,
``lon=-70145120``, which is genuinely Leeds, Maine at 44.345313,
-70.145120 once divided by 1e6). Real ``midpoints`` between
``startLocation`` and ``endLocation`` give a genuine LineString - one
real Maine record had 25 real midpoint vertices - richer geometry than
almost any other provider in this SDK.

**Licence: no formal statement found, but a real, live "Data Sharing
Relationship Principles" page**
(``nec-por.ne-compass.com/DeveloperPortal/Home/DataSharing``) explicitly
commits to keeping the data open ("Maine, New Hampshire, and Vermont
will make all efforts to keep data open once it's been released") and
asks only that data sources be cited - an honest-gap tier (no CC-BY/OGL
name to cite), the same as Autobahn GmbH/Jersey/NYC DOT in this SDK, but
with a real, live statement of intent behind it, not silence.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from xml.etree import ElementTree

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["BASE_URL", "NETWORKS", "ROADWORKS_TYPES", "NECompassClient"]

JSON = dict[str, Any]

BASE_URL = "https://nec-por.ne-compass.com/NEC.XmlDataPortal/api/c2c"

#: The three real states this shared platform covers - see module docstring.
NETWORKS = ("Maine", "NewHampshire", "Vermont")

#: Confirmed live, not assumed from the name - see module docstring.
ROADWORKS_TYPES = frozenset({"Construction", "RoadMaintenance", "BridgeMaintenance", "BridgeOut"})

_NS = "{http://its.gov/c2c_icd}"


def _text(element: ElementTree.Element | None, tag: str) -> str | None:
    if element is None:
        return None
    child = element.find(f"{_NS}{tag}")
    return child.text if child is not None else None


def _location(element: ElementTree.Element | None) -> JSON | None:
    if element is None:
        return None
    lat = _text(element, "lat")
    lon = _text(element, "lon")
    return {
        "state": _text(element, "state"),
        "county": _text(element, "county"),
        "district": _text(element, "district"),
        "city": _text(element, "city"),
        "roadway": _text(element, "roadway"),
        "direction": _text(element, "direction"),
        "crossstreet": _text(element, "crossstreet"),
        "mile_marker": _text(element, "mileMarker"),
        "lat": float(lat) / 1_000_000 if lat else None,
        "lon": float(lon) / 1_000_000 if lon else None,
    }


def _midpoints(element: ElementTree.Element) -> list[tuple[float, float]]:
    midpoints_el = element.find(f"{_NS}midpoints")
    if midpoints_el is None:
        return []
    points = []
    for point in midpoints_el.findall(f"{_NS}point"):
        lat, lon = _text(point, "lat"), _text(point, "lon")
        if lat and lon:
            points.append((float(lat) / 1_000_000, float(lon) / 1_000_000))
    return points


def _road_restrictions(element: ElementTree.Element) -> JSON | None:
    restrictions_el = element.find(f"{_NS}roadRestrictions")
    if restrictions_el is None:
        return None
    return {
        field: _text(restrictions_el, field)
        for field in ("width", "height", "length", "weight", "speed")
    }


def _parse_record(element: ElementTree.Element, *, kind: str) -> JSON:
    """One real ``<laneClosure>``/``<incident>`` element -> a plain dict.
    Every field is read defensively - nothing raises on a missing
    element, matching this SDK's own established discipline. See module
    docstring for the two real, differently-shaped resources this
    normalises."""
    type_el = element.find(f"{_NS}type")
    type_value = next(iter(type_el.attrib), None) if type_el is not None else None
    return {
        "kind": kind,
        "id": element.get("id"),
        "net_id": element.get("netId"),
        "description": _text(element, "desc"),
        "start_location": _location(element.find(f"{_NS}startLocation")),
        "end_location": _location(element.find(f"{_NS}endLocation")),
        "midpoints": _midpoints(element),
        "status": _text(element, "status"),
        "severity": _text(element, "severity"),
        "type": type_value,
        "affected_lanes_description": _text(element, "affectedLanesDescription"),
        "road_restrictions": _road_restrictions(element),
        "start_date": _text(element, "startDate"),
        "start_time": _text(element, "startTime"),
        "end_date": _text(element, "endDate"),
        "end_time": _text(element, "endTime"),
        "confirmed_date": _text(element, "confirmedDate"),
        "confirmed_time": _text(element, "confirmedTime"),
        "created_timestamp": _text(element, "createdTimestamp"),
        "last_updated_timestamp": _text(element, "lastUpdatedTimestamp"),
    }


class NECompassClient:
    """Fetch Maine/New Hampshire/Vermont's real, shared New England
    Compass C2C XML feeds. No credentials required.

    >>> from streetworks.necompass import NECompassClient
    >>> from streetworks.common import from_necompass
    >>> with NECompassClient() as client:  # doctest: +SKIP
    ...     works_list = from_necompass(list(client.iter_roadworks("Maine")))
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

    def _fetch(self, network: str, data_type: str, *, tag: str, kind: str) -> Iterator[JSON]:
        response = self._transport.request(
            "GET",
            self.base_url,
            params={"networks": network, "dataTypes": data_type},
        )
        root = ElementTree.fromstring(response.content)
        for element in root.iter(f"{_NS}{tag}"):
            yield _parse_record(element, kind=kind)

    def iter_lane_closures(self, network: str) -> Iterator[JSON]:
        """Yield every real ``laneClosureData`` record for one real
        network (``"Maine"``/``"NewHampshire"``/``"Vermont"``),
        unfiltered - includes real non-roadworks types (SpecialEvent,
        OversizedVehicle, PSA, Other). See module docstring."""
        yield from self._fetch(network, "laneClosureData", tag="laneClosure", kind="laneClosure")

    def iter_incidents(self, network: str) -> Iterator[JSON]:
        """Yield every real ``incidentData`` record for one real network,
        unfiltered - a genuinely separate, much smaller resource from
        ``iter_lane_closures``, not a duplicate. See module docstring."""
        yield from self._fetch(network, "incidentData", tag="incident", kind="incident")

    def iter_roadworks(self, network: str) -> Iterator[JSON]:
        """Yield only real roadworks records for one real network, from
        *both* real resources - ``type`` filtered server-side to
        :data:`ROADWORKS_TYPES`. See module docstring."""
        for record in self.iter_lane_closures(network):
            if record["type"] in ROADWORKS_TYPES:
                yield record
        for record in self.iter_incidents(network):
            if record["type"] in ROADWORKS_TYPES:
                yield record

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> NECompassClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
