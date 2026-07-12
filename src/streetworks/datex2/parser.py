"""Streaming DATEX II parser (roadworks profile), namespace-tolerant.

DATEX II v3 spreads elements across many namespaces (``sit:``, ``com:``,
``loc:``, plus national extensions); v2 uses a single ``D2LogicalModel``
namespace with the same local names for the concepts this profile needs. This
parser therefore matches on *local names* and reads ``xsi:type`` local parts,
which makes it tolerant of both versions and of national extensions - at the
deliberate cost of ignoring namespace semantics the roadworks profile doesn't
depend on.

Feeds can be huge (the Dutch national planned-works feed is ~170 MB
uncompressed), so parsing streams via ``iterparse`` and yields one
:class:`~streetworks.datex2.models.Situation` at a time; gzipped files are
opened transparently.
"""

from __future__ import annotations

import gzip
from collections.abc import Iterator
from pathlib import Path
from typing import IO
from xml.etree.ElementTree import Element, iterparse

from .._dt import parse_iso8601 as _dt
from .models import Location, Period, Situation, SituationRecord, Validity

__all__ = ["iter_situations", "iter_roadworks"]

_XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xsi_local(element: Element) -> str:
    value = element.get(_XSI_TYPE, "")
    return value.split(":", 1)[-1] if value else ""


def _find(element: Element, *path: str) -> Element | None:
    """Descend by local names, first match wins at each step."""
    current: Element | None = element
    for name in path:
        if current is None:
            return None
        current = next((c for c in current if _local(c.tag) == name), None)
    return current


def _findall(element: Element, name: str) -> list[Element]:
    return [c for c in element if _local(c.tag) == name]


