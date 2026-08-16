"""ANNCSU (Italy street names) -> streetworks.common gazetteer
converter.

A pure name registry, no geometry anywhere in this resource - see
:mod:`streetworks.anncsu.client`'s own module docstring for why. Every
real :class:`~streetworks.anncsu.models.Odonimo` therefore converts to a
:class:`~streetworks.common.gazetteer.Street` with
:attr:`~streetworks.common.gazetteer.GeometryGrade.ABSENT` - the same
documented "real NULL-geometry rows" state OS Open USRN already
establishes for this model, never synthesised.
"""

from __future__ import annotations

from ..anncsu.models import Odonimo
from .gazetteer import GeometryGrade, Name, Street
from .models import Identifier, SourceGrade

__all__ = ["from_anncsu"]


def from_anncsu(odonimo: Odonimo) -> Street:
    """Convert one real :class:`~streetworks.anncsu.models.Odonimo` into
    a :class:`~streetworks.common.gazetteer.Street`.

    Two real, independently-stated municipality identifiers become two
    :class:`~streetworks.common.Identifier`\\ s - the "Belfiore"
    cadastral/tax code and ISTAT's own numeric municipality code, both
    scoped ``"ANNCSU"`` since neither is a street-level identifier on
    its own, only a municipality one. ``totale_accessi`` (a real stated
    count of address points on this street) has no canonical home and
    stays on ``.raw`` only, the same discipline every other gazetteer
    converter applies to a real field without a stated consumer.
    """
    identifiers = [
        Identifier(
            scheme="progressivo_nazionale", value=str(odonimo.progressivo_nazionale)
        ),
        Identifier(
            scheme="codice_comune_belfiore", value=odonimo.codice_comune, scope="ANNCSU"
        ),
        Identifier(scheme="codice_istat", value=odonimo.codice_istat, scope="ANNCSU"),
    ]
    if odonimo.codice_comunale:
        identifiers.append(
            Identifier(
                scheme="codice_comunale",
                value=odonimo.codice_comunale,
                scope=odonimo.codice_istat,
            )
        )

    return Street(
        identifiers=tuple(identifiers),
        names=(Name(value=odonimo.odonimo),),
        geometry=None,
        geometry_grade=GeometryGrade.ABSENT,
        territory="Italy",
        source_grade=SourceGrade.REGISTER,
        raw=odonimo,
    )
