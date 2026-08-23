"""Brussels Road Events (Brussels Mobility) -> streetworks.common
converter. See :mod:`streetworks.brussels.client`'s own module
docstring for the full investigation.

**No grouping** - each real feature already stands alone; the GeoJSON
feature ``id`` is already a stable per-record reference.

**French is read as the canonical bilingual text field** - every real
text property is duplicated ``_fr``/``_nl``; both are kept on ``.raw``,
only ``_fr`` is promoted into the common model, the same choice already
made for this SDK's other bilingual sources.

**A real source-encoding quirk, unescaped here, not reproduced** - some
real text embeds literal HTML entities (e.g. ``"d&apos;arrêt"``), which
:func:`html.unescape` corrects before use - see the client's own module
docstring. Every real ``type_fr`` value also carries a trailing space
(``"Travaux "``), stripped here alongside the unescaping.

**``location_description`` drops a real but uninformative
``direction_fr`` value** - ``"Indéfini"`` ("undefined") appears live when
no real direction is stated; combining it would read as
``"<location> → Indéfini"``, worse than the location alone, so it's
excluded rather than kept verbatim.

**Dates are real ``"YYYY-MM-DD HH:MM"`` strings, no timezone stated** -
parsed naive, the same "don't silently attach an inferred timezone"
discipline :mod:`.from_necompass`/:mod:`.from_drivebc` already document.
``start_time``/``end_time`` were populated on every real record checked
(0/287 missing either) - unlike several other feeds in this SDK, there
is no real observed "no end date" gap here.

**``date_confidence`` is uniformly ``ESTIMATED``** - a live, self-
reported traffic-centre feed with no separate physically-confirmed/
scheduled distinction stated anywhere in the schema, the same reasoning
:mod:`.from_necompass`/:mod:`.from_quebec` already document for their
own comparable feeds.

**``traffic_management`` comes from ``consequences_fr``** - real,
specific text on the actual measures in place (e.g. "Bandes rétrécies",
"Trottoir obstrué"), often a real pipe-joined multi-value string when
several apply at once - kept as the source states it, not split.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_brussels"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Belgium"
_ADMINISTRATIVE_AREA = "Brussels-Capital Region"


def _text(properties: JSON, field: str) -> str | None:
    value = properties.get(field)
    return html.unescape(value).strip() if value else None


def _coordinate(feature: JSON) -> Coordinate | None:
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates")
    if geometry.get("type") != "Point" or not coordinates:
        return None
    lon, lat = coordinates[0], coordinates[1]
    return Coordinate(value=(lat, lon), crs=_CRS)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return parse_iso8601(value.replace(" ", "T"))


def _location_description(properties: JSON) -> str | None:
    location = _text(properties, "location_fr")
    direction = _text(properties, "direction_fr")
    if location and direction and direction != "Indéfini":
        return f"{location} → {direction}"
    return location


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    return WorksSite(
        reference=feature.get("id"),
        works_type=_text(properties, "type_fr"),
        location_description=_location_description(properties),
        coordinate=_coordinate(feature),
        proposed_start=_parse_date(properties.get("start_time")),
        proposed_end=_parse_date(properties.get("end_time")),
        date_confidence=DateConfidence.ESTIMATED,
        traffic_management=_text(properties, "consequences_fr"),
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_brussels(features: list[JSON]) -> list[Works]:
    """Convert real Brussels Road Events GeoJSON features (from
    :meth:`streetworks.brussels.BrusselsClient.iter_roadworks`) into
    :class:`~streetworks.common.Works`. No grouping - one ``Works`` per
    feature, see module docstring."""
    works_list = []
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
