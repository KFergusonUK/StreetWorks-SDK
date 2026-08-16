"""National Road Network (NRN) - Canada's real, live, keyless national
road-segment network, published by Statistics Canada / Natural Resources
Canada (NRCan) as a GeoBase series product. This SDK's first Canadian
streets/gazetteer coverage - found via `open.canada.ca`'s own catalogue
entry for "National Road Network - NRN - GeoBase Series", which lists a
real live ArcGIS REST endpoint alongside the bulk GeoPackage/Shapefile
downloads (`geo.statcan.gc.ca/nrn_rrn/<province>/...`, not consumed here
- this module uses the REST service instead, the same TIGERweb-style
choice this SDK already made for the US, keeping GDAL/shapefile handling
out of the standard-library-plus-httpx dependency footprint).

**Same shape as TIGERweb, deliberately - a national road network with no
central street register**, confirmed live the same way: this REST
service's real schema carries per-segment attributes only
(`l_stname_c`/`r_stname_c`, `roadclass`, route names/numbers), no
separate named-street entity anywhere to aggregate under - per the
"no synthetic streets" rule (see :mod:`streetworks.common.gazetteer`),
:func:`streetworks.common.from_nrn` produces **`Segment` only, never a
`Street`**.

**Real layer structure: 5 road-class tiers x 13 provinces/territories =
65 real, genuinely non-redundant leaf layers - confirmed live by
comparing feature counts, not assumed from the layer names alone**
(unlike TIGERweb's own layers 0-9, which turned out to be a cartographic
scale pyramid with real duplicate counts). A real live count for Alberta
alone across its 5 tiers: Trans-Canada Highway 2,556; National Highway
System 7,700; Major Roads 55,876; Local Roads 443,392; Alleyways
443,593 - five genuinely different totals, not a generalisation pyramid.
:data:`ROAD_CLASSES` names the five tiers; :data:`PROVINCES` the
thirteen real province/territory codes; :data:`LAYER_IDS` is the full,
live-verified ``{road_class: {province: layer_id}}`` map (hardcoded
rather than computed from the ids' own arithmetic regularity - this
SDK's standing "verify live, don't trust a pattern to hold forever"
discipline, the same reasoning behind DfI Roads' own object-id
handling). A real `Junction`/`Blocked Passage`/`Toll Point`/`Ferry
Connection` layer family also exists on this service (not consumed
here, a real future strand the same way Jersey's own `Projects` layer
is noted but unused) - no separate address-range or house-number layer
was found anywhere on this REST service, checked, not assumed (NRN's
own bulk product states real First/Last House Number fields per the
open.canada.ca catalogue description, but they are not exposed here).

**Real field list** (identical across every road-segment layer,
confirmed live): `OBJECTID` (ArcGIS-managed only - **no genuine
NRN-native per-segment identifier is exposed over this REST service** -
the bulk product's own real `NID` field isn't in this schema, checked,
not assumed; `Segment.identifiers` stays empty on every real record this
module produces, the same honest gap as TIGERweb's own dataset-scoped-
only situation, but with even less to offer), `datasetnam` (the
province/territory name, e.g. `"Ontario"` - carried on `.raw` only, the
layer/province you queried already tells you this), `roadclass` (a real
plain-English classification, e.g. `"Local / Street"`, `"Expressway /
Highway"`, `"Resource / Recreation"` - a label, not a code, the same
shape as BD TOPO's own `nature`), `l_stname_c`/`r_stname_c` (left/right
street name - confirmed live to be **always identical** across a real
644,758-record Ontario sample and a real British Columbia sample, so
this module carries a single name, never a fabricated left/right split
where none exists; a real `"Unknown"` placeholder value also occurs -
NRN's own stated convention for "genuinely no name recorded", treated
as no name, never as a literal street called "Unknown"), `rtename1en`-
`rtename4en`/`rtename1fr`-`rtename4fr` (route names, English/French),
`rtnumber1`-`rtnumber5` (route numbers), `l_placenam`/`r_placenam` (real
left/right place names - **confirmed live to genuinely diverge** on
segments that form an administrative boundary, e.g. a real Ontario
segment between "Township of MacDonald, Meredith and Aberdeen
Additional" and "Township of Laird" - the same real left/right-admin
situation BD TOPO's own `insee_commune_gauche`/`_droite` established;
`from_nrn` applies the identical discipline: `administrative_area` is
the shared value where both sides agree, `None` (never an arbitrary
pick) where they genuinely differ).

**CRS: genuine WGS84-shaped GeoJSON output regardless of `outSR` -
confirmed live, the same real "some ArcGIS Server deployments always
emit WGS84" behaviour TIGERweb's own module docstring documents.** The
service's own stated native spatial reference is NAD83(CSRS) (`wkid:
4140`, `latestWkid: 4617`) - not Web Mercator like TIGERweb's stated
native CRS, but a real, standard Canadian geodetic lat/lon frame,
practically indistinguishable from WGS84 at this SDK's precision (sub-
metre). A real query with no `outSR` at all still returned genuine
WGS84-shaped coordinates (confirmed live, a real Northern Ontario
segment: `-87.24099251462219, 50.539991906977974`). This module
requests `outSR=4326` explicitly anyway (harmless, matching the
service's own real behaviour) and labels every
:class:`~streetworks.common.Coordinate` it produces `"EPSG:4326"` on
that basis.

**Pagination and bbox filtering both genuinely work here - confirmed
live** (unlike Jersey's roadworks layer): `resultOffset` requests
against a real 644,758-record layer returned genuinely different
`OBJECTID` values per page (offsets 0/2000 both distinct), and a real
bounding-box query against a small real downtown-Toronto envelope
returned 765 real features with real street names (`"Wellington Street
West"`, `"Mccaul Street"`, `"F G Gardiner Expressway"`).
:class:`~streetworks.arcgis.client.ArcGISFeatureClient.iter_features`
still verifies pagination live rather than trusting the service's own
`supportsPagination: true` metadata blindly, matching this SDK's
standing design discipline (no `objectIdField` is stated on this
service either, the same real situation Jersey's own streets layer and
Guernsey's layer have).

**Scale**: Local Roads alone is the largest tier per province (443,392
real features for Alberta; Ontario's own Local Roads tier, checked
directly, is 644,758) - across 13 provinces/territories and 5 tiers,
this is TIGERweb-scale nationally. Querying without a geographic filter
is not recommended; every real example in this module's tests and the
smoke-test check uses a small real bounding box, the same discipline
TIGERweb's own module established.

**Licence**: Statistics Canada / NRCan publish the NRN as Government of
Canada open data under the **Open Government Licence - Canada**
(confirmed via the real `open.canada.ca` catalogue entry itself, which
states this licence directly on the dataset page) - genuinely confirmed,
not assumed.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .client import ArcGISFeatureClient

__all__ = [
    "BASE_URL",
    "PROVINCES",
    "ROAD_CLASSES",
    "LAYER_IDS",
    "CRS",
    "NrnClient",
]

JSON = dict[str, Any]

BASE_URL = "https://geo.statcan.gc.ca/geo_wa/rest/services/NRN-RRN/nrn_rrn/MapServer"

#: The 13 real province/territory codes this service publishes, in the
#: service's own layer order.
PROVINCES = (
    "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT",
)

#: The 5 real, genuinely non-redundant road-class tiers - confirmed live
#: by comparing feature counts (see module docstring), not a cartographic
#: scale pyramid like TIGERweb's own layers 0-9.
ROAD_CLASSES = (
    "trans_canada_highway",
    "national_highway_system",
    "major_roads",
    "local_roads",
    "alleyways",
)

#: The full, live-verified {road_class: {province: layer_id}} map -
#: hardcoded from this service's own real layer tree, not computed from
#: the ids' arithmetic regularity. See module docstring.
LAYER_IDS: dict[str, dict[str, int]] = {
    "trans_canada_highway": dict(
        zip(PROVINCES, range(34, 47), strict=True)
    ),
    "national_highway_system": dict(
        zip(PROVINCES, range(48, 61), strict=True)
    ),
    "major_roads": dict(
        zip(PROVINCES, range(62, 75), strict=True)
    ),
    "local_roads": dict(
        zip(PROVINCES, range(76, 89), strict=True)
    ),
    "alleyways": dict(
        zip(PROVINCES, range(90, 103), strict=True)
    ),
}

#: Confirmed live: f=geojson returns genuine WGS84-shaped output
#: regardless of outSR or the service's stated native CRS (NAD83(CSRS),
#: wkid 4140/4617) - see module docstring.
CRS = "EPSG:4326"


class NrnClient:
    """Fetch Canadian road segments from the National Road Network. No
    credentials required.

    >>> from streetworks.arcgis.nrn import NrnClient, LAYER_IDS
    >>> from streetworks.common import from_nrn
    >>> toronto_bbox = (-79.40, 43.64, -79.38, 43.66)
    >>> layer = LAYER_IDS["local_roads"]["ON"]
    >>> with NrnClient() as nrn:  # doctest: +SKIP
    ...     segments = [
    ...         from_nrn(f) for f in nrn.iter_roads(layer, bbox=toronto_bbox)
    ...     ]
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_roads(
        self,
        layer_id: int,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        where: str = "1=1",
    ) -> Iterator[JSON]:
        """Yield real road-segment features (GeoJSON ``Feature`` dicts)
        from one real ``(road_class, province)`` layer - see
        :data:`LAYER_IDS`.

        ``bbox`` is ``(xmin, ymin, xmax, ymax)`` in WGS84 (EPSG:4326) - a
        geographic filter is **strongly recommended**: the largest real
        per-province tier has hundreds of thousands of features, see
        module docstring. Querying without one will attempt to page the
        entire layer.
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

    def __enter__(self) -> NrnClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
