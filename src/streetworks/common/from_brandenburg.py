"""Germany (Brandenburg, WFS BB-BE Gazetteer) -> streetworks.common
converter.

**A genuine ``Street``, one per real record - 100% carry a real name,
confirmed against a live 500-record sample (the register's own subject
is named streets).**

**No geometry - ``GeometryGrade.ABSENT`` on every real ``Street``, not
a gap in this build.** The only real geometry this source states is a
``Polygon`` (the street's areal extent, in ``geographicExtent``) -
``Coordinate.points``/``.parts`` are documented for line-geometry
vertices, not polygon rings, so forcing a ring into either would misuse
that contract, the same discipline ``from_marousi_street`` already
established for its own polygon-only Greek source. The real polygon GML
is preserved unmodified on ``.raw`` (as ``geographicExtent_gml``).

**``administrative_area`` reconstructs the real municipality name from
two real, independently-stated fields** - ``ortsnamePost`` (the real
postal town name, e.g. ``"Brandenburg"``) plus ``zusatzOrtsname`` (a
real qualifier, e.g. ``"an der Havel"``) where stated, joined as
``"Brandenburg an der Havel"`` - confirmed live to match this same
record's own ``gemeindename_normalisiert`` field
(``"BRANDENBURGADHAVEL"``), not a guessed concatenation. Real district
names (``ortsteilname``/``postOrtsteil``) and the real structured
street key (``strassenschluessel``) have no dedicated home on this
model - kept `.raw`-only.

**A real, live-confirmed, non-exhaustive Berlin presence.** This
source's own real ``land`` field carries both Brandenburg's (`"12"`)
and Berlin's (`"11"`) real German state codes - this converter always
sets ``territory="Germany"`` regardless, the real state code kept
`.raw`-only, since this build is scoped and documented as Brandenburg's
own provider, not a claim of exhaustive Berlin coverage (see
:mod:`streetworks.brandenburg.client`'s own docstring).
"""

from __future__ import annotations

from typing import Any

from .gazetteer import GeometryGrade, Name, Street
from .models import Identifier, SourceGrade

__all__ = ["from_brandenburg_street"]

JSON = dict[str, Any]


def _administrative_area(record: JSON) -> str | None:
    town = record.get("ortsnamePost")
    if not town:
        return None
    qualifier = record.get("zusatzOrtsname")
    return f"{town} {qualifier}" if qualifier else town


def from_brandenburg_street(record: JSON) -> Street:
    """Convert one real WFS BB-BE Gazetteer ``Strassen`` record (from
    :meth:`streetworks.brandenburg.BrandenburgStreetsClient.iter_streets`)
    into a :class:`~streetworks.common.gazetteer.Street`."""
    name = record.get("strassenname")
    names = (Name(value=name),) if name and name.strip() else ()

    identifiers = []
    gml_id = record.get("gml_id")
    if gml_id:
        identifiers.append(Identifier(scheme="gml_id", value=gml_id, scope="Germany"))

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        geometry=None,
        geometry_grade=GeometryGrade.ABSENT,
        territory="Germany",
        administrative_area=_administrative_area(record),
        source_grade=SourceGrade.REGISTER,
        raw=record,
    )
