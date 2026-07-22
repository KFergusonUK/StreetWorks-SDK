"""Jersey RoadWorkx -> streetworks.common converter. This SDK's first
Channel Islands coverage.

Groups real ``RoadWorks`` features by ``PROJID`` into one
:class:`~streetworks.common.Works` per project - confirmed live to be the
same real shape as Street Manager's ``work_reference_number``/
``permit_reference_number``: ``NAME``/``PROJID`` are always identical (the
project key) and several ``JOBID``s (the per-record key) share one, e.g.
real project ``"P108864-JSC"`` covering ``JOBID``s 107263/107264/107265.
One :class:`~streetworks.common.WorksSite` per ``JOBID``.

``date_confidence`` is read directly off the real ``STATUS`` value
(``"In Progress"``/``"Finished"``/``"Pending"`` - see
:mod:`streetworks.arcgis.jersey`'s module docstring for how this was
confirmed to be the design brief's "planned/future dimension", not a
separate layer or type): ``"Pending"`` means the dates are proposed, not
yet real, so they land on ``proposed_start``/``proposed_end`` with
``ESTIMATED`` confidence; ``"In Progress"``/``"Finished"`` mean the dates
are real, landing on ``actual_start``/``actual_end`` with ``VERIFIED``.

Geometry is carried through in the service's own real CRS,
``EPSG:3109`` ("ETRS89 / Jersey Transverse Mercator") - confirmed live, see
:mod:`streetworks.arcgis.jersey`'s module docstring for the verification
chain and why ``outSR`` cannot be relied on to change it. Never
reprojected here either.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_jersey"]

JSON = dict[str, Any]

#: Jersey's own IANA timezone (a real, named zone - not merely an alias
#: reused from the UK's, though it shares the same UTC offsets/DST rules).
_JERSEY_TZ = ZoneInfo("Europe/Jersey")

#: See streetworks.arcgis.jersey.CRS - authoritative for every real
#: response this service gives, confirmed live not to change with outSR.
_CRS = "EPSG:3109"


def _dt(value: str | None) -> datetime | None:
    """Real ``S_DATE``/``E_DATE`` values are ``"YYYYMMDD HHMM"`` strings
    (confirmed live, e.g. ``"20211107 1000"``), 24-hour, no seconds."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d %H%M").replace(tzinfo=_JERSEY_TZ)
    except ValueError:
        return None


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    coords = geometry.get("coordinates")
    kind = geometry.get("type")
    if kind == "LineString" and coords:
        points = tuple(tuple(c) for c in coords)
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
    if kind == "Point" and coords:
        return Coordinate(value=tuple(coords), crs=_CRS)
    return None


def _to_site(feature: JSON) -> WorksSite:
    props = feature.get("properties", {})
    status = props.get("STATUS")
    start = _dt(props.get("S_DATE"))
    end = _dt(props.get("E_DATE"))
    is_pending = status == "Pending"
    if is_pending:
        confidence = DateConfidence.ESTIMATED
    elif start is not None:
        confidence = DateConfidence.VERIFIED
    else:
        confidence = DateConfidence.UNKNOWN
    return WorksSite(
        reference=props.get("JOBID"),
        works_type=props.get("WorkType") or props.get("Type"),
        status=status,
        location_description=props.get("Location"),
        coordinate=_coordinate(feature.get("geometry")),
        proposed_start=start if is_pending else None,
        proposed_end=end if is_pending else None,
        actual_start=None if is_pending else start,
        actual_end=None if is_pending else end,
        date_confidence=confidence,
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )


def from_jersey(features: list[JSON]) -> list[Works]:
    """Convert real Jersey RoadWorkx GeoJSON features (from
    :meth:`streetworks.arcgis.jersey.JerseyRoadworksClient.iter_roadworks`)
    into a list of :class:`~streetworks.common.Works`, grouped by
    ``PROJID`` - see module docstring. A feature with no ``PROJID`` at all
    (not observed live, but the field isn't a contract) gets its own
    free-standing single-site ``Works`` rather than being grouped or
    dropped."""
    by_project: dict[str, list[JSON]] = defaultdict(list)
    unresolved: list[JSON] = []
    for feature in features:
        projid = feature.get("properties", {}).get("PROJID")
        if projid:
            by_project[projid].append(feature)
        else:
            unresolved.append(feature)

    works_list: list[Works] = []
    for projid, group in by_project.items():
        sites = [_to_site(f) for f in group]
        header = group[0].get("properties", {})
        works_list.append(
            Works(
                reference=projid,
                coordinate=sites[0].coordinate if sites else None,
                promoter=header.get("Promoter"),
                territory="Jersey",
                administrative_area=header.get("Authority"),
                source_grade=SourceGrade.REGISTER,
                sites=tuple(sites),
                raw=group,
            )
        )
    for feature in unresolved:
        site = _to_site(feature)
        props = feature.get("properties", {})
        works_list.append(
            Works(
                reference=None,
                coordinate=site.coordinate,
                promoter=props.get("Promoter"),
                territory="Jersey",
                administrative_area=props.get("Authority"),
                source_grade=SourceGrade.REGISTER,
                sites=(site,),
                raw=[feature],
            )
        )
    return works_list
