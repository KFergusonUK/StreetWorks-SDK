"""France's Base Adresse Nationale (BAN) - the national address base,
~25M addresses, credential-free, Licence Ouverte / Open Licence 2.0 (Etalab).

**BAN is an address base, not a street register.** Unlike this SDK's UK
gazetteers (USRN-centric: the street is the entity, addresses are somebody
else's problem), BAN publishes addresses as its primary entity; streets
("voies") and hamlets ("lieux-dits") are not downloadable in their own
right - street naming belongs to DGFiP's **TOPO** referential (which
replaced FANTOIR in July 2023 - FANTOIR itself is now archived, see
:mod:`streetworks.ban.models`), a dataset with no geometry of its own.
See :mod:`streetworks.ban.models` for how a street's identity is still
recoverable from real BAN address data, and why that's derived, not a
literal BAN field - and for the confirmed-live BAN/TOPO join, investigated
but not built into this SDK yet.

This is the first non-UK gazetteer in this SDK, and deliberately ships
**native only** - no canonical gazetteer type, no `streetworks.common`
converter. USRN and DataVIA/NSG are one UK tradition, not two independent
data points; a canonical type gets designed once a few real,
disagreeing shapes are in hand, the same way `Works`/`WorksSite` was.

The BAN is one of France's nine official "données de référence" reference
datasets, administered by IGN with the ANCT supporting the communes who
actually create addresses - which is also why its data is commune-scoped
throughout (INSEE codes, not postcodes, are the real join key - see
:mod:`streetworks.ban.reader`).

Two access routes, both wrapped by :class:`BANClient`:

* the geocoding API (search/reverse) - a live *service*, see
  :mod:`streetworks.ban.client`.
* bulk per-département/national files - the closer analogue to OS Open
  USRN, and where the gazetteer content actually lives - see
  :mod:`streetworks.ban.reader`.
"""

from .client import GEOCODING_BASE_URL, AsyncBANClient, BANClient
from .models import BANAddress
from .reader import BULK_BASE_URL, bulk_url, iter_addresses, iter_addresses_csv

__all__ = [
    "BULK_BASE_URL",
    "GEOCODING_BASE_URL",
    "AsyncBANClient",
    "BANAddress",
    "BANClient",
    "bulk_url",
    "iter_addresses",
    "iter_addresses_csv",
]
