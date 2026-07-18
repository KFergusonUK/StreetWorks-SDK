"""Autobahn GmbH - Germany's national motorway (Autobahn) roadworks.

Autobahn GmbH's own open JSON REST API - **not** DATEX II and not OGC/WFS,
so it has its own small parser here rather than routing through
:mod:`streetworks.datex2`. Covers the national motorway network only; the
German regional road networks (state roads) are a separate WFS-based
source, out of scope here.

**Licence: unconfirmed.** Checked govdata.de's CKAN catalog entry for this
API (organisation: Mobilithek; ``license_title``/``license_url`` both
blank), the MDM portal link that entry points to (unreachable), the
community ``bundesAPI/autobahn-api`` documentation (no licence stated),
and the official autobahn.de app page (no terms of use found). None
confirm reuse/redistribution terms. Shipped anyway at the maintainer's
explicit instruction, flagged here deliberately rather than assumed open -
confirm your own reuse rights before redistributing this data.
"""

from .client import BASE_URL, AutobahnClient
from .models import DISPLAY_TYPES, Roadworks
from .parser import parse_roadworks

__all__ = [
    "AutobahnClient",
    "BASE_URL",
    "Roadworks",
    "DISPLAY_TYPES",
    "parse_roadworks",
]
