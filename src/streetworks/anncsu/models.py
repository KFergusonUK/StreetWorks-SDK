"""Italy: ANNCSU (Anagrafe Nazionale Numeri Civici e Strade Urbane) -
this SDK's own native model for the ``odonimi`` (street name) resource.
See :mod:`streetworks.anncsu.client` for the full investigation and
provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Odonimo"]


@dataclass(frozen=True)
class Odonimo:
    """One real ANNCSU street name ("odonimo") - a pure name registry
    entry, no geometry of its own (see :mod:`streetworks.anncsu.client`'s
    own module docstring for why - geometry lives only, and only
    partially, on the separate ``accessi``/addresses resource, which
    this SDK has not built yet).

    Two real, independently-stated municipality identifiers are kept:
    ``codice_comune`` (the "Belfiore" code, Italy's traditional
    cadastral/tax municipality code, e.g. ``"H501"`` for Roma) and
    ``codice_istat`` (ISTAT's own numeric municipality code, e.g.
    ``"058091"``) - related but not interchangeable, both real and
    independently stated on every row.

    ``progressivo_nazionale`` is ANNCSU's own real, national, unique
    identifier for this street - confirmed distinct per real row, not
    assumed.

    ``totale_accessi`` is a real, stated count of address points on this
    street - kept on this native object since it's genuinely useful when
    working with the raw data directly, but has no canonical `Street`
    field to map onto, so it stays on `.raw` only once converted.
    """

    progressivo_nazionale: int
    codice_comune: str
    codice_istat: str
    codice_comunale: str | None
    odonimo: str
    localita: str | None
    totale_accessi: int
    denominazione_lingua1: str | None
    denominazione_lingua2: str | None
    raw: dict[str, Any] = field(default_factory=dict)
