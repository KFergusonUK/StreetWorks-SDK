"""Declarative registry of confirmed-live jurisdictions on the North
American 511 platform - the same shape
:data:`streetworks.ogc.germany.FIELD_MAPS`/
:data:`streetworks.opendatasoft.france_departements.FIELD_MAPS` already
use for one shared client serving several distinct real authorities.
Despite the module's own Canadian origin (found while surveying
Canadian provinces beyond British Columbia), this platform is genuinely
North American, not Canada-only - Nevada is this SDK's first confirmed
US jurisdiction on it, found separately while surveying US roadworks
coverage. See :mod:`streetworks.na511.client`'s own module docstring
for how each entry here was confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "Jurisdiction",
    "ONTARIO",
    "ALBERTA",
    "SASKATCHEWAN",
    "NEW_BRUNSWICK",
    "NEWFOUNDLAND_AND_LABRADOR",
    "NOVA_SCOTIA",
    "YUKON",
    "NEVADA",
    "GEORGIA",
    "ALASKA",
    "LOUISIANA",
    "JURISDICTIONS",
]


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
#: docstring. The public self-service signup page for this one has since
#: been taken down (confirmed live 2026-08-21, days after the endpoint
#: itself was first confirmed key-gated) - the real API endpoint is
#: otherwise unaffected and still answers the identical rejection.
SASKATCHEWAN = Jurisdiction(
    base_url="https://hotline.gov.sk.ca",
    needs_key=True,
    territory="Canada",
    administrative_area="Saskatchewan Highway Hotline (Ministry of Highways)",
)

#: Confirmed live to require a real developer key - see client module
#: docstring.
NEW_BRUNSWICK = Jurisdiction(
    base_url="https://511.gnb.ca",
    needs_key=True,
    territory="Canada",
    administrative_area="New Brunswick Department of Transportation and Infrastructure",
)

#: Confirmed live to require a real developer key - see client module
#: docstring.
NEWFOUNDLAND_AND_LABRADOR = Jurisdiction(
    base_url="https://511nl.ca",
    needs_key=True,
    territory="Canada",
    administrative_area="Newfoundland and Labrador Department of Transportation and Infrastructure",
)

#: Confirmed live to require a real developer key - see client module
#: docstring. Like Saskatchewan, the public self-service signup page has
#: since been taken down (confirmed live 2026-08-21: /developers/doc
#: 404s, /developers redirects to /notfound) - the real API endpoint is
#: otherwise unaffected.
NOVA_SCOTIA = Jurisdiction(
    base_url="https://511.novascotia.ca",
    needs_key=True,
    territory="Canada",
    administrative_area="Nova Scotia Public Works",
)

#: Confirmed live to require a real developer key - see client module
#: docstring.
YUKON = Jurisdiction(
    base_url="https://511yukon.ca",
    needs_key=True,
    territory="Canada",
    administrative_area="Yukon Department of Highways and Public Works",
)

#: Confirmed live to require a real developer key - see client module
#: docstring. Not in the WZDx/CWZ US registry at all (confirmed live, no
#: Nevada row of any kind) - a genuinely separate real route, not a
#: duplicate of anything streetworks.wzdx already covers. This SDK's
#: first US jurisdiction on this platform - confirmed the identical
#: shape to every Canadian one, including a real, working
#: /developers/doc page (https://www.nvroads.com/developers/doc).
NEVADA = Jurisdiction(
    base_url="https://www.nvroads.com",
    needs_key=True,
    territory="USA",
    administrative_area="Nevada Department of Transportation (NDOT)",
)

#: Confirmed live to require a real developer key - see client module
#: docstring. Found while investigating Georgia's own ArcGIS Hub
#: "TrafficImpacts" pages (a real dead end - those turned out to be
#: per-project public-information pages, not a live data feed) - checking
#: Georgia's own 511 site (511ga.org) directly against this platform's
#: real endpoint shape confirmed it immediately: the identical
#: /api/v2/get/event path, the identical "Invalid Key" rejection, and a
#: real, working /developers/doc page matching field-for-field.
GEORGIA = Jurisdiction(
    base_url="https://511ga.org",
    needs_key=True,
    territory="USA",
    administrative_area="Georgia Department of Transportation (GDOT)",
)

#: Confirmed live to require a real developer key - see client module
#: docstring. A real gap in the earlier USA gap-state survey: Alaska had
#: only been checked against its ArcGIS Open Data catalogue
#: (`data.json`, no live closures dataset there), never directly against
#: this platform's own endpoint shape the way Rhode Island/West
#: Virginia/South Dakota/Nebraska were - found on a direct re-check,
#: confirming the identical `/api/v2/get/event` path, the identical
#: "Invalid Key" rejection, and a real, working `/developers/doc` page
#: explicitly naming "Temporary Workzones" as a real event resource.
ALASKA = Jurisdiction(
    base_url="https://511.alaska.gov",
    needs_key=True,
    territory="USA",
    administrative_area="Alaska Department of Transportation & Public Facilities (DOT&PF)",
)

#: Confirmed live to require a real developer key - see client module
#: docstring. Found while searching for real Open511 (a different,
#: unrelated standard) adopters among this SDK's remaining USA gap
#: states - none were found, but a real `/help/endpoint/event` page for
#: "511LA" surfaced instead, the same URL shape 511NY/511GA already
#: publish on this platform. Confirmed the identical `/api/v2/get/event`
#: path, the identical "Invalid Key" rejection, and a real, working
#: `/developers/doc` page. Not previously on any gap-state list - a
#: genuinely new find, not a re-check.
LOUISIANA = Jurisdiction(
    base_url="https://www.511la.org",
    needs_key=True,
    territory="USA",
    administrative_area="Louisiana Department of Transportation and Development (DOTD)",
)

JURISDICTIONS: dict[str, Jurisdiction] = {
    "ontario": ONTARIO,
    "alberta": ALBERTA,
    "saskatchewan": SASKATCHEWAN,
    "new_brunswick": NEW_BRUNSWICK,
    "newfoundland_and_labrador": NEWFOUNDLAND_AND_LABRADOR,
    "nova_scotia": NOVA_SCOTIA,
    "yukon": YUKON,
    "nevada": NEVADA,
    "georgia": GEORGIA,
    "alaska": ALASKA,
    "louisiana": LOUISIANA,
}
