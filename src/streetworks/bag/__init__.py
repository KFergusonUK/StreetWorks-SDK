"""Netherlands' BAG (Basisregistratie Adressen en Gebouwen) - the third
gazetteer, and the last before the canonical-model design session. Native
only - no canonical gazetteer type, no `streetworks.common` converter, same
discipline as `streetworks.ban` (see its package docstring).

Two credential-free routes, both wrapped by :class:`BAGClient`:

* the **PDOK Locatieserver** - live search/suggest/reverse/lookup, a
  geocoding service, not the reference dataset (see
  :mod:`streetworks.bag.client`).
* the **bulk GeoPackage** (``bag-light.gpkg``, current status only, no
  history) - the reference dataset itself, discovered via the Atom feed
  (see :mod:`streetworks.bag.atom`) and read with the standard library only,
  reusing :mod:`streetworks.openusrn`'s GeoPackage machinery (see
  :mod:`streetworks.bag.reader`).

The full-history XML extract (also offered by the Atom feed) is
investigated and documented, **not parsed** - see
:mod:`streetworks.bag.models` for what its temporal model looks like and
why building a parser for it is a canonical-model design-session decision,
not this brief's.

Licence: CC0 1.0 Universal (confirmed live from the Atom feed's own
``<rights>`` element - a correction to the design brief, see
:mod:`streetworks.bag.models`). Credit to Kadaster (LV-BAG) regardless,
consistent with how every other provider in this SDK is handled.
"""

from .atom import FEED_URL, AtomEntry, parse_feed
from .client import LOCATIESERVER_BASE_URL, BAGClient
from .models import BAGLocation
from .reader import BAGDatabase, BAGFeature, TableInfo

__all__ = [
    "FEED_URL",
    "LOCATIESERVER_BASE_URL",
    "AtomEntry",
    "BAGClient",
    "BAGDatabase",
    "BAGFeature",
    "BAGLocation",
    "TableInfo",
    "parse_feed",
]
