"""Declarative registry of confirmed-live jurisdictions on the North
American 511 platform - the same shape
:data:`streetworks.ogc.germany.FIELD_MAPS`/
:data:`streetworks.opendatasoft.france_departements.FIELD_MAPS` already
use for one shared client serving several distinct real authorities.
See :mod:`streetworks.na511.client`'s own module docstring for how each
entry here was confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Jurisdiction", "ONTARIO", "ALBERTA", "SASKATCHEWAN", "JURISDICTIONS"]


@dataclass(frozen=True)
class Jurisdiction:
    base_url: str
    needs_key: bool
    territory: str
    administrative_area: str


#: Confirmed live keyless (2026-08-21) - see client module docstring.
ONTARIO = Jurisdiction(
    base_url="https://511on.ca",
    needs_key=False,
    territory="Canada",
    administrative_area="Ontario Ministry of Transportation (MTO)",
)

#: Confirmed live to require a real developer key - see client module
#: docstring.
ALBERTA = Jurisdiction(
    base_url="https://511.alberta.ca",
    needs_key=True,
    territory="Canada",
    administrative_area="Alberta Transportation and Economic Corridors",
)

#: Confirmed live to require a real developer key - see client module
#: docstring.
SASKATCHEWAN = Jurisdiction(
    base_url="https://hotline.gov.sk.ca",
    needs_key=True,
    territory="Canada",
    administrative_area="Saskatchewan Highway Hotline (Ministry of Highways)",
)

JURISDICTIONS: dict[str, Jurisdiction] = {
    "ontario": ONTARIO,
    "alberta": ALBERTA,
    "saskatchewan": SASKATCHEWAN,
}
