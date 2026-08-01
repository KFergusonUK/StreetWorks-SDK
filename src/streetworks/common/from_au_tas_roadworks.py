"""Tasmania (Department of State Growth, Roadworks - State Roads) ->
streetworks.common converter. This SDK's seventh Australian coverage, and
its first with real line geometry (every other AU provider so far is
point-only).

One :class:`~streetworks.common.Works` per feature, each with a single
:class:`~streetworks.common.WorksSite` - no grouping key is stated in this
feed linking separate roadworks into one project, the same one-to-one shape
every other AU converter in this cluster uses.

**``Works.reference`` is ``ID`` - the only identifier this layer states.**
Unlike WA/SA/ACT, this layer has no separate GlobalID field to prefer over
its own ``objectIdField`` - ``ID`` is genuinely the best available
identifier, not a stand-in this module pretends is more stable than it
is; see :mod:`streetworks.au.tas`'s own module docstring.

``territory="Australia"``, ``administrative_area="Department of State
Growth"`` - the state road authority IS the data-owning operator, the
same rule already applied to Autobahn GmbH/TfNSW/Main Roads WA/Roads ACT.
``ROAD_NAME``/``LOCATION_DESC`` describe the worksite itself, not a
separate administrative geography, so both go into
``location_description``.

**No coordinate reprojection fallback here, unlike WA/SA** - see
:mod:`streetworks.au.tas`'s own module docstring for why: this layer's
native CRS (GDA94/MGA zone 55) has no cheap closed-form WGS84 inverse the
way WA/SA's Web Mercator does, so this module trusts the confirmed-live
``outSR=4326`` request rather than risk silently applying the wrong
formula. ``scripts/smoke_test.py`` carries the plausibility guard instead.

See :mod:`streetworks.au.tas`'s own module docstring for the full set of
real findings this mapping is built from (the real 10-record total, why
``SITE_CONTACT``/``SITE_CONTACT_PHONE`` fold into ``traffic_management``,
the genuinely unconfirmed licence) - not re-derived here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_au_tas_roadworks"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Australia"
_ADMINISTRATIVE_AREA = "Department of State Growth"


def _epoch_millis_to_dt(value: int | None) -> datetime | None:
    """``START_TIME``/``END_TIME`` are real ``esriFieldTypeDate`` fields -
    epoch milliseconds UTC, the standard ArcGIS REST convention (see
    :mod:`streetworks.au.tas`'s module docstring)."""
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _coordinate(feature: JSON) -> Coordinate | None:
    """Real line geometry, kept whole via ``Coordinate.points`` - confirmed
    live these are genuine short worksite segments, not a Victoria/QLD-style
    corridor extent, see module docstring. No reprojection fallback (see
    module docstring for why WA/SA's Web Mercator guard doesn't apply
    here) - the confirmed-live ``outSR=4326`` request is trusted as-is."""
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    kind = (geometry.get("type") or "").upper()
    if kind != "LINESTRING" or not coords:
        return None
    points = tuple((float(x), float(y)) for x, y in coords)
    return Coordinate(value=points[0], crs=_CRS, points=points)


def _location_description(properties: JSON) -> str | None:
    parts = [properties.get("ROAD_NAME"), properties.get("LOCATION_DESC")]
    text = ", ".join(p for p in parts if p)
    return text or None


def _traffic_management(properties: JSON) -> str | None:
    """``TRAFFIC_MANAGEMENT`` is the real impact prose; ``SITE_CONTACT``/
    ``SITE_CONTACT_PHONE`` (a genuinely new field pair in this AU cluster -
    a named contractor plus phone) have no canonical model field of their
    own, so they're appended here rather than dropped - see module
    docstring."""
    parts = [properties.get("TRAFFIC_MANAGEMENT")]
    contact = properties.get("SITE_CONTACT")
    phone = properties.get("SITE_CONTACT_PHONE")
    if contact or phone:
        parts.append(f"Site contact: {contact or ''} {phone or ''}".strip())
    text = " - ".join(p for p in parts if p)
    return text or None


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    start = _epoch_millis_to_dt(properties.get("START_TIME"))
    end = _epoch_millis_to_dt(properties.get("END_TIME"))
    return WorksSite(
        reference=str(properties["ID"]) if properties.get("ID") is not None else None,
        works_type=properties.get("EVENT_TYPE"),
        location_description=_location_description(properties),
        coordinate=_coordinate(feature),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN,
        traffic_management=_traffic_management(properties),
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_au_tas_roadworks(features: list[JSON]) -> list[Works]:
    """Convert real Tasmanian state-road roadworks features (from
    :meth:`streetworks.au.tas.TasRoadworksClient.iter_roadworks`) into
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
