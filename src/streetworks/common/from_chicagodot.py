"""Chicago CDOT Street Closures -> streetworks.common converter. This
SDK's third ``source_grade=register`` source (after England's Street
Manager and NYC DOT) - see :mod:`streetworks.chicagodot.client`'s own
module docstring for the full investigation behind every claim below.

**A real Works-umbrella grouping, the same shape as NYC's
``applicationtrackingid``.** ``applicationnumber`` genuinely groups
multiple real rows (one real example, ``DOT604194``, had 64 real rows
across 64 genuinely different real street locations - a citywide
restoration job). So ``from_chicagodot`` groups by it the same way
:func:`~streetworks.common.from_nycdot.from_nycdot` groups by
``applicationtrackingid`` - one ``Works`` per application, one
``WorksSite`` per real row under it. A row with no ``applicationnumber``
(not observed live, but never assumed absent) falls back to a thin,
one-site ``Works`` keyed on its own ``uniquekey``.

**``street_ref`` is never populated** - the real 46-column schema has no
segment/street identifier field, only free text (``streetname``/
``direction``/``suffix``/``streetnumberfrom``/``streetnumberto``). See
:mod:`streetworks.chicagodot.client` for the full finding.

**``date_confidence`` is uniformly ``ESTIMATED``, never ``VERIFIED``** -
real ``applicationstatus`` values (``Open``/``Closed``) describe the
*application's* lifecycle, not whether the work itself actually
happened as scheduled - the same honest gap NYC's own
``permitstatusshortdesc`` has. ``applicationstartdate``/
``applicationenddate`` map to ``proposed_start``/``proposed_end`` only;
``actual_start``/``actual_end`` stay ``None``.

**Geometry**: a real, native GeoJSON ``location`` Point field (WGS84,
populated on 99.94% of real rows) - no WKT parsing, no CRS inference
needed, unlike NYC's own EPSG:2263 WKT column.

**``traffic_management`` carries the real ``streetclosure`` value**
(``Curblane``/``Full``/``Sidewalk``/``Partial``/``Intermitte``) - a
genuine real closure-type signal this SDK's NYC converter has no
equivalent for.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_chicagodot"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "USA"
_ADMINISTRATIVE_AREA = "City of Chicago Department of Transportation (CDOT)"


def _coordinate(properties: JSON) -> Coordinate | None:
    location = properties.get("location")
    if not location or (location.get("type") or "").upper() != "POINT":
        return None
    coords = location.get("coordinates")
    if not coords:
        return None
    lon, lat = float(coords[0]), float(coords[1])
    return Coordinate(value=(lat, lon), crs=_CRS)


def _location_description(properties: JSON) -> str | None:
    street_name = properties.get("streetname")
    if not street_name:
        return None
    full_street = " ".join(
        p for p in (properties.get("direction"), street_name, properties.get("suffix")) if p
    )
    number_from = properties.get("streetnumberfrom")
    number_to = properties.get("streetnumberto")
    if number_from and number_to and number_from != number_to:
        return f"{number_from}-{number_to} {full_street}"
    if number_from:
        return f"{number_from} {full_street}"
    return full_street


def _to_site(permit: JSON) -> WorksSite:
    return WorksSite(
        reference=permit.get("uniquekey"),
        works_type=permit.get("worktypedescription"),
        status=permit.get("applicationstatus"),
        location_description=_location_description(permit),
        coordinate=_coordinate(permit),
        proposed_start=parse_iso8601(permit.get("applicationstartdate")),
        proposed_end=parse_iso8601(permit.get("applicationenddate")),
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=permit.get("streetclosure"),
        source_grade=SourceGrade.REGISTER,
        raw=permit,
    )


def from_chicagodot(permits: list[JSON]) -> list[Works]:
    """Convert real Chicago CDOT Street Closures rows (plain dicts from
    :meth:`streetworks.chicagodot.ChicagoDotClient.iter_permits`/
    ``iter_roadworks``) into :class:`~streetworks.common.Works`. Date
    fields are real ISO-8601 text (Socrata's own ``calendar_date``
    column encoding), parsed via the shared
    :func:`~streetworks._dt.parse_iso8601`."""
    grouped: dict[str, list[JSON]] = defaultdict(list)
    thin: list[JSON] = []
    for permit in permits:
        application_number = permit.get("applicationnumber")
        if application_number:
            grouped[application_number].append(permit)
        else:
            thin.append(permit)

    works_list = [
        Works(
            reference=application_number,
            coordinate=_coordinate(group[0]),
            promoter=group[0].get("primarycontactlast"),
            territory=_TERRITORY,
            administrative_area=_ADMINISTRATIVE_AREA,
            source_grade=SourceGrade.REGISTER,
            sites=tuple(_to_site(p) for p in group),
            raw=group,
        )
        for application_number, group in grouped.items()
    ]
    works_list.extend(
        Works(
            reference=permit.get("uniquekey"),
            coordinate=_coordinate(permit),
            promoter=permit.get("primarycontactlast"),
            territory=_TERRITORY,
            administrative_area=_ADMINISTRATIVE_AREA,
            source_grade=SourceGrade.REGISTER,
            sites=(_to_site(permit),),
            raw=[permit],
        )
        for permit in thin
    )
    return works_list
