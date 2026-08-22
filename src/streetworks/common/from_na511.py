"""North American 511 platform -> streetworks.common converter. See
:mod:`streetworks.na511.client` for the full live investigation.

One :class:`~streetworks.common.Works` per event, each with a single
:class:`~streetworks.common.WorksSite` - no grouping key is stated
linking separate events into one project, the same one-to-one shape
:mod:`.from_au_tas_roadworks`/:mod:`.from_drivebc` already use for their
own comparable live traveller-information feeds.

``works_type`` is ``EventSubType`` (real but sparsely populated - 0/590
in the sample this was built from); ``status`` is ``Severity`` (real but
uniformly ``"Unknown"`` in the same sample - still mapped, the same
"real field, currently uninformative" honesty already given to Lyon's
own ``intervenant``). ``traffic_management`` is ``LanesAffected`` - the
closest single-field analogue to WZDx's own ``vehicle_impact`` role
(e.g. ``"ALL LANES CLOSED"``, ``"1 Alternating Lane(s)"``). The richer
free-text ``Description`` field stays ``.raw``-only - no dedicated slot
exists for it, the same choice this SDK already makes for WZDx's own
comparably rich ``description`` field.

**``date_confidence`` is uniformly ``ESTIMATED``** - no independent
verified/status flag exists distinguishing scheduled from physically
confirmed, the same reasoning :mod:`.from_drivebc`/:mod:`.from_quebec`
already document for their own comparable live feeds. Dates are real
Unix epoch **seconds** (confirmed by magnitude, not milliseconds).

**A real "no date stated" placeholder, confirmed live on a third
jurisdiction, not assumed universal.** Alaska's own real authenticated
pull surfaced a genuine bug: ``StartDate``/``Reported`` carry .NET's
``DateTime.MinValue`` (0001-01-01, serialised as Unix epoch seconds,
``-62135596800``) on 47/57 (82%) of all real events - the majority
shape there, not an edge case. ``datetime.fromtimestamp`` parses this
without raising (Python's date range starts at year 1), so it silently
produced a nonsensical "0001-01-01" ``proposed_start`` before this was
caught - see :data:`_NULL_DATETIME_SENTINEL`. Never seen on Ontario's
or Alberta's own real samples, nor on Alaska's own ``PlannedEndDate`` -
genuinely per-field, not a whole-feed pattern.

**A real "no location stated" placeholder, same discovery.** One real
Alaska event (of 57) states ``Latitude``/``Longitude`` as exactly
``0.0``/``0.0`` with no ``EncodedPolyline`` to fall back on - the same
"Null Island" placeholder pattern this SDK already excludes for
Arkansas's own real `OneBillionContructionPlanDTIMs` dataset. Never
promoted to a real ``Coordinate``.

**Geometry prefers the real decoded ``EncodedPolyline`` (Google's
Encoded Polyline Algorithm Format) when present** - real and populated
on ~50% of real Ontario roadwork events sampled, confirmed correct by
decoding a real sample: its first/last points match that same record's
own stated ``Latitude``/``Longitude``/``LatitudeSecondary``/
``LongitudeSecondary`` within the real rounding gap between the
polyline's 5 decimal digits and the plain fields' 6. Falls back to the
plain ``Latitude``/``Longitude`` point pair otherwise - never absent
when either shape is present and real (see the Null Island exclusion
above).

``territory``/``administrative_area`` are passed in explicitly, not
derived - one client serves several distinct real jurisdictions (see
:mod:`streetworks.na511.jurisdictions`), the same design
:func:`~streetworks.common.from_wzdx` already uses for the identical
reason.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_na511"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"

#: A real, confirmed placeholder - .NET's ``DateTime.MinValue``
#: (0001-01-01 00:00:00 UTC) serialised as Unix epoch seconds. Found via
#: Alaska's real authenticated pull: 47/57 (82%) of all real events carry
#: this exact value on ``StartDate``/``Reported`` - the majority shape,
#: not an edge case. ``datetime.fromtimestamp`` parses it without error
#: (Python's date range starts at year 1), so it silently produced a
#: nonsensical "0001-01-01" ``proposed_start`` before this was found -
#: the same class of finding WZDx's own placeholder-date handling
#: already documents for this SDK. Never seen on ``PlannedEndDate``.
_NULL_DATETIME_SENTINEL = -62135596800


def _epoch_seconds_to_dt(value: int | None) -> datetime | None:
    if not value or value == _NULL_DATETIME_SENTINEL:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc)


def _decode_polyline(encoded: str, *, precision: int = 5) -> tuple[tuple[float, float], ...]:
    """Google's Encoded Polyline Algorithm Format - the standard published
    algorithm. Returns ``(lat, lon)`` pairs, per the algorithm's own
    convention - matching this SDK's own ``Coordinate`` convention. See
    module docstring for how this was confirmed correct against a real
    sample (also used, independently, by :mod:`.from_nsw_livetraffic`)."""
    factor = 10**precision
    coordinates: list[tuple[float, float]] = []
    index = lat = lon = 0
    length = len(encoded)
    while index < length:
        for is_lat in (True, False):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if is_lat:
                lat += delta
            else:
                lon += delta
        coordinates.append((lat / factor, lon / factor))
    return tuple(coordinates)


def _coordinate(event: JSON) -> Coordinate | None:
    encoded = event.get("EncodedPolyline")
    lat, lon = event.get("Latitude"), event.get("Longitude")
    if encoded:
        try:
            points = _decode_polyline(encoded)
        except (ValueError, IndexError):
            points = ()
        if points:
            return Coordinate(value=points[0], crs=_CRS, points=points)
    if lat is None or lon is None:
        return None
    lat, lon = float(lat), float(lon)
    if lat == 0.0 and lon == 0.0:
        # A real, confirmed "no location stated" placeholder, not a
        # genuine Gulf of Guinea roadwork - see module docstring.
        return None
    return Coordinate(value=(lat, lon), crs=_CRS)


def _location_description(event: JSON) -> str | None:
    road = event.get("RoadwayName")
    direction = event.get("DirectionOfTravel")
    parts = [p for p in (road, direction) if p and p != "Unknown"]
    return " - ".join(parts) or None


def _to_site(event: JSON) -> WorksSite:
    start = _epoch_seconds_to_dt(event.get("StartDate"))
    end = _epoch_seconds_to_dt(event.get("PlannedEndDate"))
    return WorksSite(
        reference=str(event["ID"]) if event.get("ID") is not None else None,
        works_type=event.get("EventSubType") or None,
        status=event.get("Severity") or None,
        location_description=_location_description(event),
        coordinate=_coordinate(event),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=event.get("LanesAffected") or None,
        source_grade=SourceGrade.OPERATOR,
        raw=event,
    )


def from_na511(events: list[JSON], *, territory: str, administrative_area: str) -> list[Works]:
    """Convert real North American 511 platform events (from
    :meth:`streetworks.na511.NA511Client.iter_roadworks`) into
    :class:`~streetworks.common.Works` - one per event, each with a
    single ``WorksSite``. ``territory``/``administrative_area`` apply to
    every ``Works`` this call produces - all ``events`` are expected to
    come from one jurisdiction's own client call. See module docstring."""
    works_list: list[Works] = []
    for event in events:
        site = _to_site(event)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                territory=territory,
                administrative_area=administrative_area,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=event,
            )
        )
    return works_list
