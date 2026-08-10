"""Western Australia (Main Roads WA WebEOC Roadworks) -> streetworks.common
converter. This SDK's third Australian coverage.

One :class:`~streetworks.common.Works` per feature, each with a single
:class:`~streetworks.common.WorksSite` - no grouping key is stated in this
feed linking separate roadworks into one project, the same one-to-one shape
:mod:`.from_nsw_livetraffic`/:mod:`.from_vic_disruptions` use.

**``Works.reference`` is ``GlobalID``, never ``FID``** - confirmed live,
``GlobalID`` is a genuine, unique GUID across every real record checked
(227/227 distinct); ``FID`` is this layer's real ``objectIdField``, but the
layer is a real ``isView: true`` ArcGIS view - its own OIDs are
reassignable view artefacts, not a stable identity, see
:mod:`streetworks.au.wa`'s own module docstring.

``territory="Australia"``, ``administrative_area="Main Roads Western
Australia"`` - the state road authority IS the data-owning operator, the
same rule already applied to Autobahn GmbH/TfNSW/DTP. See
:mod:`streetworks.au.wa`'s own module docstring for the real catalogue/
licence-notice text this is based on.

See :mod:`streetworks.au.wa`'s own module docstring for the full set of
real findings this mapping is built from (the coordinate guard, the locked
``DD/MM/YYYY`` date format, the ``Road=="LOCAL ROAD"`` sentinel, why
``WorkStatus`` never promotes a site past ``ESTIMATED``, the real
undocumented ``"PTA Works"`` work type) - not re-derived here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ._web_mercator import reproject_if_projected
from .models import Coordinate, DateConfidence, Notice, SourceGrade, Works, WorksSite

__all__ = ["from_au_wa_mainroads"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Australia"
_ADMINISTRATIVE_AREA = "Main Roads Western Australia"

#: Locked from real data, not a locale-guessing parser - see
#: streetworks.au.wa's module docstring for the day>12 evidence (397/681
#: real date values) that pins this as DD/MM, not MM/DD.
_DATE_FORMAT = "%d/%m/%Y %H:%M:%S"

#: The literal sentinel string this feed uses in place of a real road name
#: when a record is a local (not state) road - confirmed live, always
#: paired with a populated LocalRoadName (see streetworks.au.wa's module
#: docstring: the two are perfectly mutually exclusive across 227/227 real
#: records checked).
_LOCAL_ROAD_SENTINEL = "LOCAL ROAD"


def _coordinate(feature: JSON) -> Coordinate | None:
    """**The runtime coordinate guard** (streetworks.au.wa's "gating check
    1"): GeoJSON strips any per-feature CRS statement, so this can't trust
    that a prior ``outSR=4326`` request was actually honoured (confirmed
    live that it is, for this service, today - but never assumed). Any
    point outside plausible WGS84 degree range is treated as unreprojected
    Web Mercator metres and converted explicitly via
    :func:`~streetworks.common._web_mercator.reproject_if_projected`, never
    silently passed through. Either way, the result is honestly labelled
    ``EPSG:4326`` - this function never emits an unlabelled or mislabelled
    CRS. Shared with :mod:`streetworks.common.from_au_sa_trafficsa`, which
    needs the identical formula for the same reason.

    ``value`` is ``(lat, lon)`` - this SDK's stated convention for every
    EPSG:4326 ``Coordinate`` (see ``from_sct``/``from_wzdx``/
    ``from_autobahn``'s own docstrings), not the raw GeoJSON ``(lon, lat)``
    order the source states. Real-world discovery, not a design read-through:
    a live pull placed every WA point near Antarctica on a plotted map before
    this flip was added - GeoJSON's native order was passed straight through
    unswapped."""
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    kind = (geometry.get("type") or "").upper()
    if kind != "POINT" or not coords:
        return None
    x, y = reproject_if_projected(float(coords[0]), float(coords[1]))
    return Coordinate(value=(y, x), crs=_CRS)


def _parse_date(value: str | None) -> datetime | None:
    """``DD/MM/YYYY HH:MM:SS``, locked from real data - see module
    constant. Timezone-naive throughout - WA is AWST (UTC+8) year-round
    with no daylight saving, so a caller who wants an aware timestamp can
    safely attach ``+08:00`` themselves, but this module never states a
    timezone the source itself doesn't - see streetworks.au.wa's module
    docstring."""
    if not value:
        return None
    try:
        return datetime.strptime(value, _DATE_FORMAT)
    except ValueError:
        return None


def _road_name(properties: JSON) -> str | None:
    """``Road`` states the real literal sentinel ``"LOCAL ROAD"`` (not a
    real road name) on local-road records - ``LocalRoadName`` carries the
    real name in exactly those cases instead, confirmed live to be
    perfectly mutually exclusive with a real, non-sentinel ``Road`` value.
    See streetworks.au.wa's module docstring."""
    road = properties.get("Road")
    if road == _LOCAL_ROAD_SENTINEL:
        return properties.get("LocalRoadName") or road
    return road or None


def _location_description(properties: JSON) -> str | None:
    """``Descriptio`` is preferred whole - confirmed live to already be a
    real, well-formed human-readable location description (e.g. "Ashcroft
    Rd, 3 kms south of Morts Rd intersection, Boddington - Long term
    Temporary Closure - Mining"), richer than reconstructing from
    ``Road``/``Suburb``/``Region`` separately (it already includes
    chainage/qualifier detail those fields don't state). Falls back to
    joining ``Road``/``Suburb``/``Region`` only if ``Descriptio`` is ever
    empty (not observed live - 227/227 real records had it populated - but
    not assumed impossible)."""
    description = properties.get("Descriptio")
    if description:
        return description
    parts = [_road_name(properties), properties.get("Suburb"), properties.get("Region")]
    text = ", ".join(p for p in parts if p)
    return text or None


def _notices(properties: JSON) -> tuple[Notice, ...]:
    """``SeeMoreUrl`` is a real reference link (35/227 real records, one
    live pull) - ``SeeMoreName`` is confirmed always ``null`` in every real
    record checked, so ``Notice.text`` is honestly ``None`` here, not a
    fabricated label; the real URL lives on ``raw`` (sometimes a bare
    domain with no ``https://`` scheme, confirmed live - carried through
    exactly as stated, never silently corrected). See streetworks.au.wa's
    module docstring."""
    url = properties.get("SeeMoreUrl")
    if not url:
        return ()
    return (Notice(text=properties.get("SeeMoreName"), raw=url),)


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    start = _parse_date(properties.get("DateStarte"))
    end = _parse_date(properties.get("EstimatedC"))
    global_id = properties.get("GlobalID")
    return WorksSite(
        reference=global_id,
        works_type=properties.get("WorkType"),
        status=properties.get("WorkStatus") or None,
        location_description=_location_description(properties),
        coordinate=_coordinate(feature),
        proposed_start=start,
        proposed_end=end,
        # WorkStatus is a real field, confirmed always empty (0/227 real
        # records) - there is no live signal to ever promote past
        # ESTIMATED, see streetworks.au.wa's module docstring.
        date_confidence=DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN,
        traffic_management=properties.get("TrafficImp") or None,
        notices=_notices(properties),
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_au_wa_mainroads(features: list[JSON]) -> list[Works]:
    """Convert real Main Roads WA WebEOC roadworks features (from
    :meth:`streetworks.au.wa.WaMainRoadsClient.iter_roadworks`) into
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