def _text(element: Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _deep_text(element: Element, *path: str) -> str | None:
    return _text(_find(element, *path))


def _multilingual(element: Element | None) -> str | None:
    """values/value[lang] - return the first value's text."""
    if element is None:
        return None
    value = _find(element, "values", "value")
    return _text(value) or _text(element)


def _first_descendant(element: Element, name: str) -> Element | None:
    for descendant in element.iter():
        if _local(descendant.tag) == name:
            return descendant
    return None


# --------------------------------------------------------------------------- #
# Section parsers
# --------------------------------------------------------------------------- #


def _parse_validity(record: Element) -> Validity:
    validity = _find(record, "validity")
    if validity is None:
        return Validity()
    spec = _find(validity, "validityTimeSpecification")
    periods: list[Period] = []
    if spec is not None:
        for period in _findall(spec, "validPeriod"):
            periods.append(
                Period(
                    start=_dt(_deep_text(period, "startOfPeriod")),
                    end=_dt(_deep_text(period, "endOfPeriod")),
                )
            )
    return Validity(
        status=_deep_text(validity, "validityStatus"),
        overall_start=_dt(_deep_text(spec, "overallStartTime")) if spec is not None else None,
        overall_end=_dt(_deep_text(spec, "overallEndTime")) if spec is not None else None,
        periods=tuple(periods),
    )


def _parse_location(record: Element) -> Location:
    location = _find(record, "locationReference")
    if location is None:
        # v2 nests it as groupOfLocations/locationContainedInGroup etc.
        location = _first_descendant(record, "groupOfLocations")
    if location is None:
        return Location()

    kind = _xsi_local(location) or None
    points: list[tuple[float, float]] = []

    # Point locations: pointByCoordinates/pointCoordinates/latitude+longitude
    coordinates = _first_descendant(location, "pointCoordinates")
    if coordinates is not None:
        lat = _deep_text(coordinates, "latitude")
        lon = _deep_text(coordinates, "longitude")
        if lat and lon:
            points.append((float(lat), float(lon)))

    # Linear locations: gmlLineString/posList ("lon lat lon lat ..." or
    # "lat lon ..." depending on srsName; DATEX II uses lat/lon pairs).
    pos_list = _first_descendant(location, "posList")
    if pos_list is not None and pos_list.text:
        values = pos_list.text.split()
        pairs = [(float(values[i]), float(values[i + 1])) for i in range(0, len(values) - 1, 2)]
        points.extend(pairs)

    # carriageway nests (carriageway/carriageway); take the deepest one
    # that actually has text.
    carriageway = next(
        (
            _text(d)
            for d in reversed(list(location.iter()))
            if _local(d.tag) == "carriageway" and _text(d)
        ),
        None,
    )

    road_number = _text(_first_descendant(location, "roadNumber"))
    alert_c = _text(_first_descendant(location, "specificLocation"))

    return Location(
        kind=kind,
        points=tuple(points),
        carriageway=carriageway,
        road_number=road_number,
        alert_c_location=alert_c,
    )


def _parse_record(element: Element) -> SituationRecord:
    cause = _find(element, "cause")
    comments = tuple(
        text
        for comment in _findall(element, "generalPublicComment")
        if (text := _multilingual(_find(comment, "comment")))
    )
    urgent_text = _deep_text(element, "urgentRoadworks")
    return SituationRecord(
        id=element.get("id", ""),
        record_type=_xsi_local(element) or "SituationRecord",
        version=element.get("version"),
        creation_time=_dt(_deep_text(element, "situationRecordCreationTime")),
        version_time=_dt(_deep_text(element, "situationRecordVersionTime")),
        probability_of_occurrence=_deep_text(element, "probabilityOfOccurrence"),
        source_name=_multilingual(_find(element, "source", "sourceName")),
        validity=_parse_validity(element),
        location=_parse_location(element),
        cause_type=_deep_text(cause, "causeType") if cause is not None else None,
        cause_description=_multilingual(_find(cause, "causeDescription"))
        if cause is not None
        else None,
        comments=comments,
        impact_delay_band=_text(_first_descendant(element, "delayBand")),
        operator_action_status=_deep_text(element, "operatorActionStatus"),
        urgent=None if urgent_text is None else urgent_text.lower() == "true",
        road_maintenance_type=_deep_text(element, "roadMaintenanceType"),
        construction_work_type=_deep_text(element, "constructionWorkType"),
        subject_type_of_works=_deep_text(element, "subjects", "subjectTypeOfWorks"),
    )


def _parse_situation(element: Element) -> Situation:
    situation = Situation(
        id=element.get("id", ""),
        version_time=_dt(_deep_text(element, "situationVersionTime")),
        overall_severity=_deep_text(element, "overallSeverity"),
    )
    for child in element:
        if _local(child.tag) == "situationRecord":
            situation.records.append(_parse_record(child))
    return situation


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def _open_stream(source: str | Path | IO[bytes]) -> tuple[IO[bytes], bool]:
    if hasattr(source, "read"):
        return source, False
    path = Path(source)
    raw = open(path, "rb")
    magic = raw.read(2)
    raw.seek(0)
    if magic == b"\x1f\x8b":  # gzip
        return gzip.open(raw), True
    return raw, True


def iter_situations(source: str | Path | IO[bytes]) -> Iterator[Situation]:
    """Stream :class:`Situation` objects from a DATEX II document.

    ``source`` may be a path to an XML file, a path to a gzipped XML file
    (detected by magic bytes, so any filename works), or an open binary
    stream. Works with DATEX II v3 (``messageContainer``) and v2
    (``d2LogicalModel``) documents that carry a SituationPublication.
    """
    stream, owned = _open_stream(source)
    try:
        for _event, element in iterparse(stream, events=("end",)):
            if _local(element.tag) == "situation":
                yield _parse_situation(element)
                element.clear()
    finally:
        if owned:
            stream.close()


def iter_roadworks(source: str | Path | IO[bytes]) -> Iterator[Situation]:
    """Like :func:`iter_situations`, but only situations that contain at least
    one roadworks record (MaintenanceWorks/ConstructionWorks)."""
    for situation in iter_situations(source):
        if situation.roadworks:
            yield situation
