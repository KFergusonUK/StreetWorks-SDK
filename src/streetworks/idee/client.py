"""Spain: national road-transport network - IGN's (Instituto Geográfico
Nacional) real INSPIRE Annex I Theme 7 (Transport Networks) coverage,
served by IDEE (Infraestructura de Datos Espaciales de España). This
SDK's first `streets` gazetteer coverage for Spain - the counterpart to
this SDK's existing Spanish roadworks coverage (DGT, Consell de Mallorca,
SCT), a genuinely different agency and data class from all three.

.. attention::
   **Confirmed live (2026-08-15)** against real, unauthenticated requests
   directly re-verifying ``docs/inspire-gml-investigation.md``'s own
   findings - the mechanism below still matches that investigation
   exactly, live, before this build acted on it.

**Not the addresses side.** Spain's own address register (Catastro's
INSPIRE Addresses WFS) was investigated the same day this module was
built and deliberately **not** built alongside it - its documented WFS
endpoint no longer responds (every request variant tried returns a
generic error page, not a WFS response), and its own confirmed licence
explicitly prohibits redistributing the *original* data over the
internet in unmodified form, which conflicts with this SDK's usual
"real trimmed fixture" test convention. Genuinely unresolved, not
silently dropped - see ``docs/providers/pending.md``.

**The real problem this module solves: `RoadLink` alone carries no name
at all.** Confirmed at the schema level (``RoadLinkType`` extends the
shared transport-link base type with an empty ``<sequence/>`` - it adds
nothing) and confirmed live (the one schema-legal inline name field,
``geographicalName``, is absent on every real `RoadLink` sampled). The
real association runs `RoadLink` <- `Road` (not the other way round,
and not through `RoadName`, which just duplicates `Road`'s own name) -
`Road` carries the name, `localRoadCode`/`nationalRoadCode`, and a list
of ``net:link`` ``xlink:href`` references to its constituent `RoadLink`s,
whose geometry has to be fetched separately.

**Resolve does not work - confirmed dead, both ways, by the original
investigation.** Neither no resolve parameter nor an explicit
``RESOLVE=local`` (matching this service's own declared
``ResolveLocalScope=*``) inlines the referenced feature; both leave the
bare `xlink:href`. So this module never asks for resolve - it follows
the href's own URL fragment (the real gml:id after ``#``) and fetches it
directly.

**But WFS 2.0's `RESOURCEID` parameter accepts a real, comma-separated
batch - confirmed live, re-verified for this build.** A single
``GetFeature&RESOURCEID=id1,id2,...`` request returns every requested
`RoadLink`, geometry included, in one round trip - same-type batching
only (a mixed `RoadLink`+`RoadNode` batch was tried live and 500'd, so
this module never mixes feature types in one `RESOURCEID` call). So the
real shape here is: one paged `GetFeature` for `Road` (following the
server's own stated ``next`` link, not computed pagination math), then
one batched `RESOURCEID` `GetFeature` per page covering every distinct
`RoadLink` id that page's Roads reference - not one request per Road,
and never per-link `GetFeatureById`/resolve.

**A broken cross-reference is a confirmed, real, non-fatal case, not
assumed impossible.** The original investigation found 1 of 3 real
`RoadName`->`Road` hrefs it followed returned a genuine
``403 OperationProcessingFailed: feature not found`` - a stale reference
the service itself generated, not a transcription error. This module
treats an unresolved `net:link` the same way: skipped, and counted on
:attr:`~streetworks.idee.models.Road.unresolved_links`, never raised.

**CRS confirmed live: `EPSG:4258` (ETRS89), genuine lat/lon axis order.**
Every real ``srsName`` is the OGC "http URI" form
(``http://www.opengis.net/def/crs/EPSG/0/4258``); real coordinate values
confirm lat/lon in practice (a real vertex ``41.613948 2.291140`` places
the road in Barcelona, not the Mediterranean). No swap needed -
``posList`` values map straight onto this SDK's own ``(lat, lon)``
convention. Every real geometry sampled so far is a plain
``gml:LineString``/``gml:posList`` - zero curve elements across 1,000
real features in the original investigation's own dedicated check.

**Coverage confirmed live to include the Balearic Islands (Mallorca) -
but the service's own declared bounding box does not.**
``GetCapabilities``' ``Road``/``RoadLink`` featuretypes each state an
``ows:WGS84BoundingBox`` reaching only to `3.20°E` - which would exclude
part of Mallorca. A real spatial query proved this metadata wrong: a
``fes:BBOX`` filter over Mallorca's own extent (``RoadLink`` only -
``Road`` has no geometry property to filter on, confirmed live by a real
`InvalidParameterValue` exception naming it) returned real features at
`3.24-3.26°E`, genuinely east of the stated box (near Manacor/Artà). So
the capabilities bounding box understates real coverage - don't use it
to decide what's in scope, only a live query confirms that. **Plain KVP
`BBOX=` filtering timed out repeatedly against this server and was
abandoned** (60s+, zero bytes back, not a clean error) - a proper
`fes:Filter` POST request is what actually works, should spatial
filtering ever be added here. A different data class from the existing Consell de Mallorca roadworks
provider covering the same island (registry key `mallorca`, built on
`streetworks.ogc`, see :mod:`streetworks.common.from_mallorca`) - this
is the named road network, that's closures/works - no dedup conflict.

**No credentials, no rate limit stated.** Every request in this build's
own verification was unauthenticated. **Licence: CC BY 4.0**, per IDEE's
own general terms for INSPIRE download services.

**A real, deliberately unbuilt second half of this schema.** Real
classification content (`FunctionalRoadClass`/`FormOfWay`/`NumberOfLanes`)
does exist, one more hop away from `RoadLink` via the same
reverse-reference pattern - confirmed live by the original investigation,
not built here, since none of it is needed for this model's three
use cases (plotting, linking to roadworks, address street names) and it
would mean per-attribute-type round trips beyond the bounded two-hop
shape this module commits to.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from streetworks.common.models import Coordinate

from .._transport import RetryConfig, SyncTransport
from .models import Road
from .parser import parse_road_links, parse_roads_page

__all__ = ["BASE_URL", "IdeeTransportesClient"]

#: IDEE's INSPIRE Transport Networks WFS - confirmed live, keyless.
BASE_URL = "https://servicios.idee.es/wfs-inspire/transportes"

#: Not a server-confirmed limit - a defensive URL-length safety margin for
#: batched RESOURCEID requests (real Roads carry up to 40 real RoadLink
#: ids each in this build's own sampling), the same "confirmed-safe, not
#: maximal" caution this SDK already applies to Milan's stable-URL choice.
_ROADLINK_BATCH_SIZE = 100

_GEOMETRY_CRS = "EPSG:4258"


class IdeeTransportesClient:
    """Fetch Spain's real national road network. No credentials required.

    >>> from streetworks.idee import IdeeTransportesClient
    >>> from streetworks.common import from_idee
    >>> with IdeeTransportesClient() as idee:  # doctest: +SKIP
    ...     streets = [from_idee(road) for road in idee.iter_roads()]
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

    def iter_roads(self, *, count: int = 1000) -> Iterator[Road]:
        """Every real ``tn-ro:Road`` - see module docstring for the
        two-hop join this hides. Paginates via the server's own stated
        ``next`` link until exhausted."""
        url: str | None = (
            f"{BASE_URL}?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
            f"&TYPENAMES=tn-ro:Road&COUNT={count}"
        )
        while url:
            response = self._transport.request("GET", url)
            raw_roads, next_url = parse_roads_page(response.content)

            link_ids = sorted({lid for road in raw_roads for lid in road.link_ids})
            geometries = self._resolve_road_links(link_ids)

            for raw_road in raw_roads:
                yield self._to_road(raw_road, geometries)

            url = next_url

    def _resolve_road_links(
        self, link_ids: list[str]
    ) -> dict[str, list[tuple[float, float]]]:
        geometries: dict[str, list[tuple[float, float]]] = {}
        for start in range(0, len(link_ids), _ROADLINK_BATCH_SIZE):
            batch = link_ids[start : start + _ROADLINK_BATCH_SIZE]
            url = (
                f"{BASE_URL}?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
                f"&RESOURCEID={','.join(batch)}"
            )
            response = self._transport.request("GET", url)
            geometries.update(parse_road_links(response.content))
        return geometries

    @staticmethod
    def _to_road(
        raw_road: Any, geometries: dict[str, list[tuple[float, float]]]
    ) -> Road:
        parts: list[tuple[tuple[float, float], ...]] = []
        unresolved = 0
        for link_id in raw_road.link_ids:
            points = geometries.get(link_id)
            if points is None:
                unresolved += 1
            else:
                parts.append(tuple(points))

        geometry: Coordinate | None = None
        if parts:
            geometry = Coordinate(
                value=parts[0][0], crs=_GEOMETRY_CRS, parts=tuple(parts)
            )

        return Road(
            id=raw_road.id,
            name=raw_road.name,
            national_road_code=raw_road.national_road_code,
            local_road_code=raw_road.local_road_code,
            inspire_local_id=raw_road.inspire_local_id,
            inspire_namespace=raw_road.inspire_namespace,
            geometry=geometry,
            unresolved_links=unresolved,
            raw=raw_road.raw,
        )

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> IdeeTransportesClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
