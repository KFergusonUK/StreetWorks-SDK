"""National Highways (England) Road and Lane Closures - DATEX II v3.4, as JSON.

Unlike NDW (:mod:`streetworks.datex2.ndw`), National Highways' closures
service returns their DATEX II v3.4 extended profile as **JSON**, not XML, so
it needs its own parsing path rather than :mod:`streetworks.datex2.parser`
(which streams XML via ``iterparse``). This module maps that JSON shape onto
the same :class:`~streetworks.datex2.models.Situation` /
:class:`~streetworks.datex2.models.SituationRecord` models NDW uses, so
downstream code doesn't care which source it came from.

Verified against the live API (July 2026):

* **The response is XML unless you ask otherwise.** The documented default
  for the (undocumented-as-mandatory) ``X-Response-MediaType`` header is
  ``application/xml`` - an ``Accept: application/json`` header alone does
  *not* change that. This client always sends
  ``X-Response-MediaType: application/json``.
* Records sit at
  ``D2Payload.situation[].situationRecord[].sitRoadOrCarriagewayOrLaneManagement``
  - every record observed on the live feed used this single wrapper key.
* There is no ``xsi:type`` in JSON, so roadworks aren't identified by record
  type the way NDW's XML is. Instead we key off
  ``cause.causeType``: ``roadMaintenance`` / ``constructionWork`` are
  roadworks; anything else (e.g. ``authorityOperation``) is not. To reuse
  :attr:`Situation.roadworks` / :attr:`Situation.measures` unchanged, this
  module synthesises ``record_type`` from that mapping instead of adding a
  parallel field to the shared model.
* Geometry nests two ways depending on how many locations a record has:
  single-location records carry it directly under
  ``locationReference.locLinearLocation``; multi-location records carry a
  list under ``locationReference.locLocationGroupByList.locationContainedInGroup``,
  each entry shaped like a single-location's ``locationReference``. Both are
  handled here; for the multi-location case, ``Location.points`` is the
  concatenation of every segment's vertices, in group order.
* Coordinates in ``posList`` are ``"lat lon lat lon ..."`` pairs (WGS84,
  ``EPSG::4326``), matching the DATEX II convention the shared models assume.
* Pagination is a cursor URL in the ``x-next`` response header (present only
  while more pages remain) - not an offset/page-number scheme.
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import Enum
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Location, Situation, SituationRecord, Validity
from .parser import _dt

__all__ = [
    "BASE_URL",
    "ClosureType",
    "NationalHighwaysClient",
    "parse_situations",
]

JSON = dict[str, Any]

BASE_URL = "https://api.data.nationalhighways.co.uk/roads/v2.0"
_CLOSURES_PATH = "closures"

#: cause.causeType -> the record_type the shared models filter roadworks on
#: (see module docstring: NH's JSON has no xsi:type to key off instead).
_ROADWORKS_CAUSE_TYPES = {
    "roadMaintenance": "MaintenanceWorks",
    "constructionWork": "ConstructionWorks",
}


class ClosureType(str, Enum):
    PLANNED = "planned"
    UNPLANNED = "unplanned"


# --------------------------------------------------------------------------- #
# JSON -> models
# --------------------------------------------------------------------------- #


def _parse_pos_list(text: str) -> list[tuple[float, float]]:
    values = text.split()
    return [(float(values[i]), float(values[i + 1])) for i in range(0, len(values) - 1, 2)]


def _carriageway_value(supplementary: JSON | None) -> str | None:
    if not supplementary:
        return None
    for entry in supplementary.get("carriageway") or []:
        carriageway = entry.get("carriageway") or {}
        value = carriageway.get("value")
        if value == "extendedG":
            value = carriageway.get("extendedValueG") or None
        if value:
            return value
    return None


def _road_name(single_road_location: JSON | None) -> str | None:
    if not single_road_location:
        return None
    for section in single_road_location.get("linearWithinLinearElement") or []:
        by_code = ((section.get("linearElement") or {}).get("locLinearElementByCode")) or {}
        road_name = by_code.get("roadName")
        if road_name:
            return road_name
    return None


def _linear_from(location: JSON) -> tuple[list[tuple[float, float]], str | None, str | None]:
    """Extract (points, carriageway, road_number) from a location object shaped
    like ``locationReference`` (single) or one entry of ``locationContainedInGroup``
    (multi) - both carry ``locLinearLocation`` / ``locSingleRoadLinearLocation``
    as siblings."""
    linear = location.get("locLinearLocation") or {}
    pos_list = ((linear.get("gmlLineString") or {}).get("locGmlLineString") or {}).get("posList")
    points = _parse_pos_list(pos_list) if pos_list else []
    carriageway = _carriageway_value(linear.get("supplementaryPositionalDescription"))
    road_number = _road_name(location.get("locSingleRoadLinearLocation"))
    return points, carriageway, road_number


def _parse_location(location_reference: JSON | None) -> Location:
    if not location_reference:
        return Location()

    group = location_reference.get("locLocationGroupByList")
    if group is not None:
        points: list[tuple[float, float]] = []
        carriageway = road_number = None
        for item in group.get("locationContainedInGroup") or []:
            item_points, item_carriageway, item_road_number = _linear_from(item)
            points.extend(item_points)
            carriageway = carriageway or item_carriageway
            road_number = road_number or item_road_number
        return Location(
            kind="LocationGroupByList",
            points=tuple(points),
            carriageway=carriageway,
            road_number=road_number,
        )

    if "locLinearLocation" in location_reference:
        points, carriageway, road_number = _linear_from(location_reference)
        return Location(
            kind="LinearLocation",
            points=tuple(points),
            carriageway=carriageway,
            road_number=road_number,
        )

    return Location()


def _parse_validity(validity: JSON | None) -> Validity:
    if not validity:
        return Validity()
    spec = validity.get("validityTimeSpecification") or {}
    return Validity(
        status=validity.get("validityStatus"),
        overall_start=_dt(spec.get("overallStartTime")),
        overall_end=_dt(spec.get("overallEndTime")),
    )


def _parse_record(management: JSON) -> SituationRecord:
    cause = management.get("cause") or {}
    cause_type = cause.get("causeType")
    detailed = cause.get("detailedCauseType") or {}
    road_maintenance_types = detailed.get("roadMaintenanceType") or []
    comments = tuple(
        text
        for comment in management.get("generalPublicComment") or []
        if (text := (comment.get("comment") or "").strip())
    )
    return SituationRecord(
        id=management.get("idG", ""),
        record_type=_ROADWORKS_CAUSE_TYPES.get(cause_type, "RoadOrCarriagewayOrLaneManagement"),
        version=management.get("versionG"),
        creation_time=_dt(management.get("situationRecordCreationTime")),
        version_time=_dt(management.get("situationRecordVersionTime")),
        probability_of_occurrence=management.get("probabilityOfOccurrence"),
        source_name=(management.get("source") or {}).get("sourceIdentification"),
        validity=_parse_validity(management.get("validity")),
        location=_parse_location(management.get("locationReference")),
        cause_type=cause_type,
        comments=comments,
        road_maintenance_type=road_maintenance_types[0] if road_maintenance_types else None,
        construction_work_type=detailed.get("constructionWorkType"),
        raw=management,
    )


def _parse_situation(situation: JSON) -> Situation:
    result = Situation(
        id=situation.get("idG", ""),
        version_time=_dt(situation.get("situationVersionTime")),
        raw=situation,
    )
    for wrapper in situation.get("situationRecord") or []:
        management = wrapper.get("sitRoadOrCarriagewayOrLaneManagement")
        if management is not None:
            result.records.append(_parse_record(management))
    return result


def parse_situations(payload: JSON) -> list[Situation]:
    """Parse one ``D2Payload`` JSON object (as returned by the closures
    endpoint, or unwrapped already) into :class:`Situation` objects."""
    body = payload.get("D2Payload", payload)
    return [_parse_situation(s) for s in body.get("situation") or []]


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #


class NationalHighwaysClient:
    """Fetch National Highways Road and Lane Closures (DATEX II v3.4 JSON).

    Requires a subscription key from
    https://developer.data.nationalhighways.co.uk/.

    >>> from streetworks.datex2 import ClosureType, NationalHighwaysClient
    >>> with NationalHighwaysClient(subscription_key) as nh:
    ...     for situation in nh.iter_roadworks(ClosureType.PLANNED):
    ...         print(situation.id, situation.roadworks[0].cause_type)
    """

    def __init__(
        self,
        subscription_key: str,
        *,
        base_url: str = BASE_URL,
        retry: RetryConfig | None = None,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.subscription_key = subscription_key
        self.base_url = base_url.rstrip("/")
        client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=client
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            # Undocumented as mandatory, but the live API defaults to XML
            # without this - see module docstring.
            "X-Response-MediaType": "application/json",
        }

    def get_closures(
        self,
        closure_type: ClosureType | str = ClosureType.PLANNED,
        *,
        start_date_time: str | None = None,
        end_date_time: str | None = None,
        modified_since_date_time: str | None = None,
        page_cursor_url: str | None = None,
    ) -> tuple[JSON, str | None]:
        """One page of ``GET /closures``. Returns ``(payload, next_page_url)``;
        ``next_page_url`` is ``None`` once the last page has been reached.

        Pass ``page_cursor_url`` (the previous call's returned URL) to fetch a
        specific page - it already carries every query parameter, so the other
        keyword arguments are ignored when it's set.
        """
        if page_cursor_url:
            response = self._transport.request(
                "GET", page_cursor_url, header_provider=self._headers
            )
        else:
            value = closure_type.value if isinstance(closure_type, ClosureType) else closure_type
            params: dict[str, str] = {"closureType": value}
            if start_date_time:
                params["startDateTime"] = start_date_time
            if end_date_time:
                params["endDateTime"] = end_date_time
            if modified_since_date_time:
                params["modifiedSinceDateTime"] = modified_since_date_time
            response = self._transport.request(
                "GET",
                f"{self.base_url}/{_CLOSURES_PATH}",
                header_provider=self._headers,
                params=params,
            )
        payload = response.json()
        return payload, response.headers.get("x-next")

    def iter_pages(
        self,
        closure_type: ClosureType | str = ClosureType.PLANNED,
        *,
        start_date_time: str | None = None,
        end_date_time: str | None = None,
        modified_since_date_time: str | None = None,
        max_pages: int | None = None,
    ) -> Iterator[JSON]:
        """Yield each page's raw ``D2Payload`` dict, following the ``x-next``
        cursor until exhausted (or ``max_pages`` is reached)."""
        payload, next_url = self.get_closures(
            closure_type,
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            modified_since_date_time=modified_since_date_time,
        )
        pages = 1
        yield payload
        while next_url and (max_pages is None or pages < max_pages):
            payload, next_url = self.get_closures(page_cursor_url=next_url)
            pages += 1
            yield payload

    def iter_situations(
        self,
        closure_type: ClosureType | str = ClosureType.PLANNED,
        **kwargs: Any,
    ) -> Iterator[Situation]:
        """Page through the closures endpoint, yielding parsed
        :class:`Situation` objects. ``kwargs`` are forwarded to
        :meth:`iter_pages`."""
        for page in self.iter_pages(closure_type, **kwargs):
            yield from parse_situations(page)

    def iter_roadworks(
        self,
        closure_type: ClosureType | str = ClosureType.PLANNED,
        **kwargs: Any,
    ) -> Iterator[Situation]:
        """Like :meth:`iter_situations`, but only situations with at least one
        roadworks record (``cause.causeType`` of ``roadMaintenance`` or
        ``constructionWork``)."""
        for situation in self.iter_situations(closure_type, **kwargs):
            if situation.roadworks:
                yield situation

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> NationalHighwaysClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
