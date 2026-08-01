"""ACT (Temporary Traffic Management - Planned Road Closures) ->
streetworks.common converter. This SDK's sixth Australian coverage, and
its first with genuine municipal/local-street reach.

One :class:`~streetworks.common.Works` per feature, each with a single
:class:`~streetworks.common.WorksSite` - no grouping key is stated in this
feed linking separate closures into one project, the same one-to-one shape
every other AU converter in this cluster uses.

**``Works.reference`` is ``globalid``, a genuine GUID** - confirmed live,
populated on every one of 98 real records checked; ``objectid`` (the
layer's real ``objectIdField``) is not used, the same "don't key on the
row id when a real GUID exists" caution as every other AU ArcGIS provider.

``territory="Australia"``, ``administrative_area="Roads ACT"`` - the
specific operating unit that owns TTM approvals (the real attribution
string is the broader "Transport Canberra and City Services" directorate -
see :mod:`streetworks.au.act`'s own module docstring for both real strings
and why ``Roads ACT`` is used here, matching the operator-as-authority rule
already applied to Autobahn GmbH/TfNSW/Main Roads WA). ``suburb1`` is
geography, so it goes into ``location_description``, not
``administrative_area``.

See :mod:`streetworks.au.act`'s own module docstring for the full set of
real findings this mapping is built from (the ArcGIS-not-Socrata
correction, the confirmed-live ``roadWorks`` filter value, the real
embedded ``<br>`` HTML in ``roadsClosed``, why the always-``"yes"``
approval flags never promote ``DateConfidence``) - not re-derived here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_au_act_ttm"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Australia"
_ADMINISTRATIVE_AREA = "Roads ACT"


def _epoch_millis_to_dt(value: int | None) -> datetime | None:
    """``startTimeClosure``/``endTimeClosure`` are real
    ``esriFieldTypeDate`` fields - epoch milliseconds UTC, the standard
    ArcGIS REST convention (see :mod:`streetworks.au.act`'s module
    docstring)."""
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _coordinate(feature: JSON) -> Coordinate | None:
    """Point only, native ``EPSG:4326`` - no reprojection guard needed at
    all (confirmed live from the layer's own spatial reference and real
    query results), unlike WA/SA's Web Mercator services. See module
    docstring."""
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    kind = (geometry.get("type") or "").upper()
    if kind != "POINT" or not coords:
        return None
    return Coordinate(value=(float(coords[0]), float(coords[1])), crs=_CRS)


def _location_description(properties: JSON) -> str | None:
    """``roadsClosed`` (real, confirmed to genuinely embed literal HTML
    ``<br>`` line breaks - carried through exactly as stated, never
    silently stripped, see module docstring) plus ``suburb1``."""
    parts = [properties.get("roadsClosed"), properties.get("suburb1")]
    text = ", ".join(p for p in parts if p)
    return text or None


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    start = _epoch_millis_to_dt(properties.get("startTimeClosure"))
    end = _epoch_millis_to_dt(properties.get("endTimeClosure"))
    describe_activity = properties.get("describeActivity")
    works_type = properties.get("type")
    # describeActivity is only populated (and only meaningful) for the
    # real "other" type - confirmed live to correlate exactly with
    # type=='other' across every real record checked, see module
    # docstring.
    if describe_activity and works_type == "other":
        works_type = describe_activity
    return WorksSite(
        reference=properties.get("globalid"),
        works_type=works_type,
        location_description=_location_description(properties),
        coordinate=_coordinate(feature),
        proposed_start=start,
        proposed_end=end,
        # tccsCommsClosure/roadsDelegateClosure are real fields, confirmed
        # always "yes" in the live feed (only approved closures are
        # published at all) - they don't discriminate anything, so never
        # promote past ESTIMATED, see module docstring.
        date_confidence=DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN,
        traffic_management=properties.get("reasonRoadClosure") or None,
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_au_act_ttm(features: list[JSON]) -> list[Works]:
    """Convert real ACT TTM planned-road-closure features (from
    :meth:`streetworks.au.act.ActTtmClient.iter_roadworks`) into
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
