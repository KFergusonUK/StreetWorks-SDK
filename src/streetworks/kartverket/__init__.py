"""Norway: Kartverket (Matrikkelen Adresse + SSR stedsnavn) - the fourth
gazetteer, and the last before the canonical-model design session. Native
only - no canonical gazetteer type, no `streetworks.common` converter,
same discipline as `streetworks.ban`/`streetworks.bag`.

The three gazetteers so far gave three positions on street identity: the
UK (street = one first-class entity, identity and geometry unified),
France (no street entity at all, identity lives in a different dataset,
no geometry anywhere), the Netherlands (street is genuinely first-class
with a real lifecycle, but has no geometry in any product, and whether you
can see it as its own row depends on which product you pull). Norway adds
two things neither of the others has: a street code carried *inside* the
address dataset itself (`adressekode` - between the UK's separate street
register and France's separate tax register), and multilingual official
naming (Norwegian, Sámi and Kven place names, each with independent
status) - see :mod:`streetworks.kartverket.models` for the confirmed-live
detail on both, and why address-level naming and place-level naming turned
out to have different answers to "is this multilingual?".

Three credential-free routes, all wrapped by :class:`KartverketClient`:

* the **address REST API** (search/proximity) - see
  :mod:`streetworks.kartverket.client`.
* the **SSR place-names REST API** (place/name/proximity search, object
  types, languages) - the multilingual register.
* **bulk CSV downloads**, discovered via an Atom feed - the closer
  analogue to the other bulk gazetteers in this SDK, and unlike Spain,
  genuinely not GML-only - see :mod:`streetworks.kartverket.atom` and
  :mod:`streetworks.kartverket.reader`.

Licence: Creative Commons BY 4.0 (confirmed live via Geonorge metadata for
both the address API and SSR independently - not assumed to match). Credit
to Kartverket regardless, consistent with every other provider.
"""

from .atom import FEED_URL, BulkEntry, parse_feed
from .client import ADDRESS_BASE_URL, SSR_BASE_URL, AsyncKartverketClient, KartverketClient
from .models import Address, NamedForm, PlaceName
from .reader import iter_addresses

__all__ = [
    "ADDRESS_BASE_URL",
    "FEED_URL",
    "SSR_BASE_URL",
    "Address",
    "AsyncKartverketClient",
    "BulkEntry",
    "KartverketClient",
    "NamedForm",
    "PlaceName",
    "iter_addresses",
    "parse_feed",
]
