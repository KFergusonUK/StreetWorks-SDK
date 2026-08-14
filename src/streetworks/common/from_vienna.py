"""Vienna (verkehrswirksame Baustellen) -> streetworks.common converter.
See :mod:`streetworks.vienna.client`'s own module docstring for the
full investigation - in particular why the point and line layers are
both genuinely needed (disjoint, not redundant) and the real
`source_grade` correction from the investigation brief's own "operator"
assumption.

**No grouping - each feature already stands alone.** Real ``OBJECTID``
is unique across both combined layers (111/111 distinct, confirmed
live) - the same one-feature-one-``Works`` shape as
``from_lisboa``/``from_milano``, not Oslo/Helsinki's umbrella grouping.

**Coordinates stay plain ``(x, y)``, never swapped.** ``EPSG:31256``
(MGI / Austria GK East) is a genuinely projected CRS, not WGS84 - the
same discipline ``from_streetmanager``/``from_oslo``/
``from_canton_zurich`` already apply to their own projected sources.

**Geometry branches on ``Point`` vs ``LineString``** - both real shapes
in this source (unlike most single-geometry providers in this SDK).
``LineString`` populates ``Coordinate.points`` with every real vertex,
the same handling ``from_streetmanager`` already applies to its own
``LineString`` case.

**``promoter`` is ``ANTRAGSTELLER`` (applicant) - a real organisational
field, genuinely populated with third-party names** (utility companies,
the transit operator, city departments, even a private developer) -
confirming this is a genuine permit register third parties apply into,
not an authority publishing only its own works (the correction the
client module docstring documents in full). Left ``None`` where the
source itself states none (8/39 real point rows), not fabricated.

**``ANSPRECHPERSON``/``ANSPRECHPERSON_TEL`` are a genuinely mixed
field** - some real values are an individual's name, others an
organisational contact desk - preserved on ``.raw`` only, never
promoted to ``promoter`` (which ``ANTRAGSTELLER`` already covers
cleanly).

**``date_confidence`` is uniformly ``ESTIMATED``** - no explicit status
field exists in this schema, only planned ``OBJEKT_BEGINN``/
``OBJEKT_ENDE`` dates, the same call already made for Lisboa/Paris/
Milan/Stadt Zürich: a scheduled window isn't a "work is physically
happening" confirmation.

**A real, confirmed CPython quirk, not a bug in this SDK's own
``parse_iso8601``.** Real dates are shaped ``"2026-08-10Z"`` (a bare
date plus a bare ``Z``, no time component). ``parse_iso8601`` correctly
rewrites this to ``"2026-08-10+00:00"``, but
``datetime.fromisoformat("2026-08-10+00:00")`` itself silently drops
the UTC offset and returns a **naive** datetime - confirmed directly in
a plain Python shell, independent of this SDK's own code. Dates parsed
here are therefore naive, the same as every other bare-date source in
this SDK, not because the ``Z`` was ignored on purpose.

**``street_ref`` is never populated** - ``BEZEICHNUNG`` is free text, no
street/segment identifier exists anywhere in the schema, the same
discipline every other municipal-permit converter in this SDK applies.
"""

from __future__ import annotations

from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_vienna"]

JSON = dict[str, Any]

_CRS = "EPSG:31256"
_TERRITORY = "Austria"
_ADMINISTRATIVE_AREA = "Stadt Wien"


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return None
    if kind == "Point":
        return Coordinate(value=(float(coords[0]), float(coords[1])), crs=_CRS)
    if kind == "LineString":
        points = tuple((float(c[0]), float(c[1])) for c in coords)
        if not points:
            return None
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
    return None


def _location_description(properties: JSON) -> str | None:
    location = properties.get("BEZEICHNUNG")
    district = properties.get("BEZIRK")
    if location and district is not None:
        return f"{location} ({district}. Bezirk)"
    return location


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    object_id = properties.get("OBJECTID")
    return WorksSite(
        reference=str(object_id) if object_id is not None else None,
        works_type=properties.get("BEHINDERUNGSART"),
        location_description=_location_description(properties),
        coordinate=_coordinate(feature.get("geometry")),
        proposed_start=parse_iso8601(properties.get("OBJEKT_BEGINN")),
        proposed_end=parse_iso8601(properties.get("OBJEKT_ENDE")),
        date_confidence=DateConfidence.ESTIMATED,
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )


def from_vienna(features: list[JSON]) -> list[Works]:
    """Convert real Vienna verkehrswirksame Baustellen features (from
    :meth:`streetworks.vienna.ViennaClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - no grouping, one ``Works`` per
    feature. See module docstring."""
    works_list = []
    for feature in features:
        properties = feature.get("properties") or {}
        object_id = properties.get("OBJECTID")
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=str(object_id) if object_id is not None else None,
                coordinate=site.coordinate,
                promoter=properties.get("ANTRAGSTELLER"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.REGISTER,
                sites=(site,),
                raw=feature,
            )
        )
    return works_list
