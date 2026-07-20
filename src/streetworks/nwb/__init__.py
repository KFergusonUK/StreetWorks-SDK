"""NWB (Nationaal Wegenbestand) - the Dutch national road network, and
the counterpart to `streetworks.bag`'s addresses: the first non-UK
street-geometry provider in this SDK. Native only - no canonical street
type, no `streetworks.common` converter, same discipline as
`streetworks.ban`/`streetworks.bag`/`streetworks.kartverket`.

**A street is a set of `wegvakken` (road segments), not one feature** -
separated carriageways are real, separate segments. How they group back
into a real street, and whether a stated join to BAG exists, are this
module's key findings - see :mod:`streetworks.nwb.models` for the
confirmed-live detail (short version: `bag_orl`, BAG's own
`openbare_ruimte_identificatie`, is a real and clean join where present,
but isn't universal, and name-matching alone is measurably less
reliable).

Two credential-free routes, both wrapped by :class:`NWBClient`:

* the **WFS** (live queries, real `CQL_FILTER` support, real paging - see
  :mod:`streetworks.nwb.client` for a correction to the design brief's
  own paging warning).
* the **bulk GeoPackage**, discovered via a two-hop Atom feed (see
  :mod:`streetworks.nwb.atom`) and read with the standard library only,
  reusing :mod:`streetworks.openusrn`'s GeoPackage machinery like
  `streetworks.bag` does (see :mod:`streetworks.nwb.reader`).

Licence: CC0 1.0 Universal (confirmed live from the Atom feed's own
``<rights>`` element, matching BAG - not the vaguer "open data" a portal
page alone states). Roads only - the separate NWB Vaarwegen (waterways)
product is out of scope, noted so nobody fetches the wrong feed.
"""

from .atom import INDEX_FEED_URL, DatasetEntry, DownloadEntry, parse_dataset_feed, parse_index_feed
from .client import WFS_BASE_URL, AsyncNWBClient, NWBClient
from .models import Wegvak
from .reader import NWBDatabase, NWBFeature, TableInfo

__all__ = [
    "INDEX_FEED_URL",
    "WFS_BASE_URL",
    "AsyncNWBClient",
    "DatasetEntry",
    "DownloadEntry",
    "NWBClient",
    "NWBDatabase",
    "NWBFeature",
    "TableInfo",
    "Wegvak",
    "parse_dataset_feed",
    "parse_index_feed",
]
