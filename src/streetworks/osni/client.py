"""Northern Ireland: OSNI (Ordnance Survey Northern Ireland) Open Data -
Gazetteer - Streetnames. This SDK's first Northern Ireland gazetteer
coverage - a jurisdiction-distinct entry, the same treatment Jersey and
Scotland already get, never folded under a generic "UK" territory.

.. attention::
   **Confirmed live (2026-08-16)** against a real, unauthenticated bulk
   download (25,643 real features at time of writing).

**Not built the way this was originally scoped - the documented ArcGIS
REST MapServer endpoint is genuinely down, not just a stale URL.**
`services.spatialni.gov.uk` (the real, documented REST host, confirmed
from data.gov.uk's own dataset metadata) redirects every request -
`GetCapabilities`, a plain root probe, everything tried - to
`holdingpage.nics.gov.uk`, a Northern Ireland Civil Service holding page
that itself doesn't respond. Confirmed systemic across the whole domain,
not one stale path. So this module does **not** reuse
`streetworks.arcgis` (the shared ArcGIS Feature/Map Service client
Jersey/TIGERweb use) - there is no live REST service to point it at
right now.

**What's live instead: a real bulk-download route, not the REST API.**
The same dataset is published as CSV/SHP/KML/GeoJSON via OpenDataNI
(`admin.opendatani.gov.uk`), confirmed live end-to-end - the download
URL itself 302s to a signed, time-limited Cloudflare R2 URL, which this
client follows rather than hardcoding (the signed URL expires; the
`admin.opendatani.gov.uk` resource URL is the stable one, the same
"stable, filename/UUID-resolved URL" discipline
:data:`streetworks.milano.client.MANOMISSIONE_URL` already established).

**A real, load-bearing CRS disagreement within this one file, found and
resolved, not assumed.** The GeoJSON's own top-level ``crs`` block states
WGS84 (`urn:ogc:def:crs:OGC:1.3:CRS84`), and its ``geometry.coordinates``
are real WGS84 lon/lat values - this specific download route reprojects
on the way out. But every real feature *also* carries separate
``X_Coord``/``Y_Coord`` properties, real Irish Grid values (magnitude
`~334186, 377179`), not WGS84 and not the modern Irish Transverse
Mercator. This client uses ``X_Coord``/``Y_Coord``, not ``geometry`` -
the native Irish Grid value, not the reprojected one, per this SDK's
standing "never silently reproject" discipline.

**`EPSG:29902` (TM65 / Irish Grid), corrected from an initial
`EPSG:29903` guess once better live evidence existed - a real example of
this SDK revising a label rather than defending a first guess.** OSNI's
own REST endpoint, which would state `spatialReference.wkid` directly,
is still down (see above), so this dataset's own CRS still can't be
read live. But a directly comparable, same-jurisdiction service
(`streetworks.dfi_roads`' real ArcGIS FeatureServer, checked the same
week, coordinates in the same numeric range) states its own
`spatialReference` explicitly as `{"wkid": 29900, "latestWkid": 29902}`
- `29900` (TM65 / Irish National Grid) is EPSG-deprecated in favour of
`29902` (TM65 / Irish Grid), confirmed via the EPSG registry itself, not
assumed. The originally-guessed `29903` (TM75 / Irish Grid) is a real,
different, later code (geodetically near-identical per Irish
authorities, but formally distinct) - `29902` is the better-evidenced
label for Northern Ireland government Irish Grid data specifically,
still not a direct live read of *this* dataset's own declared CRS.

**A real, live-confirmed `USRN` field - genuinely surprising, kept
rather than dropped, but scoped honestly.** Every one of 25,643 real
features carries a populated, unique `USRN` value (range 2-372,710) -
confirmed 100% populated, 100% distinct, not a coincidence. Northern
Ireland is not part of GB's national USRN/NSG (National Street
Gazetteer) scheme, so this is **not** presented as a cross-referencing
national USRN - it is OSNI's own field, real and load-bearing within
this dataset, promoted as a scoped identifier
(`Identifier(scheme="usrn", scope="OSNI")`) rather than silently
dropped or conflated with the GB scheme.

**A small, real content quirk, not filtered out.** 7 of 25,643 real
`STREETNAME` values are road numbers (`A0002`, `M2`, `M3`, `M5`, `M12`,
`M22`), not street names - genuine content this dataset states, kept
as-is rather than excluded, per this SDK's "never drop real data" rule.

**No credentials.** Licence: **Open Government Licence v3.0**, confirmed
live from the dataset's own CKAN metadata (`license_title`).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport
from .models import Streetname

__all__ = ["BASE_URL", "OsniStreetnamesClient"]

JSON = dict[str, Any]

#: The stable OpenDataNI resource-download URL for "OSNI Open Data -
#: Gazetteer - Streetnames" - resolves through a signed, time-limited
#: redirect (followed automatically), not hardcoded itself. See module
#: docstring for why this route is used instead of the (currently down)
#: ArcGIS REST MapServer endpoint.
BASE_URL = (
    "https://admin.opendatani.gov.uk/dataset/"
    "8b3953f1-da42-4d98-b2b9-311e7c9c8075/resource/"
    "ce3e70dc-92f3-4107-87eb-aaa89f2690ce/download/"
    "osni_open_data_-_gazetteer_-_streetnames.geojson"
)


def _to_streetname(feature: JSON) -> Streetname:
    props: JSON = feature.get("properties") or {}
    return Streetname(
        streetname=str(props.get("STREETNAME", "")),
        usrn=int(props["USRN"]),
        objectid=int(props["OBJECTID"]),
        easting=float(props["X_Coord"]),
        northing=float(props["Y_Coord"]),
        raw=props,
    )


class OsniStreetnamesClient:
    """Fetch Northern Ireland's real OSNI Streetnames gazetteer. No
    credentials required.

    >>> from streetworks.osni import OsniStreetnamesClient
    >>> from streetworks.common import from_osni
    >>> with OsniStreetnamesClient() as osni:  # doctest: +SKIP
    ...     streets = [from_osni(s) for s in osni.iter_streetnames()]
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

    def iter_streetnames(self) -> Iterator[Streetname]:
        """Every real street name + representative point - raw,
        unfiltered (includes the small number of road-number entries,
        see module docstring)."""
        response = self._transport.request("GET", BASE_URL)
        body = response.json()
        for feature in body.get("features") or []:
            yield _to_streetname(feature)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> OsniStreetnamesClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
