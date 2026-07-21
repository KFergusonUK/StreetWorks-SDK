"""BAG -> streetworks.common gazetteer converter.

Only a ``"adres"``-type :class:`~streetworks.bag.models.BAGLocation` is a
real address - a ``"weg"``/``"woonplaats"``/``"gemeente"``/``"postcode"``
result is a different real thing the same native model happens to share a
flat shape with (see its module docstring); this converter raises rather
than silently misrepresenting one of those as an ``Address``.

**No ``suffix`` decomposition** - a real, reportable gap, not an oversight:
the Locatieserver's real sampled responses carry ``huisnummer`` (int) and a
combined ``huis_nlt`` display string, but no separate ``huisletter``/
``toevoeging`` field was observed in any sample checked this session (see
``docs/gazetteer-field-dump.md``, B1), and neither is modelled on
:class:`.BAGLocation`. So ``suffix`` is always ``None`` here - not because
Dutch addresses never have a letter/addition, but because this SDK cannot
currently state one; do not read the constant ``None`` as "BAG has no
suffix concept."

No ``Street`` is ever produced here - Dutch street names arrive only via
this converter's own ``street_name``, per the module docstring in
:mod:`.gazetteer` ("no synthetic streets").
"""

from __future__ import annotations

from ..bag.models import BAGLocation
from .gazetteer import Address
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_bag"]


def from_bag(location: BAGLocation) -> Address:
    """Convert one real ``"adres"``-type :class:`~streetworks.bag.models.BAGLocation`
    into a :class:`~streetworks.common.gazetteer.Address`. Raises
    :class:`ValueError` for any other real ``type`` this native model
    covers (``weg``, ``woonplaats``, ``gemeente``, ``postcode``, ...) -
    those are not addresses."""
    if location.type != "adres":
        raise ValueError(
            f"BAGLocation {location.id!r} has type={location.type!r}, not 'adres' - "
            "not an address"
        )
    if location.lon is None or location.lat is None:
        raise ValueError(f"BAGLocation {location.id!r} has no coordinates to convert")

    identifiers = []
    if location.identificatie:
        identifiers.append(Identifier(scheme="identificatie", value=location.identificatie))
    if location.nummeraanduiding_id:
        identifiers.append(
            Identifier(scheme="nummeraanduiding_id", value=location.nummeraanduiding_id)
        )

    street_links = (
        (Identifier(scheme="openbare_ruimte_id", value=location.openbareruimte_id),)
        if location.openbareruimte_id
        else ()
    )

    return Address(
        geometry=Coordinate(value=(location.lon, location.lat), crs="EPSG:4326"),
        identifiers=tuple(identifiers),
        housenumber=str(location.huisnummer) if location.huisnummer is not None else None,
        suffix=None,  # see module docstring - not modelled, not the same as "absent"
        street_name=location.straatnaam,
        street_links=street_links,
        territory="Netherlands",
        administrative_area=location.gemeentenaam,
        source_grade=SourceGrade.REGISTER,
        raw=location,
    )
