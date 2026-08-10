"""Copenhagen (Gravetilladelser) -> streetworks.common converter. See
:mod:`streetworks.copenhagen.client`'s own module docstring for the full
investigation - in particular why the real source and dataset name aren't
what the investigation brief guessed, and the real geometry/dedup finding
this converter is built around.

**Dedupe by ``sagsnr``, not a Jersey/NYC-style umbrella grouping.** A
repeated ``sagsnr`` in the raw feed means the *same* real permit recorded
once per geometry shape it has (confirmed live: all 832 real multi-row
permits have identical non-geometry properties across their rows) - not
several distinct worksites under one project. So this converter groups by
``sagsnr`` and emits exactly one :class:`~streetworks.common.Works` with
exactly one :class:`~streetworks.common.WorksSite` per permit, never more.

**Geometry: LineString preferred over Point; Polygon rows are never
used.** Confirmed live that every one of the 1241 real permits has a
``LineString`` or ``Point`` alternative - zero are Polygon-only - so no
polygon-ring handling is needed at all (unlike Paris's own polygon case,
which had no point alternative and had to fall back to a separately
supplied representative-point field; see :mod:`.from_paris`). If a future
permit genuinely only has Polygon geometry, ``coordinate`` is ``None``
rather than a guessed centroid - never fabricated.

**Coordinates are ``(lat, lon)``** - this SDK's stated convention for
every EPSG:4326 ``Coordinate`` (see ``from_sct``/``from_wzdx``/
``from_autobahn``'s own docstrings), swapped from the raw WFS GeoJSON
``[lon, lat]`` order.

**Dates are real but non-ISO** - ``projekt_start``/``projekt_slut`` are
Danish ``DD-MM-YY`` strings (e.g. ``"04-07-26"``), parsed here via a
bespoke ``strptime``, the same per-provider-bespoke-format discipline
:mod:`.from_jersey` already applies to its own ``YYYYMMDD HHMM`` dates.
No timezone is stated anywhere in the schema, so parsed values are
timezone-naive, the same discipline :mod:`.from_nycdot` applies.
``date_confidence`` is ``ESTIMATED`` when a start date parses, never
``VERIFIED`` - a granted permit's stated window is not an independently
confirmed "work is happening" signal, the same discipline NYC DOT/
Chicago/Paris apply.

**``entreprenoer`` (the contractor) has no dedicated model field** -
folded into ``traffic_management`` instead of dropped, the same "real
field, no home, append don't drop" discipline Tasmania's own
``SITE_CONTACT``/``SITE_CONTACT_PHONE`` get.

**``street_ref`` is never populated** - only free-text ``lokation``
exists, no street/segment identifier, the same discipline every other
municipal-permit converter in this SDK applies.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_copenhagen"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Denmark"
_ADMINISTRATIVE_AREA = "Københavns Kommune"

#: Lower wins - LineString (real line geometry) over Point; Polygon is
#: deliberately absent, see module docstring.
_GEOMETRY_PRIORITY = {"LineString": 0, "Point": 1}


def _parse_dk_date(value: str | None) -> datetime | None:
    """Real ``projekt_start``/``projekt_slut`` values are Danish
    ``DD-MM-YY`` strings (e.g. ``"04-07-26"``), not ISO-8601 - confirmed
    live, see module docstring."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d-%m-%y")
    except ValueError:
        return None


def _coordinate(feature: JSON) -> Coordinate | None:
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates")
    kind = geometry.get("type")
    if not coords:
        return None
    if kind == "Point":
        return Coordinate(value=(float(coords[1]), float(coords[0])), crs=_CRS)
    if kind == "LineString":
        points = tuple((float(v[1]), float(v[0])) for v in coords)
        if not points:
            return None
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
    return None


def _best_feature(group: list[JSON]) -> JSON:
    """The group member with the best available geometry - LineString
    over Point, Polygon rows never chosen (see module docstring). Falls
    back to the first row if none of the group has a usable geometry
    (not observed live, but not assumed impossible)."""
    ranked = [f for f in group if (f.get("geometry") or {}).get("type") in _GEOMETRY_PRIORITY]
    if not ranked:
        return group[0]
    return min(ranked, key=lambda f: _GEOMETRY_PRIORITY[f["geometry"]["type"]])


def _location_description(properties: JSON) -> str | None:
    location = properties.get("lokation")
    gravetype = properties.get("gravetype")
    if location and gravetype:
        return f"{location} ({gravetype})"
    return location or gravetype


def _operating_window(properties: JSON) -> str | None:
    start = properties.get("tidspunkt_fra")
    end = properties.get("tidspunkt_til")
    if start and end:
        return f"{start}–{end}"
    return start or end


def _traffic_management(properties: JSON) -> str | None:
    contractor = properties.get("entreprenoer")
    return f"Contractor: {contractor}" if contractor else None


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    sagsnr = properties.get("sagsnr")
    start = _parse_dk_date(properties.get("projekt_start"))
    end = _parse_dk_date(properties.get("projekt_slut"))
    return WorksSite(
        reference=str(sagsnr) if sagsnr is not None else None,
        works_type=properties.get("kategori"),
        location_description=_location_description(properties),
        coordinate=_coordinate(feature),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED if start else DateConfidence.UNKNOWN,
        operating_window=_operating_window(properties),
        traffic_management=_traffic_management(properties),
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )


def from_copenhagen(features: list[JSON]) -> list[Works]:
    """Convert real Copenhagen Gravetilladelser features (from
    :meth:`streetworks.copenhagen.CopenhagenClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - deduped by ``sagsnr`` into one
    ``Works`` with exactly one ``WorksSite`` per real permit, picking the
    best available geometry per permit. See module docstring."""
    by_case: dict[Any, list[JSON]] = defaultdict(list)
    unresolved: list[JSON] = []
    for feature in features:
        sagsnr = (feature.get("properties") or {}).get("sagsnr")
        if sagsnr is not None:
            by_case[sagsnr].append(feature)
        else:
            unresolved.append(feature)

    works_list: list[Works] = []
    for group in by_case.values():
        feature = _best_feature(group)
        properties = feature.get("properties") or {}
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=site.reference,
                coordinate=site.coordinate,
                promoter=properties.get("bygherre"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.REGISTER,
                sites=(site,),
                raw=group,
            )
        )
    for feature in unresolved:
        properties = feature.get("properties") or {}
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=None,
                coordinate=site.coordinate,
                promoter=properties.get("bygherre"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.REGISTER,
                sites=(site,),
                raw=[feature],
            )
        )
    return works_list
