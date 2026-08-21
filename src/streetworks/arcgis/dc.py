"""Washington, DC - DDOT Construction Permits, over the District's own
ArcGIS REST deployment. This SDK's first standalone Washington DC
coverage (separate from the WZDx/CWZ US registry - DC has no row there
at all).

**Service and layer, verified live, not assumed.** ``maps2.dcgis.dc.gov``
publishes a ``FEEDS/DDOT`` MapServer with a real family of permit layers:
**Construction Permit** and Occupancy Permit (each split into a rolling
``Last 30 Days`` layer plus year-by-year archives back to 2012), plus
Emergency Work Request, Valet Parking, and Non-Permit/Permit Inspection.
This module uses only the Construction Permit "Last 30 Days" layer
(:data:`CONSTRUCTION_PERMIT_LAYER`) - DDOT's real public-space excavation/
paving/landscaping/projections/fixture/rental permit, confirmed live to be
genuinely street/right-of-way work (``ISEXCAVATION`` true on ~80% of a
real 1,000-record sample), not general building-permit data - a real,
checked distinction, not assumed from the layer's name alone (an earlier
lead in this same session, a generically-named "Construction_Permits"
ArcGIS table, turned out on inspection to be Boulder, Colorado building
permits with no relation to DC at all - this module's own layer was
confirmed by reading real sample records, not by name matching).
Occupancy Permit is a related but distinct real layer - it also covers
non-construction public-space use (a real sampled record: "Panda Fest DC",
``EVENTTYPESCODEDESC="Other Special Events"``) cross-referenced to
Construction Permit only when applicable (``CONSTRUCTIONPERMITNUMBER``) -
not consumed here, the same "related but distinct, noted not consumed"
treatment :mod:`streetworks.arcgis.jersey` gives its own ``Projects``
layer.

**Real field list** (Construction Permit, confirmed via layer metadata and
live sample records): ``PERMITNUMBER``/``TRACKINGNUMBER`` (the real
identifier pair, ``PERMITNUMBER`` = ``"PA" + TRACKINGNUMBER`` on every
record sampled), ``STATUS`` (10 real distinct values confirmed live:
``Pending Assignment``, ``Assigned``, ``Resubmitted``, ``Not Paid``,
``Revise and Resubmit``, ``Approved (Pending Payment)``, ``Issued``,
``Permit Expired``, ``Cancel/Withdrawn``, ``Denied``), ``WLFULLADDRESS``,
``PERMITTEENAME``/``OWNERNAME``/``CONTRACTORNAME``/
``APPLICANTCOMPANYNAME`` (four distinct real name fields - kept apart, not
merged), ``WORKDETAIL`` (real free-text description), six real boolean
work-type flags stored as the strings ``"T"``/``"F"`` -
``ISEXCAVATION``/``ISPAVING``/``ISLANDSCAPING``/``ISPROJECTIONS``/
``ISFIXTURE``/``ISPSRENTAL`` (public-space rental) - confirmed live not
mutually exclusive (a real sample: ``('ISFIXTURE', 'ISPAVING',
'ISLANDSCAPING', 'ISPROJECTIONS')`` together on 10/1000 records) and not
always any true at all (60/1000 real records had every flag false).
``APPLICATIONDATE``/``INTAKEDATE``/``ISSUEDATE``/``EFFECTIVEDATE``/
``EXPIRATIONDATE``/``READYFORREVIEWDATE`` - real Esri date fields, epoch
milliseconds even under ``f=geojson`` (confirmed live - GeoJSON export
does not convert Esri date fields to ISO 8601 strings on this service).

**Geometry is genuine WGS84 under ``f=geojson``** - confirmed live (a real
returned pair, ``[-77.09026993519073, 38.95230917202083]``, correct for
DC), despite the layer's own stated native ``spatialReference`` being
``EPSG:26985`` (NAD83 / Maryland, meters) - the same "GeoJSON export can
be trusted per-service, but only once actually checked" situation
:mod:`streetworks.arcgis.tigerweb` documents, the opposite of Jersey's own
native-CRS-regardless-of-``outSR`` case. Real ``LATITUDE``/``LONGITUDE``
attribute fields are also present and separately populated (confirmed
live to match the geometry) - kept on ``.raw`` only, not re-derived from,
since the GeoJSON geometry is already the real WGS84 point.

**Pagination: the layer's own metadata omits ``objectIdField`` entirely**
(confirmed live: ``None``) despite a real, populated ``OBJECTID`` on every
feature and ``advancedQueryCapabilities.supportsPagination: true`` stated
- :class:`~streetworks.arcgis.client.ArcGISFeatureClient.iter_features`
doesn't trust either signal blindly (see its own module docstring); this
session live-verified offset-paging genuinely works here (all 3,453 real
"Last 30 Days" records retrieved, zero duplicate ``OBJECTID`` values), so
no fallback path is exercised for this particular layer.

**Licence: Creative Commons Attribution 4.0 International**, confirmed
live via ``opendata.dc.gov``'s own dataset ``licenseInfo`` metadata (the
District's standard open-data licence).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .client import ArcGISFeatureClient

__all__ = ["BASE_URL", "CONSTRUCTION_PERMIT_LAYER", "DCConstructionPermitsClient"]

JSON = dict[str, Any]

BASE_URL = "https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DDOT/MapServer"

#: "Construction Permit - Last 30 Days" - a rolling current-state layer,
#: not one of the year-by-year archive layers on the same service (2012
#: onward) - matching this SDK's usual "current state" scope. See module
#: docstring.
CONSTRUCTION_PERMIT_LAYER = 12


class DCConstructionPermitsClient:
    """Fetch DDOT's real Construction Permit records. No credentials
    required.

    >>> from streetworks.arcgis.dc import DCConstructionPermitsClient
    >>> from streetworks.common import from_dc
    >>> with DCConstructionPermitsClient() as dc:  # doctest: +SKIP
    ...     works_list = from_dc(list(dc.iter_roadworks()))
    """

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._arcgis = ArcGISFeatureClient(client=client)

    def iter_roadworks(self, *, where: str = "1=1") -> Iterator[JSON]:
        """Yield every real Construction Permit feature (GeoJSON
        ``Feature`` dicts) from the rolling 30-day layer, paged
        correctly - see module docstring."""
        yield from self._arcgis.iter_features(
            BASE_URL, CONSTRUCTION_PERMIT_LAYER, where=where, out_fields="*"
        )

    def close(self) -> None:
        self._arcgis.close()

    def __enter__(self) -> DCConstructionPermitsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
