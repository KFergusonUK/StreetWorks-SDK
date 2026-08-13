"""Helsinki (Kaivuilmoitus excavation notifications) -> streetworks.common
converter. See :mod:`streetworks.helsinki.client`'s own module docstring
for the full investigation - in particular why the real source resolves
the Nordic-capitals investigation brief's own unconfirmed claim, and why
the point/temporary-traffic-arrangement layers aren't used.

**Group by ``hakemustunnus`` (application reference) - an Oslo-shaped
umbrella grouping, not Copenhagen's "pick one representative geometry"
pattern.** ``id`` is genuinely unique across every real row (no tiling-
duplicate problem to dedupe first, unlike Oslo) - but ``hakemustunnus``
repeats heavily, up to 164 real rows under one reference. Checked: this
is one excavation notification genuinely spanning many real geometry
sub-areas (segmented dig zones), the same "one project, several real
sites" shape as Oslo's ``activity_id``/Jersey/NYC DOT - each row becomes
its own ``WorksSite`` under one ``Works``.

**Coordinates stay plain ``(x, y)`` = ``(easting, northing)``, never
swapped.** ``EPSG:3879`` (ETRS-GK25FIN) is a genuinely projected CRS, not
WGS84 - this SDK's ``(lat, lon)`` convention only applies to EPSG:4326.
Projected coordinates are stored as-is, the same discipline
``from_streetmanager``/``from_oslo`` already apply to their own projected
sources.

**``MultiPolygon`` geometry (the only real shape here) uses its first
polygon's first ring's first vertex as ``Coordinate.value`` only** -
``Coordinate.points``/``.parts`` are documented for line-geometry
vertices, not polygon rings, the same discipline ``from_oslo``/
``from_paris`` already apply to their own polygon case. The full raw
geometry is preserved in ``WorksSite.raw`` regardless.

**``status`` is a real, genuinely informative two-value field - unlike
Oslo's always-"granted" ``status``.** ``"Käynnissä"`` (in progress) and
``"Tuleva"`` (upcoming) are cross-checked live to exactly match a
date-based future/past split on ``tyo_alkaa`` (208 "Tuleva" rows, 208
future-dated rows). ``"Käynnissä"`` genuinely means the excavation is
active now, not merely approved - so it populates ``actual_start``/
``actual_end`` and grades ``DateConfidence.VERIFIED``, the same
``actual_start``-present rule :mod:`.from_streetmanager` already uses;
``"Tuleva"`` populates only ``proposed_start``/``proposed_end`` and grades
``ESTIMATED``.

**``promoter`` is never populated - a real, confirmed absence, not an
extraction gap.** ``hakija`` (applicant) and ``tyon_suorittaja``
(contractor) are empty on every one of 3,431 real rows checked - matches
the dataset's own published description ("licensee only to a limited
extent"). Left ``None`` rather than guessed.

**``tyon_tarkoitus`` (purpose, free text, always populated) has no home
in the canonical model** - it's a description, not a location or a
category, and forcing it into ``location_description`` or ``works_type``
would misrepresent it. Preserved in ``WorksSite.raw`` only, the same
"canonicalise the shared, preserve the specific" call Hamburg's own
independent boolean flags got in :mod:`streetworks.ogc.germany`.

**``street_ref`` is never populated** - only free-text ``osoite``
(address) exists, no street/segment identifier, the same discipline
every other municipal-permit converter in this SDK applies.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_helsinki"]

JSON = dict[str, Any]

_CRS = "EPSG:3879"
_TERRITORY = "Finland"
_ADMINISTRATIVE_AREA = "Helsingin kaupunki"

#: The one real status value confirmed live to mean "genuinely active
#: now" - see module docstring for the date-based cross-check. The only
#: other real value, "Tuleva" (upcoming), is not active yet.
_ACTIVE_STATUS = "Käynnissä"


def _coordinate(feature: JSON) -> Coordinate | None:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") != "MultiPolygon":
        return None
    polygons = geometry.get("coordinates")
    if not polygons:
        return None
    # First polygon, first ring, first vertex - ring vertices don't fit
    # Coordinate.points'/.parts' line-geometry contract, see module
    # docstring.
    ring = polygons[0][0] if polygons[0] else None
    if not ring:
        return None
    first = ring[0]
    return Coordinate(value=(float(first[0]), float(first[1])), crs=_CRS)


def _date_confidence(
    actual_start: datetime | None, proposed_start: datetime | None
) -> DateConfidence:
    if actual_start is not None:
        return DateConfidence.VERIFIED
    if proposed_start is not None:
        return DateConfidence.ESTIMATED
    return DateConfidence.UNKNOWN


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    status = properties.get("status")
    start = parse_iso8601(properties.get("tyo_alkaa"))
    end = parse_iso8601(properties.get("tyo_paattyy"))
    actual_start = start if status == _ACTIVE_STATUS else None
    actual_end = end if status == _ACTIVE_STATUS else None
    proposed_start = None if status == _ACTIVE_STATUS else start
    proposed_end = None if status == _ACTIVE_STATUS else end
    row_id = properties.get("id")
    return WorksSite(
        reference=str(row_id) if row_id is not None else None,
        works_type=properties.get("hakemus"),
        status=status,
        location_description=properties.get("osoite"),
        coordinate=_coordinate(feature),
        proposed_start=proposed_start,
        proposed_end=proposed_end,
        actual_start=actual_start,
        actual_end=actual_end,
        date_confidence=_date_confidence(actual_start, proposed_start),
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )


def from_helsinki(features: list[JSON]) -> list[Works]:
    """Convert real Helsinki Kaivuilmoitus features (from
    :meth:`streetworks.helsinki.HelsinkiClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - grouped by ``hakemustunnus``
    into one ``Works`` with one ``WorksSite`` per real geometry row. See
    module docstring."""
    by_reference: dict[Any, list[JSON]] = defaultdict(list)
    unresolved: list[JSON] = []
    for feature in features:
        reference = (feature.get("properties") or {}).get("hakemustunnus")
        if reference is not None:
            by_reference[reference].append(feature)
        else:
            unresolved.append(feature)

    works_list: list[Works] = []
    for reference, group in by_reference.items():
        sites = [_to_site(f) for f in group]
        works_list.append(
            Works(
                reference=reference,
                coordinate=sites[0].coordinate if sites else None,
                promoter=None,  # genuinely absent - see module docstring
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.REGISTER,
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
                promoter=None,
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.REGISTER,
                sites=(site,),
                raw=[feature],
            )
        )
    return works_list
