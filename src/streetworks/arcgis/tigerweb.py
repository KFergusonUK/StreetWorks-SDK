"""TIGERweb (US Census Bureau) - the national road-segment network, over
the ``TIGERweb/Transportation`` ArcGIS MapServer.

**Context that matters for the canonical model**: TIGER is a statistical
and cartographic product from the Census Bureau's MAF/TIGER system, not a
legal register - there is no statutory street identifier here equivalent
to a USRN. The closest thing to an identifier, the real ``OID`` field
(confirmed live, e.g. ``"110431686451"`` - a 12-digit numeric string,
matching the known TIGER/Line TLID shape), is **dataset-scoped**: it
identifies a record within this Census product, not a street in any
authoritative, cross-referenceable sense the way a USRN or a BAN
``toponyme_id`` does. This is exactly what
:class:`~streetworks.common.models.Identifier.scope` exists for - the US
has a central national street dataset, but not an authoritative street
register, and that distinction is recorded honestly rather than
papered over.

**Layers 0-9 are a cartographic scale pyramid, not distinct road classes -
a real correction to the design brief's own framing, confirmed live by
comparing every layer's real feature count**: layers ``1`` ("2_1M scale")
and ``2`` ("Primary Roads", no scale suffix) both report **17,612**
features nationally - the identical dataset, just labelled/generalised for
two different zoom-scale tiers, not two different road classes. The same
is true of layers ``4``/``5``/``6`` (Secondary Roads, all **248,106**) and
layers ``7``/``8`` (Local Roads, both **16,150,491**). Layer ``0``
(Interstates only, a distinct, more-generalised **5,607**-feature subset)
and layer ``3`` (Secondary Roads Interstates+US Highways, a distinct
**31,169**-feature subset) are real, separate cartographic layers, not
part of that pyramid. Layer ``9`` is Railroads - not a road at all. The
real road *class* comes from each feature's own ``MTFCC`` value, not from
which layer id you queried.

**The three full-detail layers - confirmed live via ``minScale``/
``maxScale`` (the layer with ``maxScale=1001`` in each same-count group is
the one rendered down to full zoom, i.e. the least-generalised geometry)**
are what this module queries by default: layer ``2`` (Primary Roads, MTFCC
``S1100``), layer ``6`` (Secondary Roads, MTFCC ``S1200``), layer ``8``
(Local Roads, MTFCC ``S1400`` - confirmed live, e.g. a real Washington DC
segment, ``NAME="D St NW"``). A real ``S1630`` (ramp) value was also
observed live within layer ``8`` - MTFCC's real domain is richer than the
three headline codes; this module carries whatever value is stated,
undecoded, per this SDK's standing "carry the code, don't decode" rule -
no MTFCC lookup table is bundled here.

**Real field list** (identical across all road layers, confirmed live):
``BASENAME``, ``MTFCC``, ``NAME``, ``OBJECTID`` (the ArcGIS-managed OID),
``OID`` (the real TIGER dataset id, string-typed - see above),
``PREDIR``/``PREDIRABRV`` (prefix direction, e.g. ``"NW"``),
``PREQUAL``/``PREQUALABRV``, ``PRETYP``/``PRETYPEABRV``, ``RTTYP`` (route
type - real values confirmed live: ``I`` Interstate, ``U`` US highway,
``S`` State, ``C`` County, ``M`` Municipal), ``SUFDIR``/``SUFDIRABRV``,
``SUFQUAL``/``SUFQUALABRV``, ``SUFTYP``/``SUFTYPEABRV`` (suffix type, e.g.
``"St"``).

**No Address Ranges layer exists in this REST service - checked, not
assumed, so ``Segment.address_ranges`` stays on its NWB-only footing.**
TIGER's bulk shapefile product has a real ``ADDRFEAT`` (address range
feature) file, but a live check of every TIGERweb service
(``TIGERweb/Transportation`` and the 34 other real services under
``TIGERweb/`` - boundaries, statistical areas, ``tigerWMS_Current``, none
of them roads-and-addresses) found nothing address-range-shaped exposed
over REST. Reported per the design brief's own instruction to report
either way, not silently assumed absent.

**CRS: genuinely inconsistent behaviour between the stated native CRS and
the actual GeoJSON output - verified live, not assumed.** The service's
own stated ``spatialReference`` is Web Mercator (``wkid: 102100``,
``latestWkid: 3857``). But a real ``f=geojson`` query with **no** ``outSR``
requested at all still returned genuine WGS84 lon/lat coordinates
(confirmed live, e.g. ``-77.03076800022644, 38.894642000156054`` for a
real Washington DC road, not Web Mercator's much larger numbers) - some
ArcGIS Server deployments always emit WGS84 for ``f=geojson`` regardless of
the layer's native CRS or the request's own ``outSR``. This is the
opposite of Jersey's behaviour (which stays in its native CRS regardless
of ``outSR`` - see :mod:`streetworks.arcgis.jersey`) - "GeoJSON implies
WGS84" is a real behaviour of *some* deployments, not a protocol
guarantee, and each service in this SDK states what it actually verified
rather than assuming one CRS convention applies everywhere. This module
requests ``outSR=4326`` explicitly anyway (harmless, and correct per the
service's own real behaviour) and labels every :class:`~streetworks.common.Coordinate`
it produces ``"EPSG:4326"`` on that basis.

**Pagination genuinely works here** - confirmed live (unlike Jersey):
``resultOffset``/``resultRecordCount`` requests against a real bbox query
returned genuinely different ``OBJECTID`` values per page (offsets 0/50/100
all distinct). :class:`~streetworks.arcgis.client.ArcGISFeatureClient
.iter_features` still verifies this live rather than trusting the
``supportsPagination: true`` metadata blindly, matching this module's own
design discipline.

**Scale**: layer ``8`` alone (Local Roads) has 16,150,491 real features
nationally - the largest dataset this SDK queries through a REST API.
Querying without a geographic filter is not recommended; every real
example in this module's tests and the smoke-test check uses a small
real bounding box.

**Licence**: TIGER/Line and TIGERweb are products of the US Census Bureau,
a federal government agency - works of the United States Government are
not subject to domestic copyright protection (17 U.S.C. § 105), so this
data is public domain. This session's check did not find an explicit
per-page reuse statement on census.gov's own terms-of-service page (it may
render its terms via client-side script rather than static HTML this
session's plain HTTP check could read) - the public-domain status itself
rests on the federal-government-work statute, not on having found a
specific webpage sentence, and is about as settled as US open-data law
gets.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .client import ArcGISFeatureClient

__all__ = [
    "BASE_URL",
    "PRIMARY_ROADS_LAYER",
    "SECONDARY_ROADS_LAYER",
    "LOCAL_ROADS_LAYER",
    "ROAD_LAYERS",
    "CRS",
    "TIGERwebClient",
]

JSON = dict[str, Any]

BASE_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Transportation/MapServer"

#: The three full-detail (finest cartographic tier), non-redundant road
#: layers - see module docstring for why these three and not 0/1/3/4/5/7.
PRIMARY_ROADS_LAYER = 2  #: MTFCC S1100
SECONDARY_ROADS_LAYER = 6  #: MTFCC S1200
LOCAL_ROADS_LAYER = 8  #: MTFCC S1400

ROAD_LAYERS = (PRIMARY_ROADS_LAYER, SECONDARY_ROADS_LAYER, LOCAL_ROADS_LAYER)

#: Confirmed live: f=geojson returns genuine WGS84 regardless of outSR or
#: the layer's stated native CRS (Web Mercator) - see module docstring.
CRS = "EPSG:4326"


class TIGERwebClient:
    """Fetch US road segments from TIGERweb. No credentials required.

    >>> from streetworks.arcgis.tigerweb import TIGERwebClient, LOCAL_ROADS_LAYER
    >>> from streetworks.common import from_tigerweb
    >>> dc_bbox = (-77.05, 38.89, -77.03, 38.91)
    >>> with TIGERwebClient() as tiger:  # doctest: +SKIP
    ...     segments = [
    ...         from_tigerweb(f)
    ...         for f in tiger.iter_roads(LOCAL_ROADS_LAYER, bbox=dc_bbox)
    ...     ]
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_roads(
        self,
        layer_id: int = LOCAL_ROADS_LAYER,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        where: str = "1=1",
    ) -> Iterator[JSON]:
        """Yield real road-segment features (GeoJSON ``Feature`` dicts)
        from one layer (default: Local Roads - see :data:`ROAD_LAYERS` for
        the other two full-detail layers).

        ``bbox`` is ``(xmin, ymin, xmax, ymax)`` in WGS84 (EPSG:4326) - a
        geographic filter is **strongly recommended**: layer 8 alone has
        16,150,491 real features nationally, see module docstring.
        Querying without one will attempt to page the entire national
        dataset.
        """
        geometry = None
        if bbox is not None:
            xmin, ymin, xmax, ymax = bbox
            geometry = {
                "xmin": xmin,
                "ymin": ymin,
                "xmax": xmax,
                "ymax": ymax,
                "spatialReference": {"wkid": 4326},
            }
        yield from self._arcgis.iter_features(
            BASE_URL,
            layer_id,
            where=where,
            out_fields="*",
            out_sr=4326,
            geometry=geometry,
            in_sr=4326,
        )

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> TIGERwebClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
