"""Helsinki: Kaivuilmoitus ("excavation notification") - this SDK's third
Nordic roadworks coverage (after Copenhagen and Oslo).

.. attention::
   **Confirmed live (2026-08-13)** against a real, unauthenticated pull
   (3,431 real feature rows at time of writing).

**Resolves the investigation brief's own open question - not assumed.**
``nordic-capitals-investigation.md`` flagged Helsinki "least urgent" and,
crucially, left its core claim unconfirmed: a roadworks/excavation-permit
dataset "is not confirmed" on Helsinki Region Infoshare (``hri.fi``).
Checked live via HRI's own CKAN API (``package_search``): every
excavation/permit-shaped search term (``kaivulupa``, ``kaivuilmoitus``,
``työmaa``, ``excavation``, ``katutyöt``) surfaces one real dataset -
**"Land usage permission system for public areas in the City of
Helsinki"** - backed by a live GeoServer WFS. Confirmed, not guessed.

**The real endpoint is a GeoServer WFS, not HRI's own CKAN resources.**
HRI's package metadata only lists the WFS/WMS capability URLs, not a
direct download - :data:`BASE_URL` is
``https://kartta.hel.fi/ws/geoserver/avoindata/wfs``, layer
``avoindata:Kaivuilmoitus_alue`` ("excavation notification, area"),
fetched via the shared :class:`~streetworks.ogc.OGCFeaturesClient`.

**No pagination needed - confirmed live.** A ``GetFeature`` request with
no ``count`` parameter at all returns every real row in one response
(``numberReturned == totalFeatures``, 3,431), the same single-call shape
as this SDK's Hamburg/Brandenburg sources.

**CRS: native EPSG:3879 (ETRS-GK25FIN), not server-reprojected.** The WFS
*can* reproject to WGS84 on request (tested live, genuinely correct -
e.g. ``[25.044776, 60.276336]``, real Helsinki) - **not used here**, per
this SDK's standing CRS policy of carrying a source's native CRS through
explicitly rather than asking a server to reproject (the same call
Mallorca's own module docstring documents making, even though its WFS
offers the same capability). Real observed bounds (full pull): easting
25,490,716-25,512,946, northing 6,670,530-6,686,093.

**Two other real layers on this WFS, checked live and deliberately not
used here:**

- ``Kaivuilmoitus_piste`` (the point-geometry version, 16 real rows) -
  confirmed to be a **redundant subset**, not disjoint data: all 4 of its
  distinct ``hakemustunnus`` (application reference) values already
  appear in ``Kaivuilmoitus_alue``, and a direct row-for-row comparison
  (``KP2600928``) shows identical dates/status/address between the point
  and polygon rows for the same application - just an alternate point
  representation for a handful of applications that already have full
  polygon coverage. Using both would double-count real works.
- ``Tilapainen_liikennejarjestely_alue`` ("temporary traffic arrangement",
  342 real rows) - a genuinely different application type and schema
  (``liikennejarjestely_alkaa``/``_paattyy`` instead of
  ``tyo_alkaa``/``tyo_paattyy``, no ``toiminnallinen_kunto``). Related but
  structurally distinct - the same "found, not built this pass" treatment
  Oslo gave its own separate ``/plans`` endpoint.

**Licence: CC-BY-4.0, confirmed live** via the dataset's own CKAN
``package_show`` metadata (``license_id: "CC-BY-4.0"``) - a clean,
confirmed-open licence, no hedging required, the same confidence level
as Copenhagen's.

**No credentials required** - every claim above came from a fully
unauthenticated GetFeature request.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ..ogc.client import OGCFeaturesClient

__all__ = ["BASE_URL", "TYPE_NAME", "CRS", "HelsinkiClient"]

JSON = dict[str, Any]

#: GeoServer instance behind Helsinki Region Infoshare's own "Land usage
#: permission system for public areas" dataset - found via HRI's CKAN
#: package metadata, confirmed live. See module docstring.
BASE_URL = "https://kartta.hel.fi/ws/geoserver/avoindata/wfs"

#: The excavation-notification area layer - see module docstring for why
#: this is used instead of the point layer or the temporary-traffic-
#: arrangement layer.
TYPE_NAME = "avoindata:Kaivuilmoitus_alue"

#: ETRS-GK25FIN, the WFS's real native CRS - requested explicitly rather
#: than the shared client's own EPSG:4326 default. See module docstring
#: for why this isn't reprojected server-side.
CRS = "EPSG:3879"


class HelsinkiClient:
    """Fetch Helsinki's real excavation-notification (Kaivuilmoitus)
    permits from the City of Helsinki's GeoServer WFS. No credentials
    required.

    >>> from streetworks.helsinki import HelsinkiClient
    >>> from streetworks.common import from_helsinki
    >>> with HelsinkiClient() as helsinki:  # doctest: +SKIP
    ...     works = from_helsinki(helsinki.iter_roadworks())
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._ogc = OGCFeaturesClient(client=client)

    def iter_roadworks(self) -> Iterator[JSON]:
        """Every real excavation-notification feature - raw, ungrouped.
        See :func:`streetworks.common.from_helsinki` for the
        ``hakemustunnus``-grouping this SDK applies on top. One WFS
        request fetches everything - no pagination needed, see module
        docstring."""
        payload = self._ogc.get_wfs_features(BASE_URL, type_name=TYPE_NAME, srs_name=CRS)
        yield from payload.get("features") or ()

    def close(self) -> None:
        self._ogc.close()

    def __enter__(self) -> HelsinkiClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
