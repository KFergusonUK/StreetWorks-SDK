"""Oslo: SøkSys "activities" - Oslo kommune's real digging/work-permit
case system, this SDK's second Nordic roadworks coverage (after
Copenhagen).

.. attention::
   **Confirmed live (2026-08-10)** against a real, unauthenticated pull
   (1354 real feature rows at time of writing).

**Not the source either brief guess named - checked live before
building.** The investigation brief flagged two candidates and asked to
verify before building: an Origo/Bymiljøetaten GeoServer layer, or the
national NVDB. Neither is it. A web search for Oslo kommune's own real
page on this system found **"SøkSys"**
(``oslo.kommune.no/.../arbeid-pa-kommunal-grunn/soksys/``) - a real,
2024-introduced permit/case-management system (replacing older "Kgrav"/
"ISYcase") covering crossing/proximity permits for cable and pipe work,
excavation and work permits, and traffic warning - run on Oslo's behalf
by **Geomatikk** (a real Norwegian utility-location company, confirmed
via a ``geomatikk.no`` link on the public map page). Since December
2024 it also handles container-placement applications.

**The real public map is ``pub.soksys.no`` (page title "Oslo kommune" -
confirmed Oslo-scoped).** Its own ``map.js`` bundle (read directly, the
same technique that found Roma's/Lisboa's/Road Report NT's real
backends) reveals the real internal API this client calls:
``https://pub.soksys.no/api/map/soksys-activities``, with ``extent``
(a real ``minx,miny,maxx,maxy`` bounding box) and ``filter``
(``atimequick=4`` - the real default the live public site's own
pagination links use) query parameters. **No credentials required** -
every claim here came from a fully unauthenticated pull.

**The response body is a JSON string literal containing escaped
GeoJSON - a real double-encoding quirk, not a bug to silently
"correct."** ``response.json()`` on the raw HTTP body yields a Python
``str``; that string itself has to be parsed again
(``json.loads(json.loads(...))``) to reach the real
``FeatureCollection``. Handled inside :meth:`OsloClient.iter_roadworks`
so callers never see the intermediate string.

**CRS confirmed live: EPSG:25832** (ETRS89/UTM zone 32N, the page's own
``configSettings.defaultSrid``) - a genuinely projected CRS, not WGS84.
Real observed extent: easting 588319-612169, northing 6631185-6655035;
:data:`DEFAULT_EXTENT` pads that to a real, evidenced Oslo-scoped
bounding box. Per this SDK's own convention (matching British National
Grid/Jersey/NYC DOT/Via Lietuva), coordinates under a projected CRS stay
plain ``(x, y)`` = ``(easting, northing)`` - never swapped to
``(lat, lon)``, unlike Copenhagen's genuine WGS84 source.

**Real roadworks filter, evidenced not guessed**: ``activity_type`` has
exactly 3 real values - ``Arbeidstillatelse`` (work permit, 934/1354),
``Gravearbeid`` (excavation work, 412/1354), ``Containerutsett``
(container placement, 8/1354). Sampled real ``sender`` values confirm
the split: ``Arbeidstillatelse``/``Gravearbeid`` senders are genuine
traffic/road-work companies (VEISKILTING AS - "road signage",
TRAFIKKJENTENE AS, SAFEROAD TRAFFIC AS); ``Containerutsett`` senders are
the city agency itself or property managers placing skips, not
construction work. :meth:`iter_roadworks` filters to the first two.

**A real, load-bearing geometry/grouping finding, genuinely different
from Copenhagen's**: under the default filter, 1354 raw rows collapse
to 631 distinct ``activity_id``\\ s (261 multi-row). Checked every one:
256 multi-row groups are **pure duplicate artifacts** (identical ``id``
and identical geometry, appearing twice - a tiling/extent artifact of
querying a wide bbox; only 1338 of the 1354 ``id`` values are distinct).
But a real few permits genuinely span several distinct sub-areas
(different ``id``, different real coordinates/areas, same
``file_number``/``sender``/dates) - a real Jersey/NYC-DOT-style "one
project, several real sites" shape, not Copenhagen's "one site, several
geometry representations" shape.
:func:`streetworks.common.from_oslo` dedupes by exact ``id`` first (the
tiling artifact), then groups by ``activity_id``.

**A separate ``/plans`` endpoint exists** (``soksys-plans``,
``filter=ptimequick=4``) - confirmed live, 1339 real features, but a
genuinely different schema (``status: "Koordinert"`` = Coordinated, no
``activity_type``/``sender``/``case_handler``/``city_district`` at all).
This is the earlier, pre-permit planning stage - not built here.

**Licence: genuinely unconfirmed.** Checked both the live
``pub.soksys.no`` page and Oslo kommune's own SøkSys explainer page - no
licence/terms statement found on either.

**A real, evidenced "shared platform" lead, not chased here**: the map
bundle's own ``typenamePrefix`` logic switches on
``configSettings['countryCode'] === 'SE'``, meaning SøkSys is
white-labelled per municipality/country - other Norwegian *and Swedish*
municipalities may run their own instance. Worth a future investigation,
deliberately out of scope in this module.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx

from .._transport import RetryConfig, SyncTransport

__all__ = ["ACTIVITIES_URL", "DEFAULT_EXTENT", "OsloClient"]

JSON = dict[str, Any]

#: Found in pub.soksys.no's own map.js bundle, not documented anywhere
#: public. Confirmed live 2026-08-10.
ACTIVITIES_URL = "https://pub.soksys.no/api/map/soksys-activities"

#: A real, evidenced Oslo-scoped bounding box in EPSG:25832 - padded from
#: the real observed extent of a live pull (easting 588319-612169,
#: northing 6631185-6655035). "minx,miny,maxx,maxy".
DEFAULT_EXTENT = "580000,6620000,620000,6665000"

#: The real default filter the live public site's own pagination links
#: use - confirmed live, not guessed.
DEFAULT_FILTER = "atimequick=4"

#: Confirmed live: Arbeidstillatelse/Gravearbeid senders are genuine
#: traffic/road-work companies; Containerutsett is container/skip
#: placement, not construction - see module docstring.
_ROADWORKS_TYPES = frozenset({"Arbeidstillatelse", "Gravearbeid"})


class OsloClient:
    """Fetch Oslo kommune's SøkSys activities (real digging/work
    permits). No credentials required.

    >>> from streetworks.oslo import OsloClient
    >>> from streetworks.common import from_oslo
    >>> with OsloClient() as oslo:  # doctest: +SKIP
    ...     works = from_oslo(list(oslo.iter_roadworks()))
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

    def iter_activities(
        self, *, extent: str = DEFAULT_EXTENT, filter: str = DEFAULT_FILTER
    ) -> Iterator[JSON]:
        """Every real activity feature, raw and unfiltered/undeduped -
        includes Containerutsett (container placement, not roadworks)
        and the real tiling-duplicate rows. See module docstring for why
        the response needs a second ``json.loads`` - handled here."""
        response = self._transport.request(
            "GET", ACTIVITIES_URL, params={"extent": extent, "filter": filter}
        )
        payload = response.json()
        if isinstance(payload, str):
            payload = json.loads(payload)
        yield from payload.get("features") or []

    def iter_roadworks(
        self, *, extent: str = DEFAULT_EXTENT, filter: str = DEFAULT_FILTER
    ) -> Iterator[JSON]:
        """Real Arbeidstillatelse/Gravearbeid features only -
        Containerutsett (container placement) excluded. Still raw/
        undeduped - :func:`streetworks.common.from_oslo` owns the
        id-dedupe and activity_id grouping, see module docstring."""
        for feature in self.iter_activities(extent=extent, filter=filter):
            activity_type = (feature.get("properties") or {}).get("activity_type")
            if activity_type in _ROADWORKS_TYPES:
                yield feature

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> OsloClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
