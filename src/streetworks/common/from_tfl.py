"""Transport for London (TfL) Road Disruption -> streetworks.common
converter. See :mod:`streetworks.tfl.client`'s own module docstring for
the full investigation - in particular why `corridorIds` never becomes
`street_ref` and why only `Point` geometry is handled.

**No grouping - each record already stands alone.** Real `id` values
(e.g. `"TIMS-231236"`) are unique per disruption - the same one-record-
one-`Works` shape as `from_lisboa`/`from_milano`, not Oslo/Helsinki's
umbrella grouping.

**Geometry: real `Point`, genuine WGS84 with an explicit stated CRS -
flipped to this SDK's `(lat, lon)` convention.** The cleanest CRS
situation of any provider in this SDK: every record's own `geography`
field states its CRS explicitly (`EPSG:4326`), nothing inferred or
cross-checked indirectly. Only `Point` is handled - see client module
docstring for why `LineString`/`roadDisruptionLines` isn't (never
observed populated in the real live data).

**`corridorIds` is never promoted to `street_ref`.** Confirmed live
that it's genuinely incomplete - only 51/116 real `Works` records carry
one at all, including just 11/21 of the core "TfL works" subcategory -
so it can't serve as a reliable join key, the same "a real but
incomplete field, not a join key" discipline this SDK applies wherever
a plausible identifier turns out to be unreliable. Preserved on `.raw`
only.

**`promoter` is never populated** - no per-record organisation-name
field exists in this schema (`subCategory` is a category - "Utility
works", "TfL works", "Borough works" - not a specific company or
authority name), the same honest gap Kanton Zürich's own schema has.

**`traffic_management` is `comments`** - real descriptions of the
actual measures in place (lane closures, signal timings, diversions),
a better fit than the more live-conditions-flavoured `currentUpdate`
(preserved on `.raw` only, not forced into a field it doesn't
describe).

**`status == "Active"` genuinely means the disruption is currently
happening, not merely scheduled - checked explicitly, not assumed
constant.** This endpoint only ever returned `"Active"` in the live
data checked, a structural property of what `/Road/all/Disruption`
returns, but the check is explicit so a differently-shaped future pull
still behaves correctly. When active, `actual_start`/`actual_end` are
populated and `DateConfidence.VERIFIED` is graded (the same
`actual_start`-present rule `from_streetmanager`/`from_helsinki`
already use); otherwise only `proposed_start`/`proposed_end` and
`ESTIMATED`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_tfl"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "England"
_ADMINISTRATIVE_AREA = "Transport for London"

#: The one real status value confirmed live to mean "genuinely active
#: now" - see module docstring.
_ACTIVE_STATUS = "Active"


def _coordinate(geography: JSON | None) -> Coordinate | None:
    if not geography or geography.get("type") != "Point":
        return None
    coords = geography.get("coordinates")
    if not coords:
        return None
    lon, lat = coords[0], coords[1]
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def _date_confidence(
    actual_start: datetime | None, proposed_start: datetime | None
) -> DateConfidence:
    if actual_start is not None:
        return DateConfidence.VERIFIED
    if proposed_start is not None:
        return DateConfidence.ESTIMATED
    return DateConfidence.UNKNOWN


def _to_site(record: JSON) -> WorksSite:
    status = record.get("status")
    start = parse_iso8601(record.get("startDateTime"))
    end = parse_iso8601(record.get("endDateTime"))
    is_active = status == _ACTIVE_STATUS
    actual_start = start if is_active else None
    actual_end = end if is_active else None
    proposed_start = None if is_active else start
    proposed_end = None if is_active else end
    return WorksSite(
        reference=record.get("id"),
        works_type=record.get("subCategory"),
        status=status,
        location_description=record.get("location"),
        coordinate=_coordinate(record.get("geography")),
        proposed_start=proposed_start,
        proposed_end=proposed_end,
        actual_start=actual_start,
        actual_end=actual_end,
        date_confidence=_date_confidence(actual_start, proposed_start),
        traffic_management=record.get("comments"),
        source_grade=SourceGrade.OPERATOR,
        raw=record,
    )


def from_tfl(records: list[JSON]) -> list[Works]:
    """Convert real TfL Road Disruption records (from
    :meth:`streetworks.tfl.TflClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - no grouping, one `Works` per
    record. See module docstring."""
    works_list = []
    for record in records:
        site = _to_site(record)
        works_list.append(
            Works(
                reference=record.get("id"),
                coordinate=site.coordinate,
                promoter=None,  # genuinely absent - see module docstring
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=record,
            )
        )
    return works_list
