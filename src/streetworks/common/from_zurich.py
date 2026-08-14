"""Stadt Zürich (Aktuelle Tiefbauprojekte im öffentlichen Grund) ->
streetworks.common converter. See :mod:`streetworks.zurich.client`'s own
module docstring for the full investigation - in particular the
empty-DefaultSRS-but-empirically-WGS84 finding and why this is
deliberately not deduped against Kanton Zürich.

**No grouping - each feature already stands alone.** ``baunr`` (project
number) is 140/140 distinct across the full live pull - the same
one-feature-one-``Works`` shape as ``from_lisboa``/``from_milano``, not
Oslo/Helsinki's umbrella grouping.

**Geometry: real ``MultiPolygon``, genuine WGS84 - flipped to this
SDK's ``(lat, lon)`` convention.** Confirmed live via the client
module's own empirical bounding-box cross-check (the capabilities
document's own ``DefaultSRS`` tag is blank). First polygon, first
ring, first vertex used as ``Coordinate.value`` only - the same
"ring vertices aren't ``.points``/``.parts``" discipline
``from_helsinki``/``from_oslo`` already apply.

**``promoter`` is never populated.** ``projektleiter``/
``projektleiter_email``/``tel`` name an individual project leader, not
an organisation - promoting a person's name into ``promoter`` would
misrepresent it as a company, the same call already made for the
canton's own ``ansprechperson``. ``administrative_area`` is hardcoded
to ``"Stadt Zürich"`` instead - endpoint provenance, not a record
field.

**``works_type`` is the real, constant ``"Grössere Baustelle"``** -
every one of 140 real rows carries this same category value, since this
dataset is already curated to significant/major projects, not every
minor closure. Used verbatim for traceability, the same "constant but
still useful" call made for Helsinki's ``hakemus``.

**``date_confidence`` is uniformly ``ESTIMATED``** - no status field
exists in this schema, only planned ``baubeginn``/``bauende`` dates,
the same call already made for Lisboa/Paris/Milan: a scheduled window
isn't a "work is physically happening" confirmation.

**``street_ref`` is never populated** - no street/segment identifier
exists in this schema, only free-text ``baubereich``.
"""

from __future__ import annotations

from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_zurich"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Switzerland"
_ADMINISTRATIVE_AREA = "Stadt Zürich"


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry or geometry.get("type") != "MultiPolygon":
        return None
    polygons = geometry.get("coordinates")
    if not polygons:
        return None
    ring = polygons[0][0] if polygons[0] else None
    if not ring:
        return None
    lon, lat = ring[0][0], ring[0][1]
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def _location_description(properties: JSON) -> str | None:
    return properties.get("baubereich") or properties.get("titel") or properties.get("name")


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    return WorksSite(
        reference=properties.get("baunr"),
        works_type=properties.get("kategorie"),
        location_description=_location_description(properties),
        coordinate=_coordinate(feature.get("geometry")),
        proposed_start=parse_iso8601(properties.get("baubeginn")),
        proposed_end=parse_iso8601(properties.get("bauende")),
        date_confidence=DateConfidence.ESTIMATED,
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_zurich(features: list[JSON]) -> list[Works]:
    """Convert real Stadt Zürich Aktuelle Tiefbauprojekte features (from
    :meth:`streetworks.zurich.ZurichClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - no grouping, one ``Works`` per
    feature. See module docstring."""
    works_list = []
    for feature in features:
        properties = feature.get("properties") or {}
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=properties.get("baunr"),
                coordinate=site.coordinate,
                promoter=None,  # genuinely absent - see module docstring
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.OPERATOR,
                sites=(site,),
                raw=feature,
            )
        )
    return works_list
