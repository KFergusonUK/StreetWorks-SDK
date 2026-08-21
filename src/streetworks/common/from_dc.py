"""Washington, DC (DDOT Construction Permits) -> streetworks.common
converter. This SDK's first standalone Washington DC coverage.

One :class:`~streetworks.common.Works` per feature, each with a single
:class:`~streetworks.common.WorksSite` - ``PERMITNUMBER`` is already a
unique per-record identifier (confirmed live: always ``"PA" +
TRACKINGNUMBER``), no grouping key found linking separate permits into one
project, the same one-to-one shape :mod:`.from_au_tas_roadworks` uses.

``works_type`` is built from the six real boolean work-type flags
(``ISEXCAVATION``/``ISPAVING``/``ISLANDSCAPING``/``ISPROJECTIONS``/
``ISFIXTURE``/``ISPSRENTAL``) - confirmed live not mutually exclusive, so
every true flag is joined, not just the first; ``None`` on the real
minority of records (60/1000 sampled) where every flag is false, rather
than an empty string.

**``date_confidence`` is read off the real ``STATUS`` value** - ``"Issued"``
means the permit is live/real, landing on ``actual_start``/``actual_end``
with ``VERIFIED`` confidence; every other real status (``Pending
Assignment``, ``Assigned``, ``Resubmitted``, ``Not Paid``, ``Revise and
Resubmit``, ``Approved (Pending Payment)``, ``Permit Expired``,
``Cancel/Withdrawn``, ``Denied``) lands on ``proposed_start``/
``proposed_end`` with ``ESTIMATED`` - this module doesn't distinguish
"not yet issued" from "no longer active" (``Expired``/``Cancelled``/
``Denied``) since none of those states confirm the work's real dates any
more reliably than a pending one does; see
:mod:`streetworks.arcgis.dc`'s own module docstring for the full real
status list.

Dates are real ``esriFieldTypeDate`` fields - epoch milliseconds UTC even
under this service's own ``f=geojson`` export (confirmed live, the same
convention :mod:`.from_au_tas_roadworks`/:mod:`.from_nzta` already
document for other ArcGIS sources).

Geometry is genuine WGS84 under ``f=geojson`` on this service (confirmed
live - see :mod:`streetworks.arcgis.dc`'s own module docstring), flipped
from GeoJSON's native ``(lon, lat)`` to this SDK's stated ``(lat, lon)``
``Coordinate`` convention.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_dc"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "USA"
_ADMINISTRATIVE_AREA = "District Department of Transportation"

#: Real flag field -> readable work-type label. See module docstring.
_WORK_TYPE_FLAGS = (
    ("ISEXCAVATION", "Excavation"),
    ("ISPAVING", "Paving"),
    ("ISLANDSCAPING", "Landscaping"),
    ("ISPROJECTIONS", "Projections"),
    ("ISFIXTURE", "Fixture"),
    ("ISPSRENTAL", "Public Space Rental"),
)

#: The one real STATUS value meaning the permit is live - see module
#: docstring for the full real status list this was checked against.
_ISSUED_STATUS = "Issued"


def _epoch_millis_to_dt(value: int | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _works_type(properties: JSON) -> str | None:
    labels = [label for field, label in _WORK_TYPE_FLAGS if properties.get(field) == "T"]
    return " / ".join(labels) or None


def _coordinate(feature: JSON) -> Coordinate | None:
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    if (geometry.get("type") or "").upper() != "POINT" or not coords:
        return None
    lon, lat = coords
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    status = properties.get("STATUS")
    is_issued = status == _ISSUED_STATUS
    start = _epoch_millis_to_dt(properties.get("EFFECTIVEDATE"))
    end = _epoch_millis_to_dt(properties.get("EXPIRATIONDATE"))
    confidence = (
        DateConfidence.VERIFIED
        if is_issued
        else (DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN)
    )
    return WorksSite(
        reference=properties.get("PERMITNUMBER"),
        works_type=_works_type(properties),
        status=status,
        location_description=properties.get("WLFULLADDRESS"),
        coordinate=_coordinate(feature),
        proposed_start=None if is_issued else start,
        proposed_end=None if is_issued else end,
        actual_start=start if is_issued else None,
        actual_end=end if is_issued else None,
        date_confidence=confidence,
        traffic_management=properties.get("WORKDETAIL"),
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )


def from_dc(features: list[JSON]) -> list[Works]:
    """Convert real DDOT Construction Permit features (from
    :meth:`streetworks.arcgis.dc.DCConstructionPermitsClient.iter_roadworks`)
    into :class:`~streetworks.common.Works` - one per feature, each with a
    single ``WorksSite``. See module docstring."""
    works_list: list[Works] = []
    for feature in features:
        properties = feature.get("properties") or {}
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                promoter=properties.get("PERMITTEENAME"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.REGISTER,
                sites=(site,),
                raw=feature,
            )
        )
    return works_list
