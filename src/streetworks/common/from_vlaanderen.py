"""Flanders (Belgium, Straatnamenregister) -> streetworks.common
converter.

**A genuine ``Street``, one per real record - the register's own
subject is street names, not an unlabelled segment network.**

**No geometry anywhere in this resource - ``GeometryGrade.ABSENT`` on
every real ``Street``, the same documented state ANNCSU/BEV already
establish, not a gap in this build.** See
:mod:`streetworks.vlaanderen.client`'s own docstring for the real,
richer Wegenregister WFS layer this could join back to, not attempted
here.

**``administrative_area`` is never populated - a real, confirmed API
gap, not an oversight.** The list endpoint this converter reads carries
no municipality reference at all; see
:mod:`streetworks.vlaanderen.client`'s own docstring for the documented
filter parameter that's silently ignored, and the undocumented one that
works but would need an unattempted ~300-municipality fan-out to use.

``names`` carries the real ``taal`` (language) tag via ``Name.language``
- Flanders' own register states ``"nl"`` on every record checked live,
never merged into a compound value, the same discipline NSG's own
``_eng``/``_cym`` and Digiroad's ``_su``/``_ru`` fields already
established, even though only one language has been observed live here.

``street_type`` is never populated - this register has no classification
field of its own (unlike BEV's Austrian register, which has none either,
or Iceland's LMI, which does).
"""

from __future__ import annotations

from typing import Any

from .gazetteer import GeometryGrade, Name, Street
from .models import Identifier, SourceGrade

__all__ = ["from_vlaanderen_street"]

JSON = dict[str, Any]


def from_vlaanderen_street(record: JSON) -> Street:
    """Convert one real Straatnaam record (from
    :meth:`streetworks.vlaanderen.VlaanderenStreetsClient.iter_streets`)
    into a :class:`~streetworks.common.gazetteer.Street`."""
    geografische_naam = record.get("straatnaam", {}).get("geografischeNaam", {})
    name = geografische_naam.get("spelling")
    language = geografische_naam.get("taal")
    names = (Name(value=name, language=language),) if name and name.strip() else ()

    identifiers = []
    object_id = record.get("identificator", {}).get("objectId")
    if object_id:
        identifiers.append(
            Identifier(scheme="straatnaam_objectid", value=object_id, scope="Belgium")
        )

    return Street(
        identifiers=tuple(identifiers),
        names=names,
        geometry=None,
        geometry_grade=GeometryGrade.ABSENT,
        territory="Belgium",
        source_grade=SourceGrade.REGISTER,
        raw=record,
    )
