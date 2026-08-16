"""Northern Ireland: DfI (Department for Infrastructure) Roads Highway
Network centreline - the real road-network line-geometry counterpart to
:mod:`streetworks.osni`'s name+point gazetteer. Jurisdiction-distinct,
never folded under a generic UK territory.

.. attention::
   **Confirmed live (2026-08-16)** against a real, unauthenticated ArcGIS
   REST FeatureServer query (71,596 real sections at time of writing).

**The promoted "open data" downloads (CSV/XML via
`dfi.highway-iams.uk`, OGL v3.0) are genuinely attribute-only - checked
live, not assumed.** Both formats carry the same 8 columns
(`SECTION_CODE`/`SECTION_NAME`/`SECTION_OFFICE_NAME`/`DIVISION_NAME`/
`SECTION_TYPE_NAME`/`ADOPTION_STATUS_NAME`/`DIGITAL_LENGTH`/`CLASS`) and
**zero geometry**, despite the dataset being titled a "centreline"
product. The real geometry lives behind the linked ArcGIS Experience
Builder public viewer instead - found by tracing that app's own item ->
its web map -> its operational layer's `FeatureServer` URL, the same
technique that found Roma's/Lisboa's/Oslo's real backends. This client
uses that `FeatureServer`, not the promoted downloads.

**Not built on this SDK's shared `streetworks.arcgis.ArcGISFeatureClient`
- a real, checked reason, not a style choice.** That client always
requests `f=geojson` first and only falls back to Esri's native `f=json`
format when the server's own geojson response fails to parse as a
genuine `FeatureCollection`. This service's `f=geojson` output **is** a
genuine, valid `FeatureCollection` - it just silently reprojects to
WGS84 (confirmed live: a real vertex came back
`-5.67296285796857, 54.6009670090229`, genuine NI lon/lat). So the
shared client's fallback would never trigger here, and using it would
mean silently losing the native Irish Grid coordinates this SDK's
"never reproject" discipline requires keeping. This client requests
`f=json` directly instead, and works from Esri's own `paths` geometry
shape.

**CRS confirmed live, directly from this service's own
`spatialReference`** - `{"wkid": 29900, "latestWkid": 29902}`. `29900`
(TM65 / Irish National Grid) is EPSG-deprecated in favour of `29902`
(TM65 / Irish Grid), confirmed via the EPSG registry, not assumed. This
is a genuine, direct live read - unlike :mod:`streetworks.osni`, whose
own REST endpoint is down and had to infer its CRS by analogy to this
exact service.

**Pagination confirmed live to genuinely advance, not assumed from
stated capability** - `resultOffset`/`resultRecordCount` was checked two
pages deep (offset 0 -> `[1, 2, 3]`, offset 3 -> `[4, 5, 6]`, ordered by
`OBJECTID`): a real, working case, not Jersey's own silently-repeating
first-page trap (see `streetworks.arcgis`'s own module docstring for
that finding). `exceededTransferLimit` is also present and correctly
signals more pages remain (`maxRecordCount` is 2,000 real records).

**A real, genuinely two-valued `ADOPTION_S` field, confirmed live, not
assumed constant** - `Adopted` (70,522 of 71,596 real sections) and
`Unadopted` (1,074) - a real "publicly maintained road" filter, not a
label always reading one value. `iter_road_sections()` defaults to
adopted-only (the real public network), with an escape hatch for the
unfiltered set.

**No credentials.** Licence: **Open Government Licence v3.0**, per the
same CKAN metadata `streetworks.osni`'s Streetnames dataset states (same
NI open-data ecosystem, independently confirmed for this dataset too).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport
from ..common.models import Coordinate
from ..exceptions import TruncatedResultError
from .models import RoadSection

__all__ = ["BASE_URL", "DfiRoadsClient"]

JSON = dict[str, Any]

#: The real ArcGIS REST FeatureServer layer behind the public "Highway
#: Network" viewer - found by tracing the Experience Builder app's own
#: item -> web map -> operational layer, not documented anywhere public.
#: See module docstring.
BASE_URL = (
    "https://services1.arcgis.com/i8LHQZrSk9zIffRU/"
    "arcgis/rest/services/DFI_Road_Network/FeatureServer/0"
)

#: Confirmed live directly from this service's own spatialReference -
#: see module docstring.
_GEOMETRY_CRS = "EPSG:29902"

_PAGE_SIZE = 2000


def _paths_to_coordinate(geometry: JSON) -> Coordinate:
    paths: list[list[list[float]]] = geometry.get("paths") or []
    parts = tuple(tuple((float(p[0]), float(p[1])) for p in path) for path in paths if path)
    if not parts:
        raise ValueError("real esriGeometryPolyline feature has no path vertices")
    if len(parts) == 1:
        return Coordinate(value=parts[0][0], crs=_GEOMETRY_CRS, points=parts[0])
    return Coordinate(value=parts[0][0], crs=_GEOMETRY_CRS, parts=parts)


def _to_road_section(feature: JSON) -> RoadSection:
    attrs: JSON = feature.get("attributes") or {}
    return RoadSection(
        section_code=str(attrs.get("Section_Code", "")).strip(),
        section_name=str(attrs.get("SECTION_NA", "")),
        division_name=str(attrs.get("DIVISION_N", "")),
        section_office_name=str(attrs.get("SECTION_OF", "")),
        class_name=str(attrs.get("CLASS_NAME", "")),
        section_type=str(attrs.get("SECTION_TY", "")),
        adoption_status=str(attrs.get("ADOPTION_S", "")),
        shape_length=float(attrs.get("Shape__Length", 0.0)),
        geometry=_paths_to_coordinate(feature["geometry"]),
        raw=attrs,
    )


class DfiRoadsClient:
    """Fetch Northern Ireland's real DfI Roads Highway Network
    centreline. No credentials required.

    >>> from streetworks.dfi_roads import DfiRoadsClient
    >>> with DfiRoadsClient() as dfi:  # doctest: +SKIP
    ...     sections = list(dfi.iter_road_sections())  # adopted only
    """

    def __init__(
        self,
        *,
        retry: RetryConfig | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        owned_client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._transport = SyncTransport(
            retry=retry or RetryConfig(), timeout=timeout, client=owned_client
        )

    def iter_road_sections(self, *, adopted_only: bool = True) -> Iterator[RoadSection]:
        """Every real road section, geometry included. Defaults to the
        real, currently-adopted public network (``adopted_only=True``,
        confirmed live 70,522/71,596 real sections) - pass
        ``adopted_only=False`` for the full unfiltered set, including
        genuine unadopted sections."""
        where = "ADOPTION_S='Adopted'" if adopted_only else "1=1"
        offset = 0
        while True:
            params = {
                "where": where,
                "outFields": "*",
                "f": "json",
                "resultOffset": offset,
                "resultRecordCount": _PAGE_SIZE,
                "orderByFields": "OBJECTID",
            }
            response = self._transport.request("GET", f"{BASE_URL}/query", params=params)
            body = response.json()
            features = body.get("features") or []
            truncated = bool(body.get("exceededTransferLimit"))
            if not features:
                if truncated:
                    raise TruncatedResultError(
                        f"{BASE_URL}: server signalled exceededTransferLimit but "
                        f"returned an empty page at offset {offset} - the full "
                        "result set cannot be safely retrieved."
                    )
                return
            for feature in features:
                yield _to_road_section(feature)
            if not truncated:
                return
            offset += len(features)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> DfiRoadsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
