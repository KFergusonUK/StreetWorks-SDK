"""Monaghan County Council's real road network - a pilot for Ireland's
genuine county-council road-network fan-out (31 independent local
authorities, the same real shape Germany's states have - see
``docs/providers/pending.md`` for the live investigation that ruled out
a single national named-street source and picked this county as the
first real build).

**Real, live, three separate ArcGIS REST services, one per official road
class** - confirmed live, not assumed from one sample: `National_Roads`
(27 real segments), `Regional_Roads` (122), `Local_Roads` (1,612), all
on the same hosted-feature-service deployment
(`services-eu1.arcgis.com/YDJmfAKmZVpOnK2Q`). Real fields (identical
shape across all three, `Municipal_District` absent only on
`National_Roads`): `Road_Name`, `Road_Class`, `Municipal_District`,
`Start_At`, `Finish_At`.

**`Road_Name` is a real route number, not a street name - confirmed
live, the whole reason this module exists.** Real values look like
`"L-31011-0"` (Local), `"R-183-12"` (Regional), `"N-12-0"` (National) -
Ireland's own official road-classification numbering, not a fabricated
placeholder. `Start_At`/`Finish_At` carry real junction/townland
descriptions instead (e.g. `"Creeve - 4 Roads"`) - how these roads are
genuinely identified in practice, not a database gap. See
:mod:`streetworks.common.from_monaghan`'s own module docstring for how
this converter honestly reflects that rather than fabricating a name
from the route code.

**CRS: real WGS84 GeoJSON by default - confirmed live, no `outSR`
needed.** The service's own stated native reference is `EPSG:2157`
(ITM, Irish Transverse Mercator), but a plain `f=geojson` request with
no `outSR` at all already returns genuine WGS84 (`-6.91, 54.10`-shaped,
correct for Monaghan) - the same real "GeoJSON implies WGS84" behaviour
TIGERweb's and the National Road Network's own services show.

**Pagination genuinely works here - confirmed live** (unlike Jersey's
roadworks layer): a real `resultOffset`/`resultRecordCount` request
against the 1,612-record `Local_Roads` layer returned genuinely
different `OBJECTID`s at offsets 0 and 1000, and this service states a
real `objectIdField` (`OBJECTID`) to page by regardless.

**Licence: no explicit statement found on the real ArcGIS Online items
checked** (`licenseInfo`/`accessInformation` both empty) - the same
open-by-design situation Jersey's own services have: publicly,
unauthenticatedly queryable by design, hosted directly by Monaghan
County Council itself, built on the project owner's explicit
instruction rather than a discovered licence document. Confirm your own
reuse/redistribution rights before redistributing data pulled through
this module further downstream.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .client import ArcGISFeatureClient

__all__ = ["BASE_URLS", "ROADS_LAYER", "MonaghanRoadsClient"]

JSON = dict[str, Any]

#: The three real, distinct official road-class services - see module
#: docstring. Keyed by the same lowercase class name
#: :func:`streetworks.common.from_monaghan.from_monaghan_road` expects
#: to see reflected in each record's own real ``Road_Class`` value.
BASE_URLS: dict[str, str] = {
    "national": "https://services-eu1.arcgis.com/YDJmfAKmZVpOnK2Q/arcgis/rest/services/National_Roads/FeatureServer",
    "regional": "https://services-eu1.arcgis.com/YDJmfAKmZVpOnK2Q/arcgis/rest/services/Regional_Roads/FeatureServer",
    "local": "https://services-eu1.arcgis.com/YDJmfAKmZVpOnK2Q/arcgis/rest/services/Local_Roads/FeatureServer",
}

#: The single real layer on every one of the three services above.
ROADS_LAYER = 0

#: Confirmed live: this service's real f=geojson output is WGS84
#: regardless of outSR - see module docstring.
CRS = "EPSG:4326"


class MonaghanRoadsClient:
    """Fetch Monaghan County Council's real road network. No credentials
    required.

    >>> from streetworks.arcgis.monaghan import MonaghanRoadsClient
    >>> from streetworks.common import from_monaghan_road
    >>> with MonaghanRoadsClient() as monaghan:  # doctest: +SKIP
    ...     segments = [from_monaghan_road(f) for f in monaghan.iter_roads("local")]
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_roads(self, road_class: str = "local", *, where: str = "1=1") -> Iterator[JSON]:
        """Yield every real road-segment feature (GeoJSON ``Feature``
        dicts) for one real road class - see :data:`BASE_URLS` for the
        three real, valid values (``"national"``, ``"regional"``,
        ``"local"``)."""
        yield from self._arcgis.iter_features(
            BASE_URLS[road_class], ROADS_LAYER, where=where, out_fields="*"
        )

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> MonaghanRoadsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
