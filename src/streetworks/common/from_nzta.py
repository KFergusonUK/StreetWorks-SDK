"""NZTA (Waka Kotahi Highway Information, New Zealand) -> streetworks.common
converter. This SDK's first New Zealand works coverage.

One :class:`~streetworks.common.Works` per feature, each with a single
:class:`~streetworks.common.WorksSite` - no grouping key is stated in this
feed linking separate events into one project.

**``Works.reference`` is ``eventId``** - a real, confirmed-unique integer
business identifier NZTA itself states, not ``OBJECTID`` (the layer's
internal Esri row id). ``territory="New Zealand"``,
``administrative_area="Waka Kotahi NZ Transport Agency"`` - the state
highway authority IS the data-owning operator, the same rule already
applied to Autobahn GmbH/TfNSW/Main Roads WA/Roads ACT.

**``date_confidence`` is graded from a real, evidenced status signal - the
richest in this SDK.** See :mod:`streetworks.nzta.client`'s own module
docstring for the full live-confirmed correlation: real ``status`` values
``Scheduled``/``Active``/``Resolved`` map cleanly to
``ESTIMATED``/``VERIFIED``/``VERIFIED`` respectively, mirroring the same
DATEX ``validityStatus`` convention (`from_datex2._VERIFIED_STATUSES`) -
``actual_start`` is inferred from a verified status the same way, never
``actual_end``.

**``WorksSite.street_ref`` is deliberately never populated** - NZTA's real
feed states no structured road/route identifier, only free text
(``locationArea``). See :mod:`streetworks.nzta.client`'s module docstring
for why this settles the NZ cluster's works-to-LINZ join question: there
is nothing stated to join on.

**``alternativeRoute`` real sentinel, confirmed live**: the literal
strings ``"Not Applicable"``/``"Not applicable."`` mean no alternative
route is stated (79% of real roadworks records) - excluded from
``traffic_management`` rather than surfaced as if they were real routing
instructions, the same "recognise a real, evidenced sentinel" discipline
NSW's ``0``/``-1`` delay sentinels get - never silently invented for a
record where no such value exists.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_nzta"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "New Zealand"
_ADMINISTRATIVE_AREA = "Waka Kotahi NZ Transport Agency"

#: Real, confirmed-live correlation with eventType/planned - see
#: streetworks.nzta.client's own module docstring.
_VERIFIED_STATUSES = frozenset({"Active", "Resolved"})
_ESTIMATED_STATUSES = frozenset({"Scheduled"})

#: The real, literal sentinel strings this feed uses for "no alternative
#: route stated" - confirmed live, not a guess. Matched case-insensitively
#: since both casings were observed.
_NO_ALTERNATIVE_ROUTE = frozenset({"not applicable", "not applicable."})


def _epoch_millis_to_dt(value: int | None) -> datetime | None:
    """``startDate``/``endDate`` are real ``esriFieldTypeDate`` fields -
    epoch milliseconds UTC, the standard ArcGIS REST convention."""
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _date_confidence(status: str | None) -> DateConfidence:
    if status in _VERIFIED_STATUSES:
        return DateConfidence.VERIFIED
    if status in _ESTIMATED_STATUSES:
        return DateConfidence.ESTIMATED
    return DateConfidence.UNKNOWN


def _coordinate(feature: JSON) -> Coordinate | None:
    """Point only (confirmed ``esriGeometryPoint`` live). ``outSR=4326``
    is confirmed honoured live, so no reprojection guard is built here -
    see :mod:`streetworks.nzta.client`'s module docstring."""
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    kind = (geometry.get("type") or "").upper()
    if kind != "POINT" or not coords:
        return None
    return Coordinate(value=(float(coords[0]), float(coords[1])), crs=_CRS)


def _traffic_management(properties: JSON) -> str | None:
    parts = [properties.get("impact"), properties.get("eventComments")]
    alternative_route = properties.get("alternativeRoute")
    if alternative_route and alternative_route.strip().lower() not in _NO_ALTERNATIVE_ROUTE:
        parts.append(f"Alternative route: {alternative_route}")
    text = " - ".join(p for p in parts if p)
    return text or None


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    start = _epoch_millis_to_dt(properties.get("startDate"))
    end = _epoch_millis_to_dt(properties.get("endDate"))
    status = properties.get("status")
    confidence = _date_confidence(status)
    event_id = properties.get("eventId")
    return WorksSite(
        reference=str(event_id) if event_id is not None else None,
        works_type=properties.get("eventDescription"),
        status=status,
        location_description=properties.get("locationArea"),
        coordinate=_coordinate(feature),
        proposed_start=start,
        proposed_end=end,
        actual_start=start if confidence is DateConfidence.VERIFIED else None,
        date_confidence=confidence,
        traffic_management=_traffic_management(properties),
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_nzta(features: list[JSON]) -> list[Works]:
    """Convert real NZTA road-event features (from
    :meth:`streetworks.nzta.NztaClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - one per feature, each with a
    single ``WorksSite``. See module docstring."""
    works_list: list[Works] = []
    for feature in features:
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=feature,
            )
        )
    return works_list
