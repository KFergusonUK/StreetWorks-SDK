"""Jersey RoadWorkx - Jersey's roadworks ArcGIS Feature Service. This SDK's
first Channel Islands coverage.

**Service and layer, verified live, not assumed.** ``roadworks.gov.je``
publishes three real ArcGIS services: ``JSearch`` (address/place search,
not roadworks), ``JSWFeatureService`` (the real roadworks Feature Service,
also mirrored read-only as a ``JSW`` MapServer under the same layer
numbering), and ``JSYBaseMap`` (a basemap, not roadworks data - exactly as
the design brief suspected). ``JSWFeatureService``'s real layers: ``0
adhoc``, ``1 Signs``, ``2 Embargos``, **``3 RoadWorks``** (``esriGeometry
Polyline`` - the one this module uses), ``4 Projects``. ``Projects`` is a
related but distinct real layer (capital works records - ``PROJCONTRA``,
``JOBTYPE``, ``Contractor`` fields RoadWorks doesn't have, polygon
geometry) - noted, not consumed here; a future ``WorksPlanning``-shaped
strand could revisit it.

**Real field list** (``RoadWorks``, confirmed via layer metadata): ``FID``
(the real ``objectIdField``), ``NAME``, ``S_DATE``, ``E_DATE``, ``STATUS``,
``JOBID``, ``PROJID``, ``SHOW``, ``DESCRIPT``, ``ORG``, ``Promoter``,
``Location``, ``Type``, ``TIA``, ``Timing``, ``A``-``E`` (integers, real but
unlabelled - purpose not determinable from field metadata alone, kept in
``.raw``), ``WorkType``, ``Authority``.

**The real grouping structure - confirmed live, the same shape as Street
Manager's** ``work_reference_number``/``permit_reference_number``:
``NAME`` and ``PROJID`` are always identical (confirmed across every real
record sampled) and are the project-level key; ``JOBID`` is a distinct
per-record id, several of which share one ``PROJID`` (e.g. real project
``"P108864-JSC"`` covers ``JOBID`` 107263/107264/107265, three real
``RoadWorks`` records, same dates, same location). ``from_jersey`` groups
on ``PROJID`` into one :class:`~streetworks.common.Works` per project, one
:class:`~streetworks.common.WorksSite` per ``JOBID``.

**The planned/future dimension the brief asked about is a status value,
not a separate layer or type** - confirmed live: real ``STATUS`` values are
``"In Progress"``, ``"Finished"`` and **``"Pending"``** (a real, if
minority, value - the West-Berkshire-style "starting soon" case).
``from_jersey`` reads this directly into ``WorksSite.date_confidence``:
``Pending`` -> the dates are proposed (``ESTIMATED``); ``In Progress``/
``Finished`` -> the dates are real (``VERIFIED``). No separate "planned"
layer or type needed.

**CRS: "NewJTM" is EPSG:3109, confirmed live via two independent routes,**
not assumed from the design brief's own hedge ("believed to be"). First,
the ``RoadWorks``/``JSearch`` services state only a raw WKT with no
``wkid`` (``PROJCS["NewJTM", ... latitude_of_origin=49.225,
central_meridian=-2.135, scale_factor=0.9999999, false_easting=40000,
false_northing=70000 ...]``). Second, a sibling service on the exact same
ArcGIS deployment, ``JSYBaseMap``, states ``"wkid": 3109, "latestWkid":
3109`` directly for what is evidently the same real system. Third,
cross-checked EPSG:3109's own published WKT ("ETRS89 / Jersey Transverse
Mercator") against NewJTM's stated parameters - every one matches exactly.
**``outSR`` is not honoured by this service** - confirmed live: requesting
``outSR=4326`` returned coordinates byte-identical to a request with no
``outSR`` at all, still in NewJTM. So :data:`CRS` below is authoritative
for every real response this module fetches, not a request parameter to
trust.

**Pagination: this is the real, live-confirmed case the design brief's
truncation warning was written for.** ``RoadWorks``'s own metadata states
``advancedQueryCapabilities.supportsPagination: false`` - genuinely true,
not just a conservative default: a live ``resultOffset``/
``resultRecordCount`` request returns HTTP 200 with a page that *looks*
correct but is silently the same first page every time, at any offset
(confirmed at offsets 0/500/1000/2000/21000). The real total is **22,105**
records behind a ``maxRecordCount`` of 1,000 - under 5% would come back
from a naive one-shot query, with no error. ``FID > {n} ORDER BY FID``
genuinely works instead (confirmed live) -
:class:`~streetworks.arcgis.client.ArcGISFeatureClient.iter_features`
detects the broken offset-paging live and falls back to it automatically;
this module's own :meth:`JerseyRoadworksClient.iter_roadworks` inherits
that behaviour and was live-verified this session to retrieve all 22,105
real records with zero duplicates.

**Licence: no explicit statement found, treated as open for public
consumption per instruction.** The brief expected ``copyrightText`` to say
"Jersey Government" (not itself a licence); the real, live
``copyrightText`` on every service/layer checked (``JSWFeatureService``,
``JSW``, ``JSearch``, ``JSYBaseMap``) is an **empty string** - no statement
at all. Jersey's own CKAN open-data portal (``opendata.gov.je``) publishes
several datasets under "Open Government Licence - Jersey v1.0", but a live
search found **no roadworks dataset there at all** - this service isn't
catalogued as an open dataset, so that licence text cannot be cited as
covering it. The public-facing site (``roadworks.gov.je``) redirects
anonymous visitors to a login page, even though the ArcGIS REST API
underneath is reachable without any authentication. None of that amounts to
a found licence - it's still genuinely unconfirmed in the sense of "no
document says so" - but the service is openly, unauthenticatedly queryable
by design, and this SDK's maintainer has confirmed Jersey's data is
intended for open public consumption, the same basis Autobahn GmbH's
roadworks shipped on. Real, live-captured records are committed as test
fixtures on that basis (``tests/fixtures/jersey_roadworks_real.json``), not
synthetic ones. Confirm your own reuse/redistribution rights before
redistributing data pulled through this module further downstream.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .client import ArcGISFeatureClient

__all__ = ["BASE_URL", "ROADWORKS_LAYER", "PROJECTS_LAYER", "CRS", "JerseyRoadworksClient"]

JSON = dict[str, Any]

BASE_URL = "https://roadworks.gov.je/arcgis/rest/services/JSWFeatureService/FeatureServer"

#: The real roadworks layer - esriGeometryPolyline. See module docstring.
ROADWORKS_LAYER = 3

#: A related, distinct real layer (capital works/projects) - not consumed
#: by :func:`streetworks.common.from_jersey`. See module docstring.
PROJECTS_LAYER = 4

#: EPSG:3109 "ETRS89 / Jersey Transverse Mercator" - confirmed live, see
#: module docstring for the verification chain. ``outSR`` is not honoured
#: by this service (also confirmed live), so every real response is in
#: this CRS regardless of what's requested - this constant is
#: authoritative, not a hint.
CRS = "EPSG:3109"


class JerseyRoadworksClient:
    """Fetch Jersey RoadWorkx records. No credentials required - the
    ArcGIS REST API is reachable without authentication even though the
    human-facing site gates behind a login (see module docstring).

    >>> from streetworks.arcgis.jersey import JerseyRoadworksClient
    >>> from streetworks.common import from_jersey
    >>> with JerseyRoadworksClient() as jersey:  # doctest: +SKIP
    ...     works_list = from_jersey(list(jersey.iter_roadworks()))
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_roadworks(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Yield every real ``RoadWorks`` feature (GeoJSON ``Feature``
        dicts), paged correctly - see the module and
        :mod:`streetworks.arcgis.client` docstrings for why this layer
        needs the object-id-range fallback, not ``resultOffset``. Live-
        verified this session to retrieve all 22,105 real records with
        zero duplicates."""
        yield from self._arcgis.iter_features(
            BASE_URL, ROADWORKS_LAYER, where=where, out_fields="*"
        )

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> JerseyRoadworksClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
