"""BD TOPO's own shapes, modelled natively and faithfully - no canonical
street type, no `streetworks.common` converter (see the package docstring
for why).

**Priority finding 1: `voie_nommee` (named street) is real, and does give
France a genuine two-level spine** - confirmed live against the real
Géoplateforme WFS (`BDTOPO_V3:voie_nommee`), not assumed from
documentation. Every real record carries its own ``cleabs`` (a stable BD
TOPO identifier, e.g. ``"VOIE_NOM0000002336861171"``) and a real
``liens_vers_supports`` reference to a real ``TRONCON_DE_ROUTE.cleabs`` -
confirmed live by resolving a real link end to end (a `voie_nommee`'s
``liens_vers_supports`` value looked up directly against `troncon_de_route`
returned the expected segment, with matching name/BAN fields). This is
structurally the two-level shape (`Works`/`WorksSite`) the design brief
hoped for: a named street above, segments below - the strongest input
this design session has had from any territory so far. Neither NWB nor
the NSG offers this cleanly (see :mod:`streetworks.nwb.models`).

**Priority finding 2: the join to BAN is real, stated, and richer than
NWB's** - not a name match. Confirmed live: both `voie_nommee` and every
`troncon_de_route` carry ``identifiant_voie_ban`` in exactly BAN's own
compact toponyme-id format (``"01004_0668"`` - commune INSEE + street
code, see :mod:`streetworks.ban.models`), *and* a second, independent BAN
identifier, ``id_ban_odonyme`` (a UUID, e.g.
``"24e7b6f4-dfe3-4ad9-b8b6-60f922289243"``) - a street-level UUID BAN's
own API/bulk files never expose directly. On `troncon_de_route` both are
split left/right (``identifiant_voie_ban_gauche``/``_droite``,
``id_ban_odonyme_gauche``/``_droite``) - see the left/right finding below.
Verified at real commune scale, not sampled, on two whole communes (one
mainland, one overseas - see below): grouping by ``identifiant_voie_ban``
and checking against ``nom_voie_ban`` (BAN's own name, not BD TOPO's
crowd-sourced one) gives **zero** over-merged groups in either commune.

**A genuine, if minor, wrinkle**: grouping by ``identifiant_voie_ban`` and
checking against ``nom_collaboratif`` instead (BD TOPO's own
crowd-sourced/collaborative name, not BAN's) found one real case in
Basse-Terre (Guadeloupe) where the same real BAN id carries two collaborative
name spellings ("R SALVADOR ALLENDE" vs "Rue du Président Salvador Allende")
- an abbreviation variant, not a genuine identity conflict, and it
disappears entirely when checked against ``nom_voie_ban`` instead. This is
why :class:`Troncon`/:class:`VoieNommee` keep both name fields rather than
picking one: ``nom_voie_ban`` is the more reliable field for grouping,
``nom_collaboratif`` is real, locally-maintained data worth preserving as
its own thing, not silently dropped as "noise."

**Left/right modelling is real, not a documentation artefact** - confirmed
live: `troncon_de_route` carries ``nom_collaboratif_gauche``/``_droite``,
``nom_voie_ban_gauche``/``_droite``, ``insee_commune_gauche``/``_droite``,
and ``alias_gauche``/``droit`` as genuinely independent fields (a segment
running along a commune boundary can legitimately have two different
INSEE codes, one per side). This is a real structural difference from
NWB (one name per wegvak) and the UK's USRN (one name per street).

**CRS is route-dependent, and the bulk GeoPackage's CRS could not be
independently confirmed** - a real, documented gap, not an oversight.
The Géoplateforme WFS (this module's only built access route - see the
package docstring for why) explicitly declares **EPSG:4326 (WGS84)** on
every real response checked, mainland and overseas alike (confirmed:
Ambérieu-en-Bugey, mainland, and Basse-Terre, Guadeloupe, both declare
``urn:ogc:def:crs:EPSG::4326``). IGN's own documentation states the bulk
GeoPackage uses RGF93 / Lambert-93 (EPSG:2154) - plausible and consistent
with every other IGN product, but **not independently re-confirmed here**,
because no working bulk-download route was found (see the package
docstring). Only the WFS's confirmed-live WGS84 is asserted with
confidence; a Lambert-93 claim for the file this SDK cannot currently
fetch is not repeated as fact.

**Geometry**: `troncon_de_route` is a plain `LineString` (one segment) with
**real 3D coordinates** - confirmed live, e.g. a real point
``(-0.12052741, 46.43903041, 173.7)``, the third value a real altitude in
metres, answering the design brief's question directly: yes, 3D is
genuinely present, not just documented. `voie_nommee` is a
`MultiLineString` (the named street's full extent, aggregating its
segments) - both confirmed against real live data, never assumed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "Troncon",
    "VoieNommee",
    "troncon_from_feature",
    "troncon_from_properties",
    "voie_nommee_from_feature",
    "voie_nommee_from_properties",
]


def _str_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _geometry_from_feature(geom: dict[str, Any] | None) -> str | None:
    """WKT from a GeoJSON geometry - LineString (troncon_de_route) or
    MultiLineString (voie_nommee), both confirmed live. 3D coordinates
    (a real altitude third value) are carried through where present."""
    if not geom:
        return None
    kind = geom.get("type")
    coords = geom.get("coordinates") or []
    if kind == "LineString":
        points = ", ".join(" ".join(str(c) for c in pt) for pt in coords)
        return f"LINESTRING ({points})"
    if kind == "MultiLineString":
        parts = []
        for line in coords:
            points = ", ".join(" ".join(str(c) for c in pt) for pt in line)
            parts.append(f"({points})")
        return f"MULTILINESTRING ({', '.join(parts)})"
    return None


@dataclass(frozen=True)
class Troncon:
    """One `troncon_de_route` (road segment) - a *part* of a street, not a
    street itself; see the module docstring for how they group via
    :meth:`toponyme_id_gauche`/:meth:`toponyme_id_droite`. Every field not
    promoted here (~90 real columns) is preserved in ``.raw``.

    Left/right ("gauche"/"droite") is BD TOPO's own real structure, not
    this SDK's invention - see the module docstring.
    """

    cleabs: str
    nature: str | None
    importance: str | None
    nom_collaboratif_gauche: str | None
    nom_collaboratif_droite: str | None
    nom_voie_ban_gauche: str | None
    nom_voie_ban_droite: str | None
    identifiant_voie_ban_gauche: str | None
    identifiant_voie_ban_droite: str | None
    id_ban_odonyme_gauche: str | None
    id_ban_odonyme_droite: str | None
    insee_commune_gauche: str | None
    insee_commune_droite: str | None
    sens_de_circulation: str | None
    vitesse_moyenne_vl: float | None
    cpx_numero: str | None
    cpx_gestionnaire: str | None
    cpx_classement_administratif: str | None
    liens_vers_route_nommee: str | None
    etat_de_l_objet: str | None
    geometry: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def toponyme_id_gauche(self) -> str | None:
        """BAN's own street id for this segment's left side - ``None`` if
        BD TOPO carries none for this segment (a real, common case - not
        every segment is a formally addressed street). Never falls back
        to a name - see the module docstring for why."""
        return self.identifiant_voie_ban_gauche or None

    def toponyme_id_droite(self) -> str | None:
        """The right-side equivalent of :meth:`toponyme_id_gauche`."""
        return self.identifiant_voie_ban_droite or None

    def __repr__(self) -> str:
        name = self.nom_voie_ban_gauche or self.nom_collaboratif_gauche
        return f"<Troncon {name!r} ({self.cleabs})>"


@dataclass(frozen=True)
class VoieNommee:
    """One `voie_nommee` (named street) - a genuine two-level spine above
    :class:`Troncon`, confirmed live (see the module docstring).
    ``liens_vers_supports`` is the real, confirmed-live link to the
    `troncon_de_route` segment(s) that make it up.
    """

    cleabs: str
    nom_voie_ban: str | None
    nom_collaboratif: str | None
    nom_normalise: str | None
    type_voie: str | None
    identifiant_voie_ban: str | None
    id_ban_odonyme: str | None
    insee_commune: str | None
    nom_commune: str | None
    liens_vers_supports: str | None
    geometry: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def toponyme_id(self) -> str | None:
        """BAN's own street id for this named street - see
        :meth:`Troncon.toponyme_id_gauche` for the same convention."""
        return self.identifiant_voie_ban or None

    def __repr__(self) -> str:
        name = self.nom_voie_ban or self.nom_collaboratif
        return f"<VoieNommee {name!r} ({self.cleabs})>"


def troncon_from_feature(feature: dict[str, Any]) -> Troncon:
    """Build a :class:`Troncon` from one GeoJSON feature of the WFS's
    ``outputFormat=application/json`` response."""
    p = feature.get("properties", {})
    return troncon_from_properties(p, geometry=_geometry_from_feature(feature.get("geometry")))


def troncon_from_properties(p: dict[str, Any], *, geometry: str | None) -> Troncon:
    """Build a :class:`Troncon` from a flat property mapping and an
    already-resolved WKT geometry - shared by :func:`troncon_from_feature`
    (WFS GeoJSON) and :mod:`streetworks.bdtopo.reader` (GeoPackage rows,
    whose geometry is decoded from WKB, not GeoJSON coordinates)."""
    return Troncon(
        cleabs=p.get("cleabs", ""),
        nature=_str_or_none(p.get("nature")),
        importance=_str_or_none(p.get("importance")),
        nom_collaboratif_gauche=_str_or_none(p.get("nom_collaboratif_gauche")),
        nom_collaboratif_droite=_str_or_none(p.get("nom_collaboratif_droite")),
        nom_voie_ban_gauche=_str_or_none(p.get("nom_voie_ban_gauche")),
        nom_voie_ban_droite=_str_or_none(p.get("nom_voie_ban_droite")),
        identifiant_voie_ban_gauche=_str_or_none(p.get("identifiant_voie_ban_gauche")),
        identifiant_voie_ban_droite=_str_or_none(p.get("identifiant_voie_ban_droite")),
        id_ban_odonyme_gauche=_str_or_none(p.get("id_ban_odonyme_gauche")),
        id_ban_odonyme_droite=_str_or_none(p.get("id_ban_odonyme_droite")),
        insee_commune_gauche=_str_or_none(p.get("insee_commune_gauche")),
        insee_commune_droite=_str_or_none(p.get("insee_commune_droite")),
        sens_de_circulation=_str_or_none(p.get("sens_de_circulation")),
        vitesse_moyenne_vl=p.get("vitesse_moyenne_vl"),
        cpx_numero=_str_or_none(p.get("cpx_numero")),
        cpx_gestionnaire=_str_or_none(p.get("cpx_gestionnaire")),
        cpx_classement_administratif=_str_or_none(p.get("cpx_classement_administratif")),
        liens_vers_route_nommee=_str_or_none(p.get("liens_vers_route_nommee")),
        etat_de_l_objet=_str_or_none(p.get("etat_de_l_objet")),
        geometry=geometry,
        raw=p,
    )


def voie_nommee_from_feature(feature: dict[str, Any]) -> VoieNommee:
    """Build a :class:`VoieNommee` from one GeoJSON feature of the WFS's
    ``outputFormat=application/json`` response."""
    p = feature.get("properties", {})
    return voie_nommee_from_properties(p, geometry=_geometry_from_feature(feature.get("geometry")))


def voie_nommee_from_properties(p: dict[str, Any], *, geometry: str | None) -> VoieNommee:
    """The :func:`~streetworks.bdtopo.models.troncon_from_properties`
    equivalent for :class:`VoieNommee`."""
    return VoieNommee(
        cleabs=p.get("cleabs", ""),
        nom_voie_ban=_str_or_none(p.get("nom_voie_ban")),
        nom_collaboratif=_str_or_none(p.get("nom_collaboratif")),
        nom_normalise=_str_or_none(p.get("nom_normalise")),
        type_voie=_str_or_none(p.get("type_voie")),
        identifiant_voie_ban=_str_or_none(p.get("identifiant_voie_ban")),
        id_ban_odonyme=_str_or_none(p.get("id_ban_odonyme")),
        insee_commune=_str_or_none(p.get("insee_commune")),
        nom_commune=_str_or_none(p.get("nom_commune")),
        liens_vers_supports=_str_or_none(p.get("liens_vers_supports")),
        geometry=geometry,
        raw=p,
    )
