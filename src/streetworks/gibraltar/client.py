"""Gibraltar Street Gazetteer - HM Government of Gibraltar's real, live
road-label layer, over the Geoportal's own GeoServer WFS. This SDK's
first British Overseas Territory coverage.

**Found by walking the Geoportal itself, not assumed from its INSPIRE
workspace alone.** `download.geoportal.gov.gi/geoserver` publishes two
real workspaces: `inspire` (the EU/INSPIRE-mandated layers - including
`TN_RoadTransportNetwork_RoadLink`, real link geometry but confirmed
live to carry **no name field anywhere in its schema** - the same
"geometry with no identity" outcome Germany's BKG ATKIS DLM250 WFS had)
and a richer native `gibgis` workspace underneath the same server, found
by requesting the *service-wide* `GetCapabilities` (not just the
`inspire` one the public viewer app links to). `gibgis:roads_lb_vw` -
confirmed live to be the real, distinct, named-road layer - is what
this module uses.

**Real field list** (confirmed live): `inspireId`, `label` (a composed
display string, e.g. `"Queensway - Dockyard Road - Dockyard Approach
Road"` - **not** a single real name, genuinely differing from `name` on
21% of the full 277-record layer; see
:mod:`streetworks.common.from_gibraltar`'s own module docstring for the
full real split), `name`/`collname1`/`collname2` (the real, individually
separate street names `label` composes - `name` null on 2/277 real
records, `collname1`/`collname2` real alternate names, e.g. a genuine
Llanito/Spanish local name alongside the English one), `tho_ref` (a real
cross-reference to the separate, more granular
`gibgis:thoroughfare_pl` layer - 2,026 real segment-level features, only
~30% named on a live sample; not consumed here, a real future strand the
same way Jersey's own `Projects` layer is noted but unused), `type`
(mostly null on live data), `sourceorg`/`geosrcname`/`attsrcname`/
`editor`/`geoacc`/`attacc` (provenance, undecoded), `beginLifespanVersion`/
`endLifespanVersion`/`beingupd`/`datecreate`/`dateacq`/`dateedit`.

**A real GeoJSON output-format quirk - confirmed live, not assumed from
`streetworks.ogc.OGCFeaturesClient`'s own documented default.** This
server rejects `application/geo+json` outright (`InvalidParameterValue:
Failed to find response for output format application/geo+json`) - only
plain `application/json` works. This module always passes
`output_format="application/json"` explicitly to
:meth:`~streetworks.ogc.OGCFeaturesClient.get_wfs_features` rather than
relying on that client's own default.

**CRS: real WGS84 output confirmed live when explicitly requested** -
`srsName=EPSG:4326` genuinely reprojects this layer's native
`EPSG:25830` (ETRS89 / UTM zone 30N) geometry server-side (confirmed
live, real Gibraltar coordinates, `-5.355724, 36.14059027`-shaped,
correct lon/lat order) - unlike some services this SDK has built against
(Jersey's roadworks layer, which ignores `outSR` entirely), this one
genuinely honours the request.

**No pagination needed at this real size, but checked live rather than
assumed safe.** The whole real layer is 277 features - a single request
with a generous `count` returns everything in one round trip (confirmed
live: `numberMatched == numberReturned == 277`). A real GeoServer quirk
was also found and worked around: combining `count`/`startIndex`
pagination on this *view*-backed layer without an explicit `sortBy`
fails outright (`Cannot do natural order without a primary key`) -
confirmed live; :meth:`GibraltarStreetsClient.iter_streets` always
sorts by `inspireId` and checks `numberMatched` against what it actually
received, raising rather than silently truncating if this layer ever
grows past one page.

**Licence: no single confirmed open-licence document found, built on
instruction rather than a discovered text - the same basis Jersey
shipped on.** The Geoportal's own disclaimer states reproduction/
redistribution needs "prior approval of HM Government of Gibraltar,"
qualified by "unless otherwise specified" - no more specific override
text was found on the Download Service or Publications pages checked
this session. Real, live-captured records are committed as this
module's test fixtures on the project owner's explicit instruction, the
same basis Jersey's and Autobahn GmbH's roadworks shipped on. Confirm
your own reuse/redistribution rights before redistributing data pulled
through this module further downstream.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..exceptions import TruncatedResultError
from ..ogc import OGCFeaturesClient

__all__ = ["BASE_URL", "STREETS_TYPE_NAME", "GibraltarStreetsClient"]

JSON = dict[str, Any]

BASE_URL = "https://download.geoportal.gov.gi/geoserver/ows"

#: The real named-road layer - see module docstring.
STREETS_TYPE_NAME = "gibgis:roads_lb_vw"

#: Confirmed live: this server genuinely honours a requested EPSG:4326
#: reprojection (unlike Jersey's own roadworks layer) - see module
#: docstring.
CRS = "EPSG:4326"

#: Comfortably above the real live total (277) - see module docstring.
_PAGE_SIZE = 2000


class GibraltarStreetsClient:
    """Fetch Gibraltar's real street gazetteer. No credentials required.

    >>> from streetworks.gibraltar import GibraltarStreetsClient
    >>> from streetworks.common import from_gibraltar_street
    >>> with GibraltarStreetsClient() as gibraltar:  # doctest: +SKIP
    ...     streets = [from_gibraltar_street(f) for f in gibraltar.iter_streets()]
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def iter_streets(self) -> Iterator[JSON]:
        """Yield every real street feature (GeoJSON ``Feature`` dicts).
        Raises :class:`~streetworks.exceptions.TruncatedResultError`
        rather than silently returning a partial result if this real
        277-feature layer ever grows past one page - see module
        docstring."""
        offset = 0
        while True:
            payload = self._ogc.get_wfs_features(
                BASE_URL,
                type_name=STREETS_TYPE_NAME,
                output_format="application/json",
                srs_name=CRS,
                extra_params={
                    "COUNT": str(_PAGE_SIZE),
                    "STARTINDEX": str(offset),
                    "SORTBY": "inspireId",
                },
            )
            features = payload.get("features", [])
            yield from features

            total = payload.get("numberMatched")
            returned_so_far = offset + len(features)
            if not features or len(features) < _PAGE_SIZE:
                if total is not None and returned_so_far < total:
                    raise TruncatedResultError(
                        f"{STREETS_TYPE_NAME}: expected {total} real features, "
                        f"only received {returned_so_far} - the layer may have "
                        "grown past this module's page size."
                    )
                return
            offset += len(features)

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> GibraltarStreetsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
