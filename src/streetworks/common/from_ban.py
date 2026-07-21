"""BAN -> streetworks.common gazetteer converter.

``street_links`` is the brief's own worked example of a field that must be
marked as derived rather than stated: ``BANAddress.toponyme_id`` is *not* a
literal BAN field (see :mod:`streetworks.ban.models`'s module docstring) -
it's this SDK's own derived grouping prefix. Its
:class:`~streetworks.common.models.Identifier` uses the scheme
``"ban_toponyme_id_derived"``, not a bare ``"toponyme_id"``, so that
derivation is visible wherever the identifier surfaces, not just in a
docstring a caller may never read. The plain ``csv`` bulk route's real,
*stated* ``id_fantoir`` (in practice a TOPO-length code, not the archived
FANTOIR one - see the native docstring) is kept as a separate, genuinely
stated identifier alongside it, where present.

``housenumber``/``suffix`` need no extra logic here: :class:`.BANAddress`
already carries the real route-dependency (the geocoding API folds any
suffix into ``housenumber`` and leaves ``suffix`` ``None``; only the bulk
CSV routes decompose it) - this converter just passes both fields through
unchanged.
"""

from __future__ import annotations

from datetime import date, datetime

from ..ban.models import BANAddress
from .gazetteer import Address
from .models import Coordinate, Identifier, SourceGrade

__all__ = ["from_ban"]


def _as_at(address: BANAddress) -> date | None:
    """``date_der_maj`` is real but only on the ``csv-bal`` bulk route, and
    isn't promoted onto :class:`.BANAddress` itself - read from ``.raw``
    where present (format ``"YYYY-MM-DD"``), ``None`` otherwise (the
    geocoding API and plain ``csv`` route carry no equivalent field)."""
    raw = address.raw
    value = raw.get("date_der_maj") if isinstance(raw, dict) else None
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def from_ban(address: BANAddress) -> Address:
    """Convert one real :class:`~streetworks.ban.models.BANAddress` into a
    :class:`~streetworks.common.gazetteer.Address`."""
    if address.lon is None or address.lat is None:
        raise ValueError(f"BANAddress {address.id!r} has no coordinates to convert")

    identifiers = [Identifier(scheme="ban_cle_interop", value=address.id)]
    if address.ban_id:
        identifiers.append(Identifier(scheme="ban_id", value=address.ban_id))

    street_links = [
        Identifier(
            scheme="ban_toponyme_id_derived",
            value=address.toponyme_id,
            scope=address.commune_insee,
        )
    ]
    id_fantoir = address.raw.get("id_fantoir") if isinstance(address.raw, dict) else None
    if id_fantoir:
        street_links.append(
            Identifier(scheme="id_fantoir", value=id_fantoir, scope=address.commune_insee)
        )

    return Address(
        geometry=Coordinate(value=(address.lon, address.lat), crs="EPSG:4326"),
        identifiers=tuple(identifiers),
        housenumber=address.housenumber,
        suffix=address.suffix,
        street_name=address.street,
        street_links=tuple(street_links),
        as_at=_as_at(address),
        territory="France",
        administrative_area=address.commune_nom,
        source_grade=SourceGrade.REGISTER,
        raw=address,
    )
