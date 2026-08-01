"""South Australia (Traffic SA / DIT Roadworks) -> streetworks.common
converter. This SDK's fifth Australian coverage, and its least verified -
see :mod:`streetworks.au.sa`'s own module docstring for the two access
gates (a token-gated query endpoint, a geo-restricted host) that mean no
real feature has ever been retrieved or checked against this mapping.

One :class:`~streetworks.common.Works` per feature, each with a single
:class:`~streetworks.common.WorksSite` - no grouping key is stated in this
feed's real field list linking separate records into one project, the same
one-to-one shape every other AU converter in this cluster uses.

**``Works.reference`` is ``ROADWORKS_AND_INCIDENTS_ID``, never
``ESRI_OID``** - the layer's own real display field, confirmed from the
live layer definition; ``ESRI_OID`` is an internal Esri row id, not a
identifier this layer itself states.

``territory="Australia"``, ``administrative_area="Department for
Infrastructure and Transport"`` - the state road authority IS the
data-owning operator, the same rule already applied to Autobahn GmbH/
TfNSW/DTP/Main Roads WA. ``SUBURB``/``SIDE_STREET`` are geography, so they
go into ``location_description``, not ``administrative_area``.

**``ROAD_NO``/``GIS_LINK_ID`` deliberately do not populate
``WorksSite.street_ref``** - see :mod:`streetworks.au.sa`'s own module
docstring for the headline open question this is: whether ``ROAD_NO`` is
South Australia's Common Road Referencing System number and genuinely
joins to a road register is unconfirmed, since no query has ever
succeeded against the real service. Populating a gazetteer join field from
an unverified candidate would violate this SDK's stated-identifiers-only
rule as surely as a name-match would - both values stay on ``.raw`` only,
available to a caller who wants to investigate once real data exists.

See :mod:`streetworks.au.sa`'s own module docstring for the full set of
open questions this mapping is built under (unconfirmed ``ACTIVE``
encoding, unconfirmed real ``REC_TYPE`` roadworks value, unconfirmed
``LATITUDE``/``LONGITUDE``-vs-``SHAPE`` agreement, unconfirmed coverage) -
not re-derived here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ._web_mercator import reproject_if_projected
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_au_sa_trafficsa"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Australia"
_ADMINISTRATIVE_AREA = "Department for Infrastructure and Transport"


def _epoch_millis_to_dt(value: int | None) -> datetime | None:
    """``START_DATE``/``END_DATE`` are real ``esriFieldTypeDate`` fields -
    epoch milliseconds UTC, the standard ArcGIS REST convention for this
    field type (confirmed from the live layer definition's own field
    types, independent of any real response body - see
    :mod:`streetworks.au.sa`'s module docstring)."""
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _coordinate(feature: JSON) -> Coordinate | None:
    """Point only (confirmed ``esriGeometryPoint`` from the live layer
    definition). Reuses the same runtime coordinate guard WA's converter
    introduced (:mod:`streetworks.common._web_mercator`) rather than the
    feed's own ``LATITUDE``/``LONGITUDE`` attributes, since whether those
    are genuinely WGS84 and agree with the reprojected ``SHAPE`` is
    unconfirmed - see module docstring."""
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    kind = (geometry.get("type") or "").upper()
    if kind != "POINT" or not coords:
        return None
    x, y = reproject_if_projected(float(coords[0]), float(coords[1]))
    return Coordinate(value=(x, y), crs=_CRS)


def _location_description(properties: JSON) -> str | None:
    """``DESCRIPTION`` is preferred whole, the same "richer than
    reconstructing from parts" design WA's ``Descriptio`` field earned -
    an unverified design choice here, though, since no real record has
    ever been seen to confirm ``DESCRIPTION`` is actually populated or
    genuinely richer than the individual fields. Falls back to joining
    ``LOCAL_ROAD``/``SIDE_STREET``/``SUBURB`` if ``DESCRIPTION`` is empty."""
    description = properties.get("DESCRIPTION")
    if description:
        return description
    parts = [properties.get("LOCAL_ROAD"), properties.get("SIDE_STREET"), properties.get("SUBURB")]
    text = ", ".join(p for p in parts if p)
    return text or None


def _traffic_management(properties: JSON) -> str | None:
    """``TRAFFIC_DIR``/``NO_LANES_CLOSED``/``SPEED_LIMIT`` - semi-structured
    (discrete concepts, stringly-typed fields) - joined into one free-text
    field the same way :mod:`streetworks.common.from_vic_disruptions` joins
    Victoria's own discrete impact fields."""
    parts = [
        properties.get("TRAFFIC_DIR"),
        properties.get("NO_LANES_CLOSED"),
        properties.get("SPEED_LIMIT"),
    ]
    text = " - ".join(p for p in parts if p)
    return text or None


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    start = _epoch_millis_to_dt(properties.get("START_DATE"))
    end = _epoch_millis_to_dt(properties.get("END_DATE"))
    return WorksSite(
        reference=properties.get("ROADWORKS_AND_INCIDENTS_ID"),
        works_type=properties.get("REC_TYPE"),
        # ACTIVE's real encoding is unconfirmed (Y/N, 1/0, something else -
        # no query has ever succeeded) - passed through raw, never
        # interpreted into a semantic label, see module docstring.
        status=properties.get("ACTIVE") or None,
        location_description=_location_description(properties),
        coordinate=_coordinate(feature),
        proposed_start=start,
        proposed_end=end,
        # ACTIVE is not used to grade confidence for the same reason it
        # isn't mapped to a semantic status - never promoted past
        # ESTIMATED without a confirmed "genuinely active" signal.
        date_confidence=DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN,
        traffic_management=_traffic_management(properties),
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_au_sa_trafficsa(features: list[JSON]) -> list[Works]:
    """Convert South Australian Traffic SA features (from
    :meth:`streetworks.au.sa.TrafficSaClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - one per feature, each with a
    single ``WorksSite``. See module docstring - this has never been
    checked against a real response, since no query has ever succeeded."""
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
