"""Milan (Avvisi di manomissione excavation notices) -> streetworks.common
converter. See :mod:`streetworks.milano.client`'s own module docstring
for the full investigation - in particular why the real dataset name
("manomissione", not "cantieri") resolves the populous-cities pivot's
own open question about Milan.

**No grouping - each feature already stands alone.** Every real row
carries a unique ``Numero di protocollo ingresso`` (139 rows, 139
distinct values, confirmed live) - the same one-feature-one-``Works``
shape as :mod:`.from_lisboa`, not Oslo/Helsinki's umbrella grouping.

**Geometry: real ``Point``, native WGS84 - flipped to this SDK's
``(lat, lon)`` convention**, the same handling :mod:`.from_lisboa`/
:mod:`.from_paris` already apply to their own genuine EPSG:4326 sources
(unlike :mod:`.from_streetmanager`'s British National Grid flip, or
Oslo/Helsinki's unswapped projected coordinates - this source is
genuinely WGS84, confirmed live, see the client module docstring).

**``works_type`` preserves ``Tipo di utility/attività`` verbatim,
including its own real capitalisation inconsistency**
(``"Acqua Potabile"`` vs ``"Acqua potabile"`` both appear live) - not
normalised, the same "preserve the source's own real values" discipline
:mod:`.from_oslo` applies to ``activity_type``.

**``promoter`` is the real concession-holder company**
(``Impresa proprietaria area concessione/autorizzazione``) - genuinely
populated (``MM Spa``, ``Unareti S.p.A``, ``A2A Calore & Servizi``, ...),
not a placeholder.

**``street_ref`` is never populated** - ``Nome via`` is free text, no
street/segment identifier exists anywhere in the schema, the same
discipline every other municipal-permit converter in this SDK applies.

**``date_confidence`` is uniformly ``ESTIMATED``** - no explicit status
field exists in this schema, only planned start/end dates
(``Data prevista inizio/fine lavori``), the same call already made for
Lisboa/Paris/Madrid/DriveBC: a scheduled window isn't a "work is
physically happening" confirmation. This includes the one real 2021
outlier in the live data (an already-past-dated row, kept as-is, not
silently dropped or reinterpreted) - see client module docstring.
"""

from __future__ import annotations

from typing import Any

from .._dt import parse_iso8601
from .models import Coordinate, DateConfidence, SourceGrade, Works, WorksSite

__all__ = ["from_milano"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"
_TERRITORY = "Italy"
_ADMINISTRATIVE_AREA = "Comune di Milano"


def _coordinate(geometry: JSON | None) -> Coordinate | None:
    if not geometry or geometry.get("type") != "Point":
        return None
    coords = geometry.get("coordinates")
    if not coords:
        return None
    lon, lat = coords[0], coords[1]
    return Coordinate(value=(float(lat), float(lon)), crs=_CRS)


def _location_description(properties: JSON) -> str | None:
    via = properties.get("Nome via")
    start = properties.get("Civico o descrizione di Punto Inizio intervento")
    end = properties.get("Civico o descrizione di Punto Fine Intervento")
    if not via:
        return None
    civico: str | None
    if start and end and start != end:
        civico = f"{start}-{end}"
    else:
        civico = start or end
    return f"{via}, {civico}" if civico else via


def _to_site(feature: JSON) -> WorksSite:
    properties = feature.get("properties") or {}
    start = parse_iso8601(properties.get("Data prevista inizio lavori"))
    end = parse_iso8601(properties.get("Data prevista fine lavori"))
    return WorksSite(
        reference=properties.get("Numero di protocollo ingresso"),
        works_type=properties.get("Tipo di utility/attività"),
        location_description=_location_description(properties),
        coordinate=_coordinate(feature.get("geometry")),
        proposed_start=start,
        proposed_end=end,
        date_confidence=DateConfidence.ESTIMATED,
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )


def from_milano(features: list[JSON]) -> list[Works]:
    """Convert real Milan Avvisi di manomissione features (from
    :meth:`streetworks.milano.MilanoClient.iter_roadworks`) into
    :class:`~streetworks.common.Works` - no grouping, one ``Works`` per
    feature. See module docstring."""
    works_list = []
    for feature in features:
        properties = feature.get("properties") or {}
        site = _to_site(feature)
        works_list.append(
            Works(
                reference=properties.get("Numero di protocollo ingresso"),
                coordinate=site.coordinate,
                promoter=properties.get("Impresa proprietaria area concessione/autorizzazione"),
                territory=_TERRITORY,
                administrative_area=_ADMINISTRATIVE_AREA,
                source_grade=SourceGrade.REGISTER,
                sites=(site,),
                raw=feature,
            )
        )
    return works_list
