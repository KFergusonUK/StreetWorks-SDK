"""Québec (province, MTQ) -> streetworks.common converter. This SDK's
first Canadian provincial roadworks coverage (distinct from Quebec
**City**'s own separate WZDx feed - see
:mod:`streetworks.quebec.client`'s own module docstring).

Groups real features by ``identifiantChantier`` into one
:class:`~streetworks.common.Works` per real worksite/project - confirmed
live to be the same real shape as Jersey's own ``PROJID``/``JOBID``
grouping: 391 distinct chantiers across 526 real records, 71 with 2-5
real entraves (obstructions) each. One :class:`~streetworks.common.WorksSite`
per ``identifiant``.

``works_type`` is ``identificationDesTravaux`` (the real work title, e.g.
``"Construction pont temporaire"``) and ``status`` is ``entraveType`` (a
real, clean 6-value severity/schedule enum, e.g. ``"Mineure (semaine)"``)
- the same role split :mod:`.from_lyon` already gives its own
``nomchantier``/``typeperturbation`` pair on a comparable French-language
feed.

**``date_confidence`` is uniformly ``ESTIMATED``** - no separate
verified/status flag exists distinguishing scheduled from physically
confirmed, the same reasoning :mod:`.from_drivebc` already documents for
its own comparable live "currently causing disruption" feed.

Dates are real ``"YYYY/MM/DD HH:MM:SS"`` strings (not ISO 8601) -
represented in Québec's own real IANA zone, ``America/Montreal``.

``descriptionAnglais`` - a genuinely separate, official English
description MTQ publishes alongside ``descriptionFrancais`` - stays
``.raw``-only; ``location_description`` uses the French ``localisation``
field as the canonical text, matching every other field choice here.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_quebec"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Canada"
_ADMINISTRATIVE_AREA = "Ministère des Transports et de la Mobilité durable (MTQ)"
_MONTREAL = ZoneInfo("America/Montreal")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y/%m/%d %H:%M:%S").replace(tzinfo=_MONTREAL)
    except ValueError:
        return None


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    coords = geometry.get("coordinates")
    kind = geometry.get("type")
    if kind == "LineString" and coords:
        points = tuple((float(lat), float(lon)) for lon, lat in coords)
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
    if kind == "Point" and coords:
        lon, lat = coords
        return Coordinate(value=(float(lat), float(lon)), crs=_CRS)
    return None


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    return WorksSite(
        reference=properties.get("identifiant"),
        works_type=properties.get("identificationDesTravaux") or None,
        status=properties.get("entraveType") or None,
        location_description=properties.get("localisation") or None,
        coordinate=_coordinate(feature.get("geometry")),
        proposed_start=_parse_date(properties.get("debut")),
        proposed_end=_parse_date(properties.get("fin")),
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=properties.get("entrave") or None,
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_quebec(features: list[JSON]) -> list[Works]:
    """Convert real MTQ ``chantiers_mtmdet`` GeoJSON features (from
    :meth:`streetworks.quebec.QuebecClient.iter_roadworks`) into
    :class:`~streetworks.common.Works`, grouped by ``identifiantChantier``
    - see module docstring. A feature with no ``identifiantChantier`` at
    all (not observed live, but the field isn't a contract) gets its own
    free-standing single-site ``Works`` rather than being grouped or
    dropped."""
    by_chantier: dict[str, list[JSON]] = defaultdict(list)
    unresolved: list[JSON] = []
    for feature in features:
        chantier = (feature.get("properties") or {}).get("identifiantChantier")
        if chantier:
            by_chantier[chantier].append(feature)
        else:
            unresolved.append(feature)

    works_list: list[Works] = []
    for chantier, group in by_chantier.items():
        sites = [_to_site(f) for f in group]
        works_list.append(
            Works(
                reference=chantier,
                coordinate=sites[0].coordinate if sites else None,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=tuple(sites),
                raw=group,
            )
        )
    for feature in unresolved:
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=None,
                coordinate=site.coordinate,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=[feature],
            )
        )
    return works_list
