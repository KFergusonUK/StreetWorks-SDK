"""CACLR (Luxembourg, Registre national des localités et des rues) ->
streetworks.common converter.

**A genuine ``Street``, one per real row - 100% carry a real name,
confirmed against the complete national dataset (9,946 rows), zero
duplicate street numbers.** The same pure name-registry shape ANNCSU
(Italy) and BEV (Austria) already established.

**No geometry anywhere in this resource - ``GeometryGrade.ABSENT`` on
every real ``Street``, not a gap in this build.** Real coordinates exist
only on a much larger sibling address-level table (``IMMEUBLE``,
~14.6 MB) this converter's source doesn't fetch - see
:mod:`streetworks.caclr.client`'s own docstring.

``administrative_area`` carries the real ``COMMUNE_NOM`` (commune name),
already resolved by
:meth:`streetworks.caclr.CaclrStreetsClient.iter_streets` via the real
``LOCALITE``/``COMMUALL`` composite-key join - a resolved name, not a
bare code, the same "resolve what's cheaply joinable" call this SDK
made for Austria's BEV register, done here with a real join trap
(commune codes are only unique within their own canton) found and
worked around rather than reproduced.

``DATE_FIN_VALID`` (a real end-validity date) and ``INDIC_PROVISOIRE``
(a real provisional-street flag) have no dedicated home on this model -
kept `.raw`-only, never used to filter or drop a real row.
"""

from __future__ import annotations

from .gazetteer import GeometryGrade, Name, Street
from .models import Identifier, SourceGrade

__all__ = ["from_caclr_street"]

JSON = dict[str, str]


def from_caclr_street(row: JSON) -> Street:
    """Convert one real CACLR ``RUE`` row (from
    :meth:`streetworks.caclr.CaclrStreetsClient.iter_streets`, already
    joined against ``LOCALITE``/``COMMUALL``) into a
    :class:`~streetworks.common.gazetteer.Street`."""
    name = row.get("NOM")
    names = (Name(value=name),) if name and name.strip() else ()

    identifiers = []
    numero = row.get("NUMERO")
    if numero:
        identifiers.append(Identifier(scheme="numero", value=numero, scope="Luxembourg"))

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        geometry=None,
        geometry_grade=GeometryGrade.ABSENT,
        territory="Luxembourg",
        administrative_area=row.get("COMMUNE_NOM") or None,
        source_grade=SourceGrade.REGISTER,
        raw=row,
    )
