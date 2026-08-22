"""Road Report NT (Northern Territory) -> streetworks.common converter.

One :class:`~streetworks.common.Works` per GetAll record that is actually
works, each with a single :class:`~streetworks.common.WorksSite` - no
grouping key is stated linking separate obstructions into one project,
the same one-to-one shape every other AU converter in this cluster uses.

This converter is for :meth:`streetworks.au.nt.RoadReportNtClient.iter_roadworks`
output. It does **not** turn weight limits, flooding, or other condition
records into :class:`~streetworks.common.Works` - those are not works,
and the feed's own terminology page says so. Passing a non-works record
here is a no-op for that row (skipped), so a mixed ``iter_obstructions()``
list cannot accidentally inflate the works view.

**``Works.reference`` is ``obstructionId``.** Both ``obstructionId`` and
``recordId`` were unique across the 140-record 2026-08-19 pull;
``obstructionId`` is the obstruction's own identifier. The JSON.NET
``$id`` is a serialisation artefact and is not used.

``territory="Australia"``, ``administrative_area="Department of
Infrastructure, Planning and Logistics"`` - the NT-Government road
authority IS the data-owning operator (agency name currently in flux
with a DIPL -> DLI rename; the historical DIPL string is kept until a
source record states otherwise). ``roadName`` / ``locationComment``
describe the worksite, so both go into ``location_description``.

**Geometry comes from ``startPoint`` / ``endPoint`` only.** The live
``geometry`` / ``geometries`` fields were empty on every record. Source
arrays are ``[lat, lon]`` already - :class:`~streetworks.common.Coordinate`
stores ``value``/``points`` as ``(lat, lon)``, this SDK's stated
convention for every EPSG:4326 point (confirmed in
``from_au_tas_roadworks``/``from_au_act_ttm``/``from_au_wa_mainroads``/
``from_nzta``'s own docstrings, and enforced at the source in every one
of them - the same fix this module needed too, found live: an earlier
version of this converter flipped to GeoJSON ``(lon, lat)`` order by
mistake, silently dropping every real NT point off the world-map example
(a latitude field carrying a real longitude value like 131 is out of
range and simply doesn't plot). No flip is needed here since the source
is already ``[lat, lon]`` - it's passed straight through as a 2-tuple.
Identical start and end (1/26 real Roadworks records) is a genuine
point - ``points`` stays ``None``, never a synthetic one-vertex line.

See :mod:`streetworks.au.nt`'s own module docstring for the full set of
real findings this mapping is built from (the 26/140 works split, naive
datetimes, ``dateTo`` being unused on that pull) - not re-derived here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_au_nt_roadreport"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Australia"
_ADMINISTRATIVE_AREA = "Department of Infrastructure, Planning and Logistics"
_ROADWORKS_TYPE = "Roadworks"
_ROADWORKS_TYPE_CODE = "28"


def _is_roadworks(record: JSON) -> bool:
    """Same works test as :func:`streetworks.au.nt.is_roadworks` - kept
    local so this converter does not import the client module."""
    if record.get("obstructionType") == _ROADWORKS_TYPE:
        return True
    code = record.get("obstructionTypeCode")
    return code == _ROADWORKS_TYPE_CODE or code == 28


def _parse_nt_datetime(value: Any) -> datetime | None:
    """``dateFrom`` / ``dateTo`` are naive ``YYYY-MM-DD HH:MM:SS``
    strings - no offset, no stated timezone. Kept naive; never assigned
    ACST/ACDT. See :mod:`streetworks.au.nt`."""
    if not isinstance(value, str) or not value.strip():
        return None
    return parse_iso8601(value.replace(" ", "T", 1))


def _lat_lon(value: Any) -> tuple[float, float] | None:
    """Source ``startPoint`` / ``endPoint`` are ``[lat, lon]``."""
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        return float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None


def _coordinate(record: JSON) -> Coordinate | None:
    start = _lat_lon(record.get("startPoint"))
    end = _lat_lon(record.get("endPoint"))
    if start is None and end is None:
        return None
    if start is None:
        start = end
    assert start is not None
    # Source is already [lat, lon] - this SDK's stated (lat, lon)
    # convention for EPSG:4326, no flip needed. See module docstring.
    if end is None or end == start:
        return Coordinate(value=start, crs=_CRS)
    points = (start, end)
    return Coordinate(value=points[0], crs=_CRS, points=points)


def _location_description(record: JSON) -> str | None:
    parts = [record.get("roadName"), record.get("locationComment")]
    text = ", ".join(part for part in parts if part)
    return text or None


def _traffic_management(record: JSON) -> str | None:
    """``restrictionType`` is the official impact class (With Caution /
    Road Closed / Lane Closure on real Roadworks); ``comment`` is the
    free-text advice. Folded together - no separate canonical field for
    the restriction class."""
    parts = [record.get("restrictionType"), record.get("comment")]
    text = " - ".join(part for part in parts if part and part != "-")
    return text or None


def _reference(record: JSON) -> str | None:
    obstruction_id = record.get("obstructionId")
    if obstruction_id is None:
        return None
    return str(obstruction_id)


def _to_site(record: JSON) -> WorksSite:
    start = _parse_nt_datetime(record.get("dateFrom"))
    end = _parse_nt_datetime(record.get("dateTo"))
    return WorksSite(
        reference=_reference(record),
        works_type=record.get("obstructionType"),
        status=record.get("status"),
        location_description=_location_description(record),
        coordinate=_coordinate(record),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN,
        traffic_management=_traffic_management(record),
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_au_nt_roadreport(records: list[JSON]) -> list[Works]:
    """Convert real Road Report NT GetAll records (from
    :meth:`streetworks.au.nt.RoadReportNtClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - one per works record, each with
    a single ``WorksSite``. Non-works obstruction types are skipped.
    See module docstring."""
    works_list: list[Works] = []
    for record in records:
        if not _is_roadworks(record):
            continue
        site = _to_site(record)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
