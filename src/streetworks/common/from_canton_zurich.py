"""Kanton Zürich (Baustellen Kantonsstrassen) -> streetworks.common
converter. See :mod:`streetworks.canton_zurich.client`'s own module
docstring for the full investigation - in particular the real no-
unique-identifier finding and why the two real WFS layers aren't
combined.

**No grouping - each feature already stands alone**, the same shape as
Lisboa/Paris/Milan, not Oslo/Helsinki's umbrella grouping.

**``reference`` is genuinely ``None`` - not an extraction gap.** No
field in this schema states a unique identifier; a composite of
``strassenbez``+``kmvon``+``kmbis``+``datum_baubeginn`` is 65/66 unique
in real data, but the one collision is two genuinely distinct real
closures (opposite directions of the same road, different times/
descriptions) sharing every one of those four values - proof a
fabricated composite key would misrepresent two real works as one,
not merely imperfect deduplication. Left ``None`` rather than guessed.

**Coordinates stay plain ``(x, y)`` = ``(easting, northing)``, never
swapped.** ``EPSG:2056`` (Swiss LV95) is a genuinely projected CRS, not
WGS84 - the same discipline ``from_streetmanager``/``from_oslo`` already
apply to their own projected sources.

**``Polygon`` geometry uses its first ring's first vertex as
``Coordinate.value`` only** - ``Coordinate.points``/``.parts`` are
documented for line-geometry vertices, not polygon rings, the same
discipline ``from_oslo``/``from_milano`` already apply to their own
polygon case. The full raw geometry is preserved in ``WorksSite.raw``
regardless.

**``promoter`` is never populated.** ``ansprechperson``/
``telefonnummer`` name an individual staff member, not an organisation
- promoting a person's name into ``promoter`` would misrepresent it as
a company, the same call the client module docstring already explains.
``administrative_area`` is hardcoded to ``"Kanton Zürich"`` instead -
endpoint provenance, not a record field, the same convention Germany's
``StateFieldMap`` documents for exactly this situation.

**``status_baustelle`` is a real, genuinely informative two-value
field - unlike many other municipal sources' always-approved status.**
``"aktiv (Bauzeit)"`` genuinely means the work is active now, so it
populates ``actual_start``/``actual_end`` and grades
``DateConfidence.VERIFIED`` (the same ``actual_start``-present rule
``from_streetmanager``/``from_helsinki`` already use);
``"zukünftig (Bauzeit in Zukunft)"`` populates only
``proposed_start``/``proposed_end`` and grades ``ESTIMATED``.

**``works_type`` is left unset** - no categorical work-type field
exists in this schema (only free-text ``beschreibung``/
``verkehrsfuehrung``, preserved on ``.raw`` only, not forced into a
field that doesn't fit them - the same "canonicalise the shared,
preserve the specific" call Hamburg's own independent boolean flags
got). ``traffic_management`` does map cleanly onto ``verkehrsfuehrung``,
a real, genuinely traffic-management-specific field.

**``street_ref`` is never populated** - ``strassenbez`` is a road
designation number (e.g. ``"831"``), not a stated join-able identifier
this SDK has confirmed against any register - the same "name/number is
not a join" discipline every other converter here applies.
"""

from __future__ import annotations

from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_canton_zurich"]

JSON = dict[str, Any]

_CRS = "EPSG:2056"
_TERRITORY = "Switzerland"
_ADMINISTRATIVE_AREA = "Kanton Zürich"

#: The one real status value confirmed live to mean "genuinely active
#: now" - see module docstring. The only other real value, "zukünftig
#: (Bauzeit in Zukunft)" (upcoming), is not active yet.
_ACTIVE_STATUS = "aktiv (Bauzeit)"


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry or geometry.get("type") != "Polygon":
        return None
    coords = geometry.get("coordinates")
    if not coords:
        return None
    ring = coords[0] if coords else None
    if not ring:
        return None
    first = ring[0]
    return Coordinate(value=(float(first[0]), float(first[1])), crs=_CRS)


def _location_description(properties: JSON) -> str | None:
    street = properties.get("strassenname")
    municipality = properties.get("gemeindename")
    if street and municipality:
        return f"{street} ({municipality})"
    return street or municipality


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    status = properties.get("status_baustelle")
    start = parse_iso8601(properties.get("datum_baubeginn"))
    end = parse_iso8601(properties.get("datum_bauende"))
    is_active = status == _ACTIVE_STATUS
    actual_start = start if is_active else None
    actual_end = end if is_active else None
    proposed_start = None if is_active else start
    proposed_end = None if is_active else end
    date_confidence = DateConfidence.VERIFIED if actual_start else DateConfidence.ESTIMATED
    return WorksSite(
        status=status,
        location_description=_location_description(properties),
        coordinate=_coordinate(feature.get("geometry")),
        proposed_start=proposed_start,
        proposed_end=proposed_end,
        actual_start=actual_start,
        actual_end=actual_end,
        date_confidence=date_confidence,
        traffic_management=properties.get("verkehrsfuehrung"),
        source_grade=SourceGrade.OPERATOR,
        raw=feature,
    )


def from_canton_zurich(features: list[JSON]) -> list[Works]:
    """Convert real Kanton Zürich Baustellen Kantonsstrassen features
    (from :meth:`streetworks.canton_zurich.CantonZurichClient.iter_roadworks`)
    into :class:`~streetworks.common.Works` - no grouping, one ``Works``
    per feature. See module docstring."""
    works_list = []
    for feature in features:
        site = _to_site(feature)
        works_list.append(
            Works(
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
