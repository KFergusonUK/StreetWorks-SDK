"""Kartverket (Matrikkelen addresses) -> streetworks.common gazetteer
converter. SSR (place names) is a genuinely different register - neither
street nor address - and gets no canonical type here, per the design
brief.

``street_links`` uses ``adressekode``, confirmed live as a real,
clean, **municipality-scoped** street key (grouping two whole
municipalities' bulk files by it found zero codes mapping to more than one
distinct ``adressenavn``) - and confirmed live that the same numeric code
is reused for unrelated streets in different kommuner (real example:
"Karl Johans gate 1" resolves to three different addresses in three
different municipalities, each its own ``adressekode`` - 15100 in
Sarpsborg, 13630 in Oslo, 3620 in Halden). Its
:class:`~streetworks.common.models.Identifier` always carries
``scope=kommunenummer`` - never compared unscoped.

**No confirmed, always-present per-address identifier** - a real gap, not
an oversight: ``lokalid``/``uuid_adresse`` are real but bulk-CSV-only (the
REST ``/sok``/``/punktsok`` API's own :class:`.Address` shape carries
neither); where both are absent, ``Address.identifiers`` is simply empty
rather than inventing one from the address's other fields.
"""

from __future__ import annotations

from datetime import date, datetime

from ..kartverket.models import Address as KartverketAddress
from .gazetteer import Address
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_kartverket"]


def _as_at(value: str | None) -> date | None:
    """``oppdateringsdato`` is real but its exact string format has only
    been independently confirmed live on the bulk CSV route
    (``"01.01.2024 00:00:00"``); ISO-8601 is also tried since the REST API
    may state it differently, but nothing is guessed if neither parses."""
    if not value:
        return None
    for fmt in ("%d.%m.%Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def from_kartverket(address: KartverketAddress) -> Address:
    """Convert one real :class:`~streetworks.kartverket.models.Address`
    (Vegadresse/Matrikkeladresse) into a
    :class:`~streetworks.common.gazetteer.Address`."""
    if address.nord is None or address.ost is None:
        raise ValueError(f"Address {address.adressekode!r} has no coordinates to convert")
    if not address.epsg:
        raise ValueError(
            f"Address {address.adressekode!r} states no CRS - never guessed, see "
            "the native module docstring for why CRS varies by product/file here"
        )

    identifiers = []
    if address.uuid_adresse:
        identifiers.append(Identifier(scheme="uuid_adresse", value=address.uuid_adresse))
    elif address.lokalid:
        identifiers.append(
            Identifier(scheme="lokalid", value=address.lokalid, scope=address.kommunenummer)
        )

    street_links = (
        (
            Identifier(
                scheme="adressekode", value=address.adressekode, scope=address.kommunenummer
            ),
        )
        if address.adressekode
        else ()
    )

    return Address(
        geometry=Coordinate(value=(address.ost, address.nord), crs=address.epsg),
        identifiers=tuple(identifiers),
        housenumber=str(address.nummer) if address.nummer is not None else None,
        suffix=address.bokstav or None,
        street_name=address.adressenavn,
        street_links=street_links,
        as_at=_as_at(address.oppdateringsdato),
        territory="Norway",
        administrative_area=address.kommunenavn,
        source_grade=SourceGrade.REGISTER,
        raw=address,
    )
