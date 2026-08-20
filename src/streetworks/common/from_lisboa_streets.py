"""Toponímia de Lisboa (CML) -> streetworks.common gazetteer converter.

This SDK's first Portuguese streets/gazetteer coverage - see
:mod:`streetworks.arcgis.lisboa` for the full live investigation (why
this real, keyless CML ArcGIS layer was picked over two other real
candidates found on the same service).

**Geometry: real ``LineString``/``MultiLineString`` GeoJSON, axis order
preserved exactly as the source states it (``[lon, lat]``) - not flipped
to a ``(lat, lon)`` convention.** This is the same choice
:mod:`.from_nrn`/:mod:`.from_datavia` already make for their own real
GeoJSON-native ArcGIS/WFS sources: the ``(lat, lon)`` swap other
converters in this SDK apply (e.g. :mod:`.from_geosn`) is only ever
done when *this SDK's own* closed-form CRS transform hands back a bare
``(lon, lat)`` tuple with no inherent convention of its own - GeoJSON
already has one, stated by the format itself, and there is no reason to
relabel it. A genuine ``MultiLineString`` is real here, not
hypothetical - confirmed live, e.g. "Avenida Ucrânia" spans 7 real
discontinuous ``paths`` in one record - carried via
:class:`~streetworks.common.models.Coordinate`'s own ``parts``.

**``administrative_area`` carries the real, verbatim ``FREGUESIAS``
string, including when it names more than one parish.** A single street
can genuinely cross a real freguesia (parish) boundary - CML states this
as one comma-joined field on the record itself (e.g. "Alcântara (Nova
Freguesia), Belém (Nova Freguesia)"), not as two separate fields the way
BD TOPO's own left/right commune split is - so relaying it verbatim is
honest, not a fabricated concatenation of this SDK's own invention.

**No dedicated field for ``LEGENDA`` (a short honoree bio),
``DENOMINACOES_ANTERIORES`` (real former names) or ``HISTORIAL`` (a real
prose essay on the name's origin, some genuinely several paragraphs
long)** - this SDK's :class:`~streetworks.common.gazetteer.Street` has
no naming-history concept to carry them in, so all three stay on
``.raw`` only, the same treatment Brandenburg's ``zusatzOrtsname``/
Guernsey's ``CLASS`` get for their own real fields with no canonical
home.

``identifiers`` carries the real ``COD_LOCAL`` (CML's own official
per-street code, scheme ``"cod_local"``, scope ``"Lisboa"``) - the
service's own internal ``TOP_ID``/``OBJECTID`` are not promoted, since
neither was confirmed live as a stable, externally-referenceable code
the way ``COD_LOCAL`` plausibly is (its own field name literally reads
"local code"), the same caution :mod:`.from_nrn` already applies to its
own service-scoped ``OBJECTID``.
"""

from __future__ import annotations

from typing import Any

from .gazetteer import GeometryGrade, Name, Street
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_lisboa_street"]

JSON = dict[str, Any]

_CRS = "EPSG:4326"


def _geometry(geometry: JSON | None) -> Coordinate | None:
    if not geometry:
        return None
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "LineString" and coords:
        points = tuple(tuple(c) for c in coords)
        return Coordinate(value=points[0], crs=_CRS, points=points if len(points) > 1 else None)
    if kind == "MultiLineString" and coords:
        parts = tuple(tuple(tuple(c) for c in line) for line in coords if line)
        if not parts:
            return None
        return Coordinate(value=parts[0][0], crs=_CRS, parts=parts)
    return None


def from_lisboa_street(feature: JSON) -> Street:
    """Convert one real Lisboa Toponímia GeoJSON ``Feature`` (from
    :meth:`streetworks.arcgis.lisboa.LisboaStreetsClient.iter_streets`)
    into a :class:`~streetworks.common.gazetteer.Street`."""
    properties = feature.get("properties", {})

    designacao = properties.get("DESIGNACAO")
    names = (Name(value=designacao),) if designacao and designacao.strip() else ()

    cod_local = properties.get("COD_LOCAL")
    identifiers = []
    if cod_local:
        identifiers.append(Identifier(scheme="cod_local", value=str(cod_local), scope="Lisboa"))

    geometry = _geometry(feature.get("geometry"))

    freguesias = properties.get("FREGUESIAS")

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        territory="Portugal",
        administrative_area=freguesias if freguesias and freguesias.strip() else None,
        source_grade=SourceGrade.REGISTER,
        raw=feature,
    )
