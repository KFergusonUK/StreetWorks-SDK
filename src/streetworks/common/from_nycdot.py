"""NYC DOT Street Construction Permits -> streetworks.common converter.
This SDK's second ``source_grade=register`` source (after England's
Street Manager) and the first in the US - see
:mod:`streetworks.nycdot.client`'s own module docstring for the full
investigation behind every claim below.

**A real Works-umbrella grouping, the direct Street Manager parallel.**
``applicationtrackingid`` genuinely groups multiple real permits (one
real application had 226 real permits under it - a large paving job
spanning many street segments, each its own permit/``sequencenumber``).
So ``from_nycdot`` groups by it the same way :func:`~streetworks.common.from_wzdx.from_wzdx`
groups by ``works_ref`` - one ``Works`` per application, one
``WorksSite`` per permit under it. A permit with no
``applicationtrackingid`` (not observed live, but never assumed absent)
falls back to a thin, one-site ``Works`` keyed on its own permit number.

**``street_ref`` is never populated** - the real 39-column schema has no
LION ``segmentid`` or any other street-register identifier, only free
text (``onstreetname``/``fromstreetname``/``tostreetname``). See
:mod:`streetworks.nycdot.client` for the full finding.

**``date_confidence`` is uniformly ``ESTIMATED``, never ``VERIFIED``** -
real ``permitstatusshortdesc`` values (``EXPIRED``, ``ISSUED & PRINTED``,
``DELINQUENT CONFIRMATION``, ...) describe the *permit's* lifecycle, not
whether the work itself actually happened as scheduled - there is no
real "confirmed to have occurred" signal on this dataset, unlike NZTA's
own real ``status`` field. ``issuedworkstartdate``/``issuedworkenddate``
(the authorised work window) map to ``proposed_start``/``proposed_end``
only; ``actual_start``/``actual_end`` stay ``None`` - the brief's own
"issued is not active" distinction, carried through honestly rather than
guessed at.

**Geometry**: real ``wkt`` (``LINESTRING``/``POINT``/``MULTIPOINT``,
80.5% of all real rows) parsed via the shared
:func:`~streetworks.common._wkt.coordinate_from_wkt`, native CRS
**EPSG:2263** (NAD83 / New York Long Island, ftUS) - inferred from
coordinate-value-range evidence and the near-universal NYC city-agency
GIS convention, not an explicitly stated dataset SRID, and never
silently reprojected to WGS84.

**Dates are real, but timezone-naive** - real values look like
``"2025-07-17T15:54:39.000"``, no ``Z``/offset at all (unlike WZDx's own
UTC-suffixed timestamps), so the parsed ``datetime`` objects here are
naive - presumably America/New_York local time, but that's this
converter's own inference, not something the source states, so it's
never attached as an explicit ``tzinfo``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .._dt import parse_iso8601
from ._wkt import coordinate_from_wkt
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_nycdot"]

JSON = dict[str, Any]

_CRS = "EPSG:2263"
_TERRITORY = "USA"
_ADMINISTRATIVE_AREA = "New York City Department of Transportation (DOT)"


def _coordinate(properties: JSON) -> Coordinate | None:
    return coordinate_from_wkt(properties.get("wkt"), crs=_CRS)


def _location_description(properties: JSON) -> str | None:
    on = properties.get("onstreetname")
    if not on:
        return None
    parts = [on]
    from_street = properties.get("fromstreetname")
    to_street = properties.get("tostreetname")
    if from_street and to_street:
        parts.append(f"between {from_street} and {to_street}")
    elif from_street:
        parts.append(f"at {from_street}")
    borough = properties.get("boroughname")
    if borough:
        parts.append(f"({borough.title()})")
    return " ".join(parts)


def _to_site(permit: JSON) -> WorksSite:
    return WorksSite(
        reference=permit.get("permitnumber"),
        works_type=permit.get("permittypedesc"),
        status=permit.get("permitstatusshortdesc"),
        location_description=_location_description(permit),
        coordinate=_coordinate(permit),
        proposed_start=parse_iso8601(permit.get("issuedworkstartdate")),
        proposed_end=parse_iso8601(permit.get("issuedworkenddate")),
        date_confidence=DateConfidence.ESTIMATED,
        source_grade=SourceGrade.REGISTER,
        raw=permit,
    )


def from_nycdot(permits: list[JSON]) -> list[Works]:
    """Convert real NYC DOT Street Construction Permits rows (plain dicts
    from :meth:`streetworks.nycdot.NycDotClient.iter_permits`/
    ``iter_roadworks``) into :class:`~streetworks.common.Works`. Date
    fields are real ISO-8601 text (Socrata's own ``calendar_date`` column
    encoding) - parsed here via the shared
    :func:`~streetworks._dt.parse_iso8601`, see module docstring for why
    the result is timezone-naive."""
    grouped: dict[str, list[JSON]] = defaultdict(list)
    thin: list[JSON] = []
    for permit in permits:
        tracking_id = permit.get("applicationtrackingid")
        if tracking_id:
            grouped[tracking_id].append(permit)
        else:
            thin.append(permit)

    works_list = [
        Works(
            reference=tracking_id,
            coordinate=_coordinate(group[0]),
            promoter=group[0].get("permitteename"),
            territory=_TERRITORY,
            administrative_area=_ADMINISTRATIVE_AREA,
            source_grade=SourceGrade.REGISTER,
            sites=tuple(_to_site(p) for p in group),
            raw=group,
        )
        for tracking_id, group in grouped.items()
    ]
    works_list.extend(
        Works(
            reference=permit.get("permitnumber"),
            coordinate=_coordinate(permit),
            promoter=permit.get("permitteename"),
            territory=_TERRITORY,
            administrative_area=_ADMINISTRATIVE_AREA,
            source_grade=SourceGrade.REGISTER,
            sites=(_to_site(permit),),
            raw=[permit],
        )
        for permit in thin
    )
    return works_list
