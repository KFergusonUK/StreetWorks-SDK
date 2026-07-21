"""BD TOPO -> streetworks.common gazetteer converter.

Dispatches on the real native type: :class:`~streetworks.bdtopo.models.Troncon`
(a road segment) -> :class:`~streetworks.common.gazetteer.Segment`;
:class:`~streetworks.bdtopo.models.VoieNommee` (a named street) ->
:class:`~streetworks.common.gazetteer.Street`. This is BD TOPO's real,
confirmed-live two-level spine (see :mod:`streetworks.bdtopo.models`) - the
strongest two-level source this design work found, so the mapping is
direct: ``VoieNommee.liens_vers_supports`` feeds ``Street.segment_refs``,
and each ``Troncon``'s ``toponyme_id_gauche``/``_droite`` feed
``Segment.street_refs`` - never a name match, per this SDK's own rule.

``crs`` defaults to ``"EPSG:4326"``, confirmed live on every real WFS
response (mainland and overseas alike) - this converter's only built
access route. Override it if converting from the bulk GeoPackage, whose
CRS this SDK has not independently confirmed (IGN's own docs say
Lambert-93/EPSG:2154 - plausible, not verified live - see the native
module's docstring).
"""

from __future__ import annotations

from datetime import date, datetime

from ..bdtopo.models import Troncon, VoieNommee
from ._wkt import coordinate_from_wkt
from .gazetteer import GeometryGrade, Name, Segment, Street, StreetType
from .models import Identifier, SourceGrade

__all__ = ["from_bdtopo"]


def _date(value: object) -> date | None:
    """``date_creation``/``date_modification`` are real ISO-8601 strings
    with a trailing ``Z`` (e.g. ``"2024-03-08T14:53:45.791Z"``)."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _split_ids(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    for sep in (";", ","):
        if sep in value:
            return tuple(dict.fromkeys(p.strip() for p in value.split(sep) if p.strip()))
    return (value,)


def _segment(troncon: Troncon, *, crs: str) -> Segment:
    geometry = coordinate_from_wkt(troncon.geometry, crs=crs)
    if geometry is None:
        raise ValueError(f"Troncon {troncon.cleabs!r} has no geometry to convert")

    names = []
    if troncon.nom_voie_ban_gauche:
        names.append(Name(value=troncon.nom_voie_ban_gauche, side="gauche"))
    if troncon.nom_voie_ban_droite and troncon.nom_voie_ban_droite != troncon.nom_voie_ban_gauche:
        names.append(Name(value=troncon.nom_voie_ban_droite, side="droite"))

    street_refs = []
    left = troncon.toponyme_id_gauche()
    right = troncon.toponyme_id_droite()
    if left:
        street_refs.append(
            Identifier(
                scheme="identifiant_voie_ban", value=left, scope=troncon.insee_commune_gauche
            )
        )
    if right and right != left:
        street_refs.append(
            Identifier(
                scheme="identifiant_voie_ban", value=right, scope=troncon.insee_commune_droite
            )
        )

    # A segment can genuinely straddle two communes (real, confirmed left/right
    # INSEE codes) - a single field can't honestly state two different real
    # values, so this stays None rather than picking one side arbitrarily;
    # the real split is still on the Troncon itself, via `.raw`.
    administrative_area = (
        troncon.insee_commune_gauche
        if troncon.insee_commune_gauche == troncon.insee_commune_droite
        else None
    )

    return Segment(
        geometry=geometry,
        identifiers=(Identifier(scheme="cleabs", value=troncon.cleabs),),
        names=tuple(names),
        street_refs=tuple(street_refs),
        street_type=StreetType(label=troncon.nature) if troncon.nature else None,
        administrative_area=administrative_area,
        as_at=_date(troncon.raw.get("date_modification") or troncon.raw.get("date_creation")),
        raw=troncon,
    )


def _street(voie: VoieNommee, *, crs: str) -> Street:
    geometry = coordinate_from_wkt(voie.geometry, crs=crs)

    # `nom_voie_ban` is the more reliable field for grouping (see the native
    # module docstring's Basse-Terre abbreviation-variant finding);
    # `nom_collaboratif` is kept as a second Name only when it genuinely
    # differs, not silently dropped.
    names = []
    if voie.nom_voie_ban:
        names.append(Name(value=voie.nom_voie_ban))
    if voie.nom_collaboratif and voie.nom_collaboratif != voie.nom_voie_ban:
        names.append(Name(value=voie.nom_collaboratif))

    street_id = voie.toponyme_id()
    return Street(
        identifiers=(Identifier(scheme="cleabs", value=voie.cleabs),),
        names=tuple(names),
        street_type=StreetType(label=voie.type_voie) if voie.type_voie else None,
        geometry=geometry,
        geometry_grade=GeometryGrade.PUBLISHED if geometry else GeometryGrade.ABSENT,
        segment_refs=tuple(
            Identifier(scheme="cleabs", value=cleabs)
            for cleabs in _split_ids(voie.liens_vers_supports)
        ),
        address_links=(
            (Identifier(scheme="identifiant_voie_ban", value=street_id, scope=voie.insee_commune),)
            if street_id
            else ()
        ),
        as_at=_date(voie.raw.get("date_modification") or voie.raw.get("date_creation")),
        territory="France",
        administrative_area=voie.insee_commune,
        source_grade=SourceGrade.REGISTER,
        raw=voie,
    )


def from_bdtopo(obj: Troncon | VoieNommee, *, crs: str = "EPSG:4326") -> Segment | Street:
    """Convert one real :class:`~streetworks.bdtopo.models.Troncon` or
    :class:`~streetworks.bdtopo.models.VoieNommee` into a
    :class:`~streetworks.common.gazetteer.Segment` or
    :class:`~streetworks.common.gazetteer.Street` respectively."""
    if isinstance(obj, Troncon):
        return _segment(obj, crs=crs)
    return _street(obj, crs=crs)
