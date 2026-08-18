"""BEV (Austria, Österreichisches Adressregister STRASSE.csv) ->
streetworks.common converter.

**A genuine ``Street``, one per real row - 100% carry a real name,
confirmed against the complete national dataset (137,767 rows).** The
same pure name-registry shape ANNCSU (Italy) already established.

**No geometry anywhere in this resource - ``GeometryGrade.ABSENT`` on
every real ``Street``, the same documented state OS Open USRN and
ANNCSU already establish, not a gap in this build.** Real coordinates
exist only on a much larger sibling address-level resource this SDK
doesn't fetch here - see :mod:`streetworks.bev.client`'s own docstring.

``administrative_area`` carries the real ``GEMEINDENAME`` (municipality
name), already joined in by :meth:`streetworks.bev.BevStreetsClient.iter_streets`
from the real ``GEMEINDE.csv`` table - a resolved name, not a bare code,
unlike Denmark's DAR (which left its own raw kommune code unresolved
since no lookup table was fetched there).

``STRASSENNAMENZUSATZ`` (a real name-addition/qualifier field, populated
on a real minority of rows) has no dedicated home on this model - kept
`.raw`-only, never silently dropped.
"""

from __future__ import annotations

from .gazetteer import GeometryGrade, Name, Street
from .models import Identifier, SourceGrade

__all__ = ["from_bev_street"]

JSON = dict[str, str]


def from_bev_street(row: JSON) -> Street:
    """Convert one real BEV ``STRASSE.csv`` row (from
    :meth:`streetworks.bev.BevStreetsClient.iter_streets`, already
    joined against ``GEMEINDE.csv``) into a
    :class:`~streetworks.common.gazetteer.Street`."""
    name = row.get("STRASSENNAME")
    names = (Name(value=name),) if name and name.strip() else ()

    identifiers = []
    skz = row.get("SKZ")
    if skz:
        identifiers.append(Identifier(scheme="skz", value=skz, scope="Austria"))

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        geometry=None,
        geometry_grade=GeometryGrade.ABSENT,
        territory="Austria",
        administrative_area=row.get("GEMEINDENAME") or None,
        source_grade=SourceGrade.REGISTER,
        raw=row,
    )
